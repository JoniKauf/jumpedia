import enum

from domain.enums.operation import Operation

OperationInterfaceEnum = enum.Enum(
    "OperationEnum", [("Combine", Operation.COMBINE), ("Replace", Operation.REPLACE)]
)
