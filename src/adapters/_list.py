import collections
import typing as t

from adapters import _parsers
from discord_.errors import FeedbackError
from structures import attribute
from structures.attribute import (
    AnyAttributeT,
    BaseAttribute,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from structures.list import List
from structures.task import Task
from utils import text

from . import BaseAdapter, errors
from ._attribute import (
    AnyAttributeAdapterT,
    StaticAttributeAdapter,
    TaskAttributeAdapter,
    UserAttributeAdapter,
)
from ._task import TaskAdapter

if t.TYPE_CHECKING:
    from adapters._community import CommunityAdapter


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
        for k, v in _parsers.MAPPING_PARSER.parse(raw_avm or "").items()
    }

    found_attrs = list.get_attributes_by_syn(attribute_type, *avm).values()

    for k, count in collections.Counter(found_attrs).items():
        if count > 1:
            raise FeedbackError(
                "Attributes Not Unique",
                t"The attribute `{k.name}` was specified multiple times in the attribute value mapping, probably by using different aliases!",
            )

    return {attr.id: avm[attr.norm_name] for attr in found_attrs}


class ListAdapter(BaseAdapter[List]):
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
        self, name: str, aliases: str, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        real_name = text.RealStr(name)
        real_aliases = tuple(map(text.RealStr, _parsers.LIST_PARSER.parse(aliases)))

        avm = _validate_and_convert_attribute_value_mapping(
            task_attribute_value_mapping, TaskAttribute, self._s
        )

        return TaskAdapter(self._s.create_task(real_name, real_aliases, avm), self)

    def delete_task(self, syn: str) -> None:
        task = self.get_task(syn)
        self._s.delete_task(task._s.id)

    def edit_task_name(self, syn: str, name: str) -> None:
        task = self.get_task(syn)
        self._s.edit_task_name(task._s.id, text.RealStr(name))

    def edit_task_aliases(self, syn: str, aliases: str) -> None:
        real_aliases = tuple(map(text.RealStr, _parsers.LIST_PARSER.parse(aliases)))

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

    def get_attributes(self) -> list[AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._s.get_all_attributes_flat()
        ]

    @t.overload
    def get_attribute(
        self, syn: str, type: type[StaticAttribute]
    ) -> StaticAttributeAdapter:
        pass

    @t.overload
    def get_attribute(
        self, syn: str, type: type[TaskAttribute]
    ) -> TaskAttributeAdapter:
        pass

    @t.overload
    def get_attribute(
        self, syn: str, type: type[UserAttribute]
    ) -> UserAttributeAdapter:
        pass

    def get_attribute(
        self, syn: str, type: type[AnyAttributeT]
    ) -> AnyAttributeAdapterT:
        attribute = _require_attribute_with_syn(text.NormStr(syn), type, self._s)

        return _get_attribute_adapter(attribute, self)
