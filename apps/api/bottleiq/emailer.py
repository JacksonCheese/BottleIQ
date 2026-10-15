"""Transactional account email; tokens never enter logs or API responses."""

import smtplib
import ssl
from email.message import EmailMessage

from bottleiq.config import settings


def send_account_email(recipient: str, subject: str, body: str) -> None:
    config = settings()
    if not config.smtp_host or not config.smtp_from:
        raise RuntimeError("Account email is not configured")
    message = EmailMessage()
    message["From"] = config.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if config.smtp_user:
            smtp.login(config.smtp_user, config.smtp_password)
        smtp.send_message(message)
