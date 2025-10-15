from ...database import typed
from . import BaseNonStaticAttribute, BaseNonStaticAttributeTables


class UserAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        typed.UserAttribute,
        typed.UserAttributeAlias,
        typed.UserAttributeCollectionSlot,
        typed.UserAttributeCollectionSlotAlias,
        typed.UserAttributeTaskValue,
    )
    type_id = 2