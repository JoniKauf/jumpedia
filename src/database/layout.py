from typing import ClassVar
from database.queries import BaseRow, CellAlias




class Community(BaseRow):
    id: int
    name: str
    default_selected_list_id: int


class Server(BaseRow):
    id: int
    community_id: int


# --- Per Community ---

class List(BaseRow):
    id: int
    community_id: int
    name: str

class JumpediaUser(BaseRow):
    id: int
    name: str
    power: int

class CommunityUser(BaseRow):
    community_id: int
    user_id: int
    power: int
    selected_list_id: int


# --- Static Attribute ---

class StaticAttribute(BaseRow):
    id: int
    list_id: int
    name: str
    slot_type: int
    position: int
    min_slots: int
    max_slots: int
    uniqueness: int

class StaticAttributeAlias(BaseRow):
    id: int
    static_attribute_id: int
    list_id: int
    alias: str

    @CellAlias()


# --- Task Attribute ---

class TaskAttribute(BaseRow):
    id: int
    list_id: int
    name: str
    slot_type: int
    position: int
    min_slots: int
    max_slots: int
    uniqueness: int

class TaskAttributeAlias(BaseRow):
    id: int
    task_attribute_id: int
    list_id: int
    alias: str

    @property
    def _attribute_id(self) -> int:
        return self.task_attribute_id

class TaskAttributeCollectionNode(BaseRow):
    id: int
    parent_id: int
    task_attribute_id: int
    value: bytes
    sort_value: int

    @property
    def _attribute_id(self) -> int:
        return self.task_attribute_id

class TaskAttributeCollectionNodeAlias(BaseRow):
    id: int
    task_attribute_id: int
    task_attribute_collection_node_id: int
    alias: bytes

    @property
    def _attribute_id(self) -> int:
        return self.task_attribute_id
    
    @property
    def _attribute_collection_node_id(self) -> int:
        return self.task_attribute_collection_node_id


# --- User Attribute ---

class UserAttribute(BaseRow):
    id: int
    list_id: int
    name: str
    position: int
    slot_type: int
    min_slots: int
    max_slots: int
    uniqueness: int

class UserAttributeAlias(BaseRow):
    id: int
    user_attribute_id: int
    list_id: int
    alias: str

    @property
    def _attribute_id(self) -> int:
        return self.user_attribute_id
    

class UserAttributeCollectionNode(BaseRow):
    id: int
    parent_id: int
    user_attribute_id: int
    value: bytes
    sort_value: int

class UserAttributeCollectionNodeAlias(BaseRow):
    id: int
    user_attribute_id: int
    user_attribute_collection_node_id: int
    alias: bytes

    @property
    def _attribute_id(self) -> int:
        return self.user_attribute_id
    
    @property
    def _attribute_collection_node_id(self) -> int:
        return self.user_attribute_collection_node_id


# --- Task ---

class Task(BaseRow):
    id: int
    list_id: int
    name: str

class TaskAlias(BaseRow):
    id: int
    task_id: int
    list_id: int
    alias: str

class StaticAttributeTaskValue(BaseRow):
    task_id: int
    static_attribute_id: int
    value: bytes

    @property
    def _attribute_id(self) -> int:
        return self.static_attribute_id


class TaskAttributeTaskValue(BaseRow):
    task_id: int
    task_attribute_id: int
    value: bytes

    @property
    def _attribute_id(self) -> int:
        return self.task_attribute_id

class UserAttributeTaskValue(BaseRow):
    task_id: int
    user_id: int
    user_attribute_id: int
    value: bytes

    @property
    def _attribute_id(self) -> int:
        return self.user_attribute_id