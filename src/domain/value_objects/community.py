from typing_extensions import Self

from domain import errors
from domain.entities.community import CommunityEntity
from domain.value_objects import factories
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
import typing as t


CommunityName = factories.make_constrained_str_store_type("CommunityName", Limits.COMMUNITY_NAME_LENGTH_MAX, CommunityEntity)
