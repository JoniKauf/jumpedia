


from dataclasses import dataclass
import itertools

from domain.enums.edit_mode import AliasEditMode, CollectionEditMode, FieldMappingEditMode
from domain.types.collection_entry import CollectionT
from domain.types.field_mapping import IDFieldMappingT
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.string import Str
import typing as t

@dataclass(frozen=True, slots=True, eq=False)
class EditModeService:
    def handle_alias_edit[T: Str](self, edit_mode: AliasEditMode, current: tuple[T, ...], new: tuple[T, ...]) -> tuple[T, ...]:
        if edit_mode is AliasEditMode.REPLACE:
            return new
            
        intersection = set(current).intersection(new)
        
        if not intersection:
            return (*current, *new)

        del intersection

        if edit_mode is AliasEditMode.COMBINE_ERROR_ON_COLLISION:
            raise ValueError("Error collision")

        t.assert_type(edit_mode, t.Literal[AliasEditMode.COMBINE_OVERRIDE_ON_COLLISION])

        return tuple(self._unique_and_preserve_order_and_preserve_first_seen_idx((current, new)))

    def handle_collection_edit(self, edit_mode: CollectionEditMode, current: CollectionT, new: CollectionT) -> CollectionT:
        if edit_mode is CollectionEditMode.REPLACE:
            return new

        t.assert_type(edit_mode, t.Literal[CollectionEditMode.COMBINE_ERROR_ON_ANY_SYN_COLLISION])

        FieldSlotStr.raise_if_not_unique(syn for coll in (current, new) for entry in coll for syn in (entry[0], *entry[1]))

        return (*current, *new)

    def handle_field_mapping_edit(self, edit_mode: FieldMappingEditMode, current: IDFieldMappingT, new: IDFieldMappingT) -> IDFieldMappingT:
        if edit_mode is FieldMappingEditMode.REPLACE:
            return new

        current = {k: v for k, v in current.items() if v}
        new = {k: v for k, v in current.items() if v}

        if current.keys().isdisjoint(new.keys()):
            return current | new

        if edit_mode is FieldMappingEditMode.COMBINE_ERROR_ON_COLLISION:
            raise ValueError("Intersecting")

        t.assert_type(edit_mode, t.Literal[FieldMappingEditMode.COMBINE_OVERRIDE_ON_COLLISION])

        return current | new

    def _unique_and_preserve_order_and_preserve_first_seen_idx[T: Str](self, iterables: t.Iterable[t.Iterable[T]]) -> t.Iterable[T]:
        # Combine while preserving order and original placement on collision and placing new ones right
        alias_to_first_seen_idx: dict[T, int] = {}
        i = 0

        for alias in itertools.chain.from_iterable(iterables):
            try:
                # We always need to pop existing keys because setting dict[key] = value won't replace
                # the key with the new object if the key is already in the dict
                first_seen_idx = alias_to_first_seen_idx.pop(alias)
            except KeyError:
                first_seen_idx = i
                i += 1
            
            alias_to_first_seen_idx[alias] = first_seen_idx
            
        return (alias for alias, _ in sorted(alias_to_first_seen_idx.items(), key=lambda item: item[1]))