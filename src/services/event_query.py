from typing import Dict, Any, List, Optional

ALLOWED_SORT_FIELDS = {
    "created_at",
    "approved_at",
    "rejected_at",
    "deferred_at",
    "reopened_at",
    "processed_at",
    "status",
    "priority",
    "domain",
    "client_id",
    "product_id",
}

ALLOWED_ORDER_VALUES = {"asc", "desc"}

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
DEFAULT_OFFSET = 0
DEFAULT_SORT_BY = "created_at"
DEFAULT_ORDER = "desc"


def _normalize_limit(limit: Optional[int]) -> Optional[int]:
    if limit is None:
        return None

    if limit < 0:
        return DEFAULT_LIMIT

    return min(limit, MAX_LIMIT)


def _normalize_offset(offset: Optional[int]) -> int:
    if offset is None:
        return DEFAULT_OFFSET

    if offset < 0:
        return DEFAULT_OFFSET

    return offset


def _normalize_sort_by(sort_by: Optional[str]) -> str:
    if not sort_by:
        return DEFAULT_SORT_BY

    if sort_by not in ALLOWED_SORT_FIELDS:
        return DEFAULT_SORT_BY

    return sort_by


def _normalize_order(order: Optional[str]) -> str:
    if not order:
        return DEFAULT_ORDER

    normalized = order.lower().strip()

    if normalized not in ALLOWED_ORDER_VALUES:
        return DEFAULT_ORDER

    return normalized


def filter_events(
    events: List[Dict[str, Any]],
    status: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: Optional[int] = DEFAULT_LIMIT,
    offset: Optional[int] = DEFAULT_OFFSET,
    sort_by: Optional[str] = DEFAULT_SORT_BY,
    order: Optional[str] = DEFAULT_ORDER,
) -> List[Dict[str, Any]]:
    results = []

    for event in events:
        if status and event.get("status") != status:
            continue

        if domain and event.get("domain") != domain:
            continue

        if client_id and event.get("client_id") != client_id:
            continue

        if product_id and event.get("product_id") != product_id:
            continue

        results.append(event)

    safe_sort_by = _normalize_sort_by(sort_by)
    safe_order = _normalize_order(order)
    safe_limit = _normalize_limit(limit)
    safe_offset = _normalize_offset(offset)

    reverse = safe_order == "desc"

    results = sorted(
        results,
        key=lambda event: (
            event.get(safe_sort_by) is None,
            str(event.get(safe_sort_by) or "")
        ),
        reverse=reverse
    )

    if safe_limit is None:
        return results

    return results[safe_offset:safe_offset + safe_limit]
