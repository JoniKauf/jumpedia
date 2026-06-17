import itertools
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.enums.attribute import AttributeSlotType
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore

if t.TYPE_CHECKING:

    class AttributeCollectionEntrySyn(StrStore):
        pass

else:
    AttributeCollectionEntrySyn = factories.make_constrained_str_store_type(
        "CollectionEntrySyn", CommunityLimits.ATTRIBUTE_TASK_VALUE_SLOT_LENGTH_MAX, AttributeEntity
    )