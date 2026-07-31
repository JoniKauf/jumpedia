from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    __table_args__ = ({"schema": "old"},)


class CommunityModel(BaseModel):
    __tablename__ = "community"

    id: Mapped[int] = mapped_column(primary_key=True)
    norm_name: Mapped[str]
    real_name: Mapped[str]
    default_selected_list_id: Mapped[int | None]
    limits: Mapped[str]


class ServerModel(BaseModel):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int]


class JumpediaUserModel(BaseModel):
    __tablename__ = "jumpedia_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    norm_name: Mapped[str]
    raw_name: Mapped[str]
    power: Mapped[int]


class ListModel(BaseModel):
    __tablename__ = "list"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int]
    norm_name: Mapped[str]
    real_name: Mapped[str]


class CommunityUserModel(BaseModel):
    __tablename__ = "community_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int]
    jumpedia_user_id: Mapped[int]
    power: Mapped[int]
    selected_list_id: Mapped[int | None]


class AttributeModel(BaseModel):
    __tablename__ = "attribute"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int]
    type_id: Mapped[int]
    norm_name: Mapped[str]
    real_name: Mapped[str]
    slot_type: Mapped[int]
    position: Mapped[int]
    min_slot_count: Mapped[int]
    max_slot_count: Mapped[int]
    kind: Mapped[int | None]


class AttributeAliasModel(BaseModel):
    __tablename__ = "attribute_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[int]
    list_id: Mapped[int]
    attribute_type_id: Mapped[int]
    norm_alias: Mapped[str]
    real_alias: Mapped[str]


class AttributeCollectionEntryModel(BaseModel):
    __tablename__ = "attribute_collection_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[int]
    index: Mapped[int]
    norm_slot: Mapped[str]
    slot_slot: Mapped[str]


class AttributeCollectionEntryAliasModel(BaseModel):
    __tablename__ = "attribute_collection_entry_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_collection_entry_id: Mapped[int]
    attribute_id: Mapped[int]
    norm_alias: Mapped[str]
    slot_alias: Mapped[str]


class TaskModel(BaseModel):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int]
    norm_name: Mapped[str]
    slot_name: Mapped[str]


class TaskAliasModel(BaseModel):
    __tablename__ = "task_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int]
    list_id: Mapped[int]
    norm_alias: Mapped[str]
    slot_alias: Mapped[str]


class TaskAttributeValueModel(BaseModel):
    __tablename__ = "task_attribute_value"

    list_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[int] = mapped_column(primary_key=True)
    index: Mapped[int] = mapped_column(primary_key=True)
    slot_slot: Mapped[str]


class CommunityUserTaskModel(BaseModel):
    __tablename__ = "community_user_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int]
    task_id: Mapped[int]
    community_user_id: Mapped[int]


class CommunityUserTaskAttributeValueModel(BaseModel):
    __tablename__ = "community_user_task_attribute_value"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_user_task_id: Mapped[int]
    list_id: Mapped[int]
    community_user_id: Mapped[int]
    task_id: Mapped[int]
    attribute_id: Mapped[int]
    index: Mapped[int]
    slot_slot: Mapped[str]
