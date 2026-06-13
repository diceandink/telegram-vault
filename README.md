<div align="center">
  <img src="static/logo.svg" alt="Telegram Vault Logo" width="150">

  # Telegram Vault — Intelligence Hub

  ![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-336791?style=flat-square&logo=postgresql)
  ![Telethon](https://img.shields.io/badge/Telethon-1.36.0-2CA5E0?style=flat-square&logo=telegram)
  ![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

  *An advanced OSINT & Logging system that listens to Telegram messages in real-time, saves them to a database, and provides live streaming analysis through a web dashboard.*
</div>

---


**Live Intelligence Logging**  
Real-time message streaming via WebSockets with dynamic search, context extraction, and high-performance filtering.

<img src="static/screenshot_log.png" alt="Live Intelligence Log Viewer" width="100%">

**Analytics Dashboard**  
Actionable intelligence with KPIs, message velocity charts, active users, and target analysis using interactive visualizations.

<img src="static/screenshot_dash.png" alt="Intelligence Analytics Dashboard" width="100%">

---

## Key Capabilities
- **High-Performance Streaming:** Non-blocking asynchronous message parsing via Telethon.
- **WebSocket Feeds:** Instantly pushes new logs and deleted message alerts to connected clients.
- **Data Persistence:** Built on SQLAlchemy async engine, natively supporting PostgreSQL.
- **Clean Architecture:** Modular routes, robust rate-limiting, secure authentication, and hCaptcha integration.

---

## Installation & Setup

**1. Prerequisites**
- Python 3.9+ (3.12 recommended)
- PostgreSQL Server
- Telegram API ID and API Hash (Obtain from [my.telegram.org](https://my.telegram.org))

**2. Clone & Install**

*Windows:*
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

*Linux / macOS:*
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Configure Environment**
Copy `.env.example` to `.env` and configure your deployment credentials:
```env
API_ID=your_api_id
API_HASH=your_api_hash
DATABASE_URL=postgresql+asyncpg://user:password@localhost/telegramlogs
PHONE_NUMBER=+1234567890
DASHBOARD_PASSWORD=your_secure_password
```

**4. Prepare Database**
```sql
CREATE DATABASE telegramlogs;
```

**5. Launch System**

*Windows:*
Use the provided batch script for a streamlined startup:
```bash
start.bat
```

*Linux / macOS:*
You can use `tmux`, `screen`, or run them in the background:
```bash
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 &
python3 bot.py &
```

---

## Project Structure

```text
├── app.py              # FastAPI Application (Main Entry)
├── bot.py              # Telethon Userbot Listener
├── config.py           # Environment Variables loader
├── database.py         # SQLAlchemy ORM Models
├── start.bat           # Multi-process Launcher
├── routes/             # Core Backend Logic
│   ├── auth.py         # Authentication & Rate Limiting
│   ├── dashboard.py    # Analytics Engine
│   ├── messages.py     # Log Search & API
│   └── websocket.py    # Real-Time WebSocket Broadcaster
├── middleware/         # Custom Middlewares (e.g. Security Headers)
├── templates/          # Jinja2 HTML Views
└── static/             # Assets (CSS, JS, Logo, Screenshots)
```

---

<div align="center">
  <br>
   <a href="https://github.com/diceandink">github.com/diceandink</a>
</div>
