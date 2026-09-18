# Protocol Dashboard

An interactive network visualizer built as a Computer Networks assignment by [Kinjal Boro](https://kinjalboro.me). The dashboard demonstrates how high-level user actions translate into real, application-layer network protocols.

- **GitHub Repository**: [github.com/localrice/Protocol_visualizer](https://github.com/localrice/Protocol_visualizer)
- **Live / Portfolio**: [kinjalboro.me](https://kinjalboro.me)

---

## Overview

Modern web applications abstract away the underlying networking steps. This project exposes those steps through three everyday activities:

1. **Browsing**: Demonstrates DNS hostname resolution, TCP handshakes, TLS negotiation, and HTTP/HTTPS request-response cycles.
2. **Mail**: Demonstrates the SMTP protocol in action — server connection, greeting (`EHLO`), TLS upgrade (`STARTTLS`), authentication, envelope configuration (`MAIL FROM`, `RCPT TO`), message transmission (`DATA`), and session closure (`QUIT`).
3. **Streaming**: Demonstrates HTTP Live Streaming (HLS) with adaptive media segmentation, index manifests (`playlist.m3u8`), and individual transport stream (`.ts`) video segment requests.

---

## Real Network Operations (Not a Mock Simulation)

A core requirement for this project was to make real network calls rather than replaying simulated or hardcoded traces:

- **Browsing**: Makes genuine DNS queries using `dnspython` and real HTTP/HTTPS requests using Python's standard `urllib`.
- **Mail**: Opens an actual network socket to a configured SMTP mail server, exchanges live SMTP commands, and sends a real email.
- **Streaming**: Transcodes a local MP4 into HLS segments using FFmpeg, serves them directly through Flask, and captures live HTTP GET requests made by the browser's video player.

> **Note on Packet Capture**: This project **does not** perform promiscuous or raw packet sniffing (like Wireshark or `tcpdump`). Instead, it logs real application-level protocol commands, response codes, and HTTP/socket metadata at the server application boundary.

---

## Architecture

The project is designed to be lightweight, easy to understand, and framework-free on the frontend:

- **Flask Backend (`app.py`)**: Defines REST API endpoints (`/api/browse`, `/api/mail`, `/api/stream`, `/api/stream/events`), serves static assets, and handles media delivery.
- **Activity Utilities (`utils/`)**:
  - `utils/browsing.py`: Handles public DNS lookups, protects against SSRF (blocks private/loopback addresses), and issues live HTTP/HTTPS GET requests.
  - `utils/mail.py`: Subclasses Python's `smtplib` to intercept and record SMTP commands and responses while securely masking credentials (`AUTH`).
  - `utils/streaming.py`: Uses FFmpeg to segment the sample MP4 into an HLS playlist and serves chunks via Flask while tracking requests.
  - `utils/protocol.py`: Shared helper to format protocol event objects consistently.
- **Frontend (`templates/index.html`, `static/js/app.js`, `static/css/style.css`)**:
  - Built with semantic HTML and vanilla CSS/JavaScript.
  - Features a split-screen interface: an activity panel on the left and a live, sequential protocol trace on the right.
  - Supports light and dark modes with persistent local storage.
  - Uses `hls.js` for playing HLS streams across all modern browsers.

---

## Project Structure

```text
.
├── app.py                  # Main Flask application and route handlers
├── utils/
│   ├── __init__.py         # Package marker
│   ├── browsing.py         # DNS resolution and HTTP/HTTPS fetch logic
│   ├── mail.py             # SMTP connection and command/response recorder
│   ├── protocol.py         # Standardized protocol event helper
│   └── streaming.py        # FFmpeg HLS transcoding and chunk serving
├── media/
│   └── video.mp4           # Bundled sample video for HLS streaming
├── static/
│   ├── css/
│   │   └── style.css       # Responsive styling and dark/light themes
│   └── js/
│       └── app.js          # Tab handling, API calls, playback animation, and HLS
├── templates/
│   └── index.html          # Two-panel dashboard layout
├── .env.example            # Sample configuration for SMTP
├── .gitignore              # Ignores venv, instance cache, and local .env
├── requirements.txt        # Python package dependencies
└── README.md
```

*(Note: An `instance/stream/` directory is automatically generated at runtime on first video playback to store transcoded `.m3u8` and `.ts` files; this directory is ignored by Git.)*

---

## How the Protocol Visualization Works

1. **Browsing & Mail**:
   - The frontend sends a JSON payload to `/api/browse` or `/api/mail`.
   - The backend runs the real network exchange, builds an array of ordered event objects (recording protocol type, direction, message text, headers, and relative delays), and returns them as a JSON response.
   - `static/js/app.js` renders the events into logical groups (e.g. DNS resolution, TCP connection, HTTP request/response, or SMTP interaction stages) and steps through them sequentially with micro-delays to visualize the conversation flow.

2. **Streaming**:
   - When the user clicks **Play**, the frontend posts to `/api/stream`.
   - The backend prepares the HLS files and returns the manifest URL (`/stream/playlist.m3u8`).
   - The client-side `hls.js` player loads the playlist and requests `.ts` chunks from Flask as the video buffers.
   - Every time Flask serves a chunk via `/stream/<filename>`, it records the request and response in an event queue.
   - The frontend polls `/api/stream/events?since=<seq>` every 400ms, appending new chunk requests to the timeline in real time.

---

## Streaming Implementation (Self-Hosted HLS)

Rather than embedding an external video host like YouTube, streaming is completely self-contained:

1. A sample video is provided at `media/video.mp4`.
2. When playback begins, `utils/streaming.py` checks whether an HLS playlist exists. If not, it executes an FFmpeg command:
   ```bash
   ffmpeg -y -i media/video.mp4 -c:v libx264 -g 48 -sc_threshold 0 -c:a aac -b:a 96k -f hls -hls_time 2 -hls_list_size 0 -hls_segment_filename instance/stream/segment%03d.ts instance/stream/playlist.m3u8
   ```
3. This segments the video into 2-second chunks.
4. Flask serves the `.m3u8` playlist with MIME type `application/vnd.apple.mpegurl` and `.ts` files with `video/mp2t`.
5. The protocol panel displays each manifest fetch and segment transfer with exact file sizes and headers.

---

## SMTP Configuration & Environment Variables

To use the Mail activity, configure an external SMTP provider (such as Gmail, Outlook, or Mailgun).

### Required Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SMTP_HOST` | Hostname of the outgoing SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | Port number (`587` for STARTTLS, `465` for SSL) | `587` |
| `SMTP_USERNAME` | SMTP account username / email address | `user@gmail.com` |
| `SMTP_PASSWORD` | SMTP password or app-specific password | `xxxx xxxx xxxx xxxx` |
| `SMTP_FROM` | Valid sender email address | `user@gmail.com` |

*(Optional: `DNS_RESOLVER` can be set to override the default public DNS resolver, which defaults to `1.1.1.1`.)*

### Safe Handling of Credentials

- Create a `.env` file from the provided example:
  ```bash
  cp .env.example .env
  ```
- Add your credentials to `.env`.
- **Never commit `.env` to Git.** The `.gitignore` file already excludes `.env`.
- In the dashboard, passwords and raw authentication hashes are never sent to the browser or displayed in the trace — `utils/mail.py` replaces them with `AUTH <mechanism> (credentials hidden)`.

---

## Setup and Running Locally

### 1. Prerequisites (Ubuntu / Debian)

If you are setting this up on an Ubuntu machine or a VPS:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git
```

*(For macOS, install FFmpeg via Homebrew: `brew install ffmpeg`.)*

### 2. Clone the Repository

```bash
git clone https://github.com/localrice/Protocol_visualizer.git
cd Protocol_visualizer
```

### 3. Set Up Virtual Environment

Always use a virtual environment so packages are isolated:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables (For Mail)

If you plan to test SMTP mail sending:

```bash
cp .env.example .env
# Edit .env with your favorite editor (e.g. nano .env)
```

Export the variables into your active shell session:

```bash
set -a
source .env
set +a
```

*(If you only want to test Browsing and Streaming, you can skip configuring SMTP. Browsing and Streaming will work out of the box.)*

### 6. Run the Application

```bash
python app.py
```

Or run directly with the virtual environment binary:

```bash
./venv/bin/python app.py
```

### 7. Access the Dashboard

Open your browser and navigate to:

```text
http://127.0.0.1:5000
```

---

## Common Issues & Troubleshooting

- **`ModuleNotFoundError: No module named 'flask'`**:
  You are running Python without activating the virtual environment. Either run `source venv/bin/activate` first or start the app with `./venv/bin/python app.py`.

- **`FFmpeg is not installed on the server`**:
  Streaming requires FFmpeg. On Ubuntu/Debian run `sudo apt install -y ffmpeg`. Verify it with `ffmpeg -version`.

- **`SMTP authentication failed` (Error 535)**:
  Modern providers like Gmail require an **App Password** when 2-Step Verification is active. Standard account passwords will be rejected. Generate an App Password in your Google Account security settings and put that in `SMTP_PASSWORD`.

- **`SMTP server rejected the sender` / `400` on Mail send**:
  Ensure `SMTP_FROM` is formatted as a valid email address (e.g. `user@example.com`) rather than a plain name. Most SMTP relays reject unformatted sender headers.

- **`DNS resolution error` or `private address blocked`**:
  The browsing module prevents Server-Side Request Forgery (SSRF) by disallowing queries to private IPs, localhost (`127.0.0.1`), and internal subnets. Always test with public URLs (e.g. `https://example.com` or `https://cloudflare.com`).

---

## Author & Project Info

- **Author**: Kinjal Boro
- **Website**: [https://kinjalboro.me](https://kinjalboro.me)
- **Repository**: [https://github.com/localrice/Protocol_visualizer](https://github.com/localrice/Protocol_visualizer)
