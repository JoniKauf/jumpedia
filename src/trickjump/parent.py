from dataclasses import dataclass, field
from typing import Hashable, Protocol, Self, overload

@dataclass(frozen=True)
class Lookupable():
    id: int
    name: str


@dataclass(frozen=True)
class Parent[T: Lookupable]():
    children: set[T] = field(init=False, default_factory=set)
    lookup_id: dict[int, T] = field(init=False, default_factory=dict)
    lookup_name: dict[str, T] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.reload_children_data()

    def _load_children(self):
        """(Re)Load all children with data from the database.

        Override this method!
        """
        raise NotImplementedError()
    
    def _generate_lookups(self):
        self.lookup_id.clear()
        self.lookup_name.clear()

        for child in self.children:
            self.lookup_id[child.id] = child
            self.lookup_name[child.name] = child

    def reload_children_data(self):
        """This method is automatically called once on object creation."""
        self._load_children()
        self._generate_lookups()

    def lookup_child_by_name(self, name: str) -> T:
        try:
            return self.lookup_name[name]
        except KeyError:
            raise LookupError(name)
        
    def lookup_child_by_id(self, id: int) -> T:
        try:
            return self.lookup_id[id]
        except KeyError:
            raise LookupError(id)


        

        
