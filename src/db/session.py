# db/session.py
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.base import Base
from db import models
from utils import secret  # ensures all models are registered


engine = create_engine(
    secret.listen().DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, Any, None]:
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()