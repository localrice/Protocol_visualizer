# Protocol Dashboard

A small Flask dashboard for exploring application-layer exchanges through Browsing, Mail, and Streaming activities. The interface has two main panels: activity controls on the left and a sequential protocol trace on the right.

## Current status

- [x] Browsing with real server-side DNS and HTTP/HTTPS requests
- [ ] Mail workflow
- [ ] Streaming workflow

## Features

- Explicit recursive DNS queries with dnspython (configured by `DNS_RESOLVER`, default `1.1.1.1`) and bounded HTTP/HTTPS requests for Browsing.
- Metadata-based HTTP visualization. This is not packet capture, and HTTPS payloads are not decrypted.
- Shared JSON event model with automatic protocol playback.
- Local validation, request size limits, timeouts, and basic private-destination blocking.

## Architecture

`app.py` owns Flask routes, input validation, explicit DNS/HTTP work, and protocol event generation. `templates/index.html` contains the two-panel shell. `static/js/app.js` renders the reusable event sequence and automatically advances the exchange. `static/css/style.css` contains the responsive, framework-free styling.

## Project structure

```text
.
├── app.py
├── requirements.txt
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
└── README.md
```

## Local installation

Python 3.10 or newer is recommended.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

## Ubuntu deployment prerequisites

Install Python 3, the Python virtual-environment package, and a compiler toolchain only if other project dependencies later require it. Create a dedicated unprivileged user, use a virtual environment, and place the app behind a production WSGI server and TLS-terminating reverse proxy when it is exposed publicly. Those deployment pieces are intentionally outside V1.

## Real versus simulated traffic

Browsing sends fresh A and AAAA queries to the configured recursive resolver using dnspython, then performs a real HTTP/HTTPS request from Flask. The standard HTTP client may perform its own transport lookup; the DNS exchange shown in the dashboard is the explicit dnspython query and identifies its resolver. No cache-clearing command is attempted or claimed. The dashboard only reports request and response metadata available to Python; it does not inspect raw packets. Redirect responses are displayed as responses rather than followed automatically. HTTPS includes TCP and TLS stages, then labels HTTP content as client metadata rather than decrypted wire data.

Mail and Streaming are reserved for later implementation and are not part of the completed Browsing milestone.

Set a different recursive resolver for a local or controlled demonstration with:

```bash
DNS_RESOLVER=1.1.1.1 venv/bin/python app.py
```

The application does not control or flush the public resolver cache. A future Unbound-based setup could provide that control without changing the event model.

## Security considerations

Only HTTP and HTTPS URLs are accepted. Embedded credentials, non-standard ports, and hosts that resolve to private, loopback, link-local, multicast, reserved, or unspecified addresses are rejected. Requests have an 8-second timeout and responses are read only up to 128 KiB. DNS rebinding and more advanced SSRF defenses would need additional network isolation for a public deployment; do not treat this development server as a complete SSRF gateway defense.

## Future improvements

- Add a real packet-capture mode with explicit permissions and a separate worker.
- Add a configured SMTP provider with server-side credentials and authenticated sending.
- Use a configured public media manifest for a real playback demo.
- Add DNS query type selection and richer redirect tracing.
- Run behind a production WSGI server with rate limiting and network egress policy.
