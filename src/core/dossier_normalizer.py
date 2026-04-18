from __future__ import annotations

from typing import Any

from src.core.dossier_schema import DossierView


BRAND_NAME = "Aidentitech"

REVIEWER_MAP = {
    "aidentitech": "Aidentitech",
}

CLIENT_MAP = {
    "aidentitech": "Aidentitech",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\x0c", "")
        .strip()
    )


def _normalize_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value

    text = _clean(value).lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    return None


def _normalize_brand_name(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    normalized = text.lower()
    return CLIENT_MAP.get(normalized, text.capitalize())


def _normalize_reviewer(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    normalized = text.lower()
    return REVIEWER_MAP.get(normalized, text.capitalize())


def _normalize_status(value: Any) -> str:
    text = _clean(value)
    return text.upper() if text else ""


def _normalize_outcome(value: Any) -> str:
    text = _clean(value)
    return text.lower() if text else ""


def _normalize_anchor_path(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""

    text = text.replace("\\", "/")
    text = text.replace("/Users/domenico/Desktop/", "")
    text = text.replace("./", "")

    if "aidentitech-external-anchors/" in text:
        filename = text.split("aidentitech-external-anchors/")[-1]
        return f".../{filename}"

    return text


def normalize_dossier_payload(raw: dict[str, Any]) -> DossierView:
    dossier = DossierView.model_validate(raw or {})

    dossier.dossier_type = _clean(dossier.dossier_type)
    dossier.decision_id = _clean(dossier.decision_id)
    dossier.decision_timestamp = _clean(dossier.decision_timestamp)
    dossier.client_id = _clean(dossier.client_id)
    dossier.module = _clean(dossier.module)
    dossier.latest_event_timestamp = _clean(dossier.latest_event_timestamp)
    dossier.latest_ledger_hash = _clean(dossier.latest_ledger_hash)
    dossier.dossier_hash = _clean(dossier.dossier_hash)

    dossier.engine_status = _normalize_status(dossier.engine_status)
    dossier.final_status = _normalize_status(dossier.final_status)
    dossier.latest_review_action = _normalize_status(dossier.latest_review_action)
    dossier.severity = _normalize_status(dossier.severity)

    dossier.has_human_review = _normalize_bool(dossier.has_human_review)
    dossier.has_admin_override = _normalize_bool(dossier.has_admin_override)

    if not dossier.client_name:
        dossier.client_name = _normalize_brand_name(dossier.client_id)
    else:
        dossier.client_name = _normalize_brand_name(dossier.client_name)

    dossier.module = _clean(dossier.module).lower()

    if dossier.decision:
        dossier.decision.decision_code = _clean(dossier.decision.decision_code)
        dossier.decision.severity = _normalize_status(dossier.decision.severity)
        dossier.decision.recommended_action = _clean(dossier.decision.recommended_action)
        dossier.decision.batch_disposition = _clean(dossier.decision.batch_disposition)

    if dossier.versioning:
        dossier.versioning.engine_version = _clean(dossier.versioning.engine_version)
        dossier.versioning.policy_version = _clean(dossier.versioning.policy_version)
        dossier.versioning.rules_version = _clean(dossier.versioning.rules_version)
        dossier.versioning.rules_hash = _clean(dossier.versioning.rules_hash)

    if dossier.compliance_scope:
        dossier.compliance_scope.criticality = _normalize_status(dossier.compliance_scope.criticality)
        dossier.compliance_scope.regulated = _normalize_bool(dossier.compliance_scope.regulated)
        dossier.compliance_scope.requires_audit_trail = _normalize_bool(
            dossier.compliance_scope.requires_audit_trail
        )
        dossier.compliance_scope.frameworks = [
            _clean(x) for x in (dossier.compliance_scope.frameworks or []) if _clean(x)
        ]

    if dossier.explanation:
        dossier.explanation.summary = _clean(dossier.explanation.summary)
        dossier.explanation.details = [
            _clean(x) for x in (dossier.explanation.details or []) if _clean(x)
        ]

    normalized_timeline = []
    for item in dossier.timeline:
        item.type = _normalize_status(item.type)
        item.timestamp = _clean(item.timestamp)

        data = item.data or {}

        if "status" in data:
            data["status"] = _normalize_status(data.get("status"))
        if "action" in data:
            data["action"] = _normalize_status(data.get("action"))
        if "severity" in data:
            data["severity"] = _normalize_status(data.get("severity"))
        if "reviewer_id" in data:
            data["reviewer_id"] = _normalize_reviewer(data.get("reviewer_id"))
        if "reason" in data:
            data["reason"] = _clean(data.get("reason"))

        item.data = data
        normalized_timeline.append(item)

    dossier.timeline = normalized_timeline

    normalized_audit = []
    for rule in dossier.audit:
        rule.rule_id = _clean(rule.rule_id)
        rule.outcome = _normalize_outcome(rule.outcome)
        rule.field = _clean(rule.field)
        normalized_audit.append(rule)

    dossier.audit = normalized_audit

    if dossier.proof:
        dossier.proof.ledger_hash = _clean(dossier.proof.ledger_hash)
        dossier.proof.checkpoint_hash = _clean(dossier.proof.checkpoint_hash)
        dossier.proof.anchor_sha256 = _clean(dossier.proof.anchor_sha256)
        dossier.proof.anchor_external_path = _normalize_anchor_path(dossier.proof.anchor_external_path)
        dossier.proof.timestamp_status = _normalize_status(dossier.proof.timestamp_status)
        dossier.proof.timestamp_provider = _clean(dossier.proof.timestamp_provider)
        dossier.proof.timestamp_proof = _clean(dossier.proof.timestamp_proof)

    return dossier
