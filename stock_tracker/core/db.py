"""Veritabanı motoru ve oturum yönetimi."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from stock_tracker.core.models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def init_db(db_url: str) -> None:
    """Motoru kur ve tabloları oluştur (yoksa)."""
    global _engine, _SessionFactory
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    _engine = create_engine(db_url, connect_args=connect_args, future=True)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    if _SessionFactory is None:
        raise RuntimeError("Veritabanı başlatılmadı; önce init_db() çağır.")
    return _SessionFactory()
