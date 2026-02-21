import typing as t

from sqlalchemy import (
    Engine,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    CheckConstraint,
    Index,
    JSON,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from sqlalchemy.dialects.mysql import (
    INTEGER,
    BIGINT,
    TINYINT,
    VARCHAR,
)

from utils import secret


# ============================================================
# Base
# ============================================================

class Base(DeclarativeBase):
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_bin",
        "mysql_engine": "InnoDB",
    }


# ============================================================
# Community
# ============================================================

class Community(Base):
    __tablename__ = "community"

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    norm_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)
    real_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)

    default_selected_list_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    limits: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["id", "default_selected_list_id"],
            ["list.community_id", "list.id"],
            ondelete="SET NULL",
        ),
    )


# ============================================================
# Server
# ============================================================

class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
    )

    community_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("community.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_server_community_id", "community_id"),
    )


# ============================================================
# List
# ============================================================

class List(Base):
    __tablename__ = "list"

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    community_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("community.id", ondelete="CASCADE"),
        nullable=False,
    )

    norm_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    real_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("community_id", "norm_name"),
        UniqueConstraint("id", "community_id"),
        Index("ix_list_community_id", "community_id"),
    )


# ============================================================
# JumpediaUser
# ============================================================

class JumpediaUser(Base):
    __tablename__ = "jumpedia_user"

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
    )

    norm_name: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    raw_name: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)

    power: Mapped[int] = mapped_column(nullable=False)


# ============================================================
# CommunityUser
# ============================================================

class CommunityUser(Base):
    __tablename__ = "community_user"

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    community_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("community.id", ondelete="CASCADE"),
        nullable=False,
    )

    jumpedia_user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("jumpedia_user.id", ondelete="CASCADE"),
        nullable=False,
    )

    power: Mapped[int] = mapped_column(nullable=False)

    selected_list_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        nullable=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["community_id", "selected_list_id"],
            ["list.community_id", "list.id"],
            ondelete="SET NULL",
        ),
        Index("ix_community_user_community_id", "community_id"),
        Index("ix_community_user_jumpedia_user_id", "jumpedia_user_id"),
    )


# ============================================================
# Attribute
# ============================================================

class Attribute(Base):
    __tablename__ = "attribute"

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        nullable=False,
    )

    type_id: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    kind: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    norm_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    real_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)

    slot_type: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    position: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    min_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    max_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["list_id"],
            ["list.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("list_id", "position"),
        UniqueConstraint("id", "list_id"),
        CheckConstraint("type_id BETWEEN 1 AND 3"),
        Index("ix_attribute_list_id", "list_id"),
    )


# ============================================================
# Task
# ============================================================

class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        nullable=False,
    )

    norm_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    slot_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["list_id"], ["list.id"], ondelete="CASCADE"),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("id", "list_id"),
        Index("ix_task_list_id", "list_id"),
    )


# ============================================================
# TaskAttributeValue (strict relational)
# ============================================================

class TaskAttributeValue(Base):
    __tablename__ = "task_attribute_value"

    list_id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    task_id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    attribute_id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    slot_value: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "list_id"],
            ["task.id", "task.list_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["attribute_id", "list_id"],
            ["attribute.id", "attribute.list_id"],
            ondelete="CASCADE",
        ),
    )


# ============================================================
# Engine / Session
# ============================================================

def create_engine_and_session_maker(url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(
        url,
        pool_recycle=3600,
        connect_args={
            "init_command":
                "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,"
                "NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,"
                "NO_ENGINE_SUBSTITUTION'"
        }
    )

    session_maker = sessionmaker(engine)
    return engine, session_maker


def create_schema(engine: Engine):
    Base.metadata.create_all(engine)