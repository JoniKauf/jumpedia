import typing as t

from domain.types.id import ID

AttributeID = t.NewType("AttributeID", ID)
AttributeAliasID = t.NewType("AttributeAliasID", ID)