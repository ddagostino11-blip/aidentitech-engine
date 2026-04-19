import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes_raw()
    public_bytes = public_key.public_bytes_raw()

    return {
        "private": base64.b64encode(private_bytes).decode(),
        "public": base64.b64encode(public_bytes).decode(),
    }


def load_private_key(b64_private: str) -> Ed25519PrivateKey:
    raw = base64.b64decode(b64_private)
    return Ed25519PrivateKey.from_private_bytes(raw)


def load_public_key(b64_public: str) -> Ed25519PublicKey:
    raw = base64.b64decode(b64_public)
    return Ed25519PublicKey.from_public_bytes(raw)


def sign_payload(private_key_b64: str, payload_bytes: bytes) -> str:
    key = load_private_key(private_key_b64)
    signature = key.sign(payload_bytes)
    return base64.b64encode(signature).decode()


def verify_signature(public_key_b64: str, payload_bytes: bytes, signature_b64: str) -> bool:
    try:
        key = load_public_key(public_key_b64)
        signature = base64.b64decode(signature_b64)
        key.verify(signature, payload_bytes)
        return True
    except Exception:
        return False
