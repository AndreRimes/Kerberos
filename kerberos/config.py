import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _require_hex_key(name: str, length: int = 32) -> bytes:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name} "
            f"(generate one with: python -c \"import os; print(os.urandom({length}).hex())\")"
        )
    key = bytes.fromhex(value)
    if len(key) != length:
        raise RuntimeError(
            f"{name} must decode to {length} bytes, got {len(key)}")
    return key


DB_PATH = os.environ.get("KERBEROS_DB_PATH", "kerberos.db")
TICKET_LIFETIME = int(os.environ.get("KERBEROS_TICKET_LIFETIME", "3600"))

AS_HOST = os.environ.get("AS_HOST", "0.0.0.0")
AS_PORT = int(os.environ.get("AS_PORT", "5000"))
AS_CONNECT_HOST = os.environ.get("AS_CONNECT_HOST", "localhost")

TGS_HOST = os.environ.get("TGS_HOST", "0.0.0.0")
TGS_PORT = int(os.environ.get("TGS_PORT", "5001"))
TGS_CONNECT_HOST = os.environ.get("TGS_CONNECT_HOST", "localhost")


def __getattr__(name: str):
    if name == "AS_TGS_KEY":
        return _require_hex_key("KERBEROS_AS_TGS_KEY")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
