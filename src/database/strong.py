from typing import Any as _Any

class _ColumnName(str):
    # To be used in f-strings, aka queries
    def __str__(self) -> str:
        return f"`{super().__str__()}`"

class TableMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], dct: dict[str, _Any]):
        ANNOTATIONS = '__annotations__'

        annotations: dict[str, _Any] = dct.get(ANNOTATIONS, {})
    
        for k, typ in annotations.items():
            if typ is not _ColumnName:
                raise RuntimeError(f"Not good type in strong module for class '{name}', attribute '{k}'")
            
            dct[k] = _ColumnName(k.lstrip("_"))

        return super().__new__(cls, name, bases, dct)
    
    def __str__(self) -> str:
        from utils import text
        return f"`{text.pascal_to_snake(self.__name__)}`"


DATABASE_NAME: str = 'jumpedia'

type SingleTableRowT = dict[str, _Any]
type ManyTableRowT = list[SingleTableRowT]

class Tables:
    # --- Meta ---

    class Community(metaclass=TableMeta):
        id: _ColumnName
        name: _ColumnName
        default_selected_list_id: _ColumnName

    class Guild(metaclass=TableMeta):
        id: _ColumnName
        community_id: _ColumnName

    class MetaRank(metaclass=TableMeta):
        user_id: _ColumnName
        power: _ColumnName


    # --- Per Community ---

    class List(metaclass=TableMeta):
        id: _ColumnName
        community_id: _ColumnName
        name: _ColumnName

    class User(metaclass=TableMeta):
        id: _ColumnName
        community_id: _ColumnName
        # TODO: add name
        power: _ColumnName
        selected_list_id: _ColumnName


    # --- Static Attribute ---

    class StaticAttribute(metaclass=TableMeta):
        id: _ColumnName
        list_id: _ColumnName
        name: _ColumnName
        value_type: _ColumnName
        index: _ColumnName
        min_slots: _ColumnName
        max_slots: _ColumnName
        unique_slots: _ColumnName
        unique_value_per_list: _ColumnName

    class StaticAttributeAlias(metaclass=TableMeta):
        id: _ColumnName
        static_attribute_id: _ColumnName
        list_id: _ColumnName
        alias: _ColumnName


    # --- Task Attribute ---

    class TaskAttribute(metaclass=TableMeta):
        id: _ColumnName
        list_id: _ColumnName
        name: _ColumnName
        value_type: _ColumnName
        index: _ColumnName
        min_slots: _ColumnName
        max_slots: _ColumnName
        unique_slots: _ColumnName
        unique_value_per_list: _ColumnName

    class TaskAttributeAlias(metaclass=TableMeta):
        id: _ColumnName
        task_attribute_id: _ColumnName
        list_id: _ColumnName
        alias: _ColumnName

    class TaskAttributeCollectionNode(metaclass=TableMeta):
        id: _ColumnName
        root_id: _ColumnName
        task_attribute_id: _ColumnName
        value: _ColumnName
        sort_value: _ColumnName
        _aliases: _ColumnName

    class TaskAttributeCollectionNodeAlias(metaclass=TableMeta):
        id: _ColumnName
        task_attribute_collection_node_id: _ColumnName
        alias: _ColumnName


    # --- User Attribute ---

    class UserAttribute(metaclass=TableMeta):
        id: _ColumnName
        list_id: _ColumnName
        name: _ColumnName
        index: _ColumnName
        value_type: _ColumnName
        min_slots: _ColumnName
        max_slots: _ColumnName
        unique_slots: _ColumnName

    class UserAttributeAlias(metaclass=TableMeta):
        id: _ColumnName
        user_attribute_id: _ColumnName
        list_id: _ColumnName
        alias: _ColumnName

    class UserAttributeCollectionNode(metaclass=TableMeta):
        id: _ColumnName
        root_id: _ColumnName
        user_attribute_id: _ColumnName
        value: _ColumnName
        sort_value: _ColumnName
        _aliases: _ColumnName

    class UserAttributeCollectionNodeAlias(metaclass=TableMeta):
        id: _ColumnName
        user_attribute_collection_node_id: _ColumnName
        alias: _ColumnName


    # --- Task ---

    class Task(metaclass=TableMeta):
        id: _ColumnName
        list_id: _ColumnName
        name: _ColumnName

    class TaskAlias(metaclass=TableMeta):
        id: _ColumnName
        task_id: _ColumnName
        list_id: _ColumnName
        alias: _ColumnName

    class StaticAttributeTaskValue(metaclass=TableMeta):
        task_id: _ColumnName
        static_attribute_id: _ColumnName
        value: _ColumnName

    class TaskAttributeTaskValue(metaclass=TableMeta):
        task_id: _ColumnName
        task_attribute_id: _ColumnName
        value: _ColumnName

    class UserAttributeTaskValue(metaclass=TableMeta):
        task_id: _ColumnName
        user_id: _ColumnName
        user_attribute_id: _ColumnName
        value: _ColumnName
