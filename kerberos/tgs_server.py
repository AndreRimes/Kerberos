import socket
import json

from kerberos import config, db
from kerberos.crypto_utils import encrypt, decrypt, check_expiration, gen_session_key, check_authenticator


def handle_client(conn):
    raw = conn.recv(4096)
    request = json.loads(raw.decode())

    tgt = request.get("tgt")
    service = request.get("service")
    authenticator = request.get("authenticator")

    if not tgt or not service or not authenticator:
        conn.sendall(json.dumps(
            {"error": "tgt, service, and authenticator are required"}).encode())
        return

    try:
        tgt_data = decrypt(config.AS_TGS_KEY, tgt)
    except Exception:
        conn.sendall(json.dumps({"error": "invalid tgt"}).encode())
        return

    k_client_tgs = bytes.fromhex(tgt_data["k_client_tgs"])

    try:
        auth_data = check_authenticator(k_client_tgs, authenticator)
    except Exception:
        conn.sendall(json.dumps({"error": "invalid authenticator"}).encode())
        return

    if auth_data.get("username") != tgt_data.get("username"):
        conn.sendall(json.dumps({"error": "invalid authenticator"}).encode())
        return

    if not check_expiration(tgt_data.get("valid_until")):
        conn.sendall(json.dumps({"error": "expired tgt"}).encode())
        return

    try:
        key_service = db.get_service_key(service)
    except KeyError:
        conn.sendall(json.dumps({"error": "unknown service"}).encode())
        return

    k_client_service = gen_session_key()

    ticket_service = encrypt(
        key_service,
        {
            "username": tgt_data.get("username"),
            "k_client_service": k_client_service.hex(),
            "valid_until": tgt_data.get("valid_until"),
        },
    )

    response = {
        "ticket_service": ticket_service,
        "k_client_service_enc": encrypt(
            k_client_tgs, {"k_client_service": k_client_service.hex()}
        ),
    }

    conn.sendall(json.dumps(response).encode())
    print(f"[TGS] Resposta enviada para o cliente {tgt_data.get('username')}")


def main():
    _ = config.AS_TGS_KEY
    db.init_db()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((config.TGS_HOST, config.TGS_PORT))
        s.listen()
        print(f"[TGS] Escutando em {config.TGS_HOST}:{config.TGS_PORT}")

        while True:
            conn, _ = s.accept()
            with conn:
                handle_client(conn)


if __name__ == "__main__":
    main()
