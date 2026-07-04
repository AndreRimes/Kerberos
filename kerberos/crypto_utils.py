import json
import os
import time
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_key(password: str, salt: bytes, length: int = 32) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=310_000,
    )
    return kdf.derive(password.encode())


def encrypt(key: bytes, data: dict) -> str:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    payload = nonce + ciphertext
    return payload.hex()


def decrypt(key: bytes, token_hex: str) -> dict:
    payload = bytes.fromhex(token_hex)
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())


def gen_session_key() -> bytes:
    return os.urandom(32)


def check_expiration(valid_until: float) -> bool:
    return valid_until > time.time()


def check_authenticator(session_key: bytes, token_hex: str, max_skew: float = 60.0) -> dict:
    data = decrypt(session_key, token_hex)
    if abs(time.time() - data["timestamp"]) > max_skew:
        raise ValueError("Autenticador expirado (possível replay)")

    return data
