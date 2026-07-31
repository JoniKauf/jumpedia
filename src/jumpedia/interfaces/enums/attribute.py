import enum
import typing as t

from jumpedia.domain.enums.attribute import AttributeType

AttributeTypeInterfaceEnum = enum.Enum(
    "AttributeTypeInterfaceEnum",
    [("Task", AttributeType.TASK.value), ("User", AttributeType.USER.value)],
)
