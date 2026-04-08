import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def load_private_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_data(data_bytes, private_key_path):
    private_key = load_private_key(private_key_path)

    signature = private_key.sign(
        data_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    return base64.b64encode(signature).decode()


def verify_signature(data_bytes, signature_b64, public_key_path):
    public_key = load_public_key(public_key_path)
    signature = base64.b64decode(signature_b64)

    try:
        public_key.verify(
            signature,
            data_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
