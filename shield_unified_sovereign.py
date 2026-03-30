import json
import uuid
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


# ============================================================
# CORE HELPERS
# ============================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def canonical_hash(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


# ============================================================
# SIMPLE SCHEMAS
# ============================================================

@dataclass
class SimpleSchema:
    schema_name: str
    required_fields: List[str]


DOSSIER_SCHEMA = SimpleSchema(
    schema_name="dossier",
    required_fields=[
        "case_id",
        "results",
        "manifest",
        "signature_packet",
        "chain_head",
        "lineage",
        "dossier_hash",
    ],
)

MANIFEST_SCHEMA = SimpleSchema(
    schema_name="manifest",
    required_fields=["artifacts", "manifest_hash"],
)

SIGNATURE_PACKET_SCHEMA = SimpleSchema(
    schema_name="signature_packet",
    required_fields=["signature", "key_id", "algorithm", "signed_at_utc", "attestation_ref", "packet_hash"],
)

LINEAGE_SCHEMA = SimpleSchema(
    schema_name="lineage",
    required_fields=["case_id", "nodes", "edges", "created_at_utc", "lineage_hash"],
)


# ============================================================
# POLICY
# ============================================================

@dataclass
class PolicyBundle:
    version: str
    expected_terms_hash: str
    hsm_key_id: str
    signature_algorithm: str
    thresholds: Dict[str, float]


class PolicyEngine:
    def __init__(self, policy_bundle: PolicyBundle):
        self.policy = policy_bundle

    def threshold(self, name: str, default: float) -> float:
        return float(self.policy.thresholds.get(name, default))


# ============================================================
# STORE / EVIDENCE
# ============================================================

class AppendOnlyEventStore:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.write_text("", encoding="utf-8")

    def append(self, record: Dict[str, Any]) -> None:
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(canonical_json(record) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        rows = []
        with self.filepath.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows


class ShieldVerifiedStore:
    def __init__(self, event_store: AppendOnlyEventStore, hash_fn):
        self.event_store = event_store
        self.hash_fn = hash_fn

    def append_verified(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.event_store.append(record)
        rows = self.event_store.read_all()

        if not rows:
            raise RuntimeError("STORE_EMPTY_AFTER_APPEND")

        last = rows[-1]
        if last.get("event_hash") != record.get("event_hash"):
            raise RuntimeError("STORE_ROUNDTRIP_EVENT_HASH_MISMATCH")

        report = {
            "write_verified": True,
            "event_hash": record["event_hash"],
            "checked_at": utc_now(),
        }
        report["integrity_hash"] = self.hash_fn({k: v for k, v in report.items() if k != "integrity_hash"})
        return report


class ShieldEvidenceRegistry:
    def __init__(self, base_path="./forensic_store"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_path / "evidence_registry.jsonl"
        if not self.registry_path.exists():
            self.registry_path.write_text("", encoding="utf-8")

    def register_artifact(self, kind: str, payload: Dict[str, Any], hash_fn) -> Dict[str, Any]:
        record = {
            "evidence_id": str(uuid.uuid4()),
            "kind": kind,
            "ts": utc_now(),
            "payload": payload,
        }
        record["evidence_hash"] = hash_fn({k: v for k, v in record.items() if k != "evidence_hash"})

        with self.registry_path.open("a", encoding="utf-8") as f:
            f.write(canonical_json(record) + "\n")

        return record


# ============================================================
# BUILDERS / VALIDATORS
# ============================================================

def validate_design_strict_plus(df: pd.DataFrame, label: str) -> pd.DataFrame:
    required = {"subject", "sequence", "period", "treatment", "value"}
    if not required.issubset(df.columns):
        raise ValueError(f"SCHEMA_FAIL::{label}")

    work = df.copy()
    work["value"] = pd.to_numeric(work["value"], errors="raise").astype(float)

    if (work["value"] <= 0).any():
        raise ValueError(f"NON_POSITIVE_VALUES::{label}")

    if work["subject"].nunique() < 2:
        raise ValueError(f"INSUFFICIENT_SUBJECTS::{label}")

    if work["treatment"].nunique() < 2:
        raise ValueError(f"INSUFFICIENT_TREATMENT_LEVELS::{label}")

    if work["period"].nunique() < 2:
        raise ValueError(f"INSUFFICIENT_PERIOD_LEVELS::{label}")

    return work


def sanity_check_be_result(result: Dict[str, Any], label: str):
    if "ci_90" not in result or len(result["ci_90"]) != 2:
        raise RuntimeError(f"SANITY_FAIL::{label}::CI")

    if result["ci_90"][0] <= 0 or result["ci_90"][1] <= 0:
        raise RuntimeError(f"SANITY_FAIL::{label}::NON_POSITIVE_CI")

    if result["ci_90"][0] > result["ci_90"][1]:
        raise RuntimeError(f"SANITY_FAIL::{label}::CI_ORDER")

    if "gmr" not in result or result["gmr"] <= 0:
        raise RuntimeError(f"SANITY_FAIL::{label}::GMR")


def build_signature_packet(signature: str, key_id: str, algorithm: str, signed_at_utc: str) -> Dict[str, Any]:
    packet = {
        "signature": signature,
        "key_id": key_id,
        "algorithm": algorithm,
        "signed_at_utc": signed_at_utc,
        "attestation_ref": str(uuid.uuid4()),
    }
    packet["packet_hash"] = canonical_hash({k: v for k, v in packet.items() if k != "packet_hash"})
    return packet


def build_manifest(results, replay_package, consent_bundle, dq_trace, policy, engine_version, ts):
    artifacts = {
        "results": results,
        "replay_package": replay_package,
        "consent_bundle": consent_bundle,
        "dq_trace": dq_trace,
        "config_hash": canonical_hash({
            "policy_version": policy.version,
            "thresholds": policy.thresholds,
        }),
        "system_meta": {
            "engine_version": engine_version,
            "policy_version": policy.version,
            "timestamp": ts,
        },
    }
    return {
        "artifacts": artifacts,
        "manifest_hash": canonical_hash(artifacts),
    }


def build_lineage(case_id, input_hashes, results_hash, manifest_hash, provisional_dossier_hash):
    lineage = {
        "case_id": case_id,
        "nodes": {
            "input_hashes": input_hashes,
            "results_hash": results_hash,
            "manifest_hash": manifest_hash,
            "provisional_dossier_hash": provisional_dossier_hash,
        },
        "edges": [
            ["input_hashes", "results_hash"],
            ["results_hash", "manifest_hash"],
            ["manifest_hash", "provisional_dossier_hash"],
        ],
        "created_at_utc": utc_now(),
    }
    lineage["lineage_hash"] = canonical_hash({k: v for k, v in lineage.items() if k != "lineage_hash"})
    return lineage


def build_final_dossier(case_id, results, manifest, signature_packet, chain_head, lineage):
    dossier = {
        "case_id": case_id,
        "results": results,
        "manifest": manifest,
        "signature_packet": signature_packet,
        "chain_head": chain_head,
        "lineage": lineage,
    }
    dossier["dossier_hash"] = canonical_hash({k: v for k, v in dossier.items() if k != "dossier_hash"})
    return dossier


def build_forensic_event(case_id, event_type, payload, chain_head, engine_version, policy_version):
    event = {
        "case_id": case_id,
        "event_type": event_type,
        "payload": payload,
        "prev_hash": chain_head,
        "engine_version": engine_version,
        "policy_version": policy_version,
        "ts": utc_now(),
    }
    return {
        "event": event,
        "event_hash": canonical_hash(event),
    }


def build_replay_package(auc_df, cmax_df, results, policy, ts):
    def stable_df_hash(df):
        sort_cols = [c for c in ["subject", "sequence", "period", "treatment"] if c in df.columns]
        work = df.copy().sort_values(by=sort_cols).reset_index(drop=True)
        work = work.reindex(sorted(work.columns), axis=1)
        return canonical_hash(work.to_dict(orient="records"))

    package = {
        "input_hashes": {
            "auc": stable_df_hash(auc_df),
            "cmax": stable_df_hash(cmax_df),
        },
        "results_hash": canonical_hash(results),
        "policy_version": policy.version,
        "ts": ts,
    }
    package["replay_hash"] = canonical_hash({k: v for k, v in package.items() if k != "replay_hash"})
    return package


def build_consent_bundle(user, policy_version, ts):
    bundle = {
        "user_has_signed": bool(user.has_signed_terms(policy_version)),
        "accepted_at_utc": getattr(user, "accepted_at_utc", None),
        "terms_hash": getattr(user, "terms_hash", None),
        "policy_version": policy_version,
        "verified_at": ts,
    }
    bundle["consent_hash"] = canonical_hash({k: v for k, v in bundle.items() if k != "consent_hash"})
    return bundle


# ============================================================
# VERIFIERS / GATES
# ============================================================

class ShieldMultiStageVerifier:
    def __init__(self, hsm, hash_fn):
        self.hsm = hsm
        self.hash_fn = hash_fn

    def verify_dossier(self, dossier):
        try:
            if not all(f in dossier for f in DOSSIER_SCHEMA.required_fields):
                return False, {"error": "DOSSIER_INCOMPLETE"}

            if not all(f in dossier["manifest"] for f in MANIFEST_SCHEMA.required_fields):
                return False, {"error": "MANIFEST_INCOMPLETE"}

            if self.hash_fn(dossier["manifest"]["artifacts"]) != dossier["manifest"]["manifest_hash"]:
                return False, {"error": "MANIFEST_DRIFT"}

            sig = dossier["signature_packet"]
            if not all(f in sig for f in SIGNATURE_PACKET_SCHEMA.required_fields):
                return False, {"error": "SIGNATURE_PACKET_INCOMPLETE"}

            sig_body = {k: v for k, v in sig.items() if k != "packet_hash"}
            if self.hash_fn(sig_body) != sig["packet_hash"]:
                return False, {"error": "SIG_PACKET_TAMPERED"}

            if not self.hsm.verify_signature(dossier["manifest"]["manifest_hash"], sig["signature"]):
                return False, {"error": "HSM_SIGNATURE_INVALID"}

            body = {k: v for k, v in dossier.items() if k != "dossier_hash"}
            if self.hash_fn(body) != dossier["dossier_hash"]:
                return False, {"error": "DOSSIER_HASH_MISMATCH"}

            lineage = dossier["lineage"]
            if not all(f in lineage for f in LINEAGE_SCHEMA.required_fields):
                return False, {"error": "LINEAGE_INCOMPLETE"}

            lineage_body = {k: v for k, v in lineage.items() if k != "lineage_hash"}
            if self.hash_fn(lineage_body) != lineage["lineage_hash"]:
                return False, {"error": "LINEAGE_HASH_MISMATCH"}

            return True, {"status": "EXTERNAL_OK"}
        except Exception as e:
            return False, {"error": str(e)}


class ShieldReplayValidator:
    def __init__(self, hash_fn):
        self.hash_fn = hash_fn

    def validate(self, replay_package, auc_df, cmax_df, results):
        def stable_df_hash(df):
            sort_cols = [c for c in ["subject", "sequence", "period", "treatment"] if c in df.columns]
            work = df.copy().sort_values(by=sort_cols).reset_index(drop=True)
            work = work.reindex(sorted(work.columns), axis=1)
            return self.hash_fn(work.to_dict(orient="records"))

        checks = {
            "auc_hash_match": replay_package["input_hashes"]["auc"] == stable_df_hash(auc_df),
            "cmax_hash_match": replay_package["input_hashes"]["cmax"] == stable_df_hash(cmax_df),
            "results_hash_match": replay_package["results_hash"] == self.hash_fn(results),
        }
        ok = all(checks.values())
        report = {"checks": checks, "ts": utc_now()}
        report["report_hash"] = self.hash_fn({k: v for k, v in report.items() if k != "report_hash"})
        return ok, report


class ShieldReleaseGate:
    def __init__(self, hash_fn):
        self.hash_fn = hash_fn

    def evaluate(self, dossier_ok, store_ok, replay_ok, evidence_ok):
        payload = {
            "dossier_ok": bool(dossier_ok),
            "store_ok": bool(store_ok),
            "replay_ok": bool(replay_ok),
            "evidence_ok": bool(evidence_ok),
            "release_ok": bool(dossier_ok and store_ok and replay_ok and evidence_ok),
            "ts": utc_now(),
        }
        payload["release_gate_hash"] = self.hash_fn({k: v for k, v in payload.items() if k != "release_gate_hash"})
        return payload


# ============================================================
# MAIN KERNEL
# ============================================================

class DoodogUnifiedSovereign:
    def __init__(self, hsm_vault, ntp_service, policy_bundle: PolicyBundle, storage_path="./forensic_store"):
        self.engine_version = "35.1.0-UNIFIED-SOVEREIGN"
        self.hsm = hsm_vault
        self.ntp = ntp_service
        self.policy = policy_bundle
        self.policy_engine = PolicyEngine(policy_bundle)

        self.event_store = AppendOnlyEventStore(f"{storage_path}/event_log.jsonl")
        self.evidence = ShieldEvidenceRegistry(storage_path)
        self.verified_store = ShieldVerifiedStore(self.event_store, canonical_hash)

        records = self.event_store.read_all()
        self.chain_head = records[-1]["event_hash"] if records else "GENESIS_2026_BLOCK"

    def _stable_df_hash(self, df):
        sort_cols = [c for c in ["subject", "sequence", "period", "treatment"] if c in df.columns]
        work = df.copy().sort_values(by=sort_cols).reset_index(drop=True)
        work = work.reindex(sorted(work.columns), axis=1)
        return canonical_hash(work.to_dict(orient="records"))

    def _extract_treatment_term_safe(self, model, label):
        candidates = [n for n in model.params.index if n.startswith("C(treatment)")]
        if len(candidates) != 1:
            raise ValueError(f"TREATMENT_TERM_AMBIGUITY::{label}::{candidates}")
        return candidates[0]

    def _fit_endpoint(self, df, label):
        work = df.copy()
        work["log_val"] = np.log(work["value"])
        model = smf.ols(
            "log_val ~ C(sequence) + C(period) + C(treatment) + C(subject)",
            data=work
        ).fit()

        t_term = self._extract_treatment_term_safe(model, label)

        be_lower = self.policy_engine.threshold("be_lower", 80.0)
        be_upper = self.policy_engine.threshold("be_upper", 125.0)
        cooks_th = self.policy_engine.threshold("cooks", 1.0)
        lev_th = self.policy_engine.threshold("leverage", 0.5)

        ci_raw = model.conf_int(alpha=0.10).loc[t_term]
        ci_90 = [
            round(float(np.exp(ci_raw.iloc[0]) * 100.0), 2),
            round(float(np.exp(ci_raw.iloc[1]) * 100.0), 2),
        ]

        infl = model.get_influence()
        mc = float(np.max(infl.cooks_distance[0])) if len(infl.cooks_distance[0]) else 0.0
        ml = float(np.max(infl.hat_matrix_diag)) if len(infl.hat_matrix_diag) else 0.0

        flags = []
        if mc > cooks_th:
            flags.append("HIGH_COOKS")
        if ml > lev_th:
            flags.append("HIGH_LEVERAGE")

        result = {
            "endpoint": label,
            "gmr": round(float(np.exp(model.params[t_term]) * 100.0), 2),
            "ci_90": ci_90,
            "pass_be": (ci_90[0] >= be_lower and ci_90[1] <= be_upper),
            "inspection": {
                "max_cooks": round(mc, 4),
                "max_leverage": round(ml, 4),
                "flags": flags,
                "reason_codes": flags[:],
            },
            "diagnostics": {
                "aic": round(float(model.aic), 2),
                "bic": round(float(model.bic), 2),
                "df_resid": int(model.df_resid),
                "treatment_term": t_term,
            }
        }
        sanity_check_be_result(result, label)
        return result

    def _verify_manifest_before_sign(self, manifest):
        if not all(f in manifest for f in MANIFEST_SCHEMA.required_fields):
            return False, "MANIFEST_STRUCTURE_INVALID"

        required_artifacts = {"results", "replay_package", "consent_bundle", "dq_trace", "config_hash", "system_meta"}
        if not required_artifacts.issubset(manifest["artifacts"].keys()):
            return False, "MANIFEST_ARTIFACTS_INCOMPLETE"

        if canonical_hash(manifest["artifacts"]) != manifest["manifest_hash"]:
            return False, "MANIFEST_HASH_DRIFT"

        return True, "MANIFEST_OK"

    def _verify_signature_packet(self, sig):
        if not all(f in sig for f in SIGNATURE_PACKET_SCHEMA.required_fields):
            return False, "SIG_PACKET_INCOMPLETE"

        body = {k: v for k, v in sig.items() if k != "packet_hash"}
        if canonical_hash(body) != sig["packet_hash"]:
            return False, "SIG_PACKET_TAMPERED"

        return True, "SIG_PACKET_OK"

    def _verify_lineage(self, lineage):
        if not all(f in lineage for f in LINEAGE_SCHEMA.required_fields):
            return False, "LINEAGE_INCOMPLETE"

        body = {k: v for k, v in lineage.items() if k != "lineage_hash"}
        if canonical_hash(body) != lineage["lineage_hash"]:
            return False, "LINEAGE_HASH_MISMATCH"

        return True, "LINEAGE_OK"

    def _verify_internal_integrity(self, dossier):
        try:
            if not all(f in dossier for f in DOSSIER_SCHEMA.required_fields):
                return False, {"error": "DOSSIER_INCOMPLETE"}

            if not all(f in dossier["manifest"] for f in MANIFEST_SCHEMA.required_fields):
                return False, {"error": "MANIFEST_INCOMPLETE"}

            ok_m, code_m = self._verify_manifest_before_sign(dossier["manifest"])
            if not ok_m:
                return False, {"error": code_m}

            ok_s, code_s = self._verify_signature_packet(dossier["signature_packet"])
            if not ok_s:
                return False, {"error": code_s}

            if not self.hsm.verify_signature(
                dossier["manifest"]["manifest_hash"],
                dossier["signature_packet"]["signature"]
            ):
                return False, {"error": "HSM_SIG_INVALID"}

            body = {k: v for k, v in dossier.items() if k != "dossier_hash"}
            if canonical_hash(body) != dossier["dossier_hash"]:
                return False, {"error": "DOSSIER_HASH_MISMATCH"}

            ok_l, code_l = self._verify_lineage(dossier["lineage"])
            if not ok_l:
                return False, {"error": code_l}

            return True, {"status": "INTERNAL_OK"}
        except Exception as e:
            return False, {"error": str(e)}

    def _build_payload(self, kind, extra=None):
        p = {"kind": kind, "ts": utc_now()}
        if extra:
            p.update(extra)
        p["payload_hash"] = canonical_hash({k: v for k, v in p.items() if k != "payload_hash"})
        return p

    def _record_event(self, case_id, event_type, payload):
        rec = build_forensic_event(
            case_id=case_id,
            event_type=event_type,
            payload=payload,
            chain_head=self.chain_head,
            engine_version=self.engine_version,
            policy_version=self.policy.version,
        )
        integrity = self.verified_store.append_verified(rec)
        self.chain_head = rec["event_hash"]
        return {"record": rec, "store": integrity}

    def _verify_policy_consent(self, user):
        required = (
            hasattr(user, "has_signed_terms")
            and hasattr(user, "accepted_at_utc")
            and hasattr(user, "terms_hash")
        )
        if not required:
            return False

        if not user.has_signed_terms(self.policy.version):
            return False

        if getattr(user, "terms_hash", None) != self.policy.expected_terms_hash:
            return False

        if not getattr(user, "accepted_at_utc", None):
            return False

        return True

    def _register_evidence(self, dossier, audit, replay, release, event):
        return {
            "dossier": self.evidence.register_artifact("dossier", dossier, canonical_hash),
            "audit": self.evidence.register_artifact("audit", audit, canonical_hash),
            "replay": self.evidence.register_artifact("replay", replay, canonical_hash),
            "release": self.evidence.register_artifact("release", release, canonical_hash),
            "event": self.evidence.register_artifact("event", event, canonical_hash),
        }

    def _evidence_ok(self, evidence):
        required = {"dossier", "audit", "replay", "release", "event"}
        return required.issubset(evidence.keys()) and all(evidence[k] for k in required)

    def _assert_invariants(self, audit, release, dossier):
        if not audit["dual_ok"]:
            raise RuntimeError("INVARIANT_FAIL::DUAL")
        if not release["release_ok"]:
            raise RuntimeError("INVARIANT_FAIL::GATE")
        if not dossier.get("dossier_hash"):
            raise RuntimeError("INVARIANT_FAIL::HASH")

    def execute(self, user, audit_input):
        case_id = str(uuid.uuid4())
        ts = self.ntp.get_trusted_time()

        try:
            if not self._verify_policy_consent(user):
                return {
                    "status": "REJECTED",
                    "case_id": case_id,
                    "reason": "CONSENT_FAILURE",
                }

            auc_df = validate_design_strict_plus(audit_input.auc_df, "AUC")
            cmax_df = validate_design_strict_plus(audit_input.cmax_df, "CMAX")

            results = {
                "auc": self._fit_endpoint(auc_df, "AUC"),
                "cmax": self._fit_endpoint(cmax_df, "CMAX"),
            }
            results["overall_pass"] = results["auc"]["pass_be"] and results["cmax"]["pass_be"]

            dq_trace = [
                {"stage": "input_validation", "ts": ts},
                {"stage": "scientific_fit", "ts": ts},
            ]

            manifest = build_manifest(
                results=results,
                replay_package=build_replay_package(auc_df, cmax_df, results, self.policy, ts),
                consent_bundle=build_consent_bundle(user, self.policy.version, ts),
                dq_trace=dq_trace,
                policy=self.policy,
                engine_version=self.engine_version,
                ts=ts,
            )

            ok_m, code_m = self._verify_manifest_before_sign(manifest)
            if not ok_m:
                raise RuntimeError(code_m)

            sig = build_signature_packet(
                signature=self.hsm.sign_canonical_digest(manifest["manifest_hash"]),
                key_id=self.policy.hsm_key_id,
                algorithm=self.policy.signature_algorithm,
                signed_at_utc=ts,
            )

            provisional = build_final_dossier(
                case_id=case_id,
                results=results,
                manifest=manifest,
                signature_packet=sig,
                chain_head=self.chain_head,
                lineage={"tmp": True},
            )

            lineage = build_lineage(
                case_id=case_id,
                input_hashes={"auc": self._stable_df_hash(auc_df), "cmax": self._stable_df_hash(cmax_df)},
                results_hash=canonical_hash(results),
                manifest_hash=manifest["manifest_hash"],
                provisional_dossier_hash=provisional["dossier_hash"],
            )

            dossier = build_final_dossier(
                case_id=case_id,
                results=results,
                manifest=manifest,
                signature_packet=sig,
                chain_head=self.chain_head,
                lineage=lineage,
            )

            i_ok, v_i = self._verify_internal_integrity(dossier)
            e_ok, v_e = ShieldMultiStageVerifier(self.hsm, canonical_hash).verify_dossier(dossier)

            audit = {
                "case_id": case_id,
                "internal_ok": bool(i_ok),
                "external_ok": bool(e_ok),
                "dual_ok": bool(i_ok and e_ok),
                "internal": v_i,
                "external": v_e,
                "ts": utc_now(),
            }
            audit["report_hash"] = canonical_hash({k: v for k, v in audit.items() if k != "report_hash"})

            replay_ok, replay_report = ShieldReplayValidator(canonical_hash).validate(
                dossier["manifest"]["artifacts"]["replay_package"],
                auc_df,
                cmax_df,
                results,
            )

            if not (audit["dual_ok"] and replay_ok):
                raise RuntimeError("VERIFY_OR_REPLAY_FAIL")

            verified_payload = self._build_payload(
                "DOSSIER_VERIFIED",
                {
                    "d_hash": dossier["dossier_hash"],
                    "a_hash": audit["report_hash"],
                    "l_hash": dossier["lineage"]["lineage_hash"],
                    "r_hash": replay_report["report_hash"],
                    "policy_version": self.policy.version,
                    "engine_version": self.engine_version,
                },
            )

            verified_event = self._record_event(
                case_id,
                "DOSSIER_VERIFIED",
                verified_payload,
            )

            provisional_release = {
                "status": "PENDING",
                "ts": utc_now(),
                "release_gate_hash": "PENDING",
            }

            evidence = self._register_evidence(
                dossier=dossier,
                audit=audit,
                replay=replay_report,
                release=provisional_release,
                event=verified_event["record"],
            )

            gate = ShieldReleaseGate(canonical_hash).evaluate(
                dossier_ok=audit["dual_ok"],
                store_ok=verified_event["store"].get("write_verified", False),
                replay_ok=replay_ok,
                evidence_ok=self._evidence_ok(evidence),
            )

            self._assert_invariants(audit, gate, dossier)

            release_payload = self._build_payload(
                "RELEASE_APPROVED",
                {
                    "d_hash": dossier["dossier_hash"],
                    "a_hash": audit["report_hash"],
                    "g_hash": gate["release_gate_hash"],
                    "l_hash": dossier["lineage"]["lineage_hash"],
                    "r_hash": replay_report["report_hash"],
                    "policy_version": self.policy.version,
                    "engine_version": self.engine_version,
                },
            )

            release_event = self._record_event(
                case_id,
                "RELEASE_APPROVED",
                release_payload,
            )

            self.evidence.register_artifact("release_gate_final", gate, canonical_hash)

            return {
                "status": "CERTIFIED",
                "case_id": case_id,
                "dossier": dossier,
                "audit": audit,
                "replay": replay_report,
                "gate": gate,
                "verified_event": verified_event["record"],
                "release_event": release_event["record"],
            }

        except Exception as e:
            return {
                "status": "CRITICAL_ERROR",
                "case_id": case_id,
                "error_type": type(e).__name__,
                "message": str(e),
            }


if __name__ == "__main__":
    print("S.H.I.E.L.D. Unified Sovereign ready.")