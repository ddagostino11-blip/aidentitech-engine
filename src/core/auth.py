API_KEYS = {
    "key_test_client_1": "test_client_1",
    "key_test_client_2": "test_client_2",
    "key_test_client_3": "test_client_3",
}


def get_client_from_api_key(api_key: str | None) -> str:
    if not api_key:
        raise ValueError("Missing API key")

    client_id = API_KEYS.get(api_key)

    if not client_id:
        raise ValueError("Invalid API key")

    return client_id
