from database.static import BaseRow, Cell, CellAlias, cell_body
from structures.attributes.slot_type import SlotTypeT

class Community(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()

    @Cell
    def default_selected_list_id(self_or_cls) -> int: cell_body()




class Server(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def community_id(self_or_cls) -> int: cell_body()



# --- Per Community ---

class List(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def community_id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()


class JumpediaUser(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()

    @Cell
    def power(self_or_cls) -> int: cell_body()


class CommunityUser(BaseRow):
    @Cell
    def community_id(self_or_cls) -> int: cell_body()

    @Cell
    def user_id(self_or_cls) -> int: cell_body()

    @Cell
    def power(self_or_cls) -> int: cell_body()

    @Cell
    def selected_list_id(self_or_cls) -> int: cell_body()



# --- Generic Attribute ---

class GenericAttribute(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()

    @Cell
    def slot_type(self_or_cls) -> int: cell_body()

    @Cell
    def position(self_or_cls) -> int: cell_body()

    @Cell
    def min_slots(self_or_cls) -> int: cell_body()

    @Cell
    def max_slots(self_or_cls) -> int: cell_body()

    @Cell
    def uniqueness(self_or_cls) -> int: cell_body()


class GenericAttributeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()


class GenericAttributeCollectionNode(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def parent_id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()

    @Cell
    def sort_value(self_or_cls) -> int: cell_body()


class GenericAttributeCollectionNode_ExtraAliases[T: SlotTypeT](GenericAttributeCollectionNode):
    @Cell
    def aliases(self_or_cls) -> list[T]: cell_body()


class GenericAttributeCollectionNodeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_collection_node_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> bytes: cell_body()


# --- Static Attribute ---

class StaticAttribute(GenericAttribute):
    pass


class StaticAttributeAlias(GenericAttributeAlias):
    pass



# --- Task Attribute ---

class TaskAttribute(GenericAttribute):
    pass


class TaskAttributeAlias(GenericAttributeAlias):
    pass


class TaskAttributeCollectionNode(GenericAttributeCollectionNode):
    pass

    
class TaskAttributeCollectionNode_ExtraAliases[T: SlotTypeT](GenericAttributeCollectionNode_ExtraAliases[T]):
    pass

class TaskAttributeCollectionNodeAlias(GenericAttributeCollectionNodeAlias):
    pass


# --- User Attribute ---

class UserAttribute(GenericAttribute):
    pass


class UserAttributeAlias(GenericAttributeAlias):
    pass


class UserAttributeCollectionNode(GenericAttributeCollectionNode):
    pass


class UserAttributeCollectionNode_ExtraAliases[T: SlotTypeT](GenericAttributeCollectionNode_ExtraAliases[T]):
    pass


class UserAttributeCollectionNodeAlias(GenericAttributeCollectionNodeAlias):
    pass


# --- Task ---

class Task(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()


class TaskAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()



class GenericAttributeTaskValue(BaseRow):
    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()


class StaticAttributeTaskValue(GenericAttributeTaskValue):
    pass

class TaskAttributeTaskValue(GenericAttributeTaskValue):
    pass

class UserAttributeTaskValue(GenericAttributeTaskValue):
    @Cell
    def user_id(self_or_cls) -> int: cell_body()
