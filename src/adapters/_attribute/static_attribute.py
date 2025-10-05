from ...structures.attribute import StaticAttribute
from . import BaseAttributeAdapter


class StaticAttributeAdapter(BaseAttributeAdapter[StaticAttribute]):
    @property
    def kind(self) -> int:
        return self._attribute.kind
