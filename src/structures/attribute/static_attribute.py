from database import typed
from structures.attribute import AttributeTables
from structures.attribute import BaseAttribute

class StaticAttribute(BaseAttribute):
    tables = AttributeTables(typed.StaticAttribute, typed.StaticAttributeAlias)

    def __post_init__(self) -> None:
        from structures.list import KINDS

        if self.kind not in KINDS:
            raise TypeError(f'kind {self.kind} not in {KINDS}')
        
        return super().__post_init__()
