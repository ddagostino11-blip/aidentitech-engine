def normalize_payload(payload: dict | None) -> dict:
    """
    Normalizzazione generica del payload.

    Regole:
    - se il payload è già flat, lo restituisce così com'è
    - se il payload usa struttura enterprise con `entity` e `data`,
      fa merge generico dei blocchi
    - nessuna logica di dominio nel core
    """
    if not isinstance(payload, dict):
        return {}

    entity = payload.get("entity")
    data = payload.get("data")

    # Caso 1: payload già flat / già normalizzato
    if not isinstance(entity, dict) and not isinstance(data, dict):
        return payload

    normalized = {}

    if isinstance(entity, dict):
        normalized.update(entity)

    if isinstance(data, dict):
        normalized.update(data)

    return normalized
