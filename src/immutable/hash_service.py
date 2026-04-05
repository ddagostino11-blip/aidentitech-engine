import hashlib
import json
from typing import Any, Dict


def canonicalize_data(data: Any) -> str:
    """
    Trasforma un oggetto Python in una stringa JSON stabile e ordinata.
    Serve per ottenere sempre lo stesso hash a parità di contenuto.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hash_text(text: str) -> str:
    """
    Calcola hash SHA-256 di una stringa.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_hash_data(data: Any) -> str:
    """
    Calcola hash SHA-256 di un oggetto Python serializzabile.
    """
    canonical_text = canonicalize_data(data)
    return sha256_hash_text(canonical_text)


def build_hash_record(record_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Costruisce un record hashabile con:
    - tipo record
    - payload originale
    - payload canonicalizzato
    - hash finale
    """
    canonical_payload = canonicalize_data(payload)
    digest = sha256_hash_text(canonical_payload)

    return {
        "record_type": record_type,
        "payload": payload,
        "canonical_payload": canonical_payload,
        "sha256": digest
    }
