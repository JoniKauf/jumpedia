import enum

from domain.enums.edit_mode import AliasEditMode

AliasEditModeInterfaceEnum = enum.Enum(
    "AliasEditModeInterfaceEnum",
    [
        ("Override Exsting Aliases Entirely", AliasEditMode.REPLACE),
        ("Combine With Existing Aliases - Override On Collision", AliasEditMode.COMBINE_OVERRIDE_ON_COLLISION),
        ("Combine With Existing Aliases - Error On Collision", AliasEditMode.COMBINE_ERROR_ON_COLLISION),
    ],
)
