

from dataclasses import dataclass
from adapters.base_adapter import BaseAdapter
from adapters.list_adapter import _ListAdapter
from structures.community import Community
from structures import list as list_
from structures.list import List
from utils import required, text

@dataclass(frozen=True)
class _CommunityAdapter(BaseAdapter[Community]):
    def get_lists(self) -> list[_ListAdapter]:
        return [
            _ListAdapter(self._interaction, list)
            for list in
            self._structure.get_lists()
        ]
    
    def get_list_by_name(self, name: str) -> _ListAdapter:
        name = text.sanitize(name)

        return _ListAdapter(self._interaction, required.structure_not_none(
            self._structure.get_list_by_name(name),
            List,
            name
        ))

    def create_list(self, name: str) -> _ListAdapter:
        name = text.validate_and_sanitize_name(
            name,
            list_.MAX_NAME_LENGTH
        )

        return _ListAdapter(self._interaction, self._structure.create_list(name))
    
    def delete_list(self, name: str) -> None:
        name = text.sanitize(name)

        return self._structure.delete_list_by_name(name)
    
    