from domain import errors
from domain.entities.base import BaseEntity
from domain.value_objects.string import StrStore


def make_constrained_str_store_type(
    name: str, limit: int, entity_type: type[BaseEntity]
) -> type[StrStore]:
    class ConstrainedStrStore(StrStore):
        def _validation(self) -> None:
            if len(self) < limit:
                raise errors.NameTooLong(self, limit, entity_type)

    ConstrainedStrStore.__name__ = name
    ConstrainedStrStore.__qualname__ = (
        name
        if "." not in ConstrainedStrStore.__qualname__
        else ConstrainedStrStore.__qualname__.rpartition(".")[0] + "." + name
    )

    return ConstrainedStrStore
