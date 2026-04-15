from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from src.core.db import list_api_keys, revoke_api_key, rotate_api_key
from src.core.auth import get_client_from_api_key
from src.core.ledger_chain import verify_chain

router = APIRouter(tags=["admin"])


class RevokeApiKeyRequest(BaseModel):
    api_key: str


class RotateApiKeyRequest(BaseModel):
    api_key: str


def _require_admin(x_api_key: str | None):
    try:
        return get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/admin/api-keys")
def get_api_keys():
    return list_api_keys()


@router.post("/admin/api-keys/revoke")
def revoke_api_key_endpoint(request: RevokeApiKeyRequest):
    revoked = revoke_api_key(request.api_key)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "status": "revoked",
        "api_key": request.api_key,
    }


@router.post("/admin/api-keys/rotate")
def rotate_api_key_endpoint(request: RotateApiKeyRequest):
    new_key = rotate_api_key(request.api_key)

    if not new_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "status": "rotated",
        "old_api_key": request.api_key,
        "new_api_key": new_key,
    }


@router.get("/admin/ledger/verify")
def verify_ledger(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    admin_client = _require_admin(x_api_key)

    ledger_ok = verify_chain()

    return {
        "requested_by": admin_client,
        "ledger_ok": ledger_ok,
    }
