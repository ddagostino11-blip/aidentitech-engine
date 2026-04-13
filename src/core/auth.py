from src.core.db import get_client_by_api_key


def get_client_from_api_key(api_key: str | None) -> str:
    if not api_key:
        raise ValueError("Missing API key")

    client_id = get_client_by_api_key(api_key)

    if not client_id:
        raise ValueError("Invalid API key")

    return client_id
