"""Protocol dashboard Flask application."""

from __future__ import annotations

import ipaddress
import os
import socket
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import dns.exception
import dns.resolver
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# Replace this with the real repository URL when it is known.
GITHUB_URL = "https://github.com/your-username/protocol-dashboard"
USER_AGENT = "ProtocolDashboard/1.0"
REQUEST_TIMEOUT = 8
MAX_BODY_BYTES = 128 * 1024
DNS_RESOLVER = os.environ.get("DNS_RESOLVER", "1.1.1.1")
DNS_TIMEOUT = 3


class NoRedirectHandler(HTTPRedirectHandler):
    """Prevent urllib from following an unvalidated redirect automatically."""

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def event(sequence: int, protocol: str, direction: str, event_type: str,
          message: str, fields: dict[str, str], delay: int = 800) -> dict:
    return {
        "sequence": sequence,
        "protocol": protocol,
        "direction": direction,
        "type": event_type,
        "message": message,
        "fields": fields,
        "timestamp": now_iso(),
        "delay": delay,
    }


def error_response(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def requested_json() -> dict | None:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None


def is_public_ip(address: str) -> bool:
    parsed = ipaddress.ip_address(address)
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def resolve_public_host(hostname: str) -> list[str]:
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [DNS_RESOLVER]
    resolver.timeout = DNS_TIMEOUT
    resolver.lifetime = DNS_TIMEOUT
    addresses = set()
    try:
        for record_type in ("A", "AAAA"):
            try:
                answers = resolver.resolve(hostname, record_type)
            except dns.resolver.NoAnswer:
                continue
            addresses.update(answer.to_text() for answer in answers)
    except (dns.exception.DNSException, OSError) as exc:
        raise ValueError(f"DNS lookup failed for {hostname}") from exc

    addresses = sorted(addresses)
    if not addresses:
        raise ValueError(f"DNS lookup returned no addresses for {hostname}")
    if not all(is_public_ip(address) for address in addresses):
        raise ValueError("Private or internal destinations are blocked")
    return addresses


def validate_url(value: str) -> tuple[str, str, str]:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Enter a valid HTTP or HTTPS URL")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid HTTP or HTTPS URL") from exc
    if port not in {None, 80, 443}:
        raise ValueError("Only standard HTTP and HTTPS ports are allowed")
    normalized = parsed.geturl()
    return normalized, parsed.hostname, parsed.path or "/"


def browse(url: str) -> dict:
    normalized_url, hostname, path = validate_url(url)
    addresses = resolve_public_host(hostname)
    scheme = urlparse(normalized_url).scheme.upper()
    events = [
        event(1, "DNS", "client-to-server", "query", f"DNS Query: A {hostname}", {
            "Name": hostname, "Type": "A / AAAA", "Resolver": f"Recursive Resolver {DNS_RESOLVER}:53"
        }),
        event(2, "DNS", "server-to-client", "response", "DNS Response: NOERROR", {
            "Resolver": f"Recursive Resolver {DNS_RESOLVER}:53", "Answer": ", ".join(addresses), "Status": "resolved"
        }),
    ]

    next_sequence = 3
    if scheme == "HTTPS":
        events.extend([
            event(next_sequence, "TCP", "client-to-server", "connect", "TCP connection established", {
                "Destination": f"{hostname}:443", "Transport": "TCP"
            }),
            event(next_sequence + 1, "TLS", "client-to-server", "handshake", "TLS handshake", {
                "Visibility": "Encrypted application data follows; no plaintext wire capture.", "Transport": "HTTPS"
            }),
        ])
        next_sequence += 2

    request_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    http_request = Request(normalized_url, headers=request_headers, method="GET")
    started = time.monotonic()
    try:
        opener = build_opener(NoRedirectHandler())
        with opener.open(http_request, timeout=REQUEST_TIMEOUT) as response:
            body = response.read(MAX_BODY_BYTES + 1)
            status = response.status
            reason = response.reason or ""
            response_headers = response.headers
            final_url = response.geturl()
    except HTTPError as exc:
        body = exc.read(MAX_BODY_BYTES + 1)
        status = exc.code
        reason = exc.reason or ""
        response_headers = exc.headers
        final_url = normalized_url
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError("The request timed out") from exc
    except URLError as exc:
        raise RuntimeError(f"Connection failed: {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Connection failed: {exc}") from exc

    elapsed_ms = round((time.monotonic() - started) * 1000)
    content_type = response_headers.get("Content-Type", "unknown")
    content_length = response_headers.get("Content-Length", str(len(body)))
    response_fields = {
        "Status": f"{status} {reason}".strip(),
        "Content-Type": content_type,
        "Content-Length": content_length,
        "Elapsed": f"{elapsed_ms} ms",
    }
    if response_headers.get("Server"):
        response_fields["Server"] = response_headers["Server"]
    if 300 <= status < 400:
        response_fields["Location"] = response_headers.get("Location", "not provided")
    if len(body) > MAX_BODY_BYTES:
        response_fields["Body"] = f"truncated at {MAX_BODY_BYTES} bytes"

    request_protocol = "HTTPS" if scheme == "HTTPS" else "HTTP"
    events.append(event(next_sequence, request_protocol, "client-to-server", "request", f"GET {path} HTTP/1.1", {
        "Host": hostname,
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Target": final_url,
        "Capture": "Request metadata from the HTTP client",
    }))
    events.append(event(next_sequence + 1, request_protocol, "server-to-client", "response", f"HTTP/1.1 {status} {reason}".strip(), response_fields))

    return {"success": True, "activity": "browsing", "events": events}


def simulated_mail(to: str, subject: str, body: str) -> dict:
    if not to or "@" not in to or len(to) > 254:
        raise ValueError("Enter a recipient email address")
    if not subject.strip() or len(subject) > 200:
        raise ValueError("Enter a subject up to 200 characters")
    if not body.strip() or len(body) > 4000:
        raise ValueError("Enter a message body up to 4,000 characters")
    events = [
        event(1, "SMTP", "server-to-client", "response", "220 mail.example.com SMTP Service Ready", {"Traffic": "Simulated", "Role": "Mail server"}),
        event(2, "SMTP", "client-to-server", "command", "EHLO client.example", {"Command": "EHLO", "Traffic": "Simulated"}),
        event(3, "SMTP", "server-to-client", "response", "250-mail.example.com\n250-STARTTLS\n250 AUTH ...", {"Capabilities": "STARTTLS, AUTH", "Traffic": "Simulated"}),
        event(4, "SMTP", "client-to-server", "command", "MAIL FROM:<sender@example.com>", {"Command": "MAIL FROM", "Traffic": "Simulated"}),
        event(5, "SMTP", "server-to-client", "response", "250 OK", {"Traffic": "Simulated"}),
        event(6, "SMTP", "client-to-server", "command", f"RCPT TO:<{to}>", {"Command": "RCPT TO", "Traffic": "Simulated"}),
        event(7, "SMTP", "server-to-client", "response", "250 OK", {"Traffic": "Simulated"}),
        event(8, "SMTP", "client-to-server", "command", "DATA", {"Command": "DATA", "Traffic": "Simulated"}),
        event(9, "SMTP", "server-to-client", "response", "354 End data with <CR><LF>.<CR><LF>", {"Traffic": "Simulated"}),
        event(10, "SMTP", "client-to-server", "data", f"Subject: {subject}\n\n{body}\n.", {"Recipient": to, "Traffic": "Simulated"}),
        event(11, "SMTP", "server-to-client", "response", "250 OK", {"Traffic": "Simulated"}),
        event(12, "SMTP", "client-to-server", "command", "QUIT", {"Command": "QUIT", "Traffic": "Simulated"}),
        event(13, "SMTP", "server-to-client", "response", "221 Bye", {"Traffic": "Simulated"}),
    ]
    return {"success": True, "activity": "mail", "events": events, "simulated": True}


def simulated_stream(quality: str) -> dict:
    quality = quality if quality in {"auto", "360p", "720p", "1080p"} else "auto"
    representation = {"auto": "adaptive", "360p": "360p", "720p": "720p", "1080p": "1080p"}[quality]
    paths = ["/video/manifest.mpd", "/video/segment_001.m4s", "/video/segment_002.m4s", "/video/segment_003.m4s"]
    events = [
        event(1, "DNS", "client-to-server", "query", "DNS Query: A media.example.com", {"Name": "media.example.com", "Type": "A", "Resolver": "Recursive Resolver (simulated)", "Traffic": "Simulated"}),
        event(2, "DNS", "server-to-client", "response", "DNS Response: NOERROR", {"Status": "resolved", "Answer": "203.0.113.20", "Traffic": "Simulated"}),
    ]
    sequence = 3
    for path in paths:
        kind = "Manifest / Playlist" if path.endswith(".mpd") else "Media Segment"
        events.append(event(sequence, "MANIFEST" if path.endswith(".mpd") else "SEGMENT", "client-to-server", "request", f"GET {path} HTTP/1.1", {
            "Host": "media.example.com", "Representation": representation, "Resource": kind, "Traffic": "Simulated"
        }))
        events.append(event(sequence + 1, "HTTP", "server-to-client", "response", "HTTP/1.1 200 OK", {
            "Content-Type": "application/dash+xml" if path.endswith(".mpd") else "video/iso.segment",
            "Resource": kind, "Traffic": "Simulated"
        }))
        sequence += 2
    return {"success": True, "activity": "streaming", "events": events, "simulated": True}


@app.get("/")
def index():
    return render_template("index.html", github_url=GITHUB_URL)


@app.post("/api/browse")
def browse_api():
    payload = requested_json()
    if not payload:
        return error_response("Send a JSON object with a URL")
    try:
        return jsonify(browse(payload.get("url", "")))
    except ValueError as exc:
        return error_response(str(exc))
    except RuntimeError as exc:
        return error_response(str(exc), 502)


@app.post("/api/mail")
def mail_api():
    payload = requested_json()
    if not payload:
        return error_response("Send a JSON object with mail fields")
    try:
        to = payload.get("to", "")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        if not all(isinstance(value, str) for value in (to, subject, body)):
            raise ValueError("Mail fields must be strings")
        return jsonify(simulated_mail(to.strip(), subject, body))
    except ValueError as exc:
        return error_response(str(exc))


@app.post("/api/stream")
def stream_api():
    payload = requested_json() or {}
    return jsonify(simulated_stream(payload.get("quality", "auto")))


@app.errorhandler(413)
def request_too_large(_error):
    return error_response("Request body is too large", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
