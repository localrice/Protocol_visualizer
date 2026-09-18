"""DNS and HTTP browsing functionality."""

from __future__ import annotations

import ipaddress
import os
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import dns.exception
import dns.resolver

from protocol import event

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
