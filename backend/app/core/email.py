from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """Send an email via SMTP (aiosmtplib). Falls back to console log in dev.

    TLS mode is auto-selected from the port:
      * 465  → implicit TLS (``use_tls=True``)        — Gmail SMTPS
      * 587  → STARTTLS upgrade (``start_tls=True``)  — Gmail submission, most ISPs
      * else → plaintext (Mailpit on 1025, local relays on 25)

    Credentials are stripped of stray whitespace because Gmail App Passwords
    are usually pasted with trailing spaces from the "copy" button.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_ADDRESS}>"
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    username = (settings.SMTP_USER or "").strip() or None
    password = (settings.SMTP_PASSWORD or "").strip() or None
    # Gmail App Passwords are 16 chars but presented as "xxxx xxxx xxxx xxxx".
    # Some clients fail to authenticate when the spaces are kept, so for Gmail
    # specifically we remove ALL whitespace from the password. Other providers
    # are left untouched in case a passphrase-style password contains spaces.
    if password and "gmail" in (settings.SMTP_HOST or "").lower():
        password = "".join(password.split())
    port = settings.SMTP_PORT

    # Pick TLS mode from port. aiosmtplib refuses `start_tls=True` together
    # with `use_tls=True`, so only one is set.
    send_kwargs: dict = {
        "hostname": settings.SMTP_HOST,
        "port": port,
        "username": username,
        "password": password,
    }
    if port == 465:
        send_kwargs["use_tls"] = True
    elif port == 587:
        send_kwargs["start_tls"] = True
    else:
        send_kwargs["start_tls"] = False

    try:
        await aiosmtplib.send(msg, **send_kwargs)
        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as exc:
        logger.error("email_failed", to=to, subject=subject, error=str(exc))
        if settings.ENV == "local":
            _log_to_console(to, subject, html_body)
        return False


def _log_to_console(to: str, subject: str, body: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"EMAIL TO:      {to}")
    print(f"SUBJECT:       {subject}")
    print(f"{'=' * 60}")
    print(body)
    print(f"{'=' * 60}\n")
