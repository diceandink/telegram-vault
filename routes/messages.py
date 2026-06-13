from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import timedelta
from typing import Optional
import io
import csv
from database import Message
from routes.auth import is_authenticated, get_db

router = APIRouter()


@router.get("/api/messages")
async def search_messages(
    request: Request,
    query: Optional[str] = None,
    username: Optional[str] = None,
    chat_title: Optional[str] = None,
    is_deleted: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Yetkisiz"})

    stmt = select(Message).order_by(desc(Message.timestamp))

    if query:
        stmt = stmt.where(Message.content.ilike(f"%{query}%"))
    if username:
        stmt = stmt.where(Message.username.ilike(f"%{username}%"))
    if chat_title:
        stmt = stmt.where(Message.chat_title.ilike(f"%{chat_title}%"))
    if is_deleted is not None:
        stmt = stmt.where(Message.is_deleted == is_deleted)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await db.execute(count_stmt)).scalar()

    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    messages = (await db.execute(stmt)).scalars().all()

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": m.id,
                "message_id": m.message_id,
                "chat_id": m.chat_id,
                "chat_title": m.chat_title,
                "user_id": m.user_id,
                "username": m.username,
                "sender_name": m.sender_name,
                "content": m.content,
                "timestamp": (m.timestamp + timedelta(hours=3)).isoformat(),
                "is_deleted": getattr(m, 'is_deleted', False)
            }
            for m in messages
        ]
    }


@router.get("/api/export")
async def export_messages(
    request: Request,
    query: Optional[str] = None,
    username: Optional[str] = None,
    chat_title: Optional[str] = None,
    is_deleted: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Yetkisiz"})

    stmt = select(Message).order_by(desc(Message.timestamp))

    if query:
        stmt = stmt.where(Message.content.ilike(f"%{query}%"))
    if username:
        stmt = stmt.where(Message.username.ilike(f"%{username}%"))
    if chat_title:
        stmt = stmt.where(Message.chat_title.ilike(f"%{chat_title}%"))
    if is_deleted is not None:
        stmt = stmt.where(Message.is_deleted == is_deleted)

    stmt = stmt.limit(10000)
    messages = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Mesaj_ID", "Tarih_Saat", "Grup_Kanal", "Gonderen_Ad", "Kullanici_Adi", "User_ID", "Icerik", "Silinmis_Mi"])

    for m in messages:
        tr_time = (m.timestamp + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([
            m.message_id,
            tr_time,
            m.chat_title or "Ozel",
            m.sender_name,
            m.username or "",
            m.user_id,
            m.content.replace('\n', ' '),
            "EVET" if getattr(m, 'is_deleted', False) else "HAYIR"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Sredinom_OSINT_Export.csv"}
    )


@router.get("/api/profile/{user_id}")
async def get_target_profile(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return JSONResponse(status_code=401, content={"detail": "Yetkisiz"})

    latest_msg_stmt = select(Message).where(Message.user_id == user_id).order_by(desc(Message.timestamp)).limit(1)
    first_msg_stmt = select(Message).where(Message.user_id == user_id).order_by(Message.timestamp).limit(1)

    latest_msg = (await db.execute(latest_msg_stmt)).scalar_one_or_none()
    first_msg = (await db.execute(first_msg_stmt)).scalar_one_or_none()

    if not latest_msg:
        return {"error": "User not found"}

    total_stmt = select(func.count(Message.id)).where(Message.user_id == user_id)
    total_count = (await db.execute(total_stmt)).scalar()

    group_stmt = select(Message.chat_title, func.count(Message.id)).where(Message.user_id == user_id).group_by(Message.chat_title).order_by(desc(func.count(Message.id))).limit(10)
    groups = (await db.execute(group_stmt)).all()

    ts_stmt = select(Message.timestamp).where(Message.user_id == user_id)
    timestamps = (await db.execute(ts_stmt)).scalars().all()

    hours = {str(i): 0 for i in range(24)}
    for ts in timestamps:
        tr_time = ts + timedelta(hours=3)
        hours[str(tr_time.hour)] += 1

    target_groups = set([g[0] for g in groups if g[0]])
    target_hours_total = sum(hours.values())
    target_hours_pct = {h: (c / target_hours_total if target_hours_total else 0) for h, c in hours.items()}

    clones = []
    if target_hours_total >= 5 and target_groups:
        clone_stmt = select(Message.user_id, Message.username, Message.sender_name, Message.chat_title, Message.timestamp).where(
            Message.chat_title.in_(list(target_groups)),
            Message.user_id != user_id
        )
        clone_rows = (await db.execute(clone_stmt)).all()

        user_data = {}
        for r in clone_rows:
            uid = r[0]
            if uid not in user_data:
                user_data[uid] = {'username': r[1], 'name': r[2], 'groups': set(), 'hours': {str(i): 0 for i in range(24)}, 'total': 0}
            if r[3]:
                user_data[uid]['groups'].add(r[3])

            tr_h = str((r[4] + timedelta(hours=3)).hour)
            user_data[uid]['hours'][tr_h] += 1
            user_data[uid]['total'] += 1

        for uid, data in user_data.items():
            if data['total'] < 3:
                continue

            intersection = len(target_groups.intersection(data['groups']))
            union = len(target_groups.union(data['groups']))
            group_score = (intersection / union) * 100 if union > 0 else 0

            overlap = 0
            for h in range(24):
                h_str = str(h)
                pct_a = target_hours_pct[h_str]
                pct_b = data['hours'][h_str] / data['total']
                overlap += min(pct_a, pct_b)
            time_score = overlap * 100

            total_score = (group_score * 0.4) + (time_score * 0.6)

            if total_score >= 35:
                clones.append({
                    "user_id": uid,
                    "username": data['username'],
                    "name": data['name'],
                    "score": round(total_score, 1),
                    "shared_groups": intersection
                })

        clones = sorted(clones, key=lambda x: x['score'], reverse=True)[:3]

    return {
        "user_id": user_id,
        "username": latest_msg.username or "Yok",
        "sender_name": latest_msg.sender_name or "Bilinmiyor",
        "total": total_count,
        "first_seen": (first_msg.timestamp + timedelta(hours=3)).isoformat(),
        "last_seen": (latest_msg.timestamp + timedelta(hours=3)).isoformat(),
        "groups": [{"name": g[0] or "Private", "count": g[1]} for g in groups],
        "hours": hours,
        "clones": clones
    }
