from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import hashlib
import httpx
import time
import config
from database import SessionLocal

router = APIRouter()
templates = Jinja2Templates(directory="templates")

login_attempts = defaultdict(list)
audit_log = []
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 900
AUDIT_MAX = 500


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated", False)


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    return len(login_attempts[ip]) >= RATE_LIMIT_MAX


def record_attempt(ip: str):
    login_attempts[ip].append(time.time())


def log_auth_event(ip: str, user_agent: str, password: str, success: bool, reason: str = ""):
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:12]
    audit_log.insert(0, {
        "time": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
        "ip": ip,
        "ip_hash": ip_hash,
        "user_agent": user_agent,
        "password_tried": password,
        "success": success,
        "reason": reason
    })
    if len(audit_log) > AUDIT_MAX:
        audit_log.pop()


async def verify_hcaptcha(token: str) -> bool:
    if not config.HCAPTCHA_SECRET_KEY:
        return True
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://api.hcaptcha.com/siteverify", data={
                "secret": config.HCAPTCHA_SECRET_KEY,
                "response": token
            })
            return resp.json().get("success", False)
    except Exception:
        return False


async def get_db():
    async with SessionLocal() as session:
        yield session


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request, name="login.html", context={
            "error": None,
            "hcaptcha_site_key": config.HCAPTCHA_SITE_KEY
        }
    )


@router.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    client_ip = request.client.host
    ua = request.headers.get("user-agent", "Unknown")

    if is_rate_limited(client_ip):
        log_auth_event(client_ip, ua, password, False, "Rate limited")
        return templates.TemplateResponse(
            request=request, name="login.html", context={
                "error": "Too many failed attempts. Please wait 15 minutes.",
                "hcaptcha_site_key": config.HCAPTCHA_SITE_KEY
            }, status_code=429
        )

    form_data = await request.form()
    hcaptcha_token = form_data.get("h-captcha-response", "")

    if config.HCAPTCHA_SECRET_KEY:
        if not await verify_hcaptcha(hcaptcha_token):
            record_attempt(client_ip)
            log_auth_event(client_ip, ua, password, False, "Captcha failed")
            return templates.TemplateResponse(
                request=request, name="login.html", context={
                    "error": "Captcha verification failed.",
                    "hcaptcha_site_key": config.HCAPTCHA_SITE_KEY
                }, status_code=403
            )

    if password == config.DASHBOARD_PASSWORD:
        request.session["authenticated"] = True
        request.session["login_time"] = datetime.now().isoformat()
        request.session["ip"] = client_ip
        login_attempts.pop(client_ip, None)
        log_auth_event(client_ip, ua, "••••••", True, "Success")
        return RedirectResponse(url="/", status_code=302)
    else:
        record_attempt(client_ip)
        log_auth_event(client_ip, ua, password, False, "Invalid password")
        return templates.TemplateResponse(
            request=request, name="login.html", context={
                "error": "Login failed. Please check your credentials.",
                "hcaptcha_site_key": config.HCAPTCHA_SITE_KEY
            }, status_code=401
        )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/api/login-logs")
async def get_login_logs(request: Request):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return {"logs": audit_log}
