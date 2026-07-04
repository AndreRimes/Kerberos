import os


def _require_hex_key(name: str, length: int = 32) -> bytes:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name} "
            "(must match the key used to seed the \"chat\" service, e.g. "
            "KERBEROS_SEED_SERVICES=chat:<hex> when running `python -m kerberos.seed`)"
        )
    key = bytes.fromhex(value)
    if len(key) != length:
        raise RuntimeError(f"{name} must decode to {length} bytes, got {len(key)}")
    return key


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    CHAT_DB_PATH = os.environ.get("CHAT_DB_PATH", "chat.db")

    AS_HOST = os.environ.get("AS_CONNECT_HOST", "localhost")
    AS_PORT = int(os.environ.get("AS_PORT", "5000"))
    TGS_HOST = os.environ.get("TGS_CONNECT_HOST", "localhost")
    TGS_PORT = int(os.environ.get("TGS_PORT", "5001"))

    CHAT_SERVICE_KEY = _require_hex_key("KERBEROS_CHAT_SERVICE_KEY")
