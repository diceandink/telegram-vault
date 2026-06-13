from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Text, DateTime, Boolean
from datetime import datetime
import config
import asyncio

engine = create_async_engine(config.DATABASE_URL, echo=False)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Veritabanı hazır.")
