from typing import Dict, Any, List, Optional


def filter_events(
    events: List[Dict[str, Any]],
    status: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    product_id: Optional[str] = None,
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

    return results
