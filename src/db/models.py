# db/models.py
import typing as t
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from db.base import BaseModel
from db.types import NormStrType, RealStrType
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.rank import CommunityRank, MetaRank
from domain.typing.attribute import AttributeID
from domain.typing.collection_entry import CollectionEntryID
from domain.typing.community import CommunityID
from domain.typing.list import ListID
from domain.typing.member import MemberID
from domain.typing.member_task import MemberTaskID
from domain.typing.server import ServerID
from domain.typing.task import TaskID
from domain.typing.user import UserID
from domain.value_objects import string
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import NormStr, RealStr

# --- Community ---


class CommunityModel(BaseModel):
    __tablename__ = "community"

    community_id: Mapped[CommunityID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.COMMUNITY_NAME_LENGTH_MAX
            * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        ),
        unique=True,
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.COMMUNITY_NAME_LENGTH_MAX), unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    default_selected_list_id: Mapped[ListID | None] = mapped_column(
        ForeignKey("list.list_id", ondelete="SET NULL")
    )

    community_list_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    list_attribute_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    list_task_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    attribute_alias_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    field_slot_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    collection_entry_count_max: Mapped[int] = mapped_column(INTEGER(unsigned=True))
    collection_entry_alias_count_max: Mapped[int] = mapped_column(
        INTEGER(unsigned=True)
    )


class ServerModel(BaseModel):
    __tablename__ = "server"

    server_id: Mapped[ServerID] = mapped_column(BigInteger, primary_key=True)

    community_id: Mapped[CommunityID] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )


# --- List ---


class ListModel(BaseModel):
    __tablename__ = "list"

    list_id: Mapped[ListID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    community_id: Mapped[CommunityID] = mapped_column(
        ForeignKey("community.community_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.LIST_NAME_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.LIST_NAME_LENGTH_MAX)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("community_id", "norm_name"),
    )


# --- Users ---


class UserModel(BaseModel):
    __tablename__ = "jumpedia_user"

    user_id: Mapped[UserID] = mapped_column(BigInteger, primary_key=True)

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.USER_NAME_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    raw_name: Mapped[str] = mapped_column(String(CommunityLimits.USER_NAME_LENGTH_MAX))
    power: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    __table_args__ = (
        *BaseModel.__table_args__,
        CheckConstraint(
            f"power BETWEEN {min(r for r in MetaRank)} AND {max(r for r in MetaRank)}"
        ),
    )


class MemberModel(BaseModel):
    __tablename__ = "member"

    member_id: Mapped[MemberID] = mapped_column(
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
        *BaseModel.__table_args__,
        CheckConstraint(f"power BETWEEN {min(CommunityRank)} AND {max(CommunityRank)}"),
    )


# --- Attribute ---

_KIND_TO_TYPE_CASE = " ".join(
    f"WHEN {kind.value} THEN {kind.type.value}"
    for kind in AttributeKind
    if kind is not AttributeKind.NONE
)


class AttributeModel(BaseModel):
    __tablename__ = "attribute"

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX
            * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )

    type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    kind: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    slot_type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    min_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    max_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    unique_slots: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("list_id", "kind"),
        UniqueConstraint("list_id", "norm_name"),
        UniqueConstraint("list_id", "position"),
        # Only check most important constraints here, rest is done in service layer (valid position and so on)
        CheckConstraint(
            f"kind IS NULL OR kind IN ({', '.join(str(kind.value) for kind in AttributeKind if kind is not AttributeKind.NONE)})"
        ),
        CheckConstraint(f"kind IS NULL OR type = CASE kind {_KIND_TO_TYPE_CASE} END"),
        CheckConstraint(
            f"slot_type IN ({', '.join(str(slot_type.value) for slot_type in AttributeSlotType)})",
        ),
    )


class AttributeAliasModel(BaseModel):
    __tablename__ = "attribute_alias"

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE"),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX
            * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("list_id", "norm_alias"),
    )


# --- Attribute Collection ---


class CollectionEntryModel(BaseModel):
    __tablename__ = "collection_entry"

    collection_entry_id: Mapped[CollectionEntryID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    norm_value: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.FIELD_SLOT_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_value: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("attribute_id", "norm_slot"),
        UniqueConstraint("attribute_id", "index"),
    )


class CollectionEntryAliasModel(BaseModel):
    __tablename__ = "collection_entry_alias"

    collection_entry_id: Mapped[CollectionEntryID] = mapped_column(
        ForeignKey(
            "collection_entry.collection_entry_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.FIELD_SLOT_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("attribute_id", "norm_alias"),
    )


# --- Task ---


class TaskModel(BaseModel):
    __tablename__ = "task"

    task_id: Mapped[TaskID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_name: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.FIELD_SLOT_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("list_id", "norm_name"),
    )


class TaskAliasModel(BaseModel):
    __tablename__ = "task_alias"

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE"), primary_key=True
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    list_id: Mapped[ListID] = mapped_column(
        ForeignKey("list.list_id", ondelete="CASCADE")
    )

    norm_alias: Mapped[NormStr] = mapped_column(
        NormStrType(
            CommunityLimits.FIELD_SLOT_LENGTH_MAX * string.UNICODE_STR_LENGTH_MULTIPLE_MAX_AFTER_CASING
        )
    )
    real_alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("list_id", "norm_alias"),
    )


class FieldSlotModel(BaseModel):
    __tablename__ = "field_slot"

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE"), primary_key=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE"), primary_key=True
    )

    index: Mapped[int] = mapped_column(primary_key=True)

    real_slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    norm_slot: Mapped[NormStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX * 3)
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        # Index for looking up all task slots for a given attribute
        Index(
            "ix_field_slot_attribute_task_index",
            "attribute_id",
            "task_id",
            "index",
        ),
    )


# --- User Task ---


class MemberTaskModel(BaseModel):
    __tablename__ = "user_task"

    member_task_id: Mapped[MemberTaskID] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    member_id: Mapped[MemberID] = mapped_column(
        ForeignKey("member.member_id", ondelete="CASCADE")
    )

    task_id: Mapped[TaskID] = mapped_column(
        ForeignKey("task.task_id", ondelete="CASCADE")
    )

    given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    given_by: Mapped[MemberID | None] = mapped_column(
        ForeignKey("member.member_id", ondelete="SET NULL")
    )

    __table_args__ = (
        *BaseModel.__table_args__,
        UniqueConstraint("member_id", "task_id"),
    )


class MemberFieldSlotModel(BaseModel):
    __tablename__ = "member_field_slot"

    member_task_id: Mapped[MemberTaskID] = mapped_column(
        BigInteger,
        ForeignKey("member_task.member_task_id", ondelete="CASCADE"),
        primary_key=True,
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        ForeignKey("attribute.attribute_id", ondelete="CASCADE"), primary_key=True
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    real_slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )

    norm_slot: Mapped[NormStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX * 3)
    )
