# Protocol Visualizer

A small web application that performs real network activities—such as web requests, SMTP email, and streaming—while visualizing the protocol exchanges step-by-step in the browser.

## Requirements

- **Python 3.10+**
- **FFmpeg** (required for HLS video streaming)
- Python packages (from `requirements.txt`):
  - `Flask`
  - `dnspython`
  - `gunicorn`

On Ubuntu/Debian systems:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git
```

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/localrice/Protocol_visualizer.git
   cd Protocol_visualizer
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (optional, for Mail)**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Fill in your SMTP settings in `.env`:
   ```env
   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@example.com
   SMTP_PASSWORD=your-password-or-app-password
   SMTP_FROM=your-email@example.com
   ```
   Export the variables into your session:
   ```bash
   set -a
   source .env
   set +a
   ```
   *(Browsing and Streaming work out of the box without SMTP credentials.)*

## Running

Start with Gunicorn (production):

```bash
gunicorn app:app
```

Or start the Flask development server:

```bash
python app.py
```

Open your browser and navigate to:

```text
http://127.0.0.1:5000
```

## Production Deployment (Ubuntu VPS)

Follow these steps to deploy the application as a systemd service on an Ubuntu VPS using Gunicorn.

### 1. Clone or Update the Repository

```bash
git clone https://github.com/localrice/Protocol_visualizer.git /path/to/protocol-dashboard
cd /path/to/protocol-dashboard
```

*(If updating an existing deployment, pull the latest changes: `git pull origin main`)*

### 2. Create the Python Virtual Environment

```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install FFmpeg with apt

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### 6. Create and Configure `.env`

Copy the sample environment file:

```bash
cp .env.example .env
nano .env
```

Configure your SMTP settings using standard `KEY=value` format. **Do NOT use `export`** in `.env`, as systemd's `EnvironmentFile` directive expects plain key-value entries. Set secure file permissions:

```bash
chmod 600 .env
```

### 7. Copy the Systemd Service

```bash
sudo cp deploy/protocol-dashboard.service /etc/systemd/system/protocol-dashboard.service
```

Open `/etc/systemd/system/protocol-dashboard.service` and verify `WorkingDirectory` and `PATH` match your actual project path (e.g. `/home/deploy/protocol-dashboard`). The service is pre-configured for `User=deploy`.

### 8. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 9. Enable the Service

```bash
sudo systemctl enable protocol-dashboard.service
```

### 10. Start the Service

```bash
sudo systemctl start protocol-dashboard.service
```

### 11. Check Service Status

```bash
sudo systemctl status protocol-dashboard.service
```

### 12. Test Locally

Verify that Gunicorn is serving requests locally:

```bash
curl http://127.0.0.1:5000
```

### 13. View Logs with journalctl

Follow real-time service logs:

```bash
sudo journalctl -u protocol-dashboard.service -f
```

### 14. Restart the Service After Updates

```bash
cd /path/to/protocol-dashboard
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart protocol-dashboard.service
```

To stop the service at any time:

```bash
sudo systemctl stop protocol-dashboard.service
```

---

## Cloudflare Tunnel

The application listens locally on `127.0.0.1:5000`. To route public traffic through an existing Cloudflare Tunnel (`protocol.kinjalboro.me → http://127.0.0.1:5000`):

1. Route the DNS hostname through your tunnel:
   ```bash
   cloudflared tunnel route dns <tunnel-name-or-id> protocol.kinjalboro.me
   ```

2. Add the ingress rule to your Cloudflare Tunnel configuration (`/etc/cloudflared/config.yml`):
   ```yaml
   ingress:
     - hostname: protocol.kinjalboro.me
       service: http://127.0.0.1:5000
     - service: http_status:404
   ```

3. Restart the Cloudflare Tunnel service:
   ```bash
   sudo systemctl restart cloudflared
   ```
