# Protocol Visualizer

A small web application that performs real network activities—such as web requests, SMTP email, and streaming—while visualizing the protocol exchanges step-by-step in the browser.

## Requirements

- **Python 3.10+**
- **FFmpeg** (required for HLS video streaming)
- Python packages (from `requirements.txt`):
  - `Flask`
  - `dnspython`

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

Start the Flask development server:

```bash
python app.py
```

Open your browser and navigate to:

```text
http://127.0.0.1:5000
```
