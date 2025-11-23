import collections
import typing as t

from discord_.errors import FeedbackError
from structures import attribute
from structures.attribute import (
    AnyAttributeT,
    BaseAttribute,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.attribute.slot_str import SlotTypeT
from structures.errors import AttributeMinSlotsOrMaxSlotsOutOfRangeError, AttributeValueSlotCountOutOfRangeError, CollectionEntrySynNotUniqueError, CollectionEntryNotFoundError, NotUniqueStringError, StructureCountLimitReachedError, SynsAlreadyTakenError
from structures.list import List
from structures.task import Task
from utils import text
from utils.expression_parsing.errors import BaseExpressionParsingError

from . import BaseAdapter, BaseStructureAdapter, _parsing, errors
from ._attribute import (
    AnyAttributeAdapterT,
    StaticAttributeAdapter,
    TaskAttributeAdapter,
    UserAttributeAdapter,
)
from ._task import TaskAdapter

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter


@t.overload
def _get_attribute_adapter(
    attribute: StaticAttribute, list: "ListAdapter"
) -> StaticAttributeAdapter:
    pass


@t.overload
def _get_attribute_adapter(
    attribute: TaskAttribute, list: "ListAdapter"
) -> TaskAttributeAdapter:
    pass


@t.overload
def _get_attribute_adapter(
    attribute: UserAttribute, list: "ListAdapter"
) -> UserAttributeAdapter:
    pass


def _get_attribute_adapter(
    attribute: attribute.AnyAttributeT, list: "ListAdapter"
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


def _validate_and_convert_attribute_value_mapping[T: BaseAttribute](
    raw_avm: str | None, attribute_type: type[T], list: List
) -> dict[int, t.Sequence[text.RealStr]]:
    avm: dict[text.NormStr, tuple[text.RealStr, ...]] = {
        text.NormStr(k): tuple(map(text.RealStr, v))
        for k, v in _parsing.MAPPING_PARSER.parse(raw_avm or "").items()
    }

    found_attrs = list.get_attributes_by_syn(attribute_type, *avm).values()

    for k, count in collections.Counter(found_attrs).items():
        if count > 1:
            raise FeedbackError(
                "Attributes Not Unique",
                t"The attribute `{k.name}` was specified multiple times in the attribute value mapping, probably by using different aliases!",
            )

    return {attr.id: avm[attr.norm_name] for attr in found_attrs}


def _parse_aliases(aliases: str | None) -> tuple[text.RealStr, ...]:
    try:
        return tuple(map(text.RealStr, _parsing.LIST_PARSER.parse(aliases or "[]")))
    except BaseExpressionParsingError:
        raise FeedbackError(
            "Invalid Alias Format",
            t"The syntax used to specify the aliases `{aliases}` is invalid!",
            additional=t'The syntax should represent a list of strings, so `["alias1", "alias2"]` would be a valid for example.'
        )
    
class ListAdapter(BaseStructureAdapter[List]):
    community: CommunityAdapter

    @property
    def name(self) -> text.RealStr:
        return self._s.real_name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [TaskAdapter(task, self) for task in self._s.get_tasks()]

    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(_require_task_with_syn(text.NormStr(syn), self._s), self)

    def create_task(
        self, name: str, aliases: str | None, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        real_name = text.RealStr(name)
        
        real_aliases = _parse_aliases(aliases)

        avm = _validate_and_convert_attribute_value_mapping(
            task_attribute_value_mapping, TaskAttribute, self._s
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
        except CollectionEntrySynNotUniqueError as e:
            raise errors.CollectionEntrySynNotUniqueFeedbackError(e)

        return TaskAdapter(task_s, self)

    def delete_task(self, syn: str) -> None:
        task = self.get_task(syn)
        self._s.delete_task(task._s.id)

    def edit_task_name(self, syn: str, name: str) -> None:
        task = self.get_task(syn)
        self._s.edit_task_name(task._s.id, text.RealStr(name))

    def edit_task_aliases(self, syn: str, aliases: str) -> None:
        real_aliases = tuple(map(text.RealStr, _parsing.LIST_PARSER.parse(aliases)))

        task = self.get_task(syn)
        self._s.edit_task_aliases(task._s.id, real_aliases)

    def edit_task_attribute_value_mapping(
        self, syn: str, task_attribute_value_mapping: str | None
    ) -> None:
        task = self.get_task(syn)

        avm = _validate_and_convert_attribute_value_mapping(
            task_attribute_value_mapping, TaskAttribute, self._s
        )

        self._s.edit_task_attribute_value_mapping(task._s.id, avm)

    # --- Attribute ---

    def get_attributes_flat(self) -> list[AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._s.get_all_attributes_flat()
        ]

    def get_attributes(
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
            for name, aliases in _parsing.LIST_OF_NAME_ALIASES_PARSER.parse(
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
