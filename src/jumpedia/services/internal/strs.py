import typing as t
from dataclasses import dataclass

from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.errors.business import (
    AliasesNotUnique,
    NotUniqueValuesAndAliasesAcrossCollection,
    SynsNotUnique,
)
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.string import Str


@dataclass(frozen=True, slots=True, eq=False)
class StrsService:
    def validate_unique_aliases(
        self, iterable: t.Iterable[Str], concept: Concept
    ) -> None:
        try:
            self.validate_unique_syns(iterable, concept)
        except SynsNotUnique as e:
            raise AliasesNotUnique(e.concept, e.collision)

    def validate_unique_syns(self, iterable: t.Iterable[Str], concept: Concept) -> None:
        seen: set[Str] = set()

        for elem in iterable:
            if elem in seen:
                raise SynsNotUnique(concept, elem)

            seen.add(elem)

    def validate_unique_collection_syns(
        self, iterable: t.Iterable[tuple[FieldSlotStr, t.Iterable[FieldSlotStr]]]
    ) -> None:
        syn_to_name_and_alias: dict[
            FieldSlotStr, tuple[FieldSlotStr, FieldSlotStr | None]
        ] = {}

        for name, aliases in iterable:
            syn_is_name: bool = True

            for syn in (name, *aliases):
                seen = syn_to_name_and_alias.get(syn)

                if seen is not None:
                    seen_name, seen_alias = seen

                    raise NotUniqueValuesAndAliasesAcrossCollection(
                        seen_name,
                        name,
                        seen_alias,
                        None if syn_is_name else syn,
                    )

                syn_to_name_and_alias[syn] = (name, None if syn_is_name else syn)

                syn_is_name = False
