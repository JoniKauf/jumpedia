

from domain import errors
from domain.entities.list import ListEntity
from domain.value_objects import factories
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


ListName = factories.make_constrained_str_store_type("ListName", Limits.LIST_NAME_LENGTH_MAX, ListEntity)