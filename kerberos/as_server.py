import socket
import time
import json

from kerberos import config, db
from kerberos.crypto_utils import encrypt, gen_session_key


def handle_client(conn):
    raw = conn.recv(4096)
    request = json.loads(raw.decode())

    username = request.get("username")

    if not username:
        conn.sendall(json.dumps({"error": "username is required"}).encode())
        return

    try:
        key_user = db.get_user_key(username)
        salt = db.get_user_salt(username)
    except KeyError:
        conn.sendall(json.dumps({"error": "unknown user"}).encode())
        return

    k_client_tgs = gen_session_key()

    tgt = encrypt(
        config.AS_TGS_KEY,
        {
            "username": username,
            "k_client_tgs": k_client_tgs.hex(),
            "valid_until": time.time() + config.TICKET_LIFETIME,
        },
    )

    response = {
        "k_client_tgs_enc": encrypt(key_user, {"k_client_tgs": k_client_tgs.hex()}),
        "tgt": tgt,
        "salt": salt.hex(),
    }

    conn.sendall(json.dumps(response).encode())
    print(f"[AS] Resposta enviada para o cliente {username}")


def main():
    _ = config.AS_TGS_KEY
    db.init_db()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((config.AS_HOST, config.AS_PORT))
        s.listen()
        print(f"[AS] Escutando em {config.AS_HOST}:{config.AS_PORT}")

        while True:
            conn, _ = s.accept()
            with conn:
                handle_client(conn)


if __name__ == "__main__":
    main()
