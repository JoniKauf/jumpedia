

from typing_extensions import Self

from domain import errors
from domain.entities.community import CommunityEntity
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
import typing as t

class CommunityName(StrStore):
    def _validation(self) -> None:
        if len(self) < Limits.COMMUNITY_NAME_LENGTH_MAX:
            raise errors.NameTooLong(self, Limits.COMMUNITY_NAME_LENGTH_MAX, CommunityEntity)
        