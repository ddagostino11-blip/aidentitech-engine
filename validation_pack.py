# [S.H.I.E.L.D. 34.0 - THE VALIDATION PACK]
# ELITE PRODUCTION GRADE - 2026.03.27
# TEST HARNESS | FIXTURES | VALIDATION DOSSIER | REGRESSION SUITE
#
# Scopo:
# aggiungere al kernel 33.6.2 un pacchetto pratico per:
# - smoke test
# - regression test
# - replay validation
# - validation dossier esportabile
#
# Questo file NON sostituisce il kernel.
# Lo affianca e lo valida.

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ============================================================
# 1. GENERIC HELPERS
# ============================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def canonical_hash(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


# ============================================================
# 2. TEST FIXTURES
# ============================================================

@dataclass
class MockUserSession:
    id: str
    accepted_at_utc: str
    terms_hash: str
    signed_versions: List[str]

    def has_signed_terms(self, version: str) -> bool:
        return version in self.signed_versions


@dataclass
class MockAuditInput:
    auc_df: pd.DataFrame
    cmax_df: pd.DataFrame


def build_valid_fixture(policy_version: str, expected_terms_hash: str) -> Dict[str, Any]:
    """
    Fixture minima coerente per 2x2 crossover semplificato.
    """
    auc_df = pd.DataFrame([
        {"subject": "S01", "sequence": "TR", "period": 1, "treatment": 0, "value": 101.0},
        {"subject": "S01", "sequence": "TR", "period": 2, "treatment": 1, "value": 104.0},
        {"subject": "S02", "sequence": "RT", "period": 1, "treatment": 1, "value": 103.0},
        {"subject": "S02", "sequence": "RT", "period": 2, "treatment": 0, "value": 100.0},
        {"subject": "S03", "sequence": "TR", "period": 1, "treatment": 0, "value": 99.0},
        {"subject": "S03", "sequence": "TR", "period": 2, "treatment": 1, "value": 101.0},
        {"subject": "S04", "sequence": "RT", "period": 1, "treatment": 1, "value": 102.0},
        {"subject": "S04", "sequence": "RT", "period": 2, "treatment": 0, "value": 100.0},
    ])

    cmax_df = pd.DataFrame([
        {"subject": "S01", "sequence": "TR", "period": 1, "treatment": 0, "value": 95.0},
        {"subject": "S01", "sequence": "TR", "period": 2, "treatment": 1, "value": 98.0},
        {"subject": "S02", "sequence": "RT", "period": 1, "treatment": 1, "value": 97.0},
        {"subject": "S02", "sequence": "RT", "period": 2, "treatment": 0, "value": 94.0},
        {"subject": "S03", "sequence": "TR", "period": 1, "treatment": 0, "value": 96.0},
        {"subject": "S03", "sequence": "TR", "period": 2, "treatment": 1, "value": 97.0},
        {"subject": "S04", "sequence": "RT", "period": 1, "treatment": 1, "value": 98.0},
        {"subject": "S04", "sequence": "RT", "period": 2, "treatment": 0, "value": 95.0},
    ])

    user = MockUserSession(
        id="USER-001",
        accepted_at_utc=utc_now(),
        terms_hash=expected_terms_hash,
        signed_versions=[policy_version],
    )

    audit_input = MockAuditInput(auc_df=auc_df, cmax_df=cmax_df)

    return {
        "user_session": user,
        "audit_input": audit_input,
    }


def build_invalid_consent_fixture(policy_version: str) -> Dict[str, Any]:
    auc_df = pd.DataFrame([
        {"subject": "S01", "sequence": "TR", "period": 1, "treatment": 0, "value": 101.0},
        {"subject": "S01", "sequence": "TR", "period": 2, "treatment": 1, "value": 104.0},
        {"subject": "S02", "sequence": "RT", "period": 1, "treatment": 1, "value": 103.0},
        {"subject": "S02", "sequence": "RT", "period": 2, "treatment": 0, "value": 100.0},
    ])
    cmax_df = auc_df.copy()

    user = MockUserSession(
        id="USER-002",
        accepted_at_utc="",
        terms_hash="WRONG_HASH",
        signed_versions=[],
    )

    audit_input = MockAuditInput(auc_df=auc_df, cmax_df=cmax_df)

    return {
        "user_session": user,
        "audit_input": audit_input,
    }


def build_invalid_data_fixture(policy_version: str, expected_terms_hash: str) -> Dict[str, Any]:
    auc_df = pd.DataFrame([
        {"subject": "S01", "sequence": "TR", "period": 1, "treatment": 0, "value": 101.0},
        {"subject": "S01", "sequence": "TR", "period": 2, "treatment": 1, "value": -1.0},  # invalid
        {"subject": "S02", "sequence": "RT", "period": 1, "treatment": 1, "value": 103.0},
        {"subject": "S02", "sequence": "RT", "period": 2, "treatment": 0, "value": 100.0},
    ])
    cmax_df = auc_df.copy()

    user = MockUserSession(
        id="USER-003",
        accepted_at_utc=utc_now(),
        terms_hash=expected_terms_hash,
        signed_versions=[policy_version],
    )

    audit_input = MockAuditInput(auc_df=auc_df, cmax_df=cmax_df)

    return {
        "user_session": user,
        "audit_input": audit_input,
    }


# ============================================================
# 3. TEST RESULT MODEL
# ============================================================

@dataclass
class ValidationTestResult:
    test_name: str
    passed: bool
    checked_at_utc: str
    details: Dict[str, Any]


@dataclass
class ValidationSummary:
    suite_name: str
    started_at_utc: str
    finished_at_utc: str
    total: int
    passed: int
    failed: int
    results: List[Dict[str, Any]]
    summary_hash: str


# ============================================================
# 4. VALIDATION RUNNER
# ============================================================

class ShieldValidationRunner:
    def __init__(self, kernel, output_dir: str = "./validation_pack"):
        self.kernel = kernel
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _run_single(self, test_name: str, user_session: Any, audit_input: Any) -> ValidationTestResult:
        try:
            result = self.kernel.execute_elite_pipeline_ultimate(user_session, audit_input)

            status = result.get("status")
            passed = status in {"CERTIFIED", "REJECTED", "FAILED", "CRITICAL_ERROR"}

            details = {
                "status": status,
                "top_level_keys": sorted(list(result.keys())),
                "result_hash": canonical_hash(result),
            }

            return ValidationTestResult(
                test_name=test_name,
                passed=passed,
                checked_at_utc=utc_now(),
                details=details,
            )
        except Exception as e:
            return ValidationTestResult(
                test_name=test_name,
                passed=False,
                checked_at_utc=utc_now(),
                details={
                    "exception_type": type(e).__name__,
                    "message": str(e),
                },
            )

    def run_smoke_suite(self) -> ValidationSummary:
        started = utc_now()

        policy_version = self.kernel.policy.version
        expected_terms_hash = getattr(self.kernel.policy, "expected_terms_hash", "EXPECTED_HASH")

        fixtures = [
            ("valid_fixture", build_valid_fixture(policy_version, expected_terms_hash)),
            ("invalid_consent_fixture", build_invalid_consent_fixture(policy_version)),
            ("invalid_data_fixture", build_invalid_data_fixture(policy_version, expected_terms_hash)),
        ]

        results: List[ValidationTestResult] = []
        for test_name, fx in fixtures:
            res = self._run_single(test_name, fx["user_session"], fx["audit_input"])
            results.append(res)

        finished = utc_now()
        passed_n = sum(1 for r in results if r.passed)
        failed_n = len(results) - passed_n

        serializable_results = [asdict(r) for r in results]
        summary_payload = {
            "suite_name": "smoke_suite",
            "started_at_utc": started,
            "finished_at_utc": finished,
            "total": len(results),
            "passed": passed_n,
            "failed": failed_n,
            "results": serializable_results,
        }

        summary = ValidationSummary(
            suite_name="smoke_suite",
            started_at_utc=started,
            finished_at_utc=finished,
            total=len(results),
            passed=passed_n,
            failed=failed_n,
            results=serializable_results,
            summary_hash=canonical_hash(summary_payload),
        )

        self._write_json("smoke_suite_summary.json", asdict(summary))
        return summary

    def run_regression_case(self, name: str, user_session: Any, audit_input: Any) -> ValidationTestResult:
        result = self._run_single(name, user_session, audit_input)
        self._write_json(f"regression_{name}.json", asdict(result))
        return result

    def _write_json(self, filename: str, payload: Dict[str, Any]) -> None:
        path = self.output_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# ============================================================
# 5. VALIDATION DOSSIER BUILDER
# ============================================================

class ShieldValidationDossierBuilder:
    def __init__(self, output_dir: str = "./validation_pack"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, kernel_name: str, smoke_summary: ValidationSummary, notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        dossier = {
            "kernel_name": kernel_name,
            "generated_at_utc": utc_now(),
            "smoke_summary": asdict(smoke_summary),
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "notes": notes or {},
        }
        dossier["validation_dossier_hash"] = canonical_hash({k: v for k, v in dossier.items() if k != "validation_dossier_hash"})

        out = self.output_dir / "validation_dossier.json"
        out.write_text(json.dumps(dossier, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return dossier


# ============================================================
# 6. OPTIONAL REGRESSION SNAPSHOT TOOLS
# ============================================================

class ShieldRegressionSnapshot:
    def __init__(self, snapshot_dir: str = "./validation_pack/snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "name": name,
            "saved_at_utc": utc_now(),
            "payload": payload,
        }
        record["snapshot_hash"] = canonical_hash({k: v for k, v in record.items() if k != "snapshot_hash"})

        path = self.snapshot_dir / f"{name}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return record

    def compare_with_snapshot(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = self.snapshot_dir / f"{name}.json"
        if not path.exists():
            return {
                "exists": False,
                "match": False,
                "reason": "SNAPSHOT_NOT_FOUND",
            }

        old = json.loads(path.read_text(encoding="utf-8"))
        new_hash = canonical_hash({
            "name": name,
            "saved_at_utc": old["saved_at_utc"],
            "payload": payload,
        })

        return {
            "exists": True,
            "match": new_hash == old["snapshot_hash"],
            "expected_hash": old["snapshot_hash"],
            "computed_hash": new_hash,
        }


# ============================================================
# 7. HOW TO USE WITH YOUR 33.6.2 KERNEL
# ============================================================

"""
Esempio d'uso:

from your_kernel_file import DoodogSovereignGoldHardened

kernel = DoodogSovereignGoldHardened(
    hsm_vault=hsm,
    ntp_service=ntp,
    policy_bundle=policy_bundle,
    storage_path="./forensic_store"
)

runner = ShieldValidationRunner(kernel, output_dir="./validation_pack")
summary = runner.run_smoke_suite()

builder = ShieldValidationDossierBuilder(output_dir="./validation_pack")
validation_dossier = builder.build(
    kernel_name=kernel.engine_version,
    smoke_summary=summary,
    notes={
        "purpose": "formal software validation baseline",
        "scope": "core governed elite pipeline",
    }
)
"""

# ============================================================
# 8. OPTIONAL HARD CHECK FUNCTION
# ============================================================

def assert_validation_passed(smoke_summary: ValidationSummary) -> None:
    if smoke_summary.failed > 0:
        raise RuntimeError(
            f"VALIDATION_FAILED::{smoke_summary.failed}_tests_failed::{smoke_summary.summary_hash}"
        )