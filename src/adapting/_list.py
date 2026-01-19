import typing as t

from dc_utils.errors import FeedbackError
from ..dc_utils import errors
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
from utils import orm, text
from utils.expression_parsing.errors import BaseExpressionParsingError

from . import BaseStructureAdapter
from ._attribute import (
    AnyAttributeAdapterT,
    StaticAttributeAdapter,
    TaskAttributeAdapter,
    UserAttributeAdapter,
)
from ._task import TaskAdapter
from ._user import CommunityUserAdapter
from adapting import parsing

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter

from .parsing import factory


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


def _require_task_with_syn(c: orm.Cursor, norm_syn: text.NormStr, list: List) -> Task:
    task = list.get_single_task_by_syn(c, norm_syn)

    if task is None:
        raise errors.StructureNotFoundViaSyn(norm_syn, Task, False)

    return task


def _require_attribute_with_syn[T: AnyAttributeT](
    c: orm.Cursor, norm_syn: text.NormStr, attribute_type: type[T], list: List
) -> T:
    attribute = list.get_single_attribute_of_type_by_syn(c, attribute_type, norm_syn)

    if attribute is None:
        raise errors.StructureNotFoundViaSyn(norm_syn, TaskAttribute, False)

    return attribute


def _parse_aliases(aliases: str | None) -> tuple[text.RealStr, ...]:
    if not aliases:
        return ()

    try:
        aliases = factory.LIST_PARSER.parse(aliases)
    except BaseExpressionParsingError:
        raise FeedbackError(
            "Invalid Alias Format",
            t"The syntax used to specify the aliases {aliases:,} is invalid!",
            additional=t'The syntax should represent a list of strings, so `alias1 "alias2"` would be a valid for example.',
        )

    return tuple(map(text.RealStr, aliases))


class ListAdapter(BaseStructureAdapter[List]):
    community: CommunityAdapter

    @property
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
            TaskAdapter(task, self) for task in self._o.get_tasks_of_user(self._c, user._o.id)
        ]

    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_syn(self._c, text.NormStr(syn), self._o), self
        )

    def create_task(
        self, name: str, aliases: str | None, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        real_name = text.RealStr(name)

        real_aliases = _parse_aliases(aliases)
        attributes = {
            text.NormStr(k): v
            for k, v in self._o.get_attribute_alias_mappings_of_type(
                self._c, TaskAttribute
            ).items()
        }

        avm = {} if not task_attribute_value_mapping else parsing.avm.parse(
            self._c,
            text.RealStr(task_attribute_value_mapping), attributes
        )

        try:
            task_s = self._o.create_task(self._c, real_name, real_aliases, {k.id: v for k, v in avm.items()})
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTaken(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReached(e)
        except NotUniqueStringError as e:
            raise errors.SynNotUnique(e)
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRange(e)
        except CollectionEntryNotFoundError as e:
            raise errors.CollectionEntryNotFound(e)

        return TaskAdapter(task_s, self)

    def delete_task(self, syn: str) -> None:
        task = self.get_task(syn)
        self._o.delete_task(self._c, task._o.id)

    def edit_task_name(self, syn: str, name: str) -> None:
        task = self.get_task(syn)
        self._o.edit_task_name(self._c, task._o.id, text.RealStr(name))

    def edit_task_aliases(self, syn: str, aliases: str) -> None:
        real_aliases = tuple(map(text.RealStr, parsing.aliases.parse(text.RealStr(aliases))))

        task = self.get_task(syn)
        self._o.edit_task_aliases(self._c, task._o.id, real_aliases)

    def edit_task_attribute_value_mapping(
        self, syn: str, task_attribute_value_mapping: str | None
    ) -> None:
        task = self.get_task(syn)

        avm: dict[int, t.Sequence[text.RealStr]]

        if task_attribute_value_mapping:
            avm = parsing.avm.parse(
                self._c,
                text.RealStr(task_attribute_value_mapping),
                _get_norm_syn_to_attribute_s(TaskAttribute),
            )
        else:
            avm = {}

        self._o.edit_task_attribute_value_mapping(self._c, task._o.id, avm)

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
            for attr in self._o.get_attributes_of_type(self._c, type)
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
            for name, aliases in factory.LIST_OF_NAME_ALIASES_PARSER.parse(
                collection or "[]"
            )
        )

        try:
            attr_s = self._o.create_attribute(
                self._c,
                type,
                text.RealStr(name),
                real_aliases,
                slot_type,
                max_slots,
                collection=real_collection,
            )
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTaken(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReached(e)
        except NotUniqueStringError as e:
            raise errors.SynNotUnique(e)
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRange(e)
        except CollectionEntrySynNotUniqueError as e:
            raise errors.CollectionEntrySynNotUnique(e)
        except AttributeMinSlotsOrMaxSlotsOutOfRangeError as e:
            raise errors.AttributeMinSlotsOrMaxSlotsOutOfRange(e)

        if isinstance(attr_s, TaskAttribute):
            return TaskAttributeAdapter(attr_s, self)

        return UserAttributeAdapter(attr_s, self)  # type: ignore

    def delete_attribute(
        self, type: type[TaskAttribute | UserAttribute], syn: str
    ) -> None:
        attr = self.get_attribute(type, syn)
        self._o.delete_attribute(self._c, type, attr._o.id)

    def give_task_to_user(
        self,
        syn: str,
        community_user: CommunityUserAdapter,
        user_attribute_value_mapping: str | None = None,
    ) -> TaskAdapter:
        task_s = _require_task_with_syn(self._c, text.NormStr(syn), self._o)

        avm: dict[int, t.Sequence[text.RealStr]]

        if user_attribute_value_mapping:
            avm = factory.ATTRIBUTE_VALUE_MAPPING_PARSER.parse(
                syn, _get_norm_syn_to_attribute_s(UserAttribute)
            )
        else:
            avm = {}

        try:
            self._o.give_task_to_community_user(
                self._c, task_s.id, community_user._o.id, avm
            )
        except AttributeValueSlotCountOutOfRangeError as e:
            raise errors.AttributeValueSlotCountOutOfRange(e)
        except CollectionEntryNotFoundError as e:
            raise errors.CollectionEntryNotFound(e)
        except CommunityUserAlreadyHasTaskError:
            raise FeedbackError(
                "Task Already Given",
                t"The user {community_user:,} has already been given the task {task_s.name:,}!",
            )

        return TaskAdapter(task_s, self)

    def remove_task_from_user(
        self, syn: str, community_user: CommunityUserAdapter
    ) -> None:
        task_s = _require_task_with_syn(self._c, text.NormStr(syn), self._o)

        try:
            self._o.remove_task_from_community_user(
                self._c, task_s.id, community_user._o.id
            )
        except CommunityUserDoesNotHaveTaskError:
            raise FeedbackError(
                "Task Not Given Yet",
                t"The user {community_user:,} has not been given the task {task_s.name:,} yet, therefore nothing changed!",
            )
