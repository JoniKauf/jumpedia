# db/models.py
import typing as t
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import NormStrType, RealStrType
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.attribute import AttributeAliasID, AttributeID
from domain.types.attribute_collection_entry import (
    AttributeCollectionEntryAliasID,
    AttributeCollectionEntryID,
)
from domain.types.community import CommunityID
from domain.types.community_user import CommunityUserID
from domain.types.id import ID
from domain.types.list import ListID
from domain.types.server import ServerID
from domain.types.task import TaskAliasID, TaskID
from domain.types.user import UserID
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import NormStr, RealStr

_DEFAULT_LIMITS: t.Final[CommunityLimits] = CommunityLimits.default()


# --- Community ---


class Community(Base):
    __tablename__ = "community"

    community_id: Mapped[CommunityID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.COMMUNITY_NAME_LENGTH_MAX), unique=True
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.COMMUNITY_NAME_LENGTH_MAX), unique=True
    )

    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    default_selected_list_id: Mapped[ListID | None] = mapped_column(
        ForeignKey("list.list_id", ondelete="SET NULL")
    )

    community_list_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), default=_DEFAULT_LIMITS.community_list_count_max
    )
    list_attribute_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), default=_DEFAULT_LIMITS.list_attribute_count_max
    )
    list_task_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), default=_DEFAULT_LIMITS.list_task_count_max
    )
    attribute_alias_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), default=_DEFAULT_LIMITS.attribute_alias_count_max
    )
    attribute_task_value_slot_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        default=_DEFAULT_LIMITS.attribute_task_value_slot_count_max,
    )
    attribute_collection_entry_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        default=_DEFAULT_LIMITS.attribute_collection_entry_count_max,
    )
    attribute_collection_entry_alias_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        default=_DEFAULT_LIMITS.attribute_collection_entry_alias_count_max,
    )


class Server(Base):
    __tablename__ = "server"

    server_id: Mapped[ServerID] = mapped_column(BigInteger, primary_key=True)

    community_id: Mapped[CommunityID] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )


# --- List ---


class List(Base):
    __tablename__ = "list"

    list_id: Mapped[ListID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    community_id: Mapped[CommunityID] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.LIST_NAME_LENGTH_MAX)
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.LIST_NAME_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("community_id", "norm_name"),
    )


# --- Users ---


class User(Base):
    __tablename__ = "jumpedia_user"

    user_id: Mapped[UserID] = mapped_column(BigInteger, primary_key=True)

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.USER_NAME_LENGTH_MAX)
    )
    raw_name: Mapped[str] = mapped_column(String(CommunityLimits.USER_NAME_LENGTH_MAX))
    power: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    __table_args__ = (
        *Base.__table_args__,
        CheckConstraint(
            f"power BETWEEN {min(r.value for r in MetaRank)} AND {max(r.value for r in MetaRank)}"
        ),
    )


class CommunityUser(Base):
    __tablename__ = "community_user"

    community_user_id: Mapped[CommunityUserID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    community_id: Mapped[CommunityID] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )

    user_id: Mapped[UserID] = mapped_column(
        ForeignKey("jumpedia_user.user_id", ondelete="CASCADE")
    )

    power: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    selected_list_id: Mapped[ListID | None] = mapped_column(
        ForeignKey("list.list_id", ondelete="SET NULL")
    )

    __table_args__ = (
        *Base.__table_args__,
        CheckConstraint(f"power BETWEEN {min(CommunityRank)} AND {max(CommunityRank)}"),
    )


# --- Attribute ---


class Attribute(Base):
    __tablename__ = "attribute"

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )

    type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    kind: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    slot_type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    min_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    max_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    position: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("list_id", "kind"),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("list_id", "position"),
        # Only check most important constraints here, rest is done in service layer (valid position and so on)
        CheckConstraint(
            f"(type = {AttributeType.STATIC} AND kind BETWEEN {AttributeKind.NONE + 1} AND {max(AttributeKind)}) "
            f"OR "
            f"(type in ({AttributeType.TASK}, {AttributeType.USER}) AND kind = {AttributeKind.NONE})"
        ),
        CheckConstraint(
            f"slot_type BETWEEN {min(AttributeSlotType)} AND {max(AttributeSlotType)}"
        ),
    )


class AttributeAlias(Base):
    __tablename__ = "attribute_alias"

    attribute_alias_id: Mapped[AttributeAliasID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("list_id", "norm_alias"),
    )


# --- Attribute Collection ---


class AttributeCollectionEntry(Base):
    __tablename__ = "attribute_collection_entry"

    attribute_collection_entry_id: Mapped[AttributeCollectionEntryID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    norm_value: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )
    real_value: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("attribute_id", "norm_slot"),
        UniqueConstraint("attribute_id", "index"),
    )


class AttributeCollectionEntryAlias(Base):
    __tablename__ = "attribute_collection_entry_alias"

    attribute_collection_entry_alias_id: Mapped[AttributeCollectionEntryAliasID] = (
        mapped_column(Integer, primary_key=True, autoincrement=True)
    )

    attribute_collection_entry_id: Mapped[AttributeCollectionEntryID] = mapped_column(
        ForeignKey(
            "attribute_collection_entry.attribute_collection_entry_id",
            ondelete="CASCADE",
        )
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("attribute_id", "norm_alias"),
    )


# --- Task ---


class Task(Base):
    __tablename__ = "task"

    task_id: Mapped[TaskID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("list_id", "norm_name"),
    )


class TaskAlias(Base):
    __tablename__ = "task_alias"

    task_alias_id: Mapped[TaskAliasID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE")
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("list_id", "norm_alias"),
    )


# --- Static Task Values ---


class TaskAttributeValue(Base):
    __tablename__ = "task_attribute_value"

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE"), primary_key=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE"), primary_key=True
    )

    index: Mapped[int] = mapped_column(primary_key=True)

    real_slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )


# --- User Task ---


class CommunityUserTask(Base):
    __tablename__ = "community_user_task"

    community_user_task_id: Mapped[ID] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    community_user_id: Mapped[CommunityUserID] = mapped_column(
        ForeignKey("community_user.community_user_id", ondelete="CASCADE")
    )

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE")
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("community_user_id", "task_id"),
    )


class CommunityUserTaskAttributeValue(Base):
    __tablename__ = "community_user_task_attribute_value"

    community_user_task_attribute_value_id: Mapped[ID] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    community_user_task_id: Mapped[ID] = mapped_column(
        ForeignKey("community_user_task.community_user_task_id", ondelete="CASCADE")
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    real_slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *Base.__table_args__,
        UniqueConstraint("community_user_task_id", "attribute_id", "index"),
    )
