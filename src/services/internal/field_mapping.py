import decimal
import functools
import types as ts
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.edit_mode import FieldMappingEditMode
from domain.errors.business import NotFoundByName
from domain.types.attribute import (
    AnyAttributeTypeT,
    AttributeID,
    SlotTypeT,
    StaticAttributeTypeT,
)
from domain.types.collection_entry import CollectionSlotTypeFrozenT, CollectionT
from domain.types.field_mapping import (
    AbstractFieldMappingIDToSlotTypeT,
    FrozenFieldMappingEntityToStrings,
    AbstractFieldMappingIDToStringsT,
    MutableFieldMappingIDToStringsT,
    RawFieldMappingT,
)
from domain.types.task import TaskID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.filter import (
    AndFilter,
    NonEmptyComparisonFilter,
    FilterT,
    EmptyComparisonFilter,
    OpType,
    OrFilter,
)
from domain.value_objects.string import NormStr, RealStr
from services.internal.edit_mode import EditModeService
from services.internal.slot_type import SlotTypeService

_OP_TO_COMP_ANY_FUNC: t.Final[
    frozendict[OpType, t.Callable[[SlotTypeT, t.Iterable[SlotTypeT]], bool]]
] = frozendict(
    {
        OpType.EQ: lambda v, field: v in field,
        OpType.NEQ: lambda v, field: v not in field,
        OpType.LT: lambda v, field: any(v < slot for slot in field),  # pyright: ignore[reportOperatorIssue]
        OpType.LTE: lambda v, field: any(v <= slot for slot in field),  # pyright: ignore[reportOperatorIssue]
        OpType.GT: lambda v, field: any(v > slot for slot in field),  # pyright: ignore[reportOperatorIssue]
        OpType.GTE: lambda v, field: any(v >= slot for slot in field),  # pyright: ignore[reportOperatorIssue]
    }
)


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingService:
    _slot_type_service: SlotTypeService
    _edit_mode_service: EditModeService

    def build_raw[T: AttributeType](
        self,
        field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FrozenFieldMappingEntityToStrings[T]:
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
        field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity],
    ) -> AbstractFieldMappingIDToStringsT:
        unchecked_field_mapping: AbstractFieldMappingIDToStringsT = {}

        for attr_syn, value in field_mapping:
            attr = syn_to_attribute[attr_syn]

            if attr in unchecked_field_mapping:
                raise ValueError("Attr mentioned more than once")

            unchecked_field_mapping[attr.attribute_id] = tuple(value)

        return unchecked_field_mapping

    def build[T: AttributeType](
        self,
        unchecked_field_mapping: AbstractFieldMappingIDToStringsT,
        attributes: t.AbstractSet[AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FrozenFieldMappingEntityToStrings[T]:
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
                self._slot_type_service.to_slot_typed_str(
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
        current_field_mapping: AbstractFieldMappingIDToStringsT,
        new_field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection: t.Mapping[AttributeID, CollectionT],
    ) -> FrozenFieldMappingEntityToStrings[T]:
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
        attributes: t.Iterable[AttributeEntity[AnyAttributeTypeT]],
    ) -> MutableFieldMappingIDToStringsT:
        static_field_mapping: MutableFieldMappingIDToStringsT = {}

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
    ) -> frozendict[TaskID, MutableFieldMappingIDToStringsT]:
        static_field_mapping: frozendict[TaskID, MutableFieldMappingIDToStringsT] = (
            frozendict((task.task_id, {}) for task in tasks)
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

    def filter_and_sort_and_yield(
        self,
        field_mappings: t.Sequence[AbstractFieldMappingIDToSlotTypeT],
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> t.Sequence[AbstractFieldMappingIDToSlotTypeT]:
        fms = self._filter(
            field_mappings,
            filter,
            syn_to_attribute,
            attribute_id_to_collection_value_to_entry_index,
        )
        fms = self._sort(
            fms,
            sort,
            syn_to_attribute,
            attribute_id_to_collection_value_to_entry_index,
        )
        return fms

    def _filter[T: AttributeType](
        self,
        field_mappings: t.Sequence[AbstractFieldMappingIDToSlotTypeT],
        filter: FilterT | None,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> t.Sequence[AbstractFieldMappingIDToSlotTypeT]:
        if filter is None:
            return field_mappings

        return tuple(
            self._recursively_solve_filter(
                {id(fm): fm for fm in field_mappings},
                filter,
                syn_to_attribute,
                attribute_id_to_collection_value_to_entry_index,
            ).values()
        )

    def _recursively_solve_filter[T: AttributeType](
        self,
        id_to_field_mappings: t.Mapping[int, AbstractFieldMappingIDToSlotTypeT],
        filter: FilterT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> t.Mapping[int, AbstractFieldMappingIDToSlotTypeT]:
        match filter:
            case OrFilter() as or_filter:
                yet_invalid: dict[int, AbstractFieldMappingIDToSlotTypeT] = dict(
                    id_to_field_mappings
                )
                valid: dict[int, AbstractFieldMappingIDToSlotTypeT] = {}

                for operand in or_filter.operands:
                    if not yet_invalid:
                        break

                    new_valid = self._recursively_solve_filter(
                        yet_invalid,
                        operand,
                        syn_to_attribute,
                        attribute_id_to_collection_value_to_entry_index,
                    )

                    for k in new_valid:
                        del yet_invalid[k]

                    valid.update(new_valid)

                return valid

            case AndFilter() as and_filter:
                still_valid: t.Mapping[int, AbstractFieldMappingIDToSlotTypeT] = dict(
                    id_to_field_mappings
                )

                for operand in and_filter.operands:
                    if not still_valid:
                        break

                    still_valid = self._recursively_solve_filter(
                        still_valid,
                        operand,
                        syn_to_attribute,
                        attribute_id_to_collection_value_to_entry_index,
                    )

                return still_valid

            case EmptyComparisonFilter() | NonEmptyComparisonFilter() as comp_filter:
                attr_syn = AttributeSynStr(comp_filter.attribute)

                attr = syn_to_attribute.get(attr_syn)

                if attr is None:
                    raise NotFoundByName(attr_syn, AttributeEntity)

                if isinstance(comp_filter, EmptyComparisonFilter):
                    want_empty = comp_filter.op is OpType.EQ

                    # Return all field mappings where the field for the
                    # specified attribute is empty (or not empty if operator is NEQ)
                    return {
                        id: field_mapping
                        for id, field_mapping in id_to_field_mappings.items()
                        if (not field_mapping.get(attr.attribute_id)) is want_empty
                    }

                elif isinstance(comp_filter, NonEmptyComparisonFilter):
                    comp_any = _OP_TO_COMP_ANY_FUNC[comp_filter.op]
                    value = self._slot_type_service.single_to_slot_type(FieldSlotStr(comp_filter.value), attr.field_config.slot_type)

                    coll_value_to_idx = attribute_id_to_collection_value_to_entry_index.get(attr.attribute_id)

                    # Attribute has collection
                    if coll_value_to_idx:
                        value_idx = coll_value_to_idx[value]

                        return {
                            id: field_mapping
                            for id, field_mapping in id_to_field_mappings.items()
                            if comp_any(value_idx, (coll_value_to_idx[slot] for slot in field_mapping.get(attr.attribute_id, ())))
                        }
                    else:
                        return {
                            id: field_mapping
                            for id, field_mapping in id_to_field_mappings.items()
                            if comp_any(value, field_mapping.get(attr.attribute_id, ()))
                        }

                t.assert_never(comp_filter)

        t.assert_never(filter)

    def _sort[T: AttributeType](
        self,
        field_mappings: t.Sequence[AbstractFieldMappingIDToSlotTypeT],
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> t.Sequence[AbstractFieldMappingIDToSlotTypeT]:
        # Warning: Complicated code ahead! But it allows for fast, multi-key, asc/desc sorting

        # --- Normalize Sorts As Much As Possible --- #
        clean_sorts: list[tuple[AttributeEntity[T], bool]] = []
        seen: set[AttributeEntity[T]] = set()

        for syn, asc in sort:
            attr = syn_to_attribute[syn]

            # Remove duplicate attrs, they don't affect final result
            # Even if an attr is duplicated, the later keys still matter! Don't break!
            if attr in seen:
                continue

            seen.add(attr)

            clean_sorts.append((attr, asc))

            # Short circuit when we know last sort results in unique sort values
            if attr.slot_unique_across_list:
                break

        del sort

        # Sort by name by default
        if not clean_sorts:
            name_attr: AttributeEntity[StaticAttributeTypeT]

            for attr in syn_to_attribute.values():
                if attr.kind is AttributeKind.NAME:
                    name_attr = attr  # type: ignore
                    break
            else:
                raise ValueError("Data error, no name attribute found!!!")

            clean_sorts = [(name_attr, True)]  # type: ignore

        # --- Gather Sorting Data --- #
        field_mappings_and_their_sort_value: list[
            tuple[
                AbstractFieldMappingIDToSlotTypeT,
                tuple[tuple[SlotTypeT, ...], ...],
            ]
        ] = []

        for field_mapping in field_mappings:
            # Map every attr into the typed field of the task
            task_sort_value: list[tuple[SlotTypeT, ...]] = []

            for attr, _ in clean_sorts:
                coll_value_to_entry_idx = (
                    attribute_id_to_collection_value_to_entry_index.get(
                        attr.attribute_id
                    )
                )

                # Collection exists for given attr
                if coll_value_to_entry_idx:
                    # It is possible that a slot does not match any collection value in case that
                    # a user attribute's collection is edited and staff did not yet fix the users'
                    # data. Therefore allow for default and put as -1 (sort first/last)
                    task_sort_value.append(
                        tuple(
                            coll_value_to_entry_idx.get(slot, -1)
                            for slot in field_mapping.get(attr.attribute_id, ())
                        )
                    )
                else:
                    task_sort_value.append(
                        tuple(slot for slot in field_mapping.get(attr.attribute_id, ()))
                    )

            field_mappings_and_their_sort_value.append((field_mapping, tuple(task_sort_value)))

        # --- Apply Sort --- #
        def compare_sort_values(
            a: tuple[
                AbstractFieldMappingIDToSlotTypeT,
                tuple[tuple[SlotTypeT, ...], ...],
            ],
            b: tuple[
                AbstractFieldMappingIDToSlotTypeT,
                tuple[tuple[SlotTypeT, ...], ...],
            ],
        ) -> int:
            values_a = a[1]
            values_b = b[1]

            for va, vb, (_, asc) in zip(values_a, values_b, clean_sorts):
                if va < vb:
                    return -1 if asc else 1

                if va > vb:
                    return 1 if asc else -1

            return 0

        return tuple(
            field_mapping
            for field_mapping, _ in sorted(
                field_mappings_and_their_sort_value,
                key=functools.cmp_to_key(compare_sort_values),
            )
        )