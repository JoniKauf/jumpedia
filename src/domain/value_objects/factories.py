from domain import errors
from domain.entities.base import BaseEntity
from domain.value_objects.string import Str


def make_length_limited_str_store_type(
    name: str, limit: int, entity_type: type[BaseEntity]
) -> type[Str]:
    class ConstrainedStrStore(Str):
        def _validation(self) -> None:
            if len(self) < limit:
                raise errors.NameTooLong(self, limit, entity_type)

    ConstrainedStrStore.__name__ = name
    ConstrainedStrStore.__qualname__ = (
        name
        if "." not in name
        else name.rpartition(".")[0] + "." + name
    )

    return ConstrainedStrStore
