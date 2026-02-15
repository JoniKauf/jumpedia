import typing as t

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from sqlalchemy.dialects.mysql import (
    INTEGER,
    BIGINT,
    TINYINT,
    VARCHAR,
)


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

    norm_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
        unique=True,
    )

    real_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
        unique=True,
    )

    default_selected_list_id: Mapped[int | None] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("list.id", ondelete="SET NULL"),
        nullable=True,
    )

    limits: Mapped[str] = mapped_column(
        JSON,
        nullable=False,
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


# ============================================================
# List
# ============================================================

class List(Base):
    __tablename__ = "list"

    __table_args__ = (
        UniqueConstraint("community_id", "norm_name"),
    )

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

    norm_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    real_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
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

    norm_name: Mapped[str] = mapped_column(
        VARCHAR(32),
        nullable=False,
    )

    raw_name: Mapped[str] = mapped_column(
        VARCHAR(32),
        nullable=False,
    )

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
        ForeignKey("list.id", ondelete="SET NULL"),
    )


# ============================================================
# Attribute
# ============================================================

class Attribute(Base):
    __tablename__ = "attribute"

    __table_args__ = (
        UniqueConstraint("list_id", "kind"),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("list_id", "position"),

        CheckConstraint("type_id < 256"),
        CheckConstraint("kind IS NULL OR kind <= 255"),
        CheckConstraint("slot_type < 256"),
    )

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    type_id: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    kind: Mapped[int | None] = mapped_column(
        TINYINT(unsigned=True),
        nullable=True,
    )

    norm_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    real_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    slot_type: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    min_slot_count: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    max_slot_count: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )


# ============================================================
# AttributeAlias
# ============================================================

class AttributeAlias(Base):
    __tablename__ = "attribute_alias"

    __table_args__ = (
        UniqueConstraint("list_id", "norm_alias"),
        CheckConstraint("attribute_type_id < 256"),
    )

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.id", ondelete="CASCADE"),
        nullable=False,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    attribute_type_id: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    norm_alias: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    real_alias: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )


# ============================================================
# Task
# ============================================================

class Task(Base):
    __tablename__ = "task"

    __table_args__ = (
        UniqueConstraint("list_id", "norm_name"),
    )

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    norm_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    slot_name: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )


# ============================================================
# TaskAlias
# ============================================================

class TaskAlias(Base):
    __tablename__ = "task_alias"

    __table_args__ = (
        UniqueConstraint("list_id", "norm_alias"),
    )

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    norm_alias: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    slot_alias: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )


# ============================================================
# TaskAttributeValue (composite PK)
# ============================================================

class TaskAttributeValue(Base):
    __tablename__ = "task_attribute_value"

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        primary_key=True,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        primary_key=True,
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.id", ondelete="CASCADE"),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        primary_key=True,
    )

    slot_slot: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )


# ============================================================
# CommunityUserTask
# ============================================================

class CommunityUserTask(Base):
    __tablename__ = "community_user_task"

    __table_args__ = (
        UniqueConstraint(
            "list_id",
            "task_id",
            "community_user_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    community_user_id: Mapped[int] = mapped_column(
        ForeignKey("community_user.id", ondelete="CASCADE"),
        nullable=False,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )


# ============================================================
# CommunityUserTaskAttributeValue
# ============================================================

class CommunityUserTaskAttributeValue(Base):
    __tablename__ = "community_user_task_attribute_value"

    __table_args__ = (
        UniqueConstraint(
            "community_user_task_id",
            "attribute_id",
            "index",
        ),
        UniqueConstraint(
            "list_id",
            "community_user_id",
            "task_id",
            "attribute_id",
            "index",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.id", ondelete="CASCADE"),
        nullable=False,
    )

    community_user_id: Mapped[int] = mapped_column(
        ForeignKey("community_user.id", ondelete="CASCADE"),
        nullable=False,
    )

    community_user_task_id: Mapped[int] = mapped_column(
        ForeignKey("community_user_task.id", ondelete="CASCADE"),
        nullable=False,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.id", ondelete="CASCADE"),
        nullable=False,
    )

    index: Mapped[int] = mapped_column(
        TINYINT(unsigned=True),
        nullable=False,
    )

    slot_slot: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )


# ============================================================
# Engine / Session
# ============================================================

def create_engine_and_session(url: str):
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


    Session = sessionmaker(engine)

    return engine, Session


# ============================================================
# Create schema
# ============================================================

def create_schema(engine):
    Base.metadata.create_all(engine)
