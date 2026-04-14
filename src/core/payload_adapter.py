def normalize_payload(input_payload: dict) -> dict:
    """
    Converte payload enterprise → payload engine interno
    """

    # fallback compatibilità (se già formato vecchio)
    if "product_id" in input_payload:
        return input_payload

    data = input_payload.get("data", {})
    context = input_payload.get("context", {})
    entity = input_payload.get("entity", {})

    return {
        "product_id": entity.get("product_id"),
        "batch": entity.get("batch"),
        "gmp_compliant": data.get("gmp_compliant"),
        "temperature": data.get("temperature"),
        "batch_record_reviewed": data.get("batch_record_reviewed"),
        "deviation_open": data.get("deviation_open"),
        "capa_open": data.get("capa_open"),
        # puoi estendere qui senza rompere il core
    }
