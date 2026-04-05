from typing import Dict, Any, List

from src.regulatory.diff_engine import build_regulatory_deltas
from src.regulatory.models import RegulatoryDelta


def simulate_regulatory_change_detection() -> List[RegulatoryDelta]:
    """
    Simula il rilevamento di un cambio normativo.
    Per ora usa due strutture statiche:
    - old_structure = normativa precedente
    - new_structure = normativa aggiornata
    """

    old_structure: Dict[str, Any] = {
        "rules": {
            "temperature_warning_high": 8,
            "temperature_critical_high": 25,
            "gmp_required": True
        }
    }

    new_structure: Dict[str, Any] = {
        "rules": {
            "temperature_warning_high": 6,
            "temperature_critical_high": 20,
            "gmp_required": True,
            "stability_report_required": True
        }
    }

    deltas = build_regulatory_deltas(
        old_structure=old_structure,
        new_structure=new_structure,
        document_id="DOC-EMA-001",
        source_id="EMA",
        domain="pharma",
        jurisdiction="EU"
    )

    return deltas


def serialize_deltas(deltas: List[RegulatoryDelta]) -> List[Dict[str, Any]]:
    """
    Converte gli oggetti RegulatoryDelta in dict semplici,
    utili per debug, API o stampa.
    """
    serialized = []

    for delta in deltas:
        serialized.append({
            "delta_id": delta.delta_id,
            "document_id": delta.document_id,
            "source_id": delta.source_id,
            "domain": delta.domain,
            "jurisdiction": delta.jurisdiction,
            "detected_at": delta.detected_at.isoformat(),
            "change_type": delta.change_type,
            "rule_id": delta.rule_id,
            "old_value": delta.old_value,
            "new_value": delta.new_value,
            "impact_level": delta.impact_level,
            "summary": delta.summary,
            "details": delta.details,
            "metadata": delta.metadata,
        })

    return serialized


def run_regulatory_detection_demo() -> Dict[str, Any]:
    """
    Primo orchestratore regulatory.
    Simula una detection completa e restituisce output strutturato.
    """
    deltas = simulate_regulatory_change_detection()

    return {
        "status": "ok",
        "detected_changes": len(deltas),
        "deltas": serialize_deltas(deltas)
    }
