from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4

from src.regulatory.models import RegulatoryDelta, RegulatoryRuleVersion


def freeze_and_create_rule_version(
    *,
    current_rule_version: Optional[RegulatoryRuleVersion],
    delta: RegulatoryDelta
) -> Tuple[Optional[RegulatoryRuleVersion], RegulatoryRuleVersion]:
    """
    Congela la versione corrente della regola e crea una nuova versione attiva.
    Ritorna:
    - old_version_frozen
    - new_version_active
    """

    frozen_old_version = None

    if current_rule_version is not None:
        current_rule_version.valid_to = datetime.utcnow()
        current_rule_version.is_active = False
        frozen_old_version = current_rule_version

    new_version = RegulatoryRuleVersion(
        rule_version_id=str(uuid4()),
        rule_id=delta.rule_id,
        domain=delta.domain,
        jurisdiction=delta.jurisdiction,
        version_label=f"{delta.rule_id}-v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        valid_from=datetime.utcnow(),
        valid_to=None,
        is_active=True,
        previous_version_id=current_rule_version.rule_version_id if current_rule_version else None,
        source_delta_id=delta.delta_id,
        rule_payload={
            "rule_id": delta.rule_id,
            "value": delta.new_value,
            "change_type": delta.change_type,
            "impact_level": delta.impact_level,
            "summary": delta.summary
        }
    )

    return frozen_old_version, new_version


def serialize_rule_version(rule_version: RegulatoryRuleVersion) -> dict:
    return {
        "rule_version_id": rule_version.rule_version_id,
        "rule_id": rule_version.rule_id,
        "domain": rule_version.domain,
        "jurisdiction": rule_version.jurisdiction,
        "version_label": rule_version.version_label,
        "valid_from": rule_version.valid_from.isoformat(),
        "valid_to": rule_version.valid_to.isoformat() if rule_version.valid_to else None,
        "is_active": rule_version.is_active,
        "previous_version_id": rule_version.previous_version_id,
        "source_delta_id": rule_version.source_delta_id,
        "rule_payload": rule_version.rule_payload
    }


def serialize_versioning_result(
    frozen_old_version: Optional[RegulatoryRuleVersion],
    new_version: RegulatoryRuleVersion
) -> dict:
    return {
        "frozen_old_version": serialize_rule_version(frozen_old_version) if frozen_old_version else None,
        "new_active_version": serialize_rule_version(new_version)
    }
