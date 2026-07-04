import logging

from flask import current_app

from .crypto_utils import check_expiration, decrypt
from .kerberos_client import KerberosError, KerberosUnavailable, get_service_ticket, get_tgt

SERVICE_NAME = "chat"

logger = logging.getLogger(__name__)


class LoginError(Exception):
    """Bad credentials / invalid ticket. Safe to show the caller as a 401."""


class LoginUnavailable(Exception):
    """The AS or TGS could not be reached. Safe to show the caller as a 503."""


def login(username: str, password: str) -> dict:
    """Runs the full AS-REQ -> TGS-REQ -> AP-REQ handshake for `username`.

    Talks to the AS/TGS only over the network (kerberos_client) and verifies
    the resulting service ticket with our own pre-shared key (config) --
    no import of, or access to, the kerberos package's database.

    Raises LoginError/LoginUnavailable (safe to show the caller) on failure;
    the real reason is logged server-side so AS/TGS errors don't leak
    details that would help an attacker enumerate users.
    """
    cfg = current_app.config

    try:
        tgt, k_client_tgs = get_tgt(
            cfg["AS_HOST"], cfg["AS_PORT"], username, password)
        ticket_service, _k_client_service = get_service_ticket(
            cfg["TGS_HOST"], cfg["TGS_PORT"], tgt, k_client_tgs, SERVICE_NAME, username=username
        )
    except KerberosUnavailable as exc:
        logger.error(
            "login for %r failed: AS/TGS unreachable: %s", username, exc)
        raise LoginUnavailable("authentication service unavailable") from exc
    except KerberosError as exc:
        logger.info(
            "login failed for %r during AS/TGS exchange: %s", username, exc)
        raise LoginError("invalid credentials") from exc

    try:
        ticket_data = decrypt(cfg["CHAT_SERVICE_KEY"], ticket_service)
    except Exception as exc:
        logger.warning(
            "login failed for %r: could not verify service ticket: %s", username, exc)
        raise LoginError("invalid credentials") from exc

    if not check_expiration(ticket_data.get("valid_until")):
        logger.info("login failed for %r: expired service ticket", username)
        raise LoginError("invalid credentials")

    return {
        "username": ticket_data["username"],
        "valid_until": ticket_data["valid_until"],
    }
