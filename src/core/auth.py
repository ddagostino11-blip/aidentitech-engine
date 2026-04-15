from src.core.db import get_client_by_api_key


def get_client_from_api_key(api_key: str | None) -> dict:
    if not api_key:
        raise ValueError("Missing API key")

    client = get_client_by_api_key(api_key)

    if not client:
        raise ValueError("Invalid API key")

    return {
        "client_id": client.get("client_id"),
        "role": client.get("role", "client"),
    }
