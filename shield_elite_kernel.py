import json
import hashlib
import os
from datetime import datetime, timezone


class ShieldEliteKernel:
    def __init__(self, hsm_vault, ntp_service, policy_bundle, storage_path="./test_store"):
        self.hsm_vault = hsm_vault
        self.hsm = hsm_vault
        self.ntp_service = ntp_service
        self.ntp = ntp_service
        self.policy_bundle = policy_bundle
        self.policy = policy_bundle

        self.engine_version = "33.6.2-SOVEREIGN-GOLD-HARDENED"
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        self.event_store_path = os.path.join(self.storage_path, "shield_events.jsonl")

    # -------------------------
    # basic helpers
    # -------------------------

    def _trusted_time(self):
        if self.ntp_service is not None and hasattr(self.ntp_service, "get_trusted_time"):
            return self.ntp_service.get_trusted_time()
        return datetime.now(timezone.utc).isoformat()

    def _canonical_json(self, payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def _sha256(self, payload):
        if isinstance(payload, str):
            raw = payload.encode("utf-8")
        else:
            raw = self._canonical_json(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _append_event(self, event):
        with open(self.event_store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    def _load_events(self):
        if not os.path.exists(self.event_store_path):
            return []

        rows = []
        with open(self.event_store_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    # -------------------------
    # user / input validation
    # -------------------------

    def _check_user_consent(self, user):
        if user is None:
            return False

        accepted_at_utc = getattr(user, "accepted_at_utc", None)
        terms_hash = getattr(user, "terms_hash", None)
        expected_terms_hash = getattr(self.policy_bundle, "expected_terms_hash", "EXPECTED_HASH")

        if hasattr(user, "has_signed_terms"):
            signed = bool(user.has_signed_terms(getattr(self.policy_bundle, "version", "TEST_POLICY_V1")))
        else:
            signed = bool(getattr(user, "_signed", False))

        return bool(accepted_at_utc) and terms_hash == expected_terms_hash and signed

    def _fit_endpoint_elite_consistent(self, df, endpoint):
        if endpoint not in {"AUC", "CMAX"}:
            raise Exception("UNSUPPORTED_ENDPOINT")

        required = {"subject", "sequence", "period", "treatment", "value"}
        missing = required - set(df.columns)
        if missing:
            raise Exception(f"MISSING_COLUMNS:{sorted(missing)}")

        if (df["value"] < 0).any():
            raise Exception("NEGATIVE_VALUES_NOT_ALLOWED")

        if not df["treatment"].isin([0, 1]).all():
            raise Exception("TREATMENT_AMBIGUITY")

        return True

    def _extract_rows(self, audit_input):
        auc_rows = []
        cmax_rows = []

        if hasattr(audit_input, "auc_df") and audit_input.auc_df is not None:
            self._fit_endpoint_elite_consistent(audit_input.auc_df, "AUC")
            auc_rows = audit_input.auc_df.to_dict(orient="records")

        if hasattr(audit_input, "cmax_df") and audit_input.cmax_df is not None:
            self._fit_endpoint_elite_consistent(audit_input.cmax_df, "CMAX")
            cmax_rows = audit_input.cmax_df.to_dict(orient="records")

        return auc_rows, cmax_rows

    # -------------------------
    # dossier / manifest / integrity
    # -------------------------

    def _build_manifest_core(self, auc_rows, cmax_rows, user):
        return {
            "engine_version": self.engine_version,
            "policy_version": getattr(self.policy_bundle, "version", "TEST_POLICY_V1"),
            "expected_terms_hash": getattr(self.policy_bundle, "expected_terms_hash", "EXPECTED_HASH"),
            "hsm_key_id": getattr(self.policy_bundle, "hsm_key_id", "KEY_001"),
            "signature_algorithm": getattr(self.policy_bundle, "signature_algorithm", "SHA256_RSA"),
            "user_terms_hash": getattr(user, "terms_hash", None),
            "auc_rows": auc_rows,
            "cmax_rows": cmax_rows,
        }

    def _build_dossier(self, user, audit_input):
        auc_rows, cmax_rows = self._extract_rows(audit_input)

        manifest_core = self._build_manifest_core(auc_rows, cmax_rows, user)
        manifest_hash = self._sha256(manifest_core)
        signature = self.hsm.sign_canonical_digest(manifest_hash)

        manifest = dict(manifest_core)
        manifest["manifest_hash"] = manifest_hash

        dossier = {
            "generated_at_utc": self._trusted_time(),
            "manifest": manifest,
            "signature_packet": {
                "signature": signature,
                "algorithm": getattr(self.policy_bundle, "signature_algorithm", "SHA256_RSA"),
                "hsm_key_id": getattr(self.policy_bundle, "hsm_key_id", "KEY_001"),
            },
        }
        dossier["dossier_hash"] = self._sha256(
            {
                "manifest_hash": manifest_hash,
                "signature": signature,
            }
        )
        return dossier

    def _verify_internal_integrity_complete(self, dossier):
        try:
            manifest = dossier["manifest"]
            signature_packet = dossier["signature_packet"]

            manifest_core = dict(manifest)
            manifest_hash = manifest_core.pop("manifest_hash")
            recomputed_manifest_hash = self._sha256(manifest_core)
            manifest_ok = manifest_hash == recomputed_manifest_hash

            signature_ok = self.hsm.verify_signature(
                manifest_hash,
                signature_packet["signature"],
            )

            expected_dossier_hash = self._sha256(
                {
                    "manifest_hash": manifest_hash,
                    "signature": signature_packet["signature"],
                }
            )
            dossier_ok = dossier.get("dossier_hash") == expected_dossier_hash

            ok = manifest_ok and signature_ok and dossier_ok
            details = {
                "manifest_ok": manifest_ok,
                "signature_ok": signature_ok,
                "dossier_ok": dossier_ok,
            }
            return ok, details
        except Exception as exc:
            return False, {"error": str(exc)}

    # -------------------------
    # pipeline
    # -------------------------

    def execute_elite_pipeline_ultimate(self, user, audit_input):
        if not self._check_user_consent(user):
            return {
                "status": "REJECTED",
                "gate": {
                    "consent_ok": False,
                    "release_ok": False,
                },
            }

        dossier = self._build_dossier(user, audit_input)

        ok, integrity = self._verify_internal_integrity_complete(dossier)
        if not ok:
            return {
                "status": "CRITICAL_ERROR",
                "dossier": dossier,
                "gate": {
                    "consent_ok": True,
                    "release_ok": False,
                },
                "integrity": integrity,
            }

        previous_events = self._load_events()
        replay_seen_before = any(
            e.get("dossier_hash") == dossier["dossier_hash"] for e in previous_events
        )

        gate = {
            "consent_ok": True,
            "release_ok": True,
            "replay_seen_before": replay_seen_before,
        }

        event = {
            "event": "SHIELD_CERTIFICATION",
            "timestamp": self._trusted_time(),
            "engine_version": self.engine_version,
            "policy_version": getattr(self.policy_bundle, "version", "TEST_POLICY_V1"),
            "dossier_hash": dossier["dossier_hash"],
            "manifest_hash": dossier["manifest"]["manifest_hash"],
        }
        self._append_event(event)

        audit_core = {
            "dossier_hash": dossier["dossier_hash"],
            "manifest_hash": dossier["manifest"]["manifest_hash"],
            "release_ok": gate["release_ok"],
            "replay_seen_before": gate["replay_seen_before"],
            "event_hash": self._sha256(event),
        }
        audit = dict(audit_core)
        audit["report_hash"] = self._sha256(audit_core)

        return {
            "status": "CERTIFIED",
            "engine_version": self.engine_version,
            "policy_version": getattr(self.policy_bundle, "version", "TEST_POLICY_V1"),
            "dossier": dossier,
            "gate": gate,
            "event": event,
            "audit": audit,
        }
