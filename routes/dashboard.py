from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from datetime import datetime, timedelta
from database import Message
from routes.auth import is_authenticated, get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="index.html", context={})


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="admin.html", context={})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={})


@router.get("/api/dashboard")
async def get_dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Yetkisiz"})

    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(hours=24)

    total_stmt = select(func.count(Message.id))
    total = (await db.execute(total_stmt)).scalar()

    deleted_stmt = select(func.count(Message.id)).where(Message.is_deleted == True)
    total_deleted = (await db.execute(deleted_stmt)).scalar()

    last_hour_stmt = select(func.count(Message.id)).where(Message.timestamp >= one_hour_ago)
    last_hour = (await db.execute(last_hour_stmt)).scalar()

    active_users_stmt = select(func.count(func.distinct(Message.user_id))).where(Message.timestamp >= one_day_ago)
    active_users = (await db.execute(active_users_stmt)).scalar()

    top_group_stmt = (
        select(Message.chat_title, func.count(Message.id).label("cnt"))
        .where(Message.timestamp >= one_hour_ago)
        .group_by(Message.chat_title)
        .order_by(desc("cnt"))
        .limit(1)
    )
    top_group_row = (await db.execute(top_group_stmt)).first()
    top_group = {"name": top_group_row[0] or "Yok", "count": top_group_row[1]} if top_group_row else {"name": "Yok", "count": 0}

    top_del_stmt = (
        select(Message.chat_title, func.count(Message.id).label("cnt"))
        .where(Message.timestamp >= one_hour_ago, Message.is_deleted == True)
        .group_by(Message.chat_title)
        .order_by(desc("cnt"))
        .limit(1)
    )
    top_del_row = (await db.execute(top_del_stmt)).first()
    top_deleted_group = {"name": top_del_row[0] or "Yok", "count": top_del_row[1]} if top_del_row else {"name": "Yok", "count": 0}

    dialect = db.bind.dialect.name
    if dialect == 'sqlite':
        velocity_stmt = text("""
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) AS hr, COUNT(*) AS cnt
            FROM messages
            WHERE timestamp >= :since
            GROUP BY hr
            ORDER BY hr ASC
        """)
    else:
        velocity_stmt = text("""
            SELECT date_trunc('hour', timestamp) AS hr, COUNT(*) AS cnt
            FROM messages
            WHERE timestamp >= :since
            GROUP BY hr
            ORDER BY hr ASC
        """)
    
    velocity_rows = (await db.execute(velocity_stmt, {"since": one_day_ago})).all()

    velocity_map = {}
    for row in velocity_rows:
        hr_val = row[0]
        if isinstance(hr_val, str):
            hr_val = datetime.strptime(hr_val, "%Y-%m-%d %H:%M:%S")
        tr_hour = (hr_val + timedelta(hours=3)).strftime("%H:%M")
        velocity_map[tr_hour] = row[1]

    velocity = []
    for h in range(24, 0, -1):
        slot_utc = now - timedelta(hours=h)
        tr_hour = (slot_utc + timedelta(hours=3)).strftime("%H:%M")
        velocity.append({"hour": tr_hour, "count": velocity_map.get(tr_hour, 0)})

    top_groups_stmt = (
        select(Message.chat_title, func.count(Message.id).label("cnt"))
        .where(Message.timestamp >= one_day_ago)
        .group_by(Message.chat_title)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_groups_rows = (await db.execute(top_groups_stmt)).all()
    top_groups = [{"name": r[0] or "Private", "count": r[1]} for r in top_groups_rows]

    top_users_stmt = (
        select(Message.username, Message.sender_name, Message.user_id, func.count(Message.id).label("cnt"))
        .where(Message.timestamp >= one_day_ago)
        .group_by(Message.username, Message.sender_name, Message.user_id)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_users_rows = (await db.execute(top_users_stmt)).all()
    top_users = [{"username": r[0] or "?", "name": r[1] or "?", "user_id": r[2], "count": r[3]} for r in top_users_rows]

    return {
        "total": total,
        "total_deleted": total_deleted,
        "last_hour": last_hour,
        "active_users_24h": active_users,
        "top_group": top_group,
        "top_deleted_group": top_deleted_group,
        "velocity": velocity,
        "top_groups": top_groups,
        "top_users": top_users,
        "generated_at": (now + timedelta(hours=3)).strftime("%H:%M:%S")
    }
