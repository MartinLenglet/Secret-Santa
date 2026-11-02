import os
from pathlib import Path

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)
    state: Mapped[str] = mapped_column(default="draft")
    data: Mapped[dict] = mapped_column(JSON)


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("event_id", "giver"),
        UniqueConstraint("event_id", "recipient"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    giver: Mapped[str] = mapped_column(String)
    recipient: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(default="pending")
    error: Mapped[str | None] = mapped_column(String, nullable=True)


def default_database() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return Path(os.environ.get("SANTA_DATABASE", root / "SecretSanta" / "santa.sqlite3"))


def open_database(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def recover_interrupted(sessions: sessionmaker) -> None:
    with sessions.begin() as session:
        interrupted = session.query(EventRecord).filter_by(state="sending").all()
        for record in interrupted:
            record.state = "partial"
            for delivery in session.query(Delivery).filter_by(event_id=record.id, status="sending"):
                delivery.status = "uncertain"
                delivery.error = "Envoi interrompu : vérifiez Gmail avant de réessayer."
