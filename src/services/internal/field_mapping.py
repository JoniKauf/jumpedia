import decimal
import functools
import types as ts
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.edit_mode import FieldMappingEditMode
from domain.types.attribute import AttributeID
from domain.types.collection_entry import CollectionT
from domain.types.field_mapping import (
    FieldMappingEntityFrozenT,
    FieldMappingEntityT,
    FieldMappingIDMutT,
    FieldMappingIDT,
    FieldMappingRawT,
)
from domain.types.task import TaskID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.string import NormStr, RealStr
from services.internal.edit_mode import EditModeService
from services.internal.slot_type import SlotTypeService


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingService:
    _slot_type_service: SlotTypeService
    _edit_mode_service: EditModeService

    def build_raw[T: AttributeType](
        self,
        field_mapping: FieldMappingRawT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FieldMappingEntityFrozenT[T]:
        unchecked_field_mapping = self._try_convert_syns_to_attr_ids(
            field_mapping, syn_to_attribute
        )

        return self.build(
            unchecked_field_mapping,
            frozenset(syn_to_attribute.values()),
            attr_id_to_collection,
        )

    def _try_convert_syns_to_attr_ids(
        self,
        field_mapping: FieldMappingRawT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity],
    ) -> FieldMappingIDT:
        unchecked_field_mapping: FieldMappingIDT = {}

        for attr_syn, value in field_mapping:
            attr = syn_to_attribute[attr_syn]

            if attr in unchecked_field_mapping:
                raise ValueError("Attr mentioned more than once")

            unchecked_field_mapping[attr.attribute_id] = tuple(value)

        return unchecked_field_mapping

    def build[T: AttributeType](
        self,
        unchecked_field_mapping: FieldMappingIDT,
        attributes: t.AbstractSet[AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FieldMappingEntityFrozenT[T]:
        res: dict[AttributeEntity[T], tuple[FieldSlotStr, ...]] = {}

        for attr in attributes:
            v = unchecked_field_mapping.get(attr.attribute_id)

            if v is None:
                if attr.field_config.min_slot_count > 0:
                    raise ValueError("Required attr missing")

                v = ()

            if len(v) < attr.field_config.min_slot_count:
                raise ValueError("attr min count underflow")

            if len(v) > attr.field_config.max_slot_count:
                raise ValueError("attr max count overflow")

            v = tuple(
                self._slot_type_service.convert_to_slot_typed(
                    slot, attr.field_config.slot_type
                )
                for slot in v
            )

            collection = attr_id_to_collection.get(attr.attribute_id)

            # Not None or empty
            if collection:
                syn_to_value: dict[FieldSlotStr, FieldSlotStr] = {
                    syn: entry_with_aliases[0]
                    for entry_with_aliases in collection
                    for syn in (
                        entry_with_aliases[0],
                        *entry_with_aliases[1],
                    )
                }

                collectionified_v: list[FieldSlotStr] = []

                for slot in v:
                    slot = syn_to_value.get(slot)

                    if slot is None:
                        raise ValueError("Unknown slot")

                    collectionified_v.append(slot)

                v = tuple(collectionified_v)

            if attr.field_config.unique_slots and len(v) > 1 and len(set(v)) != len(v):
                raise ValueError("Not unique slots when attribute requires it")

            res[attr] = v

        return frozendict(res)

    def build_edit[T: AttributeType](
        self,
        edit_mode: FieldMappingEditMode,
        current_field_mapping: FieldMappingIDT,
        new_field_mapping: FieldMappingRawT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FieldMappingEntityFrozenT[T]:
        # Build the new mapping to see if even valid on its own
        new_fm = {
            attr.attribute_id: v
            for attr, v in self.build_raw(
                new_field_mapping, syn_to_attribute, attribute_id_to_collection
            ).items()
        }

        del new_field_mapping

        # Edit the new mapping with the current
        new_fm = self._edit_mode_service.handle_field_mapping_edit(
            edit_mode, current_field_mapping, new_fm
        )

        del current_field_mapping

        # Rebuild combined mapping to see if end result is valid
        return self.build(
            new_fm, frozenset(syn_to_attribute.values()), attribute_id_to_collection
        )

    def get_static_field_mapping_single(
        self,
        task: TaskEntity,
        task_aliases: tuple[FieldSlotStr, ...],
        attributes: t.Iterable[AttributeEntity.OfAnyTypeT],
    ) -> FieldMappingIDMutT:
        static_field_mapping: FieldMappingIDMutT = {}

        for attr in attributes:
            if attr.type is not AttributeType.STATIC:
                continue

            match attr.kind:
                case AttributeKind.ID:
                    static_field_mapping[attr.attribute_id] = (
                        FieldSlotStr._create_from_real_and_norm(
                            RealStr._create(str(task.task_id)),
                            NormStr._create(str(task.task_id)),
                        ),
                    )

                case AttributeKind.NAME:
                    static_field_mapping[attr.attribute_id] = (task.name,)

                case AttributeKind.ALIAS:
                    static_field_mapping[attr.attribute_id] = task_aliases

                case _:
                    assert attr.kind is not AttributeKind.NONE
                    t.assert_never(attr.kind)

        return static_field_mapping

    def get_static_field_mapping_many(
        self,
        tasks: t.Sequence[TaskEntity],
        task_id_to_aliases: t.Mapping[TaskID, tuple[FieldSlotStr, ...]],
        attributes: t.Iterable[AttributeEntity],
    ) -> frozendict[TaskID, FieldMappingIDMutT]:
        static_field_mapping: frozendict[TaskID, FieldMappingIDMutT] = frozendict(
            (task.task_id, {}) for task in tasks
        )

        for attr in attributes:
            if attr.type is not AttributeType.STATIC:
                continue

            match attr.kind:
                case AttributeKind.ID:
                    for task in tasks:
                        task_id_str = str(task.task_id)

                        static_field_mapping[task.task_id][attr.attribute_id] = (
                            FieldSlotStr._create_from_real_and_norm(
                                RealStr._create(task_id_str),
                                NormStr._create(task_id_str),
                            ),
                        )

                case AttributeKind.NAME:
                    for task in tasks:
                        static_field_mapping[task.task_id][attr.attribute_id] = (
                            task.name,
                        )

                case AttributeKind.ALIAS:
                    for task in tasks:
                        static_field_mapping[task.task_id][attr.attribute_id] = (
                            task_id_to_aliases.get(task.task_id, ())
                        )

                case _:
                    assert attr.kind is not AttributeKind.NONE
                    t.assert_never(attr.kind)

        return static_field_mapping

    def sort[T: AttributeType](
        self,
        sorts: t.Sequence[tuple[AttributeSynStr, bool]],
        task_id_to_field_mapping: t.Mapping[
            TaskID, frozendict[AttributeID, tuple[FieldSlotStr, ...]]
        ],
        syn_to_attr: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> tuple[frozendict[AttributeID, tuple[FieldSlotStr, ...]], ...]:
        # Warning: Complicated code ahead! But it allows for fast, multi-key, asc/desc sorting

        # --- Normalize Sorts As Much As Possible --- #
        clean_sorts: list[tuple[AttributeEntity[T], bool]] = []
        seen: set[AttributeEntity[T]] = set()

        for sort in sorts:
            syn, asc = sort
            attr = syn_to_attr[syn]

            # Remove duplicate attrs, they don't affect final result
            if attr in seen:
                continue

            seen.add(attr)

            clean_sorts.append((attr, asc))

            # Short circuit when we know last sort results in unique sort values
            if attr.slot_unique_across_list:
                break

        del sorts

        # Sort by name by default
        if not clean_sorts:
            name_attr: AttributeEntity.OfTypeStaticT

            for attr in syn_to_attr.values():
                if attr.kind is AttributeKind.NAME:
                    name_attr = attr  # type: ignore
                    break
            else:
                raise ValueError("Data error, no name attribute found!!!")

            clean_sorts = [(name_attr, True)]  # type: ignore

        # --- Gather Sorting Data --- #
        task_id_to_sort_value: dict[
            TaskID, list[tuple[AttributeSlotType.SlotTypeT, ...]]
        ] = {}

        # TODO: Could be optimized to only fetch collection entry values excluding aliases
        # because all data should be the value, not any aliases of the collection. Aliases
        # are only for lookup.
        attr_id_to_collection_value_to_collection_entry_index: dict[
            AttributeID, dict[FieldSlotStr, int]
        ] = {
            attr: {entry[0]: i for i, entry in enumerate(coll)}
            for attr, coll in attr_id_to_collection.items()
        }

        for task_id, field_mapping in task_id_to_field_mapping.items():
            # Map every attr into the typed field of the task
            task_sort_value: list[tuple[AttributeSlotType.SlotTypeT, ...]] = []

            for attr, _ in clean_sorts:
                value_to_collection_entry_idx = (
                    attr_id_to_collection_value_to_collection_entry_index.get(
                        attr.attribute_id, {}
                    )
                )

                # Collection exists for given attr
                if value_to_collection_entry_idx:
                    # It is possible that a slot does not match any collection value in case that
                    # a user attribute's collection is edited and staff did not yet fix the users'
                    # data.
                    task_sort_value.append(
                        tuple(
                            value_to_collection_entry_idx.get(slot, -1)
                            for slot in field_mapping.get(attr.attribute_id, ())
                        )
                    )
                else:
                    task_sort_value.append(
                        tuple(
                            self._slot_type_service.convert_to_type(
                                slot, attr.field_config.slot_type, _validate=False
                            )
                            for slot in field_mapping.get(attr.attribute_id, ())
                        )
                    )

            task_id_to_sort_value[task_id] = task_sort_value

        # --- Apply Sort --- #
        def compare_task_sort_values(
            a: tuple[TaskID, frozendict[AttributeID, tuple[FieldSlotStr, ...]]],
            b: tuple[TaskID, frozendict[AttributeID, tuple[FieldSlotStr, ...]]],
        ) -> int:
            values_a = task_id_to_sort_value[a[0]]
            values_b = task_id_to_sort_value[b[0]]

            # Compare each value of the specified attribute for the given two tasks until one is greater, otherwise equal
            for va, vb, (_, asc) in zip(values_a, values_b, clean_sorts):
                if va < vb:
                    return -1 if asc else 1

                if va > vb:
                    return 1 if asc else -1

            return 0

        return tuple(
            field_mapping
            for _, field_mapping in sorted(
                task_id_to_field_mapping.items(),
                key=functools.cmp_to_key(compare_task_sort_values),
            )
        )
