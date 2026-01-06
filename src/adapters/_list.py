import itertools
import typing as t

from discord_.errors import FeedbackError
from structures import attribute
from structures.attribute import (
    AnyAttributeT,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.slot_str import SlotTypeT
from structures.errors import (
    AttributeMinSlotsOrMaxSlotsOutOfRangeError,
    AttributeValueSlotCountOutOfRangeError,
    CollectionEntryNotFoundError,
    CollectionEntrySynNotUniqueError,
    CommunityUserAlreadyHasTaskError,
    CommunityUserDoesNotHaveTaskError,
    NotUniqueStringError,
    StructureCountLimitReachedError,
    SynsAlreadyTakenError,
)
from structures.list import List
from structures.task import Task
from utils import text
from utils.expression_parsing.errors import BaseExpressionParsingError

from . import BaseStructureAdapter, errors
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

from . import parsing


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


def _require_task_with_syn(norm_syn: text.NormStr, list: List) -> Task:
    task = list.get_single_task_by_syn(norm_syn)

    if task is None:
        raise errors.StructureNotFoundViaSynFeedbackError(norm_syn, Task, False)

    return task


def _require_attribute_with_syn[T: AnyAttributeT](
    norm_syn: text.NormStr, attribute_type: type[T], list: List
) -> T:
    attribute = list.get_single_attribute_by_syn(attribute_type, norm_syn)

    if attribute is None:
        raise errors.StructureNotFoundViaSynFeedbackError(
            norm_syn, TaskAttribute, False
        )

    return attribute


def _parse_aliases(aliases: str | None) -> tuple[text.RealStr, ...]:
    if not aliases:
        return ()

    try:
        aliases = parsing.LIST_PARSER.parse(aliases)
    except BaseExpressionParsingError:
        raise FeedbackError(
            "Invalid Alias Format",
            t"The syntax used to specify the aliases `{aliases}` is invalid!",
            additional=t'The syntax should represent a list of strings, so `alias1 "alias2"` would be a valid for example.',
        )

    return tuple(map(text.RealStr, aliases))


def _get_norm_syn_to_attribute_s[T: AnyAttributeT](type: type[T], *types: type[T]) -> dict[text.NormStr, T]:
    syn_to_attr: dict[text.NormStr, T] = {}

    for attr_type in (type, *types):
        for alias, attr in list_obj._s.get_attribute_alias_mapping(
            attr_type
        ).items():
            syn_to_attr[NormStr(alias)] = attr

        syn_to_attr |= {attr.norm_name: attr for attr in ATTRS_SORTED}

    return syn_to_attr

class ListAdapter(BaseStructureAdapter[List]):
    community: CommunityAdapter

    @property
    def name(self) -> text.RealStr:
        return self._s.real_name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [TaskAdapter(task, self) for task in self._s.get_tasks()]

    def get_tasks_of_user(self, user: CommunityUserAdapter) -> list[TaskAdapter]:
        return [
            TaskAdapter(task, self) for task in self._s.get_tasks_of_user(user._s.id)
        ]

    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(_require_task_with_syn(text.NormStr(syn), self._s), self)

    def create_task(
        self, name: str, aliases: str | None, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        real_name = text.RealStr(name)

        real_aliases = _parse_aliases(aliases)
        attributes = {
            text.NormStr(k): v
            for k, v in self._s.get_attribute_alias_mapping(TaskAttribute).items()
        }

        avm = parsing.ATTRIBUTE_VALUE_MAPPING_PARSER.parse(
            task_attribute_value_mapping, attributes
        )

        try:
            task_s = self._s.create_task(real_name, real_aliases, avm)
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTakenFeedbackError(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReachedFeedbackError(e)
        except NotUniqueStringError as e:
            raise errors.SynNotUniqueFeedbackError(e)
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRangeFeedbackError(e)
        except CollectionEntryNotFoundError as e:
            raise errors.CollectionEntryNotFoundFeedbackError(e)

        return TaskAdapter(task_s, self)

    def delete_task(self, syn: str) -> None:
        task = self.get_task(syn)
        self._s.delete_task(task._s.id)

    def edit_task_name(self, syn: str, name: str) -> None:
        task = self.get_task(syn)
        self._s.edit_task_name(task._s.id, text.RealStr(name))

    def edit_task_aliases(self, syn: str, aliases: str) -> None:
        real_aliases = tuple(map(text.RealStr, parsing.LIST_PARSER.parse(aliases)))

        task = self.get_task(syn)
        self._s.edit_task_aliases(task._s.id, real_aliases)

    def edit_task_attribute_value_mapping(
        self, syn: str, task_attribute_value_mapping: str | None
    ) -> None:
        task = self.get_task(syn)

        avm: dict[int, t.Sequence[text.RealStr]] 

        if task_attribute_value_mapping:
            avm = parsing.ATTRIBUTE_VALUE_MAPPING_PARSER.parse(task_attribute_value_mapping, _get_norm_syn_to_attribute_s(TaskAttribute))
        else:
            avm = {}

        self._s.edit_task_attribute_value_mapping(task._s.id, avm)

    # --- Attribute ---

    def get_attributes_flat(self) -> list[AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._s.get_all_attributes_flat()
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
            _get_attribute_adapter(attr, self) for attr in self._s.get_attributes(type)
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
            for attrs in self._s.get_all_attributes()
        )  # type: ignore

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
        self, type: type[AnyAttributeT], syn: str
    ) -> AnyAttributeAdapterT:
        attribute = _require_attribute_with_syn(text.NormStr(syn), type, self._s)

        return _get_attribute_adapter(attribute, self)

    @t.overload
    def create_attribute(
        self,
        type: type[TaskAttribute],
        name: str,
        slot_type: type[SlotTypeT],
        max_slots: int,
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
        max_slots: int,
        aliases: str | None,
        collection: str | None,
    ) -> UserAttributeAdapter:
        pass

    def create_attribute(
        self,
        type: type[TaskAttribute | UserAttribute],
        name: str,
        slot_type: type[SlotTypeT],
        max_slots: int,
        aliases: str | None,
        collection: str | None,
    ) -> TaskAttributeAdapter | UserAttributeAdapter:
        real_aliases = _parse_aliases(aliases)

        real_collection = tuple(
            (text.RealStr(name), tuple(map(text.RealStr, aliases)))
            for name, aliases in parsing.LIST_OF_NAME_ALIASES_PARSER.parse(
                collection or "[]"
            )
        )

        try:
            attr_s = self._s.create_attribute(
                type,
                text.RealStr(name),
                real_aliases,
                slot_type,
                max_slots,
                collection=real_collection,
            )
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTakenFeedbackError(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReachedFeedbackError(e)
        except NotUniqueStringError as e:
            raise errors.SynNotUniqueFeedbackError(e)
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRangeFeedbackError(e)
        except CollectionEntrySynNotUniqueError as e:
            raise errors.CollectionEntrySynNotUniqueFeedbackError(e)
        except AttributeMinSlotsOrMaxSlotsOutOfRangeError as e:
            raise errors.AttributeMinSlotsOrMaxSlotsOutOfRangeFeedbackError(e)

        if isinstance(attr_s, TaskAttribute):
            return TaskAttributeAdapter(attr_s, self)

        return UserAttributeAdapter(attr_s, self)  # type: ignore

    def delete_attribute(
        self, type: type[TaskAttribute | UserAttribute], syn: str
    ) -> None:
        attr = self.get_attribute(type, syn)
        self._s.delete_attribute(type, attr._s.id)

    def give_task_to_user(
        self,
        syn: str,
        community_user: CommunityUserAdapter,
        user_attribute_value_mapping: str | None = None,
    ) -> TaskAdapter:
        task_s = _require_task_with_syn(text.NormStr(syn), self._s)

        avm: dict[int, t.Sequence[text.RealStr]]

        if user_attribute_value_mapping:
            avm = parsing.ATTRIBUTE_VALUE_MAPPING_PARSER.parse(syn, _get_norm_syn_to_attribute_s(UserAttribute))
        else:
            avm = {}

        try:
            self._s.give_task_to_community_user(task_s.id, community_user._s.id, avm)
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRangeFeedbackError(e)
        except CollectionEntryNotFoundError as e:
            raise errors.CollectionEntryNotFoundFeedbackError(e)
        except CommunityUserAlreadyHasTaskError:
            raise FeedbackError(
                "Task Already Given",
                t"The user `{community_user}` has already been given the task `{task_s.name}`!",
            )

        return TaskAdapter(task_s, self)

    def remove_task_from_user(
        self, syn: str, community_user: CommunityUserAdapter
    ) -> None:
        task_s = _require_task_with_syn(text.NormStr(syn), self._s)

        try:
            self._s.remove_task_from_community_user(task_s.id, community_user._s.id)
        except CommunityUserDoesNotHaveTaskError:
            raise FeedbackError(
                "Task Not Given Yet",
                t"The user `{community_user}` has not been given the task `{task_s.name}` yet, therefore nothing changed!",
            )
        