from adapters._attribute import BaseAttributeAdapter
from structures.attribute.static_attribute import StaticAttribute

class StaticAttributeAdapter(BaseAttributeAdapter[StaticAttribute]):    
    @property
    def kind(self) -> int:
        return self._attribute.kind