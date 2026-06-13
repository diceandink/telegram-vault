import asyncio
import logging
import httpx
import sys
from telethon import TelegramClient, events
from telethon.errors import (
    AuthKeyError, AuthKeyDuplicatedError, AuthKeyUnregisteredError,
    SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError,
    UserDeactivatedBanError, UserDeactivatedError,
    FloodWaitError
)
from sqlalchemy import select
from datetime import datetime, timezone
from database import SessionLocal, Message, init_db
from config import API_ID, API_HASH, PHONE_NUMBER

AUTH_FATAL_ERRORS = (
    AuthKeyError,
    AuthKeyDuplicatedError,
    AuthKeyUnregisteredError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    UserDeactivatedBanError,
    UserDeactivatedError,
)

logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

client = TelegramClient('userbot_session', API_ID, API_HASH)


@client.on(events.NewMessage())
async def handler(event):
    if event.is_private:
        return

    if not event.message or not event.message.message:
        return

    try:
        chat = await event.get_chat()
        sender = await event.get_sender()

        chat_title = getattr(chat, 'title', 'Private Chat')
        sender_name = "Unknown"
        if sender:
            first_name = getattr(sender, 'first_name', '') or ''
            last_name = getattr(sender, 'last_name', '') or ''
            sender_name = f"{first_name} {last_name}".strip() or "Unknown"

        user_id = event.sender_id
        username = getattr(sender, 'username', None) if sender else None
        content = event.message.message

        print(f"[{chat_title}] {sender_name}: {content[:50]}")

        timestamp = event.date.replace(tzinfo=None)

        async with SessionLocal() as session:
            new_msg = Message(
                message_id=event.message.id,
                chat_id=event.chat_id,
                chat_title=chat_title,
                user_id=user_id,
                username=username,
                sender_name=sender_name,
                content=content,
                timestamp=timestamp
            )
            session.add(new_msg)
            await session.commit()

            try:
                async with httpx.AsyncClient() as http:
                    await http.post("http://127.0.0.1:8000/internal/broadcast", json={
                        "chat_title": chat_title,
                        "chat_id": event.chat_id,
                        "sender_name": sender_name,
                        "username": username,
                        "user_id": user_id,
                        "content": content,
                        "timestamp": timestamp.isoformat()
                    }, timeout=2.0)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error: {e}")


@client.on(events.MessageDeleted())
async def delete_handler(event):
    if not event.deleted_ids:
        return

    if len(event.deleted_ids) > 5:
        return

    try:
        async with SessionLocal() as session:
            for msg_id in event.deleted_ids:
                result = await session.execute(
                    select(Message).where(
                        Message.message_id == msg_id,
                        Message.chat_id == event.chat_id if event.chat_id else True
                    )
                )
                msg = result.scalar_one_or_none()

                if msg:
                    time_diff = (datetime.now(timezone.utc).replace(tzinfo=None) - msg.timestamp).total_seconds()

                    if (86280 < time_diff < 86520) or (604680 < time_diff < 604920):
                        continue

                    msg.is_deleted = True
                    await session.commit()

                    try:
                        async with httpx.AsyncClient() as http:
                            await http.post("http://127.0.0.1:8000/internal/broadcast", json={
                                "type": "DELETED",
                                "message_id": msg_id,
                                "chat_id": msg.chat_id
                            }, timeout=2.0)
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Deletion log error: {e}")


async def main():
    await init_db()
    MAX_RETRIES = 5
    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            logger.info("Telegram Vault Userbot starting...")
            await client.start(phone=PHONE_NUMBER)

            logger.info("Loading dialogs...")
            await client.get_dialogs()

            logger.info("System Active! Listening to all messages.")
            retry_count = 0
            await client.run_until_disconnected()

        except AUTH_FATAL_ERRORS as e:
            logger.critical(
                f"[CRITICAL AUTH ERROR] Bot STOPPED: {type(e).__name__}: {e}\n"
                f"Delete the session file and restart the bot."
            )
            try:
                with open("AUTH_ERROR.flag", "w") as f:
                    f.write(f"{type(e).__name__}: {e}")
            except Exception:
                pass
            sys.exit(1)

        except FloodWaitError as e:
            wait_time = e.seconds + 10
            logger.warning(f"FloodWait: Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            retry_count += 1
            err_str = str(e).lower()

            if any(kw in err_str for kw in [
                'resendcode', 'auth_key', 'session', 'phone_code',
                'code_invalid', 'code_expired', 'deactivated', 'banned',
                'password', 'two-factor'
            ]):
                logger.critical(f"[CRITICAL AUTH ERROR] Bot STOPPED: {e}")
                try:
                    with open("AUTH_ERROR.flag", "w") as f:
                        f.write(str(e))
                except Exception:
                    pass
                sys.exit(1)

            wait = min(5 * retry_count, 60)
            logger.error(f"Connection lost ({retry_count}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
            await asyncio.sleep(wait)

    logger.critical(f"Maximum retry count reached ({MAX_RETRIES}). Bot stopping.")
    sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
