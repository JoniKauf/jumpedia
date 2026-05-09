# db/models.py
from sqlalchemy import (
    CheckConstraint, ForeignKey, String, Integer, BigInteger, JSON,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
import domain
from domain import rank
from domain.limits import Limits
import typing as t


_DEFAULT_LIMITS: t.Final[Limits] = Limits.default()

# --- Community ---

class Community(Base):
    __tablename__ = "community"

    community_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    norm_name: Mapped[str] = mapped_column(String(255), unique=True)
    real_name: Mapped[str] = mapped_column(String(255), unique=True)

    default_selected_list_id: Mapped[int | None] = mapped_column(
        ForeignKey("list.list_id", ondelete="SET NULL")
    )

    community_list_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.community_list_count_max)
    list_attribute_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.list_attribute_count_max)
    list_task_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.list_task_count_max)
    attribute_alias_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.attribute_alias_count_max)
    attribute_task_value_slot_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.attribute_task_value_slot_count_max)
    attribute_collection_entry_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.attribute_collection_entry_count_max)
    attribute_collection_entry_alias_count_max: Mapped[int] = mapped_column(Integer, default=_DEFAULT_LIMITS.attribute_collection_entry_alias_count_max)


class Server(Base):
    __tablename__ = "server"

    server_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )


# --- List ---

class List(Base):
    __tablename__ = "list"

    list_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )

    norm_name: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("community_id", "norm_name"),
        Base.__table_args__,
    )


# --- Users ---

class User(Base):
    __tablename__ = "jumpedia_user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    norm_name: Mapped[str] = mapped_column(String(32))
    raw_name: Mapped[str] = mapped_column(String(32))
    power: Mapped[int] = mapped_column(Integer)


class CommunityUser(Base):
    __tablename__ = "community_user"

    community_user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("jumpedia_user.jumpedia_user_id", ondelete="CASCADE")
    )

    power: Mapped[int] = mapped_column(Integer)

    selected_list_id: Mapped[int | None] = mapped_column(
        ForeignKey("list.list_id", ondelete="SET NULL")
    )


# --- Attribute ---

class Attribute(Base):
    __tablename__ = "attribute"

    attribute_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    type_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[int | None] = mapped_column(Integer)

    norm_name: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(255))

    slot_type: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)

    min_slot_count: Mapped[int] = mapped_column(Integer)
    max_slot_count: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("list_id", "kind"),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("list_id", "position"),
        Base.__table_args__,
    )


class AttributeAlias(Base):
    __tablename__ = "attribute_alias"

    attribute_alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    attribute_type_id: Mapped[int] = mapped_column(Integer)

    norm_alias: Mapped[str] = mapped_column(String(255))
    real_alias: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("list_id", "norm_alias"),
        Base.__table_args__,
    )


# --- Attribute Collection ---

class AttributeCollectionEntry(Base):
    __tablename__ = "attribute_collection_entry"

    attribute_collection_entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(Integer)

    norm_slot: Mapped[str] = mapped_column(String(255))
    slot_slot: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("attribute_id", "norm_slot"),
        UniqueConstraint("attribute_id", "index"),
        Base.__table_args__,
    )


class AttributeCollectionEntryAlias(Base):
    __tablename__ = "attribute_collection_entry_alias"

    attribute_collection_entry_alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    attribute_collection_entry_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_collection_entry.attribute_collection_entry_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[str] = mapped_column(String(255))
    slot_alias: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("attribute_id", "norm_alias"),
        Base.__table_args__,
    )


# --- Task ---

class Task(Base):
    __tablename__ = "task"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_name: Mapped[str] = mapped_column(String(255))
    slot_name: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("list_id", "norm_name"),
        Base.__table_args__,
    )


class TaskAlias(Base):
    __tablename__ = "task_alias"

    task_alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE")
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[str] = mapped_column(String(255))
    slot_alias: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("list_id", "norm_alias"),
        Base.__table_args__,
    )


# --- Static Task Values ---

class TaskAttributeValue(Base):
    __tablename__ = "task_attribute_value"

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE"),
        primary_key=True
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE"),
        primary_key=True
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE"),
        primary_key=True
    )

    index: Mapped[int] = mapped_column(primary_key=True)

    slot_slot: Mapped[str] = mapped_column(String(255))


# --- User Task ---

class CommunityUserTask(Base):
    __tablename__ = "community_user_task"

    community_user_task_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    list_id: Mapped[int] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    community_user_id: Mapped[int] = mapped_column(
        ForeignKey("community_user.community_user_id", ondelete="CASCADE")
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE")
    )

    __table_args__ = (
        UniqueConstraint("list_id", "task_id", "community_user_id"),
        Base.__table_args__,
    )


class CommunityUserTaskAttributeValue(Base):
    __tablename__ = "community_user_task_attribute_value"

    community_user_task_attribute_value_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    community_user_task_id: Mapped[int] = mapped_column(
        ForeignKey("community_user_task.community_user_task_id", ondelete="CASCADE")
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(Integer)

    slot_slot: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint("community_user_task_id", "attribute_id", "index"),
        Base.__table_args__,
    )