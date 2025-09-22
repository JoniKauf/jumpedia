from database import typed
from structures.attribute import AttributeTables
from structures.attribute import BaseAttribute


class StaticAttribute(BaseAttribute):
    tables = AttributeTables(
        typed.StaticAttribute,
        typed.StaticAttributeAlias
    )

    kind: int