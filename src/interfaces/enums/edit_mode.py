import enum

from domain.enums.edit_mode import AliasEditMode, CollectionEditMode, FieldMappingEditMode

AliasEditModeInterfaceEnum = enum.Enum(
    "AliasEditModeInterfaceEnum",
    [
        ("Replace Current", AliasEditMode.REPLACE),
        ("Combine With Current Aliases - Override On Collision", AliasEditMode.COMBINE_OVERRIDE_ON_COLLISION),
        ("Combine With Current Aliases - Error On Collision", AliasEditMode.COMBINE_ERROR_ON_COLLISION),
    ],
)

CollectionEditModeInterfaceEnum = enum.Enum(
    "CollectionEditModeInterfaceEnum",
    [
        ("Replace Current", CollectionEditMode.REPLACE),
        ("Combine With Current Aliases - Error On Any Value Or Alias Collision", CollectionEditMode.COMBINE_ERROR_ON_ANY_SYN_COLLISION),
    ],
)

FieldMappingEditModeInterfaceEnum = enum.Enum(
    "FieldMappingEditModeInterfaceEnum",
    [
        ("Replace Current", FieldMappingEditMode.REPLACE),
        ("Combine With Current Field Mapping - Override Slots On Attribute Collision", FieldMappingEditMode.COMBINE_OVERRIDE_ON_COLLISION),
        ("Combine With Current Field Mapping - Error On Attribute Collision", FieldMappingEditMode.COMBINE_ERROR_ON_COLLISION)
    ]
)