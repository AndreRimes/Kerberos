import os

from kerberos import db


def _parse_user_pairs(raw: str):
    pairs = []
    for item in filter(None, (p.strip() for p in raw.split(","))):
        username, _, password = item.partition(":")
        if username and password:
            pairs.append((username, password))
    return pairs


def _parse_service_specs(raw: str):
    specs = []
    for item in filter(None, (s.strip() for s in raw.split(","))):
        name, _, key_hex = item.partition(":")
        if name:
            specs.append((name, bytes.fromhex(key_hex) if key_hex else None))
    return specs


def main():
    db.init_db()

    for username, password in _parse_user_pairs(os.environ.get("KERBEROS_SEED_USERS", "")):
        db.create_user(username, password)
        print(f"[seed] usuario garantido: {username}")

    for name, key in _parse_service_specs(os.environ.get("KERBEROS_SEED_SERVICES", "")):
        db.create_service(name, key=key)
        print(f"[seed] servico garantido: {name}")


if __name__ == "__main__":
    main()
