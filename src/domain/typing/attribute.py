import decimal
import typing as t

from domain.enums.attribute import AttributeKind, AttributeType
from domain.typing.common import ID

AttributeID = t.NewType("AttributeID", ID)
AttributeAliasID = t.NewType("AttributeAliasID", ID)

type SlotTypeT = bool | int | decimal.Decimal | str

type TaskAttributeTypeT = t.Literal[AttributeType.TASK]
type UserAttributeTypeT = t.Literal[AttributeType.USER]

type AnyAttributeTypeT = TaskAttributeTypeT | UserAttributeTypeT

type NoneKindedAttributeT = t.Literal[AttributeKind.NONE]
type TaskKindedAttributeT = t.Literal[
    AttributeKind.ID, AttributeKind.NAME, AttributeKind.ALIAS, AttributeKind.CREATED_AT
]
type UserKindedAttributeT = t.Literal[AttributeKind.GIVEN_AT, AttributeKind.GIVEN_BY]
