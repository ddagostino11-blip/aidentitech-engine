from typing import Dict, Any, List, Optional


def filter_events(
    events: List[Dict[str, Any]],
    status: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    sort_by: Optional[str] = "created_at",
    order: Optional[str] = "desc",
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

    reverse = order == "desc"

    if sort_by:
        results = sorted(
            results,
            key=lambda event: event.get(sort_by) or "",
            reverse=reverse
        )

    safe_offset = max(offset or 0, 0)
    safe_limit = max(limit or 0, 0)

    if safe_limit == 0:
        return results[safe_offset:]

    return results[safe_offset:safe_offset + safe_limit]
