import typing as t
from dataclasses import field

from ...database import typed
from . import AttributeTables, BaseAttribute

if t.TYPE_CHECKING:
    from ..list import KindsT
    

class StaticAttribute(BaseAttribute):
    tables = AttributeTables(typed.StaticAttribute, typed.StaticAttributeAlias)

    kind: KindsT = field(default=None)  # pyright: ignore[reportAssignmentType]

    def __post_init__(self) -> None:
        from structures.list import KINDS

        if self.kind not in KINDS:
            raise TypeError(f"kind {self.kind} not in {KINDS}")

        return super().__post_init__()
