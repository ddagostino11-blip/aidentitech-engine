import json
import hashlib
from datetime import datetime, timezone


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def canonical_hash(data):
    return hashlib.sha256(
        canonical_json(data).encode("utf-8")
    ).hexdigest()
