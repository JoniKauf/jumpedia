import enum

from domain.enums.operation import Operation

OperationEnum = enum.Enum(
    "OperationEnum", [("Combine", Operation.COMBINE), ("Replace", Operation.REPLACE)]
)
