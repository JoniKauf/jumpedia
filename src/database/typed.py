from database.simple_orm import AUTO_SNAKE, BaseRow, Cell, cell_body


class _Blocks:
    # For BaseAttribute
    class BaseAttribute_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class BaseAttribute_ListId(BaseRow, table_name=None):
        @Cell
        def list_id(self_or_cls) -> int: cell_body()
    class BaseAttribute_Name(BaseRow, table_name=None):
        @Cell
        def name(self_or_cls) -> str: cell_body()
    class BaseAttribute_SlotType(BaseRow, table_name=None):
        @Cell
        def slot_type(self_or_cls) -> int: cell_body()
    class BaseAttribute_Position(BaseRow, table_name=None):
        @Cell
        def position(self_or_cls) -> int: cell_body()
    class BaseAttribute_MinSlots(BaseRow, table_name=None):
        @Cell
        def min_slots(self_or_cls) -> int: cell_body()
    class BaseAttribute_MaxSlots(BaseRow, table_name=None):
        @Cell
        def max_slots(self_or_cls) -> int: cell_body()
    class BaseAttribute_Uniqueness(BaseRow, table_name=None):
        @Cell
        def uniqueness(self_or_cls) -> int: cell_body()

    # For BaseAttributeAlias
    class BaseAttributeAlias_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class BaseAttributeAlias_AttributeId(BaseRow, table_name=None):
        @Cell
        def attribute_id(self_or_cls) -> int: cell_body()
    class BaseAttributeAlias_ListId(BaseRow, table_name=None):
        @Cell
        def list_id(self_or_cls) -> int: cell_body()
    class BaseAttributeAlias_Alias(BaseRow, table_name=None):
        @Cell
        def alias(self_or_cls) -> str: cell_body()

    # For BaseAttributeCollectionNode
    class BaseAttributeCollectionNode_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class BaseAttributeCollectionNode_ParentId(BaseRow, table_name=None):
        @Cell
        def parent_id(self_or_cls) -> int: cell_body()
    class BaseAttributeCollectionNode_AttributeId(BaseRow, table_name=None):
        @Cell
        def attribute_id(self_or_cls) -> int: cell_body()
    class BaseAttributeCollectionNode_Value(BaseRow, table_name=None):
        @Cell
        def value(self_or_cls) -> bytes: cell_body()
    class BaseAttributeCollectionNode_SortValue(BaseRow, table_name=None):
        @Cell
        def sort_value(self_or_cls) -> int: cell_body()

    # For BaseAttributeCollectionNodeAlias
    class BaseAttributeCollectionNodeAlias_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class BaseAttributeCollectionNodeAlias_AttributeId(BaseRow, table_name=None):
        @Cell
        def attribute_id(self_or_cls) -> int: cell_body()

    class BaseAttributeCollectionNodeAlias_AttributeCollectionNodeId(BaseRow, table_name=None):
        @Cell
        def attribute_collection_node_id(self_or_cls) -> int: cell_body()

    class BaseAttributeCollectionNodeAlias_Alias(BaseRow, table_name=None):
        @Cell
        def alias(self_or_cls) -> int: cell_body()

    # For BaseAttributeTaskValue
    class BaseAttributeTaskValue_TaskId(BaseRow, table_name=None):
        @Cell
        def task_id(self_or_cls) -> int: cell_body()
    class BaseAttributeTaskValue_AttributeId(BaseRow, table_name=None):
        @Cell
        def attribute_id(self_or_cls) -> int: cell_body()
    class BaseAttributeTaskValue_Value(BaseRow, table_name=None):
        @Cell
        def value(self_or_cls) -> bytes: cell_body()

    # For Community
    class Community_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class Community_Name(BaseRow, table_name=None):
        @Cell
        def name(self_or_cls) -> str: cell_body()
    class Community_DefaultSelectedListId(BaseRow, table_name=None):
        @Cell
        def default_selected_list_id(self_or_cls) -> int: cell_body()

    # For Server
    class Server_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class Server_CommunityId(BaseRow, table_name=None):
        @Cell
        def community_id(self_or_cls) -> int: cell_body()

    # For List
    class List_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class List_CommunityId(BaseRow, table_name=None):
        @Cell
        def community_id(self_or_cls) -> int: cell_body()
    class List_Name(BaseRow, table_name=None):
        @Cell
        def name(self_or_cls) -> str: cell_body()

    # For JumpediaUser
    class JumpediaUser_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class JumpediaUser_Name(BaseRow, table_name=None):
        @Cell
        def name(self_or_cls) -> str: cell_body()
    class JumpediaUser_Power(BaseRow, table_name=None):
        @Cell
        def power(self_or_cls) -> int: cell_body()

    # For CommunityUser
    class CommunityUser_CommunityId(BaseRow, table_name=None):
        @Cell
        def community_id(self_or_cls) -> int: cell_body()
    class CommunityUser_UserId(BaseRow, table_name=None):
        @Cell
        def user_id(self_or_cls) -> int: cell_body()
    class CommunityUser_Power(BaseRow, table_name=None):
        @Cell
        def power(self_or_cls) -> int: cell_body()
    class CommunityUser_SelectedListId(BaseRow, table_name=None):
        @Cell
        def selected_list_id(self_or_cls) -> int: cell_body()

    # For Task
    class Task_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class Task_ListId(BaseRow, table_name=None):
        @Cell
        def list_id(self_or_cls) -> int: cell_body()
    class Task_Name(BaseRow, table_name=None):
        @Cell
        def name(self_or_cls) -> str: cell_body()

    # For TaskAlias
    class TaskAlias_Id(BaseRow, table_name=None):
        @Cell
        def id(self_or_cls) -> int: cell_body()
    class TaskAlias_TaskId(BaseRow, table_name=None):
        @Cell
        def task_id(self_or_cls) -> int: cell_body()
    class TaskAlias_ListId(BaseRow, table_name=None):
        @Cell
        def list_id(self_or_cls) -> int: cell_body()
    class TaskAlias_Alias(BaseRow, table_name=None):
        @Cell
        def alias(self_or_cls) -> str: cell_body()

    # For UserAttributeTaskValue
    class UserAttributeTaskValue_UserId(BaseRow, table_name=None):
        @Cell
        def user_id(self_or_cls) -> int: cell_body()


class BaseAttribute(
    _Blocks.BaseAttribute_Id,
    _Blocks.BaseAttribute_ListId,
    _Blocks.BaseAttribute_Name,
    _Blocks.BaseAttribute_SlotType,
    _Blocks.BaseAttribute_Position,
    _Blocks.BaseAttribute_MinSlots,
    _Blocks.BaseAttribute_MaxSlots,
    _Blocks.BaseAttribute_Uniqueness,
    table_name=AUTO_SNAKE
):
    pass


class BaseAttributeAlias(
    _Blocks.BaseAttributeAlias_Id,
    _Blocks.BaseAttributeAlias_AttributeId,
    _Blocks.BaseAttributeAlias_ListId,
    _Blocks.BaseAttributeAlias_Alias,
    table_name=AUTO_SNAKE
):
    pass


class BaseAttributeCollectionNode(
    _Blocks.BaseAttributeCollectionNode_Id,
    _Blocks.BaseAttributeCollectionNode_ParentId,
    _Blocks.BaseAttributeCollectionNode_AttributeId,
    _Blocks.BaseAttributeCollectionNode_Value,
    _Blocks.BaseAttributeCollectionNode_SortValue,
    table_name=AUTO_SNAKE
):
    pass


class BaseAttributeCollectionNodeAlias(
    _Blocks.BaseAttributeCollectionNodeAlias_Id,
    _Blocks.BaseAttributeCollectionNodeAlias_AttributeId,
    _Blocks.BaseAttributeCollectionNodeAlias_AttributeCollectionNodeId,
    _Blocks.BaseAttributeAlias_Alias,
    table_name=AUTO_SNAKE
):
    pass

class BaseAttributeTaskValue(
    _Blocks.BaseAttributeTaskValue_TaskId,
    _Blocks.BaseAttributeTaskValue_AttributeId,
    _Blocks.BaseAttributeTaskValue_Value,
    table_name=AUTO_SNAKE
):
    pass


class Community(
    _Blocks.Community_Id,
    _Blocks.Community_Name,
    _Blocks.Community_DefaultSelectedListId,
    table_name=AUTO_SNAKE
):
    pass


class Server(
    _Blocks.Server_Id,
    _Blocks.Server_CommunityId,
    table_name=AUTO_SNAKE
):
    pass


# --- Per Community ---

class List(
    _Blocks.List_Id,
    _Blocks.List_CommunityId,
    _Blocks.List_Name,
    table_name=AUTO_SNAKE
):
    pass


class JumpediaUser(
    _Blocks.JumpediaUser_Id,
    _Blocks.JumpediaUser_Name,
    _Blocks.JumpediaUser_Power,
    table_name=AUTO_SNAKE
):
    pass


class CommunityUser(
    _Blocks.CommunityUser_CommunityId,
    _Blocks.CommunityUser_UserId,
    _Blocks.CommunityUser_Power,
    _Blocks.CommunityUser_SelectedListId,
    table_name=AUTO_SNAKE
):
    pass


# --- Static Attribute ---

class StaticAttribute(BaseAttribute, table_name=AUTO_SNAKE):
    pass


class StaticAttributeAlias(BaseAttributeAlias, table_name=AUTO_SNAKE):
    pass


# --- Task Attribute ---

class TaskAttribute(BaseAttribute, table_name=AUTO_SNAKE):
    pass


class TaskAttributeAlias(BaseAttributeAlias, table_name=AUTO_SNAKE):
    pass


class TaskAttributeCollectionNode(BaseAttributeCollectionNode, table_name=AUTO_SNAKE):
    pass

class TaskAttributeCollectionNodeAlias(BaseAttributeCollectionNodeAlias, table_name=AUTO_SNAKE):
    pass


# --- User Attribute ---

class UserAttribute(BaseAttribute, table_name=AUTO_SNAKE):
    pass


class UserAttributeAlias(BaseAttributeAlias, table_name=AUTO_SNAKE):
    pass


class UserAttributeCollectionNode(BaseAttributeCollectionNode, table_name=AUTO_SNAKE):
    pass

class UserAttributeCollectionNodeAlias(BaseAttributeCollectionNodeAlias, table_name=AUTO_SNAKE):
    pass


# --- Task ---

class Task(
    _Blocks.Task_Id,
    _Blocks.Task_ListId,
    _Blocks.Task_Name,
    table_name=AUTO_SNAKE
):
    pass


class TaskAlias(
    _Blocks.TaskAlias_Id,
    _Blocks.TaskAlias_TaskId,
    _Blocks.TaskAlias_ListId,
    _Blocks.TaskAlias_Alias,
    table_name=AUTO_SNAKE
):
    pass


class StaticAttributeTaskValue(BaseAttributeTaskValue, table_name=AUTO_SNAKE):
    pass

class TaskAttributeTaskValue(BaseAttributeTaskValue, table_name=AUTO_SNAKE):
    pass

class UserAttributeTaskValue(
    _Blocks.UserAttributeTaskValue_UserId,
    BaseAttributeTaskValue, 
    table_name=AUTO_SNAKE
):
    pass