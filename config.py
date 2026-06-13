import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./telegramlogs.db")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", None)
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-secret-key-immediately")
HCAPTCHA_SITE_KEY = os.getenv("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET_KEY = os.getenv("HCAPTCHA_SECRET_KEY", "")
