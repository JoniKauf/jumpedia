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

from jumpedia.db.base import SCHEMA_NAME, BaseModel
from jumpedia.db.types import NormHashType, RealStrType
from jumpedia.domain.enums.attribute import AttributeKind, AttributeSlotType
from jumpedia.domain.enums.rank import CommunityRank, MetaRank
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.collection_entry import CollectionEntryID
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.member import MemberID
from jumpedia.domain.typing.member_task import MemberTaskID
from jumpedia.domain.typing.server import ServerID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects import string
from jumpedia.domain.value_objects.community import CommunityLimits
from jumpedia.domain.value_objects.string import NormHash, RealStr

# --- Community ---


class CommunityModel(BaseModel):
    __tablename__ = "community"

    community_id: Mapped[CommunityID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.COMMUNITY_NAME_LENGTH_MAX)
    )
    name_hash: Mapped[NormHash] = mapped_column(
        NormHashType,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    default_selected_list_id: Mapped[ListID | None] = mapped_column(
        Integer,
        ForeignKey(f"{SCHEMA_NAME}.list.list_id", ondelete="SET NULL", use_alter=True),
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
        Integer, ForeignKey(CommunityModel.community_id, ondelete="CASCADE")
    )


# --- List ---


class ListModel(BaseModel):
    __tablename__ = "list"

    list_id: Mapped[ListID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    community_id: Mapped[CommunityID] = mapped_column(
        Integer, ForeignKey(CommunityModel.community_id, ondelete="CASCADE")
    )

    name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.LIST_NAME_LENGTH_MAX)
    )
    name_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        UniqueConstraint("community_id", "name_hash"),
        *BaseModel.__table_args__,
    )


# --- Users ---


class UserModel(BaseModel):
    __tablename__ = "user"

    user_id: Mapped[UserID] = mapped_column(BigInteger, primary_key=True)

    name: Mapped[str] = mapped_column(String(CommunityLimits.USER_NAME_LENGTH_MAX))

    meta_rank: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    __table_args__ = (
        CheckConstraint(
            f"meta_rank BETWEEN {min(r for r in MetaRank)} AND {max(r for r in MetaRank)}"
        ),
        *BaseModel.__table_args__,
    )


class MemberModel(BaseModel):
    __tablename__ = "member"

    member_id: Mapped[MemberID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    community_id: Mapped[CommunityID] = mapped_column(
        Integer, ForeignKey(CommunityModel.community_id, ondelete="CASCADE")
    )

    user_id: Mapped[UserID] = mapped_column(
        BigInteger, ForeignKey(UserModel.user_id, ondelete="CASCADE")
    )

    community_rank: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    selected_list_id: Mapped[ListID | None] = mapped_column(
        Integer, ForeignKey(ListModel.list_id, ondelete="SET NULL")
    )

    __table_args__ = (
        CheckConstraint(
            f"community_rank BETWEEN {min(CommunityRank)} AND {max(CommunityRank)}"
        ),
        *BaseModel.__table_args__,
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
        Integer, ForeignKey(ListModel.list_id, ondelete="CASCADE")
    )

    name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )
    name_hash: Mapped[NormHash] = mapped_column(NormHashType)

    type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    kind: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    slot_type: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    min_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    max_slot_count: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    unique_slots: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    # visibility: Mapped[int] = mapped_column(TINYINT(unsigned=True))  # TODO: coming soon!

    __table_args__ = (
        UniqueConstraint("list_id", "kind"),
        UniqueConstraint("list_id", "name_hash"),
        UniqueConstraint("list_id", "position"),
        # Only check most important constraints here, rest is done in service layer (valid position and so on)
        CheckConstraint(
            f"kind IS NULL OR kind IN ({', '.join(str(kind.value) for kind in AttributeKind if kind is not AttributeKind.NONE)})"
        ),
        CheckConstraint(f"kind IS NULL OR type = CASE kind {_KIND_TO_TYPE_CASE} END"),
        CheckConstraint(
            f"slot_type IN ({', '.join(str(slot_type.value) for slot_type in AttributeSlotType)})",
        ),
        *BaseModel.__table_args__,
    )


class AttributeAliasModel(BaseModel):
    __tablename__ = "attribute_alias"

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer,
        ForeignKey(AttributeModel.attribute_id, ondelete="CASCADE"),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    list_id: Mapped[ListID] = mapped_column(
        Integer, ForeignKey(ListModel.list_id, ondelete="CASCADE")
    )

    alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.ATTRIBUTE_SYN_LENGTH_MAX)
    )
    alias_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        UniqueConstraint("list_id", "alias_hash"),
        *BaseModel.__table_args__,
    )


# --- Attribute Collection ---


class CollectionEntryModel(BaseModel):
    __tablename__ = "collection_entry"

    collection_entry_id: Mapped[CollectionEntryID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer, ForeignKey(AttributeModel.attribute_id, ondelete="CASCADE")
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True))

    value: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    value_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        UniqueConstraint("attribute_id", "value_hash"),
        UniqueConstraint("attribute_id", "index"),
        *BaseModel.__table_args__,
    )


class CollectionEntryAliasModel(BaseModel):
    __tablename__ = "collection_entry_alias"

    collection_entry_id: Mapped[CollectionEntryID] = mapped_column(
        Integer,
        ForeignKey(
            CollectionEntryModel.collection_entry_id,
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer, ForeignKey(AttributeModel.attribute_id, ondelete="CASCADE")
    )

    alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    alias_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        UniqueConstraint("attribute_id", "alias_hash"),
        *BaseModel.__table_args__,
    )


# --- Task ---


class TaskModel(BaseModel):
    __tablename__ = "task"

    task_id: Mapped[TaskID] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    list_id: Mapped[ListID] = mapped_column(
        Integer, ForeignKey(ListModel.list_id, ondelete="CASCADE")
    )

    name: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    name_hash: Mapped[NormHash] = mapped_column(NormHashType)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("list_id", "name_hash"),
        *BaseModel.__table_args__,
    )


class TaskAliasModel(BaseModel):
    __tablename__ = "task_alias"

    task_id: Mapped[TaskID] = mapped_column(
        Integer, ForeignKey(TaskModel.task_id, ondelete="CASCADE"), primary_key=True
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    list_id: Mapped[ListID] = mapped_column(
        Integer, ForeignKey(ListModel.list_id, ondelete="CASCADE")
    )

    alias: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    alias_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        UniqueConstraint("list_id", "alias_hash"),
        *BaseModel.__table_args__,
    )


class FieldSlotModel(BaseModel):
    __tablename__ = "field_slot"

    task_id: Mapped[TaskID] = mapped_column(
        Integer, ForeignKey(TaskModel.task_id, ondelete="CASCADE"), primary_key=True
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer,
        ForeignKey(AttributeModel.attribute_id, ondelete="CASCADE"),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(primary_key=True)

    slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    slot_hash: Mapped[NormHash] = mapped_column(NormHashType)

    __table_args__ = (
        # Index for looking up all task slots for a given attribute
        Index(
            "ix_field_slot_attribute_task_index",
            "attribute_id",
            "task_id",
            "index",
        ),
        *BaseModel.__table_args__,
    )


# --- User Task ---


class MemberTaskModel(BaseModel):
    __tablename__ = "member_task"

    member_task_id: Mapped[MemberTaskID] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    member_id: Mapped[MemberID] = mapped_column(
        Integer, ForeignKey(MemberModel.member_id, ondelete="CASCADE")
    )

    task_id: Mapped[TaskID] = mapped_column(
        Integer, ForeignKey(TaskModel.task_id, ondelete="CASCADE")
    )

    given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    given_by: Mapped[MemberID | None] = mapped_column(
        Integer, ForeignKey(MemberModel.member_id, ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("member_id", "task_id"),
        *BaseModel.__table_args__,
    )


class MemberFieldSlotModel(BaseModel):
    __tablename__ = "member_field_slot"

    member_task_id: Mapped[MemberTaskID] = mapped_column(
        BigInteger,
        ForeignKey(MemberTaskModel.member_task_id, ondelete="CASCADE"),
        primary_key=True,
    )

    attribute_id: Mapped[AttributeID] = mapped_column(
        Integer,
        ForeignKey(AttributeModel.attribute_id, ondelete="CASCADE"),
        primary_key=True,
    )

    index: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)

    slot: Mapped[RealStr] = mapped_column(
        RealStrType(CommunityLimits.FIELD_SLOT_LENGTH_MAX)
    )
    slot_hash: Mapped[NormHash] = mapped_column(NormHashType)
