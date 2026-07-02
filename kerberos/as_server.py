import socket
import json


def handle_client(conn):
    raw = conn.recv(4096)
    request = json.loads(raw.decode())

    username = request.get("username", None)

    if not username:
        pass

    key_user = get_user_key(username)

    session_key_tgs = gen_session_key()

    tgt = encrypt(KEY_AS_TGS,
        {
            


        }
    )


        






def main():
    HOST, PORT = "127.0.0.1", 5000

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[AS] Escutando em {HOST}:{PORT}")

        while True:
            conn, _ = s.accept()
            with conn:
                handle_client(conn)

if __name__ == "__main__":
    main()
