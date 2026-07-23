
from dataclasses import dataclass
import typing as t

from domain.entities.base import BaseEntity
from domain.errors.business import SynsNotUnique
from domain.value_objects.string import Str

@dataclass(frozen=True, slots=True, eq=False)
class StrsService:
    def validate_unique_aliases(self, iterable: t.Iterable[Str], type: type[BaseEntity]) -> None:
        seen: set[Str] = set()

        for elem in iterable:
            if elem in seen:
                raise SynsNotUnique(type, elem)

            seen.add(elem)