"""Simulated SMTP protocol visualization based on captured development exchange."""

from __future__ import annotations

import os
import socket

from utils.protocol import event


class MailError(Exception):
    """A safe, user-facing error message without credential details."""


def _event(sequence: int, direction: str, event_type: str, message: str,
           fields: dict[str, str] | None = None, delay: int = 700,
           protocol: str = "SMTP") -> dict:
    return event(sequence, protocol, direction, event_type, message, fields or {}, delay)


def _validate_message(to: str, subject: str, body: str) -> None:
    if not to or "@" not in to or len(to) > 254:
        raise MailError("Enter a recipient email address")
    if not subject.strip() or len(subject) > 200:
        raise MailError("Enter a subject up to 200 characters")
    if not body.strip() or len(body) > 4000:
        raise MailError("Enter a message body up to 4,000 characters")


def _simulate_smtp_events(to: str, subject: str, body: str) -> list[dict]:
    """Generate the simulated SMTP exchange based on the captured development session."""
    client_host = socket.getfqdn() or "localhost"

    raw_from = os.environ.get("SMTP_FROM", "Kinjal's Protocol Visualizer").strip() or "Kinjal's Protocol Visualizer"
    raw_user = os.environ.get("SMTP_USERNAME", "mortestingkarone@gmail.com").strip() or "visualizer@kinjalboro.me"

    if "@" in raw_from:
        sender_email = raw_from
        from_header = raw_from
    else:
        sender_email = raw_user if "@" in raw_user else "visualizer@kinjalboro.me"
        from_header = f"{raw_from} <{sender_email}>"

    message_data = (
        f"From: {from_header}\r\n"
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
        f"{body}"
    )

    steps = [
        # (protocol, direction, event_type, message, fields)
        ("TCP", "client-to-server", "connect", "TCP connection established", {"Destination": "smtp.gmail.com:587"}),
        ("SMTP", "server-to-client", "response", "220 smtp.gmail.com ESMTP", {}),
        ("SMTP", "client-to-server", "command", f"EHLO {client_host}", {}),
        ("SMTP", "server-to-client", "response", "250 smtp.gmail.com at your service", {}),
        ("SMTP", "client-to-server", "command", "STARTTLS", {}),
        ("SMTP", "server-to-client", "response", "220 2.0.0 Ready to start TLS", {}),
        ("SMTP", "client-to-server", "command", f"EHLO {client_host}", {}),
        ("SMTP", "server-to-client", "response", "250 smtp.gmail.com at your service", {}),
        ("SMTP", "client-to-server", "command", "AUTH PLAIN (credentials hidden)", {}),
        ("SMTP", "server-to-client", "response", "235 2.7.0 Accepted", {}),
        ("SMTP", "client-to-server", "command", f"MAIL FROM:<{sender_email}>", {}),
        ("SMTP", "server-to-client", "response", "250 2.1.0 OK", {}),
        ("SMTP", "client-to-server", "command", f"RCPT TO:<{to}>", {}),
        ("SMTP", "server-to-client", "response", "250 2.1.5 OK", {}),
        ("SMTP", "client-to-server", "command", "DATA", {}),
        ("SMTP", "server-to-client", "response", "354 Go ahead", {}),
        ("SMTP", "client-to-server", "data", message_data, {}),
        ("SMTP", "server-to-client", "response", "250 2.0.0 OK", {}),
        ("SMTP", "client-to-server", "command", "QUIT", {}),
        ("SMTP", "server-to-client", "response", "221 2.0.0 closing connection", {}),
    ]

    events = []
    for seq, (proto, direction, event_type, msg, fields) in enumerate(steps, start=1):
        events.append(_event(seq, direction, event_type, msg, fields=fields, delay=700, protocol=proto))
    return events


def send_mail(to: str, subject: str, body: str) -> dict:
    """Validate input and return the simulated SMTP protocol exchange."""
    to = to.strip()
    _validate_message(to, subject, body)
    events = _simulate_smtp_events(to, subject, body)
    return {"success": True, "activity": "mail", "events": events, "simulated": True}

