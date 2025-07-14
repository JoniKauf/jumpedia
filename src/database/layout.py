from database.static import BaseRow, Cell, FakeCell, cell_body

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

class StaticAttribute(BaseRow):
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


class StaticAttributeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def static_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.static_attribute_id


# --- Task Attribute ---

class TaskAttribute(BaseRow):
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


class TaskAttributeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def task_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.task_attribute_id

class TaskAttributeCollectionNode(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def parent_id(self_or_cls) -> int: cell_body()

    @Cell
    def task_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()

    @Cell
    def sort_value(self_or_cls) -> int: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.task_attribute_id

class TaskAttributeCollectionNodeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def task_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def task_attribute_collection_node_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> bytes: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.task_attribute_id
    
    @FakeCell
    def _attribute_collection_node_id(self_or_cls) -> int:
        return self_or_cls.task_attribute_collection_node_id


# --- User Attribute ---

class UserAttribute(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def name(self_or_cls) -> str: cell_body()

    @Cell
    def position(self_or_cls) -> int: cell_body()

    @Cell
    def slot_type(self_or_cls) -> int: cell_body()

    @Cell
    def min_slots(self_or_cls) -> int: cell_body()

    @Cell
    def max_slots(self_or_cls) -> int: cell_body()

    @Cell
    def uniqueness(self_or_cls) -> int: cell_body()


class UserAttributeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def user_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def list_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> str: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.user_attribute_id
    

class UserAttributeCollectionNode(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def parent_id(self_or_cls) -> int: cell_body()

    @Cell
    def user_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()

    @Cell
    def sort_value(self_or_cls) -> int: cell_body()

    @Cell
    def aliases(self_or_cls) -> frozenset:
        

    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.user_attribute_id


class UserAttributeCollectionNodeAlias(BaseRow):
    @Cell
    def id(self_or_cls) -> int: cell_body()

    @Cell
    def user_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def user_attribute_collection_node_id(self_or_cls) -> int: cell_body()

    @Cell
    def alias(self_or_cls) -> bytes: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.user_attribute_id
    
    @FakeCell
    def _attribute_collection_node_id(self_or_cls) -> int:
        return self_or_cls.user_attribute_collection_node_id


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


class StaticAttributeTaskValue(BaseRow):
    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def static_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.static_attribute_id


class TaskAttributeTaskValue(BaseRow):
    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def task_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.task_attribute_id

class UserAttributeTaskValue(BaseRow):
    @Cell
    def task_id(self_or_cls) -> int: cell_body()

    @Cell
    def user_id(self_or_cls) -> int: cell_body()

    @Cell
    def user_attribute_id(self_or_cls) -> int: cell_body()

    @Cell
    def value(self_or_cls) -> bytes: cell_body()


    @FakeCell
    def _attribute_id(self_or_cls) -> int:
        return self_or_cls.user_attribute_id