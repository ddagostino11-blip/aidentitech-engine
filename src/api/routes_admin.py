from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.db import list_api_keys, revoke_api_key, rotate_api_key

router = APIRouter(tags=["admin"])


class RevokeApiKeyRequest(BaseModel):
    api_key: str


class RotateApiKeyRequest(BaseModel):
    api_key: str


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
