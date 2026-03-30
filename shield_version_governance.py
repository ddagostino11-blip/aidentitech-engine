# [S.H.I.E.L.D. 34.1 - VERSION GOVERNANCE LAYER]
# ELITE PRODUCTION GRADE - 2026.03.27
# VERSION REGISTRY | POLICY LOCK | ENGINE/POLICY COMPATIBILITY | RELEASE FREEZE
#
# Questo modulo aggiunge:
# 1. registry versioni
# 2. freeze delle release
# 3. compatibilità engine/policy
# 4. blocco se runtime non coerente
# 5. audit delle promozioni di versione
#
# Si integra SENZA stravolgere la logica della 33.7 / 33.6.2.

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List


# ============================================================
# 1. CORE HELPERS
# ============================================================

def vg_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def vg_canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def vg_canonical_hash(data: Any) -> str:
    return hashlib.sha256(vg_canonical_json(data).encode("utf-8")).hexdigest()


# ============================================================
# 2. DATA MODELS
# ============================================================

@dataclass
class VersionRecord:
    engine_version: str
    policy_version: str
    status: str                 # DRAFT / APPROVED / FROZEN / RETIRED
    created_at_utc: str
    created_by: str
    notes: str
    compatibility_hash: str


@dataclass
class VersionPromotionRecord:
    engine_version: str
    policy_version: str
    from_status: str
    to_status: str
    promoted_at_utc: str
    promoted_by: str
    reason: str
    promotion_hash: str


# ============================================================
# 3. VERSION REGISTRY
# ============================================================

class ShieldVersionRegistry:
    """
    Registry append-only semplificato.
    File:
    - versions.json
    - promotions.jsonl
    """

    def __init__(self, base_dir: str = "./forensic_store/version_registry"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.versions_path = self.base_dir / "versions.json"
        self.promotions_path = self.base_dir / "promotions.jsonl"

        if not self.versions_path.exists():
            self.versions_path.write_text("[]", encoding="utf-8")

        if not self.promotions_path.exists():
            self.promotions_path.write_text("", encoding="utf-8")

    def _load_versions(self) -> List[Dict[str, Any]]:
        return json.loads(self.versions_path.read_text(encoding="utf-8"))

    def _save_versions(self, records: List[Dict[str, Any]]) -> None:
        self.versions_path.write_text(vg_canonical_json(records), encoding="utf-8")

    def register_version(
        self,
        engine_version: str,
        policy_version: str,
        created_by: str = "SYSTEM",
        notes: str = ""
    ) -> Dict[str, Any]:
        records = self._load_versions()

        for r in records:
            if r["engine_version"] == engine_version and r["policy_version"] == policy_version:
                return r

        payload = {
            "engine_version": engine_version,
            "policy_version": policy_version,
        }
        compatibility_hash = vg_canonical_hash(payload)

        rec = VersionRecord(
            engine_version=engine_version,
            policy_version=policy_version,
            status="DRAFT",
            created_at_utc=vg_utc_now(),
            created_by=created_by,
            notes=notes,
            compatibility_hash=compatibility_hash,
        )

        records.append(asdict(rec))
        self._save_versions(records)
        return asdict(rec)

    def get_version(self, engine_version: str, policy_version: str) -> Optional[Dict[str, Any]]:
        for r in self._load_versions():
            if r["engine_version"] == engine_version and r["policy_version"] == policy_version:
                return r
        return None

    def promote_version(
        self,
        engine_version: str,
        policy_version: str,
        to_status: str,
        promoted_by: str = "SYSTEM",
        reason: str = ""
    ) -> Dict[str, Any]:
        if to_status not in {"APPROVED", "FROZEN", "RETIRED"}:
            raise ValueError(f"INVALID_TARGET_STATUS::{to_status}")

        records = self._load_versions()
        target = None
        for r in records:
            if r["engine_version"] == engine_version and r["policy_version"] == policy_version:
                target = r
                break

        if target is None:
            raise RuntimeError("VERSION_NOT_REGISTERED")

        from_status = target["status"]
        target["status"] = to_status
        self._save_versions(records)

        promotion_payload = {
            "engine_version": engine_version,
            "policy_version": policy_version,
            "from_status": from_status,
            "to_status": to_status,
            "promoted_at_utc": vg_utc_now(),
            "promoted_by": promoted_by,
            "reason": reason,
        }
        promotion_hash = vg_canonical_hash(promotion_payload)

        promotion = VersionPromotionRecord(
            engine_version=engine_version,
            policy_version=policy_version,
            from_status=from_status,
            to_status=to_status,
            promoted_at_utc=promotion_payload["promoted_at_utc"],
            promoted_by=promoted_by,
            reason=reason,
            promotion_hash=promotion_hash,
        )

        with self.promotions_path.open("a", encoding="utf-8") as f:
            f.write(vg_canonical_json(asdict(promotion)) + "\n")

        return asdict(promotion)

    def assert_version_allowed(self, engine_version: str, policy_version: str, allowed_statuses=None) -> Dict[str, Any]:
        if allowed_statuses is None:
            allowed_statuses = {"APPROVED", "FROZEN"}

        rec = self.get_version(engine_version, policy_version)
        if rec is None:
            raise RuntimeError("VERSION_NOT_REGISTERED")

        if rec["status"] not in allowed_statuses:
            raise RuntimeError(f"VERSION_STATUS_BLOCKED::{rec['status']}")

        return rec


# ============================================================
# 4. VERSION GOVERNANCE MIXIN
# ============================================================

class ShieldVersionGovernanceMixin:
    """
    Mixin da aggiungere al kernel.
    Richiede:
    - self.engine_version
    - self.policy.version
    - self.policy
    """

    def _init_version_governance(self, registry_dir: str = "./forensic_store/version_registry", created_by: str = "SYSTEM"):
        self.version_registry = ShieldVersionRegistry(registry_dir)
        self.version_record = self.version_registry.register_version(
            engine_version=self.engine_version,
            policy_version=self.policy.version,
            created_by=created_by,
            notes="Auto-registered at kernel bootstrap",
        )

    def _assert_runtime_version_governance(self):
        """
        Blocco runtime se engine/policy non sono in stato valido.
        """
        rec = self.version_registry.assert_version_allowed(
            engine_version=self.engine_version,
            policy_version=self.policy.version,
            allowed_statuses={"APPROVED", "FROZEN"},
        )

        expected_hash = vg_canonical_hash({
            "engine_version": self.engine_version,
            "policy_version": self.policy.version,
        })

        if rec["compatibility_hash"] != expected_hash:
            raise RuntimeError("ENGINE_POLICY_COMPATIBILITY_MISMATCH")

        return rec

    def promote_self_to_approved(self, promoted_by: str = "SYSTEM", reason: str = "Validation complete"):
        return self.version_registry.promote_version(
            engine_version=self.engine_version,
            policy_version=self.policy.version,
            to_status="APPROVED",
            promoted_by=promoted_by,
            reason=reason,
        )

    def freeze_self_release(self, promoted_by: str = "SYSTEM", reason: str = "Release frozen"):
        return self.version_registry.promote_version(
            engine_version=self.engine_version,
            policy_version=self.policy.version,
            to_status="FROZEN",
            promoted_by=promoted_by,
            reason=reason,
        )


# ============================================================
# 5. DROP-IN EXAMPLE FOR YOUR KERNEL 33.6.2 / 33.7
# ============================================================

"""
USO:

class DoodogSovereignGoldHardened(ShieldVersionGovernanceMixin):
    def __init__(...):
        ...
        self._init_version_governance(created_by="DOODOG")
        # opzionale: promuovi manualmente in un secondo momento

    def execute_elite_pipeline_ultimate(...):
        self._assert_runtime_version_governance()
        ...
"""

# ============================================================
# 6. COMPLETE INTEGRATED EXAMPLE
# ============================================================

class DoodogVersionGovernedKernel(ShieldVersionGovernanceMixin):
    """
    Esempio minimo integrato.
    Adattalo al tuo kernel reale ereditando dal mixin.
    """

    def __init__(self, policy):
        self.engine_version = "33.6.2-SOVEREIGN-GOLD-HARDENED"
        self.policy = policy
        self._init_version_governance(created_by="DOODOG")

    def execute(self):
        self._assert_runtime_version_governance()
        return {
            "status": "OK",
            "engine_version": self.engine_version,
            "policy_version": self.policy.version,
        }


# ============================================================
# 7. HOW TO APPLY TO YOUR CURRENT KERNEL
# ============================================================

"""
A) Importa il mixin in cima al file del tuo kernel:

from shield_version_governance import ShieldVersionGovernanceMixin

B) Cambia la classe:

class DoodogSovereignGoldHardened(ShieldVersionGovernanceMixin):

C) Dentro __init__ aggiungi in fondo:

self._init_version_governance(created_by="DOODOG")

D) All'inizio di execute_elite_pipeline_ultimate aggiungi:

self._assert_runtime_version_governance()

E) Dopo validazione ufficiale, promuovi la versione:
self.promote_self_to_approved(promoted_by="DOODOG", reason="Validation suite passed")

F) Quando vuoi congelare una release:
self.freeze_self_release(promoted_by="DOODOG", reason="Released to governed production")
"""

# ============================================================
# 8. OPTIONAL BOOTSTRAP SCRIPT
# ============================================================

if __name__ == "__main__":
    class MockPolicy:
        version = "TEST_POLICY_V1"

    k = DoodogVersionGovernedKernel(MockPolicy())

    # se vuoi testare:
    # k.promote_self_to_approved(promoted_by="LOCAL_TEST", reason="bootstrap approval")
    # print(k.execute())

    print("Version governance layer ready.")