import typing as t
from functools import cached_property
from types import EllipsisType

from dc_utils import errors, parsing
from structures import attribute
from structures.attribute import (
    AnyAttributeT,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.errors import (
    AttributeMinSlotsOrMaxSlotsOutOfRangeError,
    AttributeValueSlotCountOutOfRangeError,
    CollectionEntryAliasLimitReachedError,
    CollectionEntryLimitReachedError,
    CollectionEntryNotFoundError,
    CollectionEntrySynNotUniqueError,
    CommunityUserAlreadyHasTaskError,
    CommunityUserDoesNotHaveTaskError,
    InvalidSlotStrError,
    NotAllTasksFitMinAndMaxSlotCountChangesError,
    StructureCountLimitReachedError,
    StructureNotFoundError,
    SynNotUniqueError,
    SynsAlreadyTakenError,
    TooLongSynError,
    TooManyAliasesError,
)
from structures.list import List
from structures.task import Task
from utils import orm, text

from . import BaseStructureAdapter
from ._attribute import (
    AnyAttributeAdapterT,
    StaticAttributeAdapter,
    TaskAttributeAdapter,
    UserAttributeAdapter,
)
from ._task import TaskAdapter
from ._user import CommunityUserAdapter

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter


@t.overload
def _get_attribute_adapter(
    attribute: StaticAttribute, list: ListAdapter
) -> StaticAttributeAdapter:
    pass


@t.overload
def _get_attribute_adapter(
    attribute: TaskAttribute, list: ListAdapter
) -> TaskAttributeAdapter:
    pass


@t.overload
def _get_attribute_adapter(
    attribute: UserAttribute, list: ListAdapter
) -> UserAttributeAdapter:
    pass


@t.overload
def _get_attribute_adapter(
    attribute: attribute.AnyAttributeT, list: ListAdapter
) -> AnyAttributeAdapterT:
    pass


def _get_attribute_adapter(
    attribute: attribute.AnyAttributeT, list: ListAdapter
) -> AnyAttributeAdapterT:
    if isinstance(attribute, StaticAttribute):
        return StaticAttributeAdapter(attribute, list)

    if isinstance(attribute, TaskAttribute):
        return TaskAttributeAdapter(attribute, list)

    if isinstance(attribute, UserAttribute):
        return UserAttributeAdapter(attribute, list)

    t.assert_never(attribute)


def _require_task_with_syn(c: orm.Cursor, norm_syn: text.NormStr, list: List) -> Task:
    tup = list.get_task_by_syn(c, norm_syn)

    if tup is None:
        raise errors.StructureNotFoundViaSyn(norm_syn, Task)

    return tup[0]


@t.overload
def _require_attribute_with_syn(
    c: orm.Cursor, norm_syn: text.NormStr, attribute_type: EllipsisType, list: List
) -> AnyAttributeT:
    pass


@t.overload
def _require_attribute_with_syn[T: AnyAttributeT](
    c: orm.Cursor,
    norm_syn: text.NormStr,
    attribute_type: type[T] | EllipsisType,
    list: List,
) -> T:
    pass


def _require_attribute_with_syn(
    c: orm.Cursor,
    norm_syn: text.NormStr,
    attribute_type: type[AnyAttributeT] | EllipsisType,
    list: List,
) -> AnyAttributeT:
    tup = list.get_attribute_by_syn(c, norm_syn, type=attribute_type)

    if tup is None:
        raise errors.StructureNotFoundViaSyn(norm_syn, TaskAttribute)

    return tup[0]


def _parse_aliases(aliases_raw: str | None) -> tuple[text.RealStr, ...]:
    if not aliases_raw:
        return ()

    aliases = parsing.value_sequence.parse(text.RealStr(aliases_raw))

    return tuple(map(text.RealStr, aliases))


class ListAdapter(BaseStructureAdapter[List]):
    community: CommunityAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.community._c

    @property
    def name(self) -> text.RealStr:
        return self._o.real_name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [TaskAdapter(task, self) for task in self._o.get_tasks(self._c)]

    def get_tasks_of_user(self, user: CommunityUserAdapter) -> list[TaskAdapter]:
        return [
            TaskAdapter(task, self)
            for task in self._o.get_tasks_of_user(self._c, user._o.id)
        ]

    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_syn(self._c, text.NormStr(syn), self._o), self
        )

    def _parse_attribute_value_mapping[T: AnyAttributeT](
        self, type: type[T], attribute_value_mapping: str | None
    ) -> tuple[dict[int, tuple[text.RealStr, ...]], dict[text.RealStr, T]]:
        if not attribute_value_mapping:
            return {}, {}

        syn_to_attr = self._o.get_attributes_by_syn(self._c, ..., type=type)

        avm = parsing.avm.parse(
            self._c,
            text.RealStr(attribute_value_mapping),
            {text.NormStr(k): v for k, v in syn_to_attr.items()},
        )

        return {k.id: v for k, v in avm.items()}, syn_to_attr

    def create_task(
        self, name: str, aliases: str | None, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        real_name = text.RealStr(name)

        real_aliases = _parse_aliases(aliases)
        avms, _ = self._parse_attribute_value_mapping(
            TaskAttribute, task_attribute_value_mapping
        )

        try:
            task_s = self._o.create_task(
                self._c,
                real_name,
                real_aliases,
                avms,
            )
        except (
            SynsAlreadyTakenError,
            StructureCountLimitReachedError,
            SynNotUniqueError,
            AttributeValueSlotCountOutOfRangeError,
            CollectionEntryNotFoundError,
        ) as e:
            raise errors.create_feedback_from_structure_error(e)

        return TaskAdapter(task_s, self)

    def delete_task(self, syn: str) -> TaskAdapter:
        task = self.get_task(syn)

        try:
            self._o.delete_task(self._c, task._o.id)
        except StructureNotFoundError:
            raise errors.StructureNotFoundViaSyn(syn, Task)

        return task

    def edit_task_name(self, syn: str, name: str) -> tuple[TaskAdapter, SlotStr]:
        task = self.get_task(syn)

        try:
            new_name = self._o.edit_task_name(self._c, task._o.id, text.RealStr(name))
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTaken(e)
        except InvalidSlotStrError as e:
            raise errors.InvalidSlotStr(e)

        return task, new_name

    def edit_task_aliases(
        self, syn: str, aliases: str
    ) -> tuple[TaskAdapter, tuple[SlotStr, ...]]:
        task = self.get_task(syn)

        try:
            slot_aliases = self._o.edit_task_aliases(
                self._c,
                task._o.id,
                tuple(
                    map(
                        text.RealStr,
                        parsing.value_sequence.parse(text.RealStr(aliases)),
                    )
                ),
            )
        except (
            SynsAlreadyTakenError,
            SynNotUniqueError,
            AttributeValueSlotCountOutOfRangeError,
            InvalidSlotStrError,
        ) as e:
            raise errors.create_feedback_from_structure_error(e)

        return (task, slot_aliases)

    def edit_task_attribute_value_mapping(
        self, syn: str, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        task = self.get_task(syn)
        tavm = self._parse_attribute_value_mapping(
            TaskAttribute, task_attribute_value_mapping
        )[0]

        try:
            _ = self._o.edit_task_attribute_value_mapping(
                self._c,
                task._o.id,
                tavm,
            )
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.create_feedback_from_structure_error(e)

        return task  # we dont return the mapping bec of issues with hashing attribute adapter

    def give_task_to_user(
        self,
        syn: str,
        community_user: CommunityUserAdapter,
        user_attribute_value_mapping: str | None = None,
    ) -> TaskAdapter:
        task_o = _require_task_with_syn(self._c, text.NormStr(syn), self._o)

        uavm = self._parse_attribute_value_mapping(
            UserAttribute, user_attribute_value_mapping
        )[0]

        try:
            self._o.give_task_to_community_user(
                self._c, task_o.id, community_user._o.id, uavm
            )
        except (
            CollectionEntryNotFoundError,
            AttributeValueSlotCountOutOfRangeError,
            CommunityUserAlreadyHasTaskError,
        ) as e:
            raise errors.create_feedback_from_structure_error(
                e, community_user=community_user._o, task=task_o
            )

        return TaskAdapter(task_o, self)

    def remove_task_from_user(
        self, syn: str, community_user: CommunityUserAdapter
    ) -> TaskAdapter:
        task_s = _require_task_with_syn(self._c, text.NormStr(syn), self._o)

        try:
            self._o.remove_task_from_community_user(
                self._c, task_s.id, community_user._o.id
            )
        except CommunityUserDoesNotHaveTaskError:
            raise errors.TaskNotGivenYet(community_user._o, task_s)

        return TaskAdapter(task_s, self)

    # --- Attribute ---

    def get_attributes_flat(self) -> list[AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._o.get_attributes(self._c)
        ]

    @t.overload
    def get_attributes(
        self, type: type[StaticAttribute]
    ) -> list[StaticAttributeAdapter]:
        pass

    @t.overload
    def get_attributes(self, type: type[TaskAttribute]) -> list[TaskAttributeAdapter]:
        pass

    @t.overload
    def get_attributes(self, type: type[UserAttribute]) -> list[UserAttributeAdapter]:
        pass

    def get_attributes(self, type: type[AnyAttributeT]) -> list[AnyAttributeAdapterT]:  # type: ignore
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._o.get_attributes(self._c, type=type)
        ]

    def get_all_attributes(
        self,
    ) -> tuple[
        list[StaticAttributeAdapter],
        list[TaskAttributeAdapter],
        list[UserAttributeAdapter],
    ]:
        return tuple(
            [_get_attribute_adapter(attr, self) for attr in attrs]
            for attrs in self._o.get_attributes_grouped(self._c)
        )  # type: ignore

    @t.overload
    def get_attribute(self, type: EllipsisType, syn: str) -> AnyAttributeAdapterT:
        pass

    @t.overload
    def get_attribute(
        self, type: type[StaticAttribute], syn: str
    ) -> StaticAttributeAdapter:
        pass

    @t.overload
    def get_attribute(
        self, type: type[TaskAttribute], syn: str
    ) -> TaskAttributeAdapter:
        pass

    @t.overload
    def get_attribute(
        self, type: type[UserAttribute], syn: str
    ) -> UserAttributeAdapter:
        pass

    def get_attribute(
        self, type: type[AnyAttributeT] | EllipsisType, syn: str
    ) -> AnyAttributeAdapterT:
        attribute = _require_attribute_with_syn(
            self._c, text.NormStr(syn), type, self._o
        )

        return _get_attribute_adapter(attribute, self)

    @t.overload
    def create_attribute(
        self,
        type: type[TaskAttribute],
        name: str,
        slot_type: type[SlotTypeT],
        max_slot_count: int,
        aliases: str | None,
        collection: str | None,
    ) -> TaskAttributeAdapter:
        pass

    @t.overload
    def create_attribute(
        self,
        type: type[UserAttribute],
        name: str,
        slot_type: type[SlotTypeT],
        max_slot_count: int,
        aliases: str | None,
        collection: str | None,
    ) -> UserAttributeAdapter:
        pass

    def create_attribute(
        self,
        type: type[TaskAttribute | UserAttribute],
        name: str,
        slot_type: type[SlotTypeT],
        max_slot_count: int,
        aliases: str | None,
        collection: str | None,
    ) -> TaskAttributeAdapter | UserAttributeAdapter:
        real_aliases = _parse_aliases(aliases)

        if not collection:
            real_collection = ()
        else:
            real_collection = tuple(
                (text.RealStr(name), tuple(map(text.RealStr, aliases)))
                for name, aliases in parsing.mapping.parse(text.RealStr(collection))
            )

        try:
            attr_s = self._o.create_attribute(
                self._c,
                type,
                text.RealStr(name),
                real_aliases,
                slot_type,
                max_slot_count,
                collection=real_collection,
            )
        except (
            SynNotUniqueError,
            StructureCountLimitReachedError,
            TooManyAliasesError,
            TooLongSynError,
            SynsAlreadyTakenError,
            AttributeMinSlotsOrMaxSlotsOutOfRangeError,
            InvalidSlotStrError,
            CollectionEntryLimitReachedError,
            CollectionEntryAliasLimitReachedError,
            CollectionEntrySynNotUniqueError,
        ) as e:
            raise errors.create_feedback_from_structure_error(e)

        if isinstance(attr_s, TaskAttribute):
            return TaskAttributeAdapter(attr_s, self)

        return UserAttributeAdapter(attr_s, self)

    def delete_attribute(
        self, type: type[TaskAttribute | UserAttribute], syn: str
    ) -> None:
        attr = self.get_attribute(type, syn)

        # Yes, no exception should be raised
        self._o.delete_attribute(self._c, type, attr._o.id)

    def edit_attribute_name(
        self, type: type[AnyAttributeT], syn: str, name: str
    ) -> tuple[AnyAttributeAdapterT, text.RealStr]:
        name = text.RealStr(name)

        attribute = self.get_attribute(type, syn)

        self._o.edit_attribute_name(self._c, type, attribute._o.id, name)

        return (attribute, name)

    def edit_attribute_aliases(
        self, type: type[AnyAttributeT], syn: str, aliases: str
    ) -> tuple[AnyAttributeAdapterT, tuple[text.RealStr, ...]]:
        attribute = self.get_attribute(type, syn)

        new_aliases = parsing.value_sequence.parse(text.RealStr(aliases))

        try:
            new_aliases = self._o.edit_attribute_aliases(
                self._c, type, attribute._o.id, map(text.RealStr, new_aliases)
            )
        except (
            SynNotUniqueError,
            TooManyAliasesError,
            TooLongSynError,
            SynsAlreadyTakenError,
        ) as e:
            raise errors.create_feedback_from_structure_error(e)

        return (attribute, new_aliases)

    def edit_attribute_min_and_max_slot_count(
        self, type: type[TaskAttribute | UserAttribute], syn: str, min: int, max: int
    ) -> TaskAttributeAdapter | UserAttributeAdapter:
        attribute = self.get_attribute(type, syn)

        try:
            self._o.edit_attribute_min_max_slot_count(
                self._c, type, attribute._o.id, min, max
            )
        except (
            AttributeMinSlotsOrMaxSlotsOutOfRangeError,
            NotAllTasksFitMinAndMaxSlotCountChangesError,
        ) as e:
            raise errors.create_feedback_from_structure_error(e)

        return attribute

    def edit_attribute_collection(
        self, type: type[TaskAttribute | UserAttribute], syn: str, collection: str
    ) -> TaskAttributeAdapter | UserAttributeAdapter: ...

    def edit_attribute_position(
        self, syn_a: str, syn_b: str
    ) -> tuple[AnyAttributeAdapterT, AnyAttributeAdapterT]:
        attr_a = self.get_attribute(..., syn_a)
        attr_b = self.get_attribute(..., syn_b)

        self._o.edit_attribute_position(self._c, attr_a.id, attr_b.id)

        return attr_a, attr_b
