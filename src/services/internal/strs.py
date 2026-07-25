import typing as t
from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.enums.concept import Concept
from domain.errors.business import NotUniqueSynsAcrossNamesAndAliases, SynsNotUnique
from domain.value_objects.string import Str


@dataclass(frozen=True, slots=True, eq=False)
class StrsService:
    def validate_unique_syns(self, iterable: t.Iterable[Str], concept: Concept) -> None:
        seen: set[Str] = set()

        for elem in iterable:
            if elem in seen:
                raise SynsNotUnique(concept, elem)

            seen.add(elem)

    def validate_unique_names_and_aliases(
        self, iterable: t.Iterable[tuple[Str, t.Iterable[Str]]], concept: Concept
    ) -> None:
        syn_to_name_and_alias: dict[Str, tuple[Str, Str | None]] = {}

        for name, aliases in iterable:
            syn_is_name: bool = True

            for syn in (name, *aliases):
                seen = syn_to_name_and_alias.get(syn)

                if seen is not None:
                    seen_name, seen_alias = seen

                    raise NotUniqueSynsAcrossNamesAndAliases(
                        concept,
                        seen_name,
                        name,
                        seen_alias,
                        None if syn_is_name else syn,
                    )

                syn_to_name_and_alias[syn] = (name, None if syn_is_name else syn)

                syn_is_name = False
