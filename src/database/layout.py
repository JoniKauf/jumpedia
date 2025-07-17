from database.static import BaseRow, Cell, cell_body
from structures.attributes.slot_type import SlotTypeT


# --- Bases ---

class Snippets:
    """Whole tables split up into tables so they can be reused for specific queries.
    
    For example, if one would fetch all rows from a table with just the
    `id` row, then here would be a class with just the `id` cell that would
    later be combined into the class that includes all columns of the table.
    """
    class SnippetBaseAttributeCollectionNode(BaseRow):
        @Cell
        def attribute_collection_node_id(self_or_cls) -> int: cell_body()

        @Cell
        def alias(self_or_cls) -> bytes: cell_body()
    

class BaseAttribute(BaseRow):
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


class BaseAttributeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()


class BaseAttributeCollectionNode(BaseRow):
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






class BaseAttributeCollectionNodeAlias(Snippets.SnippetBaseAttributeCollectionNode):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    


class BaseAttributeTaskValue(BaseRow):
    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()



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



# --- Static Attribute ---

class StaticAttribute(BaseAttribute):
    pass


class StaticAttributeAlias(BaseAttributeAlias):
    pass



# --- Task Attribute ---

class TaskAttribute(BaseAttribute):
    pass


class TaskAttributeAlias(BaseAttributeAlias):
    pass


class TaskAttributeCollectionNode(BaseAttributeCollectionNode):
    pass

class TaskAttributeCollectionNodeAlias(BaseAttributeCollectionNodeAlias):
    pass


# --- User Attribute ---

class UserAttribute(BaseAttribute):
    pass


class UserAttributeAlias(BaseAttributeAlias):
    pass


class UserAttributeCollectionNode(BaseAttributeCollectionNode):
    pass

class UserAttributeCollectionNodeAlias(BaseAttributeCollectionNodeAlias):
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



class StaticAttributeTaskValue(BaseAttributeTaskValue):
    pass

class TaskAttributeTaskValue(BaseAttributeTaskValue):
    pass

class UserAttributeTaskValue(BaseAttributeTaskValue):
    @Cell
    def user_id(self_or_cls) -> int: cell_body()
