import functools
import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.concept import Concept
from domain.enums.edit_mode import FieldMappingEditMode
from domain.errors.business import (
    AttributeMentionedMoreThanOnce,
    AttributeNotMentioned,
    CollectionEntryNotFoundViaSyn,
    NotFoundByName,
    NotFoundBySyn,
    NotUniqueSlots,
    SlotCountConfigNotFulfilled,
)
from domain.errors.internal import KindedAttributeMissing
from domain.sentinels.default import DEFAULT
from domain.typing.attribute import (
    AnyAttributeTypeT,
    AttributeID,
    SlotTypeT,
    TaskAttributeTypeT,
)
from domain.typing.collection_entry import AbstractCollectionT
from domain.typing.field_mapping import (
    AbstractFieldMappingIDToSlotTypeT,
    AbstractFieldMappingIDToStringsT,
    FrozenFieldMappingEntityToStrings,
    FrozenFieldMappingIDToStringsT,
    MutableFieldMappingIDToStringsT,
    RawFieldMappingT,
)
from domain.typing.member_task import MemberTaskID
from domain.typing.task import TaskID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.filter import (
    AndFilter,
    EmptyComparisonFilter,
    FilterT,
    NonEmptyComparisonFilter,
    OpType,
    OrFilter,
)
from domain.value_objects.list import ListNameStr
from domain.value_objects.member import OptionalMemberWrapper
from domain.value_objects.string import NormStr, RealStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.field_slot import FieldSlotRepository
from repositories.member import MemberRepository
from repositories.member_field_slot import MemberFieldSlotRepository
from repositories.member_task import MemberTaskRepository
from repositories.task import TaskRepository
from services.dtos.member_task import MemberTaskInfo
from services.dtos.task import TaskInfo
from services.dtos.user import UserRef
from services.internal.edit_mode import (
    AbstractFieldMappingEntityToStringT,
    EditModeService,
)
from services.internal.slot_type import SlotTypeService
from services.list import ListAccessService
from services.member import MemberAccessService, MemberExistenceService
from services.member_task import MemberTaskAccessService
from services.task import TaskAccessService

# Type checkers do not know that values passed in share the same SlotTypeT every time
# They complain because comparisons between the different types is obviously not always valid
_OP_TO_COMP_ANY_FUNC: t.Final[
    frozendict[OpType, t.Callable[[SlotTypeT, t.Iterable[SlotTypeT]], bool]]
] = frozendict(
    {
        OpType.EQ: lambda v, field: v in field,
        OpType.NEQ: lambda v, field: v not in field,
        OpType.LT: lambda v, field: any(
            v < slot for slot in field  # pyright: ignore[reportOperatorIssue]
        ),
        OpType.LTE: lambda v, field: any(
            v <= slot for slot in field  # pyright: ignore[reportOperatorIssue]
        ),
        OpType.GT: lambda v, field: any(
            v > slot for slot in field  # pyright: ignore[reportOperatorIssue]
        ),
        OpType.GTE: lambda v, field: any(
            v >= slot for slot in field  # pyright: ignore[reportOperatorIssue]
        ),
    }
)


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingBuildService:
    """Validate and build field mappings."""

    _edit_mode_service: EditModeService
    _slot_type_service: SlotTypeService

    def build_raw[T: AttributeType](
        self,
        field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, AbstractCollectionT],
        *,
        complete: bool = True,
    ) -> FrozenFieldMappingEntityToStrings[T]:
        unchecked_field_mapping = self._try_convert_syns_to_attr_ids(
            field_mapping, syn_to_attribute
        )

        return self.build(
            unchecked_field_mapping,
            frozenset(syn_to_attribute.values()),
            attr_id_to_collection,
            complete=complete,
        )

    def _try_convert_syns_to_attr_ids(
        self,
        field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity],
    ) -> AbstractFieldMappingIDToStringsT:
        unchecked_field_mapping: AbstractFieldMappingIDToStringsT = {}

        for attr_syn, value in field_mapping:
            attr = syn_to_attribute.get(attr_syn)

            if attr is None:
                raise NotFoundBySyn(Concept.ATTRIBUTE, attr_syn)

            if attr in unchecked_field_mapping:
                raise AttributeMentionedMoreThanOnce(attr)

            unchecked_field_mapping[attr.attribute_id] = tuple(value)

        return unchecked_field_mapping

    def build[T: AttributeType](
        self,
        unchecked_field_mapping: AbstractFieldMappingIDToStringsT,
        attributes: t.AbstractSet[AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[AttributeID, AbstractCollectionT],
        *,
        complete: bool = True,
    ) -> FrozenFieldMappingEntityToStrings[T]:
        res: dict[AttributeEntity[T], tuple[FieldSlotStr, ...]] = {}

        for attr in attributes:
            field = unchecked_field_mapping.get(attr.attribute_id, ())

            if complete:
                if (
                    len(field) < attr.field_config.min_slot_count
                    or len(field) > attr.field_config.max_slot_count
                ):
                    raise SlotCountConfigNotFulfilled(attr, tuple(field))

            field = tuple(
                self._slot_type_service.single_to_slot_typed_str(
                    slot, attr.field_config.slot_type
                )
                for slot in field
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

                collectionified_field: list[FieldSlotStr] = []

                for slot in field:
                    value = syn_to_value.get(slot)

                    if value is None:
                        raise CollectionEntryNotFoundViaSyn(
                            attr,
                            tuple((entry[0], tuple(entry[1])) for entry in collection),
                            slot,
                        )

                    collectionified_field.append(value)

                field = tuple(collectionified_field)

            if (
                attr.field_config.unique_slots
                and len(field) > 1
                and len(set(field)) != len(field)
            ):
                raise NotUniqueSlots(attr, field)

            res[attr] = field

        return frozendict(res)

    def build_edit[T: AttributeType](
        self,
        edit_mode: FieldMappingEditMode,
        current_field_mapping: AbstractFieldMappingEntityToStringT,
        new_field_mapping: RawFieldMappingT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection: t.Mapping[AttributeID, AbstractCollectionT],
    ) -> FrozenFieldMappingEntityToStrings[T]:
        # Build the new mapping to see if even valid on its own
        new_fm = {
            attr: v
            for attr, v in self.build_raw(
                new_field_mapping,
                syn_to_attribute,
                attribute_id_to_collection,
                complete=edit_mode
                not in (
                    FieldMappingEditMode.COMBINE_OVERRIDE_ON_COLLISION,
                    FieldMappingEditMode.COMBINE_ERROR_ON_COLLISION,
                ),
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
            {attr.attribute_id: f for attr, f in new_fm.items()},
            frozenset(syn_to_attribute.values()),
            attribute_id_to_collection,
        )


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingExtractionService:
    """Extract kinded field mappings from existing data."""

    def get_task_kinded_field_mapping_single(
        self,
        task: TaskEntity,
        task_aliases: tuple[FieldSlotStr, ...],
        attributes: t.Iterable[AttributeEntity[AnyAttributeTypeT]],
    ) -> MutableFieldMappingIDToStringsT:
        static_field_mapping: MutableFieldMappingIDToStringsT = {}

        for attr in attributes:
            match attr.kind:
                case AttributeKind.ID:
                    task_id_str = str(task.task_id)

                    static_field_mapping[attr.attribute_id] = (
                        # It's just an integer so nothing is different in normalized version
                        # No need to convert
                        FieldSlotStr._create_from_real_and_norm(
                            RealStr._create(task_id_str),
                            NormStr._create(task_id_str),
                        ),
                    )

                case AttributeKind.NAME:
                    static_field_mapping[attr.attribute_id] = (task.name,)

                case AttributeKind.ALIAS:
                    static_field_mapping[attr.attribute_id] = task_aliases

                case AttributeKind.CREATED_AT:
                    static_field_mapping[attr.attribute_id] = (
                        FieldSlotStr(RealStr._create(str(task.created_at))),
                    )

                case (
                    AttributeKind.NONE | AttributeKind.GIVEN_AT | AttributeKind.GIVEN_BY
                ):
                    pass

                case _:
                    t.assert_never(attr)

        return static_field_mapping

    def get_user_kinded_field_mapping_single(
        self,
        member_task: MemberTaskEntity,
        given_by: MemberEntity | None,
        attributes: t.Iterable[AttributeEntity[AnyAttributeTypeT]],
    ) -> MutableFieldMappingIDToStringsT:
        static_field_mapping: MutableFieldMappingIDToStringsT = {}

        for attr in attributes:
            match attr.kind:
                case AttributeKind.GIVEN_AT:
                    static_field_mapping[attr.attribute_id] = (
                        FieldSlotStr(RealStr._create(str(member_task.given_at))),
                    )

                case AttributeKind.GIVEN_BY:
                    static_field_mapping[attr.attribute_id] = (
                        (
                            FieldSlotStr(
                                RealStr._create(str(OptionalMemberWrapper(given_by)))
                            )
                        ),
                    )

                case (
                    AttributeKind.NONE
                    | AttributeKind.ID
                    | AttributeKind.NAME
                    | AttributeKind.ALIAS
                    | AttributeKind.CREATED_AT
                ):
                    pass

                case _:
                    t.assert_never(attr)

        return static_field_mapping

    def get_task_kinded_field_mapping_many(
        self,
        tasks: t.Sequence[TaskEntity],
        task_id_to_aliases: t.Mapping[TaskID, tuple[FieldSlotStr, ...]],
        attributes: t.Iterable[AttributeEntity],
    ) -> frozendict[TaskID, MutableFieldMappingIDToStringsT]:
        mapping: frozendict[TaskID, MutableFieldMappingIDToStringsT] = frozendict(
            (task.task_id, {}) for task in tasks
        )

        for attr in attributes:
            match attr.kind:
                case AttributeKind.ID:
                    for task in tasks:
                        task_id_str = str(task.task_id)

                        mapping[task.task_id][attr.attribute_id] = (
                            FieldSlotStr._create_from_real_and_norm(
                                RealStr._create(task_id_str),
                                NormStr._create(task_id_str),
                            ),
                        )

                case AttributeKind.NAME:
                    for task in tasks:
                        mapping[task.task_id][attr.attribute_id] = (task.name,)

                case AttributeKind.ALIAS:
                    for task in tasks:
                        mapping[task.task_id][attr.attribute_id] = (
                            task_id_to_aliases.get(task.task_id, ())
                        )

                case AttributeKind.CREATED_AT:
                    for task in tasks:
                        mapping[task.task_id][attr.attribute_id] = (
                            FieldSlotStr(RealStr._create(str(task.created_at))),
                        )

                case (
                    AttributeKind.NONE | AttributeKind.GIVEN_AT | AttributeKind.GIVEN_BY
                ):
                    pass

                case _:
                    t.assert_never(attr)

        return mapping

    def get_user_kinded_field_mapping_many(
        self,
        member_tasks: t.Sequence[MemberTaskEntity],
        member_task_id_to_given_by: t.Mapping[MemberTaskID, MemberEntity],
        attributes: t.Iterable[AttributeEntity[AnyAttributeTypeT]],
    ) -> frozendict[TaskID, MutableFieldMappingIDToStringsT]:
        mapping: frozendict[TaskID, MutableFieldMappingIDToStringsT] = frozendict(
            (member_task.task_id, {}) for member_task in member_tasks
        )

        for attr in attributes:
            match attr.kind:
                case AttributeKind.GIVEN_AT:
                    for member_task in member_tasks:
                        mapping[member_task.task_id][attr.attribute_id] = (
                            FieldSlotStr(RealStr._create(str(member_task.given_at))),
                        )

                case AttributeKind.GIVEN_BY:
                    for member_task in member_tasks:
                        mapping[member_task.task_id][attr.attribute_id] = (
                            (
                                FieldSlotStr(
                                    RealStr._create(
                                        str(
                                            OptionalMemberWrapper(
                                                member_task_id_to_given_by[
                                                    member_task.member_task_id
                                                ]
                                            )
                                        )
                                    )
                                )
                            ),
                        )

                case (
                    AttributeKind.NONE
                    | AttributeKind.ID
                    | AttributeKind.NAME
                    | AttributeKind.ALIAS
                    | AttributeKind.CREATED_AT
                ):
                    pass

                case _:
                    t.assert_never(attr)

        return mapping


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingTransformationService:
    """Transform field mappings via sorting, filtering and more."""

    _slot_type_service: SlotTypeService

    def filter_sort_yield[T: AttributeType](
        self,
        field_mappings: t.Sequence[AbstractFieldMappingIDToSlotTypeT],
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> frozendict[AttributeEntity[T], tuple[tuple[SlotTypeT, ...], ...]]:
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
        fms = self._yield(fms, yield_, syn_to_attribute)
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

        # Map field mappings to their own Python IDs for fast dict/set operations
        # Normalize slots of type str to have their comparison be not case-sensitive
        field_mappings_adjusted_for_filtering = {
            id(fm): {
                attribute_id: tuple(
                    NormStr.normalize(slot) if isinstance(slot, str) else slot
                    for slot in field
                )
                for attribute_id, field in fm.items()
            }
            for fm in field_mappings
        }

        filtered = self._recursively_solve_filter(
            field_mappings_adjusted_for_filtering,
            filter,
            syn_to_attribute,
            attribute_id_to_collection_value_to_entry_index,
        )

        return tuple(fm for fm in field_mappings if id(fm) in filtered)

    def _recursively_solve_filter(
        self,
        id_to_field_mappings: t.Mapping[int, AbstractFieldMappingIDToSlotTypeT],
        filter: FilterT,
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity],
        attribute_id_to_collection_value_to_entry_index: t.Mapping[
            AttributeID, t.Mapping[SlotTypeT, int]
        ],
    ) -> t.Mapping[int, AbstractFieldMappingIDToSlotTypeT]:
        """Recursively run through the filter and short circuit where possible.

        For example:
        - (A and B) -> Only test tasks in B that succeeded in A
        - (A or B) -> Only test tasks in B that failed in A and combine all succeeded at the end

        Always short circuit when no more tasks are left to examine.

        We use a mapping to the Python id() of each given field mapping to make use of
        fast dict operations like removing elements in O(1). We don't just use a set
        because for 1. abstract mappings are not hashable and 2. if we used frozendicts
        hashing them would be slow (once per frozendict).
        """

        match filter:
            # --- OR ---
            # One of the operands must be true to be valid
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

            # --- AND --- #
            # All operands must be true to be valid
            case AndFilter() as and_filter:
                still_valid: t.Mapping[int, AbstractFieldMappingIDToSlotTypeT] = dict(
                    id_to_field_mappings
                )

                for operand in and_filter.operands:
                    # No more elements that are valid -> stop
                    if not still_valid:
                        break

                    still_valid = self._recursively_solve_filter(
                        still_valid,
                        operand,
                        syn_to_attribute,
                        attribute_id_to_collection_value_to_entry_index,
                    )

                return still_valid

            # --- COMPARISON ---
            # Check if the given comparison expression is true for a given field_mapping
            case EmptyComparisonFilter() | NonEmptyComparisonFilter() as comp_filter:
                attr_syn = AttributeSynStr(comp_filter.attribute)

                attr = syn_to_attribute.get(attr_syn)

                if attr is None:
                    raise NotFoundBySyn(Concept.ATTRIBUTE, attr_syn)

                # Examples: "a is _", "a is not _"
                if isinstance(comp_filter, EmptyComparisonFilter):
                    want_empty = comp_filter.op is OpType.EQ

                    # Return all field mappings where the field for the
                    # specified attribute is empty (or not empty if operator is NEQ)
                    return {
                        id: field_mapping
                        for id, field_mapping in id_to_field_mappings.items()
                        if (not field_mapping.get(attr.attribute_id)) is want_empty
                    }

                # Examples: "a is value", "a >= value", "a < value"
                elif isinstance(comp_filter, NonEmptyComparisonFilter):
                    comp_any = _OP_TO_COMP_ANY_FUNC[comp_filter.op]
                    value = self._slot_type_service.single_to_slot_type(
                        FieldSlotStr(comp_filter.value), attr.field_config.slot_type
                    )

                    coll_value_to_idx = (
                        attribute_id_to_collection_value_to_entry_index.get(
                            attr.attribute_id
                        )
                    )

                    # Attribute has collection, compare collection index
                    if coll_value_to_idx:
                        value_idx = coll_value_to_idx[value]

                        return {
                            id: field_mapping
                            for id, field_mapping in id_to_field_mappings.items()
                            if comp_any(
                                value_idx,
                                (
                                    coll_value_to_idx.get(slot, -1)
                                    for slot in field_mapping.get(attr.attribute_id, ())
                                ),
                            )
                        }
                    # Attribute has no collection, compare actual value
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
            name_attr: AttributeEntity

            for attr in syn_to_attribute.values():
                if attr.kind is AttributeKind.NAME:
                    name_attr = attr
                    break
            else:
                # CRITICAL!! THIS IS BAD!
                raise KindedAttributeMissing(AttributeKind.NAME)

            clean_sorts = [(name_attr, True)]

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

            field_mappings_and_their_sort_value.append(
                (field_mapping, tuple(task_sort_value))
            )

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

    def _yield[T: AttributeType](
        self,
        field_mappings: t.Sequence[AbstractFieldMappingIDToSlotTypeT],
        yield_: t.Sequence[AttributeSynStr],
        syn_to_attribute: t.Mapping[AttributeSynStr, AttributeEntity[T]],
    ) -> frozendict[AttributeEntity[T], tuple[tuple[SlotTypeT, ...], ...]]:
        final_yield: tuple[AttributeEntity[T], ...]

        if not yield_:
            final_yield = tuple(
                sorted(
                    set(syn_to_attribute.values()), key=lambda attr: attr.position.value
                )
            )
        else:
            final_yield = tuple(
                dict.fromkeys((syn_to_attribute[syn] for syn in yield_), None)
            )

        return frozendict(
            (
                attr,
                tuple(
                    field_mapping.get(attr.attribute_id, ())
                    for field_mapping in field_mappings
                ),
            )
            for attr in final_yield
        )


@dataclass(frozen=True, slots=True, eq=False)
class FieldMappingService:
    _attribute_repository: AttributeRepository
    _collection_entry_repository: CollectionEntryRepository
    _field_slot_repository: FieldSlotRepository
    _member_field_slot_repository: MemberFieldSlotRepository
    _member_repository: MemberRepository
    _member_task_repository: MemberTaskRepository
    _task_repository: TaskRepository

    _list_access_service: ListAccessService
    _field_mapping_extraction_service: FieldMappingExtractionService
    _field_mapping_transformation_service: FieldMappingTransformationService
    _member_access_service: MemberAccessService
    _member_task_access_service: MemberTaskAccessService
    _slot_type_service: SlotTypeService
    _task_access_service: TaskAccessService

    @t.overload
    def get_info(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
    ) -> TaskInfo:
        pass

    @t.overload
    def get_info(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT,
    ) -> MemberTaskInfo:
        pass

    def get_info(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT | None = None,
    ) -> TaskInfo | MemberTaskInfo:
        community, _, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        ATTRIBUTE_TYPES: t.AbstractSet[AttributeType]
        ATTRIBUTE_KINDS: t.AbstractSet[AttributeKind]

        target_member_and_member_task: tuple[MemberEntity, MemberTaskEntity] | None = (
            None
        )

        if target_user is None:
            ATTRIBUTE_TYPES = AttributeType.TASK.as_set()
            ATTRIBUTE_KINDS = AttributeKind.NONE_OR_TASK_KINDED
        else:
            ATTRIBUTE_TYPES = AttributeType.ALL
            ATTRIBUTE_KINDS = AttributeKind.ALL

            target_member_and_member_task = (
                self._member_task_access_service.get_member_task_or_raise(
                    target_user, community.community_id, task.task_id
                )
            )

        del target_user

        attrs = self._attribute_repository.get_all_by_list_id_ordered_by_position(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )

        task_kinded_field_mapping = (
            self._field_mapping_extraction_service.get_task_kinded_field_mapping_single(
                task, self._task_repository.get_aliases_by_task_id(task.task_id), attrs
            )
        )

        task_field_mapping = self._field_slot_repository.get_field_mapping_by_task_id(
            task.task_id
        )

        user_kinded_field_mapping: MutableFieldMappingIDToStringsT = {}
        user_field_mapping: FrozenFieldMappingIDToStringsT = frozendict()

        if target_member_and_member_task is not None:
            _, member_task = target_member_and_member_task

            user_kinded_field_mapping = self._field_mapping_extraction_service.get_user_kinded_field_mapping_single(
                member_task,
                self._member_repository.get_by_member_id(member_task.member_id),
                attrs,
            )

            user_field_mapping = self._member_field_slot_repository.get_field_mapping_by_member_id_and_task_id(
                member_task.member_id, member_task.task_id
            )

        field_mapping = (
            task_kinded_field_mapping
            | user_kinded_field_mapping
            | task_field_mapping
            | user_field_mapping
        )

        del task_kinded_field_mapping, task_field_mapping, user_field_mapping

        final_data = frozendict(
            (attr, field_mapping.get(attr.attribute_id, ())) for attr in attrs
        )

        if target_member_and_member_task is not None:
            return MemberTaskInfo(
                task,
                target_member_and_member_task[1],
                target_member_and_member_task[0],
                final_data,
            )

        # Assert type is what we think the type checker assumes and then cast to what we
        # know it is. It is only task data, no user data.
        t.assert_type(final_data, FrozenFieldMappingEntityToStrings[AnyAttributeTypeT])
        final_data = t.cast(
            FrozenFieldMappingEntityToStrings[TaskAttributeTypeT], final_data
        )

        return TaskInfo(task, final_data)

    @t.overload
    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[TaskAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        """Get all summaries with the specified filter, sort and yield."""

    @t.overload
    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT,
        missing: t.Literal[False],
    ) -> frozendict[
        AttributeEntity[AnyAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        """Get all user specific summaries with the specified filter, sort and yield."""

    @t.overload
    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT,
        missing: t.Literal[True],
    ) -> frozendict[
        AttributeEntity[TaskAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        """Get all summaries with the specified filter, sort and yield a user is
        missing.
        """

    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT | None = None,
        missing: bool = False,
    ) -> (
        frozendict[
            AttributeEntity[TaskAttributeTypeT],
            tuple[tuple[SlotTypeT, ...], ...],
        ]
        | frozendict[
            AttributeEntity[AnyAttributeTypeT],
            tuple[tuple[SlotTypeT, ...], ...],
        ]
    ):
        community, _, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        ATTRIBUTE_TYPES: t.AbstractSet[AttributeType]
        ATTRIBUTE_KINDS: t.AbstractSet[AttributeKind]

        target_member: MemberEntity | None = None

        # Task
        if target_user is None:
            ATTRIBUTE_TYPES = AttributeType.TASK.as_set()
            ATTRIBUTE_KINDS = AttributeKind.NONE_OR_TASK_KINDED
        # User
        else:
            ATTRIBUTE_TYPES = AttributeType.ALL
            ATTRIBUTE_KINDS = AttributeKind.ALL

            target_member = self._member_access_service.get_or_create_with_user_ref(
                target_user, community.community_id
            )

        del target_user

        syn_to_attr = self._attribute_repository.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )
        attrs_sorted = tuple(
            sorted(set(syn_to_attr.values()), key=lambda attr: attr.position.value)
        )

        tasks: tuple[TaskEntity, ...]
        _task_id_to_user_kinded_field_mapping: frozendict[
            TaskID, MutableFieldMappingIDToStringsT
        ] = frozendict()
        _task_id_to_user_field_mapping: frozendict[
            TaskID, FrozenFieldMappingIDToStringsT
        ] = frozendict()

        # Task
        if target_member is None:
            tasks = self._task_repository.get_all_by_list_id(lst.list_id)
        # User
        elif not missing:
            (
                tasks,
                _task_id_to_user_kinded_field_mapping,
                _task_id_to_user_field_mapping,
            ) = self._calc_user_field_mapping_data(lst, target_member, attrs_sorted)
        # User Missing
        else:
            tasks = self._task_repository.get_all_missing_by_list_id_and_member_id(
                lst.list_id, target_member.member_id
            )

        _task_id_to_task_kinded_field_mapping = (
            self._field_mapping_extraction_service.get_task_kinded_field_mapping_many(
                tasks,
                self._task_repository.get_grouped_aliases_by_list_id(lst.list_id),
                attrs_sorted,
            )
        )

        _task_id_to_task_field_mapping = (
            self._field_slot_repository.get_task_field_mapping_by_list_id(lst.list_id)
        )

        # Combine all mappings into the final one
        # DO NOT DEL these variables to clean up the namespace. This is a generator
        # which means that when the generator is used, the variables must still have
        # their value!
        field_mappings_untyped_gen = tuple(
            (
                _task_id_to_task_kinded_field_mapping.get(task.task_id, frozendict())
                | _task_id_to_user_kinded_field_mapping.get(task.task_id, frozendict())
                | _task_id_to_task_field_mapping.get(task.task_id, frozendict())
                | _task_id_to_user_field_mapping.get(task.task_id, frozendict())
            )
            for task in tasks
        )

        attr_id_to_slot_type = {
            attr.attribute_id: attr.field_config.slot_type for attr in attrs_sorted
        }

        # Iterate generator to create typed mappings
        field_mappings = tuple(
            {
                attr_id: tuple(
                    self._slot_type_service.many_to_slot_type(
                        f, attr_id_to_slot_type[attr_id], validate=False
                    )
                )
                for attr_id, f in fm.items()
            }
            for fm in field_mappings_untyped_gen
        )

        # Map each attribute to a mapping which maps the collections value to its index in the collection
        # Used for sorting and filtering
        # Highly complicated comprehension but not worth making it 10x longer than it needs to be
        attr_id_to_coll_value_to_idx = {
            attr_id: {
                slot_typed: idx
                for slot_typed, idx in zip(
                    self._slot_type_service.many_to_slot_type(
                        value_to_idx, attr_id_to_slot_type[attr_id], validate=False
                    ),
                    value_to_idx.values(),
                )
            }
            for attr_id, value_to_idx in self._collection_entry_repository.get_grouped_value_to_index_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, AttributeKind.NONE_KINDED
            ).items()
        }

        return self._field_mapping_transformation_service.filter_sort_yield(
            field_mappings,
            filter,
            sort,
            yield_,
            syn_to_attr,
            attr_id_to_coll_value_to_idx,
        )

    def _calc_user_field_mapping_data(
        self,
        lst: ListEntity,
        target_member: MemberEntity,
        attrs_sorted: tuple[AttributeEntity[AnyAttributeTypeT], ...],
    ) -> tuple[
        tuple[TaskEntity, ...],
        frozendict[TaskID, MutableFieldMappingIDToStringsT],
        frozendict[TaskID, FrozenFieldMappingIDToStringsT],
    ]:
        member_tasks_to_tasks = self._member_task_repository.get_member_tasks_and_tasks_by_list_id_and_member_id(
            lst.list_id, target_member.member_id
        )

        member_tasks = tuple(member_tasks_to_tasks.keys())
        tasks = tuple(member_tasks_to_tasks.values())

        task_id_to_user_kinded_field_mapping = self._field_mapping_extraction_service.get_user_kinded_field_mapping_many(
            member_tasks,
            self._member_task_repository.get_given_by_member_by_list_id_and_member_id(
                lst.list_id, target_member.member_id
            ),
            attrs_sorted,
        )

        task_id_to_user_field_mapping = (
            self._member_field_slot_repository.get_grouped_field_mapping_by_member_id(
                target_member.member_id
            )
        )
        return (
            tasks,
            task_id_to_user_kinded_field_mapping,
            task_id_to_user_field_mapping,
        )
