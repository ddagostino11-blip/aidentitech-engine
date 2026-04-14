def validate_payload(payload: dict | None):
    payload = payload or {}

    required_fields = [
        "product_id",
        "batch",
        "gmp_compliant",
        "temperature",
    ]

    missing_fields = [
        field for field in required_fields
        if field not in payload or payload.get(field) is None
    ]

    if missing_fields:
        raise ValueError(
            f"Missing required payload fields for pharma: {', '.join(missing_fields)}"
        )
