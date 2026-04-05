from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class RegulatorySource:
    source_id: str
    authority_name: str
    domain: str
    jurisdiction: str
    source_type: str
    endpoint: Optional[str] = None
    is_active: bool = True


@dataclass
class RegulatoryDocumentVersion:
    document_id: str
    source_id: str
    title: str
    jurisdiction: str
    domain: str
    version_label: str
    published_at: datetime
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    content_hash: Optional[str] = None
    raw_text: Optional[str] = None
    normalized_structure: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegulatoryDelta:
    delta_id: str
    document_id: str
    source_id: str
    domain: str
    jurisdiction: str
    detected_at: datetime
    change_type: str
    rule_id: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    impact_level: str = "MEDIUM"
    summary: str = ""
    details: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LegalReviewTask:
    review_id: str
    delta_id: str
    assigned_team: str
    priority: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    decision: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RegulatoryRuleVersion:
    rule_version_id: str
    rule_id: str
    domain: str
    jurisdiction: str
    version_label: str
    valid_from: datetime
    valid_to: Optional[datetime] = None
    is_active: bool = True
    previous_version_id: Optional[str] = None
    source_delta_id: Optional[str] = None
    rule_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClientImpactAlert:
    alert_id: str
    client_id: str
    delta_id: str
    domain: str
    jurisdiction: str
    priority: str
    alert_type: str
    created_at: datetime
    message: str
    recommended_action: str
    impacted_entities: List[str] = field(default_factory=list)
