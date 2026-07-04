"""Crypto primitives for talking to the Kerberos AS/TGS.

Deliberately duplicated from kerberos/crypto_utils.py rather than imported:
the chat backend and the kerberos package are separate systems that only
talk over the network. This file must stay wire-compatible with it --
same PBKDF2 params, same AES-GCM nonce-prefixed hex payload format.
"""
import os
import json
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


def decrypt(key: bytes, token_hex: str) -> dict:
    payload = bytes.fromhex(token_hex)
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())


def check_expiration(valid_until: float) -> bool:
    return valid_until > time.time()


def encrypt(key: bytes, data: dict) -> str:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    payload = nonce + ciphertext
    return payload.hex()


def make_authenticator(session_key: bytes, username: str) -> str:
    return encrypt(session_key, {"username": username, "timestamp": time.time()})
