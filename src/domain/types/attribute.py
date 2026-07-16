import decimal
import typing as t

from domain.enums.attribute import AttributeType
from domain.types.common import ID

AttributeID = t.NewType("AttributeID", ID)
AttributeAliasID = t.NewType("AttributeAliasID", ID)

type SlotTypeT = bool | int | decimal.Decimal | str

type TaskAttributeTypeT = t.Literal[AttributeType.TASK]
type UserAttributeTypeT = t.Literal[AttributeType.USER]

type AnyAttributeTypeT = TaskAttributeTypeT | UserAttributeTypeT