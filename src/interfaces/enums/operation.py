import enum

from domain.enums.operation import Operation

OperationInterfaceEnum = enum.Enum(
    "OperationEnum",
    [
        ("Replace Existing Entirely", Operation.REPLACE),
        ("Combine And Override On Collision", Operation.COMBINE_OVERRIDE_ON_COLLISION),
        ("Combine And Error On Collision", Operation.COMBINE_ERROR_ON_COLLISION),
    ],
)
