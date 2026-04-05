from datetime import datetime
from typing import List
from uuid import uuid4

from src.regulatory.models import RegulatoryDelta, LegalReviewTask


def _priority_from_impact(impact_level: str) -> str:
    mapping = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL"
    }
    return mapping.get(impact_level, "MEDIUM")


def create_legal_review_tasks(
    deltas: List[RegulatoryDelta],
    assigned_team: str = "GLOBAL_LEGAL"
) -> List[LegalReviewTask]:
    tasks: List[LegalReviewTask] = []

    for delta in deltas:
        task = LegalReviewTask(
            review_id=str(uuid4()),
            delta_id=delta.delta_id,
            assigned_team=assigned_team,
            priority=_priority_from_impact(delta.impact_level),
            status="pending_review",
            created_at=datetime.utcnow(),
            reviewed_at=None,
            reviewer_name=None,
            decision=None,
            notes=None
        )
        tasks.append(task)

    return tasks


def serialize_review_tasks(tasks: List[LegalReviewTask]) -> list:
    serialized = []

    for task in tasks:
        serialized.append({
            "review_id": task.review_id,
            "delta_id": task.delta_id,
            "assigned_team": task.assigned_team,
            "priority": task.priority,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
            "reviewer_name": task.reviewer_name,
            "decision": task.decision,
            "notes": task.notes
        })

    return serialized
