from typing import Any

from pydantic import BaseModel, Field


class DecisionData(BaseModel):
    decision_code: str | None = None
    severity: str | None = None
    risk_score: int | float | str | None = None
    recommended_action: str | None = None
    batch_disposition: str | None = None


class VersioningData(BaseModel):
    engine_version: str | None = None
    policy_version: str | None = None
    rules_version: str | None = None
    rules_hash: str | None = None


class ComplianceScopeData(BaseModel):
    criticality: str | None = None
    regulated: bool | str | None = None
    requires_audit_trail: bool | str | None = None
    frameworks: list[str] = Field(default_factory=list)


class ExplanationData(BaseModel):
    summary: str | None = None
    details: list[str] = Field(default_factory=list)


class TimelineItemData(BaseModel):
    type: str | None = None
    timestamp: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AuditRuleData(BaseModel):
    rule_id: str | None = None
    outcome: str | None = None
    field: str | None = None
    actual_value: Any = None


class ProofData(BaseModel):
    ledger_hash: str | None = None
    checkpoint_hash: str | None = None
    anchor_sha256: str | None = None
    anchor_external_path: str | None = None
    timestamp_status: str | None = None
    timestamp_provider: str | None = None
    timestamp_proof: str | None = None


class DossierView(BaseModel):
    dossier_type: str | None = None
    decision_id: str | None = None
    decision_timestamp: str | None = None
    client_id: str | None = None
    client_name: str | None = None
    module: str | None = None

    engine_status: str | None = None
    final_status: str | None = None

    has_human_review: bool | str | None = None
    has_admin_override: bool | str | None = None
    latest_review_action: str | None = None
    review_count: int | None = None
    override_count: int | None = None
    latest_event_timestamp: str | None = None
    events_count: int | None = None

    severity: str | None = None
    risk_score: int | float | str | None = None
    latest_ledger_hash: str | None = None
    dossier_hash: str | None = None

    decision: DecisionData = Field(default_factory=DecisionData)
    versioning: VersioningData = Field(default_factory=VersioningData)
    compliance_scope: ComplianceScopeData = Field(default_factory=ComplianceScopeData)
    explanation: ExplanationData = Field(default_factory=ExplanationData)
    timeline: list[TimelineItemData] = Field(default_factory=list)
    audit: list[AuditRuleData] = Field(default_factory=list)
    proof: ProofData = Field(default_factory=ProofData)
