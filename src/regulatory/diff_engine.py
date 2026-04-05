from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4

from src.regulatory.models import RegulatoryDelta


def _impact_from_change(old_value: Any, new_value: Any) -> str:
    if old_value is None and new_value is not None:
        return "HIGH"

    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        difference = abs(new_value - old_value)

        if difference >= 10:
            return "CRITICAL"
        if difference >= 5:
            return "HIGH"
        if difference > 0:
            return "MEDIUM"

    if old_value != new_value:
        return "MEDIUM"

    return "LOW"


def build_regulatory_deltas(
    old_structure: Dict[str, Any],
    new_structure: Dict[str, Any],
    *,
    document_id: str,
    source_id: str,
    domain: str,
    jurisdiction: str
) -> List[RegulatoryDelta]:
    deltas: List[RegulatoryDelta] = []

    old_rules = old_structure.get("rules", {})
    new_rules = new_structure.get("rules", {})

    all_rule_ids = sorted(set(old_rules.keys()) | set(new_rules.keys()))

    for rule_id in all_rule_ids:
        old_value = old_rules.get(rule_id)
        new_value = new_rules.get(rule_id)

        if old_value == new_value:
            continue

        if rule_id not in old_rules:
            change_type = "rule_created"
            summary = f"New rule '{rule_id}' created."
        elif rule_id not in new_rules:
            change_type = "rule_removed"
            summary = f"Rule '{rule_id}' removed."
        else:
            change_type = "rule_updated"
            summary = f"Rule '{rule_id}' updated."

        impact_level = _impact_from_change(old_value, new_value)

        details = [
            f"Old value: {old_value}",
            f"New value: {new_value}",
            f"Detected change type: {change_type}"
        ]

        deltas.append(
            RegulatoryDelta(
                delta_id=str(uuid4()),
                document_id=document_id,
                source_id=source_id,
                domain=domain,
                jurisdiction=jurisdiction,
                detected_at=datetime.utcnow(),
                change_type=change_type,
                rule_id=rule_id,
                old_value=old_value,
                new_value=new_value,
                impact_level=impact_level,
                summary=summary,
                details=details,
                metadata={
                    "old_exists": rule_id in old_rules,
                    "new_exists": rule_id in new_rules
                }
            )
        )

    return deltas
