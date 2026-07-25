import enum
import typing as t

from domain.enums.attribute import AttributeType

AttributeTypeInterfaceEnum = enum.Enum(
    "AttributeTypeInterfaceEnum",
    [("Task", AttributeType.TASK.value), ("User", AttributeType.USER.value)],
)
