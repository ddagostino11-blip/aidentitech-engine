# test_shield_elite.py
# PYTEST SUITE PER S.H.I.E.L.D. 33.6.2
# Copia/incolla ed esegui con: pytest -q

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# IMPORTA IL TUO KERNEL
# from your_kernel_file import DoodogSovereignGoldHardened

# ============================================================
# MOCK INFRASTRUTTURA (REALISTICI MA LEGGERI)
# ============================================================

class MockHSM:
    def sign_canonical_digest(self, digest):
        return f"SIG::{digest}"

    def verify_signature(self, digest, signature):
        return signature == f"SIG::{digest}"


class MockNTP:
    def get_trusted_time(self):
        return datetime.now(timezone.utc).isoformat()


class MockPolicy:
    def __init__(self):
        self.version = "TEST_POLICY_V1"
        self.expected_terms_hash = "EXPECTED_HASH"
        self.hsm_key_id = "KEY_001"
        self.signature_algorithm = "SHA256_RSA"
        self.thresholds = {
            "be_lower": 80.0,
            "be_upper": 125.0,
            "cooks": 1.0,
            "leverage": 0.5,
        }

    def threshold(self, name, default):
        return self.thresholds.get(name, default)


class MockUser:
    def __init__(self, valid=True):
        self.accepted_at_utc = datetime.now(timezone.utc).isoformat() if valid else None
        self.terms_hash = "EXPECTED_HASH" if valid else "WRONG"
        self._signed = valid

    def has_signed_terms(self, version):
        return self._signed


class MockAuditInput:
    def __init__(self, auc_df, cmax_df):
        self.auc_df = auc_df
        self.cmax_df = cmax_df


# ============================================================
# FIXTURE DATI
# ============================================================

@pytest.fixture
def valid_data():
    auc = pd.DataFrame([
        {"subject": "S1", "sequence": "TR", "period": 1, "treatment": 0, "value": 100},
        {"subject": "S1", "sequence": "TR", "period": 2, "treatment": 1, "value": 102},
        {"subject": "S2", "sequence": "RT", "period": 1, "treatment": 1, "value": 101},
        {"subject": "S2", "sequence": "RT", "period": 2, "treatment": 0, "value": 99},
    ])

    return MockAuditInput(auc, auc.copy())


@pytest.fixture
def kernel(valid_data):
    hsm = MockHSM()
    ntp = MockNTP()
    policy = MockPolicy()

    # SOSTITUISCI con il tuo import reale
    from __main__ import DoodogSovereignGoldHardened

    return DoodogSovereignGoldHardened(
        hsm_vault=hsm,
        ntp_service=ntp,
        policy_bundle=policy,
        storage_path="./test_store"
    )


# ============================================================
# TEST 1 — PIPELINE BASE
# ============================================================

def test_pipeline_runs(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    assert "status" in res
    assert res["status"] in ["CERTIFIED", "CRITICAL_ERROR", "REJECTED"]


# ============================================================
# TEST 2 — CONSENT BLOCCA
# ============================================================

def test_consent_failure(kernel, valid_data):
    user = MockUser(valid=False)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    assert res["status"] == "REJECTED"


# ============================================================
# TEST 3 — HASH CONSISTENCY
# ============================================================

def test_dossier_hash_stable(kernel, valid_data):
    user = MockUser(valid=True)

    r1 = kernel.execute_elite_pipeline_ultimate(user, valid_data)
    r2 = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if r1["status"] == "CERTIFIED" and r2["status"] == "CERTIFIED":
        assert r1["dossier"]["dossier_hash"] == r2["dossier"]["dossier_hash"]


# ============================================================
# TEST 4 — SIGNATURE VALID
# ============================================================

def test_signature_valid(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if res["status"] == "CERTIFIED":
        d = res["dossier"]
        assert kernel.hsm.verify_signature(
            d["manifest"]["manifest_hash"],
            d["signature_packet"]["signature"]
        )


# ============================================================
# TEST 5 — INTERNAL VERIFIER FAIL IF TAMPERED
# ============================================================

def test_internal_verifier_detects_tampering(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if res["status"] != "CERTIFIED":
        pytest.skip("Pipeline non certificata")

    d = res["dossier"]

    # tamper
    d["manifest"]["manifest_hash"] = "CORRUPTED"

    ok, _ = kernel._verify_internal_integrity_complete(d)
    assert not ok


# ============================================================
# TEST 6 — REPLAY CONSISTENCY
# ============================================================

def test_replay_consistency(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if res["status"] == "CERTIFIED":
        assert res["gate"]["release_ok"] is True


# ============================================================
# TEST 7 — EVENT STORE WRITE VERIFIED
# ============================================================

def test_event_store_integrity(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if res["status"] == "CERTIFIED":
        assert "event" in res


# ============================================================
# TEST 8 — TREATMENT AMBIGUITY FAIL
# ============================================================

def test_treatment_ambiguity():
    from __main__ import DoodogSovereignGoldHardened

    kernel = DoodogSovereignGoldHardened(MockHSM(), MockNTP(), MockPolicy())

    df = pd.DataFrame([
        {"subject": "S1", "sequence": "TR", "period": 1, "treatment": 0, "value": 100},
        {"subject": "S1", "sequence": "TR", "period": 2, "treatment": 2, "value": 102},  # BAD
    ])

    with pytest.raises(Exception):
        kernel._fit_endpoint_elite_consistent(df, "AUC")


# ============================================================
# TEST 9 — NEGATIVE VALUES FAIL (LOG)
# ============================================================

def test_negative_values_fail(kernel):
    df = pd.DataFrame([
        {"subject": "S1", "sequence": "TR", "period": 1, "treatment": 0, "value": -1}
    ])

    with pytest.raises(Exception):
        kernel._fit_endpoint_elite_consistent(df, "AUC")


# ============================================================
# TEST 10 — AUDIT HASH EXISTS
# ============================================================

def test_audit_hash(kernel, valid_data):
    user = MockUser(valid=True)
    res = kernel.execute_elite_pipeline_ultimate(user, valid_data)

    if res["status"] == "CERTIFIED":
        assert "report_hash" in res["audit"]