

from dataclasses import dataclass
from adapters.base_adapter import BaseAdapter
from adapters.list_adapter import ListAdapter
from structures.community import Community
from structures import list as list_
from structures.list import List
from utils import required, text

@dataclass(frozen=True)
class CommunityAdapter(BaseAdapter[Community]):
    def get_lists(self) -> list[ListAdapter]:
        return [
            ListAdapter(self.context, list)
            for list in
            self._structure.get_lists()
        ]
    
    def get_list_by_name(self, name: str) -> ListAdapter:
        name = text.sanitize(name)

        return ListAdapter(self.context, required.structure_not_none(
            self._structure.get_list_by_name(name),
            List,
            name
        ))

    def create_list(self, name: str) -> ListAdapter:
        name = text.validate_and_sanitize_name(
            name,
            list_.MAX_NAME_LENGTH
        )

        return ListAdapter(self.context, self._structure.create_list(name))
    
    def delete_list(self, name: str) -> None:
        name = text.sanitize(name)

        return self._structure.delete_list_by_name(name)