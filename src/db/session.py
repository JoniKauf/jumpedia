import typing as t
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db import models
from db.base import BaseModel
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
    BaseModel.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> t.Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
