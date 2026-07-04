import json
import socket

from .crypto_utils import decrypt, derive_key, make_authenticator


class KerberosError(Exception):
    pass


class KerberosUnavailable(KerberosError):
    pass


def _request(host: str, port: int, payload: dict) -> dict:
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(json.dumps(payload).encode())
            raw = sock.recv(4096)
        response = json.loads(raw.decode())
    except OSError as exc:
        raise KerberosUnavailable(f"could not reach {host}:{port}") from exc

    if "error" in response:
        raise KerberosError(response["error"])
    return response


def get_tgt(host: str, port: int, username: str, password: str) -> tuple[str, bytes]:
    response = _request(host, port, {"username": username})

    salt = bytes.fromhex(response["salt"])
    key_user = derive_key(password, salt)

    try:
        session_data = decrypt(key_user, response["k_client_tgs_enc"])
    except Exception as exc:
        raise KerberosError("invalid credentials") from exc

    return response["tgt"], bytes.fromhex(session_data["k_client_tgs"])


def get_service_ticket(
    host: str, port: int, tgt: str, k_client_tgs: bytes, service: str, username: str
) -> tuple[str, bytes]:
    response = _request(
        host,
        port,
        {
            "tgt": tgt,
            "service": service,
            "authenticator": make_authenticator(k_client_tgs, username)
        }
    )

    try:
        session_data = decrypt(k_client_tgs, response["k_client_service_enc"])
    except Exception as exc:
        raise KerberosError("invalid tgs response") from exc

    return response["ticket_service"], bytes.fromhex(session_data["k_client_service"])
