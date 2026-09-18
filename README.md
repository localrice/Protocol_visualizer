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

### 1. Install System Dependencies & FFmpeg

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git
```

### 2. Clone or Update the Repository

```bash
git clone https://github.com/localrice/Protocol_visualizer.git /var/www/protocol-dashboard
cd /var/www/protocol-dashboard
```

*(If updating an existing deployment: `git pull origin main`)*

### 3. Create and Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the Environment File (.env)

```bash
cp .env.example .env
nano .env
```
Configure your SMTP settings if using the Mail feature. Set restrictive file permissions:
```bash
chmod 600 .env
```

### 6. Install and Configure the Systemd Service

Copy the template service file:
```bash
sudo cp deploy/protocol-dashboard.service /etc/systemd/system/protocol-dashboard.service
```

Edit `/etc/systemd/system/protocol-dashboard.service` to match your deployment:
- Replace `User=<user>` and `Group=<user>` with your Linux username (e.g., `ubuntu` or `www-data`).
- Replace `/path/to/protocol-dashboard` with your actual repository path (e.g., `/var/www/protocol-dashboard`).

### 7. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now protocol-dashboard
```

### 8. Check Service Status

```bash
sudo systemctl status protocol-dashboard
```

### 9. View Logs

```bash
sudo journalctl -u protocol-dashboard -f
```

### 10. Restarting the Service After Updates

```bash
cd /var/www/protocol-dashboard
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart protocol-dashboard
```

To stop the service at any time:
```bash
sudo systemctl stop protocol-dashboard
```
