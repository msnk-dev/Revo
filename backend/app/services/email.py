import smtplib
from email.message import EmailMessage

from app.config import settings


def send_plain(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as client:
        client.send_message(message)

