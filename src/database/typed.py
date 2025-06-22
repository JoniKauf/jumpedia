from typing import Any as _Any

class ColumnName(str):
    # When used in f-strings, so mostly queries
    def __str__(self) -> str:
        return f"`{super().__str__()}`"

class TableMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], dct: dict[str, _Any]):
        ANNOTATIONS = '__annotations__'

        annotations: dict[str, _Any] = dct.get(ANNOTATIONS, {})
        
        for k, typ in annotations.items():
            if typ is not ColumnName:
                raise RuntimeError(f"Not good type in strong module for class '{name}', attribute '{k}'")
            
            if k not in dct:
                dct[k] = ColumnName(k.lstrip("_"))

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
        id: ColumnName
        name: ColumnName
        default_selected_list_id: ColumnName


    class Server(metaclass=TableMeta):
        id: ColumnName
        community_id: ColumnName


    # --- Per Community ---

    class List(metaclass=TableMeta):
        id: ColumnName
        community_id: ColumnName
        name: ColumnName

    class MetaUser(metaclass=TableMeta):
        id: ColumnName
        name: ColumnName
        meta_power: ColumnName

    class CommunityUser(metaclass=TableMeta):
        community_id: ColumnName
        user_id: ColumnName
        power: ColumnName
        selected_list_id: ColumnName


    # --- Static Attribute ---

    class StaticAttribute(metaclass=TableMeta):
        id: ColumnName
        list_id: ColumnName
        name: ColumnName
        value_type: ColumnName
        index: ColumnName
        min_slots: ColumnName
        max_slots: ColumnName
        uniqueness: ColumnName

    class StaticAttributeAlias(metaclass=TableMeta):
        id: ColumnName
        static_attribute_id: ColumnName
        list_id: ColumnName
        alias: ColumnName

        _attribute_id: ColumnName = ColumnName('static_attribute_id')


    # --- Task Attribute ---

    class TaskAttribute(metaclass=TableMeta):
        id: ColumnName
        list_id: ColumnName
        name: ColumnName
        value_type: ColumnName
        index: ColumnName
        min_slots: ColumnName
        max_slots: ColumnName
        uniqueness: ColumnName

    class TaskAttributeAlias(metaclass=TableMeta):
        id: ColumnName
        task_attribute_id: ColumnName
        list_id: ColumnName
        alias: ColumnName

        _attribute_id: ColumnName = ColumnName('task_attribute_id')

    class TaskAttributeCollectionNode(metaclass=TableMeta):
        id: ColumnName
        root_id: ColumnName
        task_attribute_id: ColumnName
        value: ColumnName
        sort_value: ColumnName

        _aliases: ColumnName
        _attribute_id: ColumnName = ColumnName('task_attribute_id')

    class TaskAttributeCollectionNodeAlias(metaclass=TableMeta):
        id: ColumnName
        task_attribute_collection_node_id: ColumnName
        alias: ColumnName

        _attribute_collection_node_id: ColumnName = ColumnName('task_attribute_collection_node_id')


    # --- User Attribute ---

    class UserAttribute(metaclass=TableMeta):
        id: ColumnName
        list_id: ColumnName
        name: ColumnName
        index: ColumnName
        value_type: ColumnName
        min_slots: ColumnName
        max_slots: ColumnName
        uniqueness: ColumnName

    class UserAttributeAlias(metaclass=TableMeta):
        id: ColumnName
        user_attribute_id: ColumnName
        list_id: ColumnName
        alias: ColumnName

        _attribute_id: ColumnName = ColumnName('user_attribute_id')

    class UserAttributeCollectionNode(metaclass=TableMeta):
        id: ColumnName
        root_id: ColumnName
        user_attribute_id: ColumnName
        value: ColumnName
        sort_value: ColumnName

        _aliases: ColumnName
        _attribute_id: ColumnName = ColumnName('user_attribute_id')

    class UserAttributeCollectionNodeAlias(metaclass=TableMeta):
        id: ColumnName
        user_attribute_collection_node_id: ColumnName
        alias: ColumnName

        _attribute_collection_node_id: ColumnName = ColumnName('user_attribute_collection_node_id')


    # --- Task ---

    class Task(metaclass=TableMeta):
        id: ColumnName
        list_id: ColumnName
        name: ColumnName

    class TaskAlias(metaclass=TableMeta):
        id: ColumnName
        task_id: ColumnName
        list_id: ColumnName
        alias: ColumnName

    class StaticAttributeTaskValue(metaclass=TableMeta):
        task_id: ColumnName
        static_attribute_id: ColumnName
        value: ColumnName

        _attribute_id: ColumnName = ColumnName('static_attribute_id')

    class TaskAttributeTaskValue(metaclass=TableMeta):
        task_id: ColumnName
        task_attribute_id: ColumnName
        value: ColumnName

        _attribute_id: ColumnName = ColumnName('task_attribute_id')

    class UserAttributeTaskValue(metaclass=TableMeta):
        task_id: ColumnName
        user_id: ColumnName
        user_attribute_id: ColumnName
        value: ColumnName

        _attribute_id: ColumnName = ColumnName('user_attribute_id')