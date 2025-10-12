import typing as t

from . import parsers
from ..structures import attribute
from ..structures.attribute import BaseAttribute
from ..structures.attribute.static_attribute import StaticAttribute
from ..structures.attribute.task_attribute import TaskAttribute
from ..structures.attribute.user_attribute import UserAttribute
from ..structures.list import List
from ..structures.task import Task
from ..utils import argparsing, text
from . import BaseAdapter, errors
from ._attribute import AnyAttributeAdapterT
from ._attribute.static_attribute import StaticAttributeAdapter
from ._attribute.task_attribute import TaskAttributeAdapter
from ._attribute.user_attribute import UserAttributeAdapter
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

    assert_never(attribute)


def _require_task_with_syn(norm_syn: text.NormStr, list: List) -> Task:
    task = list.get_task_by_syn(norm_syn)

    if task is None:
        raise errors.StructureNotFoundViaSynFeedbackError(norm_syn, Task)

    return task


def _require_attribute_with_syn[T: BaseAttribute](
    norm_syn: text.NormStr, attribute_type: type[T], list: List
) -> T:
    attribute = list.get_attribute_by_syn(attribute_type, norm_syn)

    if attribute is None:
        raise errors.StructureNotFoundViaSynFeedbackError(norm_syn, TaskAttribute)

    return attribute


class ListAdapter(BaseAdapter):
    _list: List

    community: CommunityAdapter

    @property
    def name(self) -> text.RealStr:
        return self._list.real_name

    # --- Task ---

    def get_tasks(self) -> list[TaskAdapter]:
        return [TaskAdapter(task, self) for task in self._list.get_tasks()]

    def get_task(self, syn: str) -> TaskAdapter:
        return TaskAdapter(
            _require_task_with_syn(text.raw_to_norm(syn), self._list), self
        )

    def create_task(
        self, name: str, aliases: str, task_attribute_value_mapping: str | None
    ) -> TaskAdapter:
        aliases_set = frozenset()

        avm = {
            self.get_attribute(k).id: v
            for k, v in _parse_kwargs(task_attribute_value_mapping or "").items()
        }

        return TaskAdapter(self._list.create_task(name, aliases_set, avm), self)

    def delete_task(self, syn: str) -> None:
        task = self.get_task(syn)
        self._list.delete_task(task._task.id)

    def edit_task_name(self, syn: str, new_name: str) -> None:
        task = self.get_task(syn)
        self._list.edit_task_name(task._task.id, new_name)

    def edit_task_aliases(self, syn: str, new_aliases: str) -> None:
        aliases_set = frozenset(_parse_args(new_aliases))

        task = self.get_task(syn)
        self._list.edit_task_aliases(task._task.id, aliases_set)

    def edit_task_attribute_value_mapping(
        self, syn: str, new_task_attribute_value_mapping: str
    ) -> None:
        task = self.get_task(syn)

        avm = {
            self.get_attribute(k).id: v
            for k, v in _parse_kwargs(new_task_attribute_value_mapping).items()
        }

        self._list.edit_task_attribute_value_mapping(task._task.id, avm)

    # --- Attribute ---

    def get_attributes(self) -> list[AnyAttributeAdapterT]:
        return [
            _get_attribute_adapter(attr, self)
            for attr in self._list.get_all_attributes_flat()
        ]

    def get_attribute(self, syn: str) -> AnyAttributeAdapterT:
        attribute = _require_attribute_with_syn(text.raw_to_norm(syn), self._list)

        return _get_attribute_adapter(attribute, self)

    def get_task_attribute(self, syn: str) -> TaskAttributeAdapter:
        task_attribute = _require_task_attribute_with_syn(
            text.raw_to_norm(syn), self._list
        )
        return TaskAttributeAdapter(task_attribute, self)
