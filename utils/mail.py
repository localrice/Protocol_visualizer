"""SMTP delivery and application-level conversation events."""

from __future__ import annotations

import os
import smtplib
import socket
from email.message import EmailMessage

from utils.protocol import event

SMTP_TIMEOUT = 15


class MailError(Exception):
    """A safe, user-facing SMTP error without credential details."""


def _event(sequence: int, direction: str, event_type: str, message: str,
           fields: dict[str, str] | None = None, delay: int = 700,
           protocol: str = "SMTP") -> dict:
    return event(sequence, protocol, direction, event_type, message, fields or {}, delay)


def _response_text(reply: bytes | str) -> str:
    if isinstance(reply, bytes):
        return reply.decode("utf-8", errors="replace")
    return str(reply)


def _settings() -> tuple[str, int, str, str, str]:
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "").strip()
    raw_port = os.environ.get("SMTP_PORT", "587").strip()
    if not all((host, username, password, sender)):
        raise MailError("SMTP is not configured on the server")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise MailError("SMTP_PORT must be a number") from exc
    if not 1 <= port <= 65535:
        raise MailError("SMTP_PORT must be between 1 and 65535")
    return host, port, username, password, sender


def _validate_message(to: str, subject: str, body: str) -> None:
    if not to or "@" not in to or len(to) > 254:
        raise MailError("Enter a recipient email address")
    if not subject.strip() or len(subject) > 200:
        raise MailError("Enter a subject up to 200 characters")
    if not body.strip() or len(body) > 4000:
        raise MailError("Enter a message body up to 4,000 characters")


class _RecordingMixin:
    """Record SMTP commands and replies while keeping AUTH data private."""

    def __init__(self, events: list[dict], *args, **kwargs):
        self._events = events
        self._data_pending = False
        super().__init__(*args, **kwargs)

    def _record(self, direction: str, event_type: str, message: str) -> None:
        self._events.append(_event(len(self._events) + 1, direction, event_type, message))

    def putcmd(self, cmd, args=""):
        command = cmd.upper()
        if command == "AUTH":
            mechanism = str(args).split(" ", 1)[0]
            display = f"AUTH {mechanism} (credentials hidden)".strip()
        else:
            display = command if not args else f"{command} {args}"
        self._record("client-to-server", "command", display)
        return super().putcmd(cmd, args)

    def getreply(self):
        code, reply = super().getreply()
        self._record("server-to-client", "response", f"{code} {_response_text(reply)}")
        self._data_pending = code == 354
        return code, reply

    def send(self, data):
        result = super().send(data)
        if self._data_pending:
            text = data.decode(self.command_encoding, errors="replace") if isinstance(data, bytes) else str(data)
            if text.endswith("\r\n.\r\n"):
                text = text[:-5]
            self._record("client-to-server", "data", text)
            self._data_pending = False
        return result


class RecordingSMTP(_RecordingMixin, smtplib.SMTP):
    pass


class RecordingSMTPSSL(_RecordingMixin, smtplib.SMTP_SSL):
    pass


def send_mail(to: str, subject: str, body: str) -> dict:
    """Send one message and return only the SMTP commands/replies observed."""
    _validate_message(to, subject, body)
    host, port, username, password, sender = _settings()
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    events: list[dict] = []
    smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None

    try:
        if port == 465:
            smtp = RecordingSMTPSSL(events, timeout=SMTP_TIMEOUT)
        else:
            smtp = RecordingSMTP(events, timeout=SMTP_TIMEOUT)
        smtp.connect(host, port)
        events.insert(0, _event(1, "client-to-server", "connect", "TCP connection established", {
            "Destination": f"{host}:{port}",
        }, protocol="TCP"))
        for event_number, recorded_event in enumerate(events, start=1):
            recorded_event["sequence"] = event_number

        ehlo_name = socket.getfqdn() or "localhost"
        smtp.ehlo(ehlo_name)

        if port != 465:
            smtp.starttls()
            smtp.ehlo(ehlo_name)

        smtp.login(username, password)

        smtp.mail(sender)

        smtp.rcpt(to)

        smtp.data(message.as_bytes())

        smtp.quit()
        return {"success": True, "activity": "mail", "events": events, "real": True}
    except (smtplib.SMTPException, OSError, socket.timeout) as exc:
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            message_text = "SMTP authentication failed"
        elif isinstance(exc, smtplib.SMTPServerDisconnected):
            message_text = "SMTP server disconnected"
        elif isinstance(exc, smtplib.SMTPRecipientsRefused):
            message_text = "SMTP server rejected the recipient"
        elif isinstance(exc, smtplib.SMTPDataError):
            message_text = "SMTP server rejected the message data"
        else:
            message_text = "SMTP delivery failed"
        raise MailError(message_text) from exc
    finally:
        if smtp is not None:
            try:
                smtp.close()
            except OSError:
                pass
