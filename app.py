from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from database import init_db
from middleware.security import security_headers
from routes import auth, messages, dashboard, websocket
import os
import config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="Sredinom", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, max_age=1800, https_only=True, same_site='strict')

app.middleware("http")(security_headers)

if not os.path.exists("templates"):
    os.makedirs("templates")

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(messages.router)
app.include_router(dashboard.router)
app.include_router(websocket.router)


@app.on_event("startup")
async def startup_event():
    await init_db()
