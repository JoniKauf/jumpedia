import itertools
import typing as t
from types import MappingProxyType

from requests import delete

from src.utils import orm

from ..utils.text import NormStr, RealStr
from . import BaseStructure, errors
from .attribute import (
    ALL_ATTRIBUTE_TYPES,
    AnyAttributeT,
    BaseAttribute,
    BaseNonStaticAttribute,
    StaticAttribute,
    TaskAttribute,
    UserAttribute,
)
from .attribute.slot_type import SlotStr, SlotType
from .jumpedia import db
from .task import Task
from .task.attribute_value_mapping import AttributeValueMapping, AvmT
from .user import CommunityUser, JumpediaUser

if t.TYPE_CHECKING:
    from .community import Community


STATIC_ATTRIBUTE_KIND_OF_ID: t.Final = 1
STATIC_ATTRIBUTE_KIND_OF_NAME: t.Final = 2
STATIC_ATTRIBUTE_KIND_OF_ALIASES: t.Final = 3

type KindT = t.Literal[1, 2, 3]
KINDS: tuple[t.Literal[1], t.Literal[2], t.Literal[3]] = t.get_args(KindT.__value__)

type _RawAvmT = dict[int, list[SlotStr]]


class List(BaseStructure):
    community: "Community"
    id: int
    real_name: RealStr
    norm_name: NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.community.identity)

    @property
    def name(self) -> str:
        return self.real_name

    @property
    def connector(self) -> orm.Connector:
        return self.community.connector

    # --- All Attributes ---

    def get_attributes[T: BaseAttribute](self, type: type[T]) -> list[T]:
        return [
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute)
        ]

    def get_attribute_by_id[T: BaseAttribute](self, type: type[T], id: int) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(
            table_type, (table_type.id, orm.Operator.EQ, id)
        )
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_name[T: BaseAttribute](
        self, type: type[T], norm_name: NormStr
    ) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(
            table_type, (table_type.norm_name, orm.Operator.EQ, norm_name)
        )
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_alias[T: BaseAttribute](
        self, type: type[T], norm_alias: NormStr
    ) -> T | None:
        AttributeAliasTable: t.Any = type.tables.attribute_alias

        with self.connector.cursor() as c:
            row = c.fetch_one(
                AttributeAliasTable.select(
                    "*",
                ).where(
                    (AttributeAliasTable.list_id, orm.Operator.EQ, self.id),
                    (AttributeAliasTable.norm_alias, orm.Operator.EQ, norm_alias),
                )
            )

        if row is None:
            return None

        return self.get_attribute_by_id(type, row.attribute_id)

    def get_attribute_by_syn[T: BaseAttribute](
        self, type: type[T], norm_syn: NormStr
    ) -> T | None:
        return self.get_attribute_by_name(
            type, norm_syn
        ) or self.get_attribute_by_alias(type, norm_syn)

    def get_all_attributes_flat(self) -> tuple[AnyAttributeT, ...]:
        return tuple(
            attr for type in ALL_ATTRIBUTE_TYPES for attr in self.get_attributes(type)
        )

    def get_all_attributes(
        self,
    ) -> tuple[list[StaticAttribute], list[TaskAttribute], list[UserAttribute]]:
        return tuple(
            self.get_attributes(type) for type in ALL_ATTRIBUTE_TYPES
        )  # type: ignore

    def get_any_attribute_by_id(self, id: int) -> AnyAttributeT | None:
        for type in ALL_ATTRIBUTE_TYPES:
            attr = self.get_attribute_by_id(type, id)

            if attr is not None:
                return attr

    def get_any_attribute_by_name(self, norm_name: NormStr) -> AnyAttributeT | None:
        for type in ALL_ATTRIBUTE_TYPES:
            attr = self.get_attribute_by_name(type, norm_name)

            if attr is not None:
                return attr

    def get_any_attribute_by_alias(self, norm_alias: NormStr) -> AnyAttributeT | None:
        for type in ALL_ATTRIBUTE_TYPES:
            attr = self.get_attribute_by_alias(type, norm_alias)

            if attr is not None:
                return attr

    def get_any_attribute_by_syn(self, norm_syn: NormStr) -> AnyAttributeT | None:
        for type in ALL_ATTRIBUTE_TYPES:
            attr = self.get_attribute_by_syn(type, norm_syn)

            if attr is not None:
                return attr

    def get_static_attribute_by_kind(self, kind: KindT) -> StaticAttribute:
        if kind not in KINDS:
            raise ValueError(f"Kind {kind} is not valid")

        StaticAttributeTable = db.StaticAttribute

        with self.connector.cursor() as c:
            row = c.fetch_one(
                StaticAttributeTable.select("*").where(
                    (StaticAttributeTable.list_id, orm.Operator.EQ, self.id),
                    (StaticAttributeTable.kind, orm.Operator.EQ, kind),
                )
            )

        if row is None:
            raise RuntimeError(
                f"Critical error! Could not find static attribute with kind {kind}"
            )

        return self._attribute_row_to_obj(StaticAttribute, row)

    @t.overload
    def create_attribute[T: StaticAttribute](
        self,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: SlotType,
        max_slots: int,
        *,
        min_slots: int,
        kind: KindT,
    ) -> T:
        pass

    @t.overload
    def create_attribute[T: BaseNonStaticAttribute](
        self,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: SlotType,
        max_slots: int,
        *,
        collection: t.Sequence[tuple[RealStr, t.Iterable[RealStr]]] = (),
    ) -> T:
        pass

    def create_attribute[T: BaseAttribute](
        self,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: SlotType,
        max_slots: int,
        *,
        min_slots: int = 0,
        kind: KindT | None = None,
        collection: t.Sequence[tuple[RealStr, t.Iterable[RealStr]]] = (),
    ) -> T:  # Higher kinded attributes not supported yet, otherwise T[TSlot]
        from . import errors

        assert (min_slots or kind) != issubclass(
            type, BaseNonStaticAttribute
        ), "Typing not followed on attribute creation #1"
        assert (not collection) != issubclass(
            type, BaseNonStaticAttribute
        ), "Typing not followed on attribute creation #2"

        (real_name, *real_aliases), (norm_name, *norm_aliases) = (
            NormStr.unique_reals_and_norms((real_name, *real_aliases))
        )

        with self.locked:
            attrs = self.get_all_attributes_flat()

            if len(attrs) >= self.community.limits.list_attribute_count_max:
                raise errors.LimitOfStructuresReachedError(
                    self.community.limits.list_attribute_count_max, type
                )

            for syn in (norm_name, *norm_aliases):
                if len(syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                    raise errors.SynTooLongError(
                        len(syn),
                        self.community.jumpedia.limits.attribute_syn_length_max,
                        type,
                    )

                attr_ = self.get_any_attribute_by_syn(syn)
                if attr_ is not None:
                    raise errors.SynAlreadyTakenError(syn, attr_)

            if not (
                min_slots
                <= max_slots
                <= self.community.jumpedia.limits.attribute_task_value_slot_count_max
            ):
                raise errors.ElementCountOutOfRangeError(
                    min_slots,
                    self.community.jumpedia.limits.attribute_task_value_slot_count_max,
                    type,
                )

            position = max(attr.position for attr in attrs) + 1 if attrs else 1

            AttributeTable = t.cast(
                type[db.AbstractAttributeTable], type.tables.attribute
            )

            with self.connector.cursor() as c:
                additional: tuple[orm.ColumnBind[t.Any, t.Any], ...] = ()

                if issubclass(AttributeTable, db.StaticAttribute):
                    additional = (AttributeTable.kind.bind(kind),)

                execute_data = c.execute(
                    AttributeTable.insert(
                        AttributeTable.list_id.bind(self.id),
                        AttributeTable.norm_name.bind(norm_name),
                        AttributeTable.real_name.bind(real_name),
                        AttributeTable.slot_type.bind(slot_type.id),
                        AttributeTable.position.bind(position),
                        AttributeTable.min_slots.bind(min_slots),
                        AttributeTable.max_slots.bind(max_slots),
                        *additional,
                    ),
                    get_last_generated_id=True,
                )

                attribute_id = execute_data.last_generated_id
                assert attribute_id is not None

                self._insert_attribute_aliases(
                    c, type, attribute_id, real_aliases, norm_aliases
                )

                attribute = type(
                    list=self,
                    id=attribute_id,
                    real_name=real_name,
                    norm_name=norm_name,
                    slot_type=slot_type,
                    position=position,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    kind=kind,
                )

                if collection:
                    assert isinstance(
                        attribute, BaseNonStaticAttribute
                    ), "Typing not followed on attribute creation #3"
                    attribute.set_collection(collection)

                return attribute

    def delete_attribute(self, type: type[BaseAttribute], id: int) -> None:
        from . import errors

        AttributeTable = t.cast(type[db.AbstractAttributeTable], type.tables.attribute)

        with self.locked, self.connector.cursor() as c:
            execute_data = c.execute(
                AttributeTable.delete().where(
                    (AttributeTable.list_id, orm.Operator.EQ, self.id),
                    (AttributeTable.id, orm.Operator.EQ, id),
                ),
                get_affected_row_count=True,
            )

        if execute_data.affected_row_count < 1:
            raise errors.StructureNotFoundError(type)

    def edit_attribute_name(
        self, type: type[BaseAttribute], id: int, real_name: RealStr
    ) -> None:
        norm_name = NormStr(real_name)

        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise errors.StructureNotFoundError(type)

            if real_name == attribute.real_name:
                return

            self._validate_attribute_syns(norm_name, allowed_attributes={attribute})

            AttributeTable = t.cast(
                type[db.AbstractAttributeTable], type.tables.attribute
            )

            with self.connector.cursor() as c:
                execute_data = c.execute(
                    AttributeTable.update(
                        AttributeTable.norm_name.set(norm_name),
                        AttributeTable.real_name.set(real_name),
                    ).where(
                        (AttributeTable.list_id, orm.Operator.EQ, self.id),
                        (AttributeTable.id, orm.Operator.EQ, attribute.id),
                    ),
                    get_affected_row_count=True,
                )

                assert execute_data.affected_row_count == 1

                # If the new name is an alias, remove the alias
                if norm_name in attribute.get_norm_aliases():
                    AttributeAliasTable = attribute.__class__.tables.attribute_alias

                    c.execute(
                        AttributeAliasTable.delete().where(
                            (AttributeAliasTable.list_id, orm.Operator.EQ, self.id),
                            (
                                AttributeAliasTable.attribute_id,
                                orm.Operator.EQ,
                                attribute.id,
                            ),
                            (
                                AttributeAliasTable.norm_alias,
                                orm.Operator.EQ,
                                norm_name,
                            ),
                        )
                    )

    def edit_attribute_aliases(
        self, type: type[BaseAttribute], id: int, aliases: t.Iterable[RealStr]
    ) -> None:
        (*real_aliases,), (*norm_aliases,) = NormStr.unique_reals_and_norms(aliases)

        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise errors.StructureNotFoundError(type)

            self._validate_attribute_syns(
                norm_aliases={*norm_aliases}, allowed_attributes={attribute}
            )

            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(attribute.norm_name)
            except ValueError:
                pass
            else:
                real_aliases.pop(idx)
                norm_aliases.pop(idx)

            AttributeAliasTable = type.tables.attribute_alias

            with self.connector.cursor() as c:
                # Delete all aliases
                c.execute(
                    AttributeAliasTable.delete().where(
                        (AttributeAliasTable.list_id, orm.Operator.EQ, self.id),
                        (
                            AttributeAliasTable.attribute_id,
                            orm.Operator.EQ,
                            attribute.id,
                        ),
                    )
                )

                self._insert_attribute_aliases(
                    c, type, attribute.id, real_aliases, norm_aliases
                )

    def _fetch_from_attribute_table[T: db.AnyAttributeTable](
        self, table_type: type[T], *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[T]:
        with self.connector.cursor() as c:
            query = table_type.select("*").where(
                (table_type.list_id, orm.Operator.EQ, self.id), *where
            )

            if issubclass(table_type, db.StaticAttribute):
                query = query.order_by((table_type.kind, orm.Order.ASC))  # type: ignore

            return c.fetch_all(query)  # type: ignore

    def _attribute_row_to_obj[T: BaseAttribute](
        self, type: type[T], row: db.AnyAttributeTable
    ) -> T:
        if issubclass(type, StaticAttribute):
            assert isinstance(row, db.StaticAttribute)

            return type(
                list=self,
                id=row.id,
                real_name=row.real_name,
                norm_name=row.norm_name,
                slot_type=SlotType.get_by_id(row.slot_type),
                position=row.position,
                min_slots=row.min_slots,
                max_slots=row.max_slots,
                kind=row.kind,
            )

        return type(
            list=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name,
            slot_type=SlotType.get_by_id(row.slot_type),
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots,
        )

    def _cook_raw_task_attribute_value_mapping(
        self, task_attribute_value_mapping: t.Mapping[int, t.Sequence[SlotStr]]
    ) -> dict[TaskAttribute, list[SlotStr]]:
        id_to_attr = {attr.id: attr for attr in self.get_attributes(TaskAttribute)}

        # Check if all required attributes are given
        for attr in id_to_attr.values():
            if attr.required and attr.id not in task_attribute_value_mapping:
                raise feedbacks.temp(
                    f"Attribute {attr} is required (min >= 1 slots) but it received no values"
                )

        if not task_attribute_value_mapping:
            return {}

        attribute_value_mapping: dict[TaskAttribute, list[SlotStr]] = {}

        # Convert ids to attributes and validate value
        for attr_id, v in task_attribute_value_mapping.items():
            if attr_id not in id_to_attr:
                raise errors.StructureNotFoundError(TaskAttribute)

            attr = id_to_attr[attr_id]
            val = attr.raw_to_value(v)

            attribute_value_mapping[attr] = val

        return attribute_value_mapping

    def _insert_attribute_aliases(
        self,
        c: orm.Cursor,
        type: type[BaseAttribute],
        attribute_id: int,
        real_aliases: t.Sequence[RealStr],
        norm_aliases: t.Sequence[NormStr],
    ) -> None:
        if not norm_aliases:
            return

        AttributeAliasTable: type[db.AllAttributeAliasTable] = type.tables.attribute_alias  # type: ignore
        count = len(norm_aliases)

        c.execute(
            AttributeAliasTable.insert(
                AttributeAliasTable.attribute_id.bind(
                    *itertools.repeat(attribute_id, count)
                ),
                AttributeAliasTable.list_id.bind(*itertools.repeat(self.id, count)),
                AttributeAliasTable.norm_alias.bind(*norm_aliases),
                AttributeAliasTable.real_alias.bind(*real_aliases),
            )
        )

    # --- Tasks ---

    def get_tasks(self, *where: tuple[t.Any, orm.Operator, t.Any]) -> list[Task]:
        return [
            self._task_row_to_obj(data) for data in self._fetch_tasks_from_table(*where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table((db.Task.id, orm.Operator.EQ, id))
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_name(self, norm_name: NormStr) -> Task | None:
        data = self._fetch_tasks_from_table(
            (db.Task.norm_name, orm.Operator.EQ, norm_name)
        )
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_alias(self, norm_alias: NormStr) -> Task | None:
        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.TaskAlias.select(db.TaskAlias.task_id).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.id),
                    (db.TaskAlias.norm_alias, orm.Operator.EQ, norm_alias),
                )
            )

        if row is None:
            return None

        return self.get_task_by_id(row.task_id)

    def get_task_by_syn(self, norm_syn: NormStr) -> Task | None:
        return self.get_task_by_name(norm_syn) or self.get_task_by_alias(norm_syn)

    def _get_attributes_and_data_for_non_static_attribute_value_mapping[
        T: BaseNonStaticAttribute
    ](
        self, c: orm.Cursor, type: type[T], community_user_id: int
    ) -> tuple[dict[tuple[int, int], T], dict[int, dict[int, _RawAvmT]]]:
        task_attrs = self.get_attributes(type)
        id_to_attr = {(attr.type_id, attr.id): attr for attr in task_attrs}
        del task_attrs

        AttributeTaskValueTable = t.cast(
            type[db.AbstractAttributeTaskValueTable], type.tables.attribute_task_value
        )

        additional_where: tuple[tuple[t.Any, orm.Operator, t.Any], ...] = ()

        if issubclass(AttributeTaskValueTable, db.UserAttributeTaskValue):
            additional_where = (
                (AttributeTaskValueTable.user_id, orm.Operator.EQ, community_user_id),
            )

        rows = c.fetch_all(
            AttributeTaskValueTable.select(
                AttributeTaskValueTable.task_id,
                AttributeTaskValueTable.attribute_id,
                AttributeTaskValueTable.slot_slot,
                AttributeTaskValueTable.index,
            )
            .where(
                (AttributeTaskValueTable.list_id, orm.Operator.EQ, self.id),
                *additional_where,
            )
            .order_by(
                (AttributeTaskValueTable.task_id, orm.Order.ASC),
                (AttributeTaskValueTable.attribute_id, orm.Order.ASC),
                (AttributeTaskValueTable.index, orm.Order.ASC),
            )
        )

        raw_data: dict[int, dict[int, _RawAvmT]] = {}
        value: list[SlotStr] = []
        prev_ta: tuple[int, int] = (-1, -1)

        for row in rows:
            ta = (row.task_id, row.attribute_id)

            if prev_ta == ta:
                value.append(row.slot_slot)
            else:
                raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = value
                value = [
                    row.slot_slot
                ]  # DO NOT CLEAR (or at least copy for data if so), otherwise list is in data is affected
                prev_ta = ta

        if value:
            raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = value

        return (id_to_attr, raw_data)

    def get_tasks_attribute_value_mapping(
        self, user_id: int | None
    ) -> tuple[list[AnyAttributeT], list[AttributeValueMapping]]:
        id_to_task: dict[int, Task] = {task.id: task for task in self.get_tasks()}
        type_id_and_id_to_attribute: dict[tuple[int, int], AnyAttributeT] = {}

        raw_data: dict[int, dict[int, _RawAvmT]] = {}

        ATTRIBUTES_TYPES_TO_HANDLE = (
            (StaticAttribute, TaskAttribute) if user_id is None else ALL_ATTRIBUTE_TYPES
        )

        with self.connector.cursor() as c:
            community_user: CommunityUser | None = None

            if user_id is not None:
                jumpedia_user = self.community.jumpedia.get_jumpedia_user_by_id(user_id)

                if jumpedia_user is None:
                    raise errors.StructureNotFoundError(JumpediaUser)

                community_user = self.community.get_community_user_by_id(user_id)

                if community_user is None:
                    raise errors.StructureNotFoundError(CommunityUser)

            del user_id

            # --- Static Attribute ---
            static_attrs = self.get_attributes(StaticAttribute)

            type_id_and_id_to_attribute |= {
                (attr.type_id, attr.id): attr for attr in static_attrs
            }

            id_attr, name_attr, aliases_attr = static_attrs
            del static_attrs

            for id, task in id_to_task.items():
                # Set all nested dictionaries once here
                raw_data[id] = {typ.type_id: {} for typ in ATTRIBUTES_TYPES_TO_HANDLE}

                static_avm: _RawAvmT = raw_data[id][StaticAttribute.type_id]

                static_avm[id_attr.id] = id_attr.raw_to_value([str(id)])
                static_avm[name_attr.id] = [task.slot_name]

            rows = c.fetch_all(
                db.TaskAlias.select(
                    db.TaskAlias.slot_alias, db.TaskAlias.task_id
                ).where((db.TaskAlias.list_id, orm.Operator.EQ, self.id))
            )

            task_id_to_aliases = itertools.groupby(rows, lambda row: row.task_id)

            for task_id, aliases in task_id_to_aliases:
                raw_data[task_id][StaticAttribute.type_id][aliases_attr.id] = list(
                    alias.slot_alias for alias in aliases
                )

            # --- Task Attribute ---

            attr_mapping, new_data = (
                self._get_attributes_and_data_for_non_static_attribute_value_mapping(
                    c, TaskAttribute, -1
                )
            )

            type_id_and_id_to_attribute |= attr_mapping
            raw_data.update(new_data)

            # --- User Attribute ---

            if community_user is not None:
                attr_mapping, new_data = (
                    self._get_attributes_and_data_for_non_static_attribute_value_mapping(
                        c, UserAttribute, community_user.jumpedia_user_id
                    )
                )

                type_id_and_id_to_attribute |= attr_mapping
                raw_data.update(new_data)

        # --- Final Conversion ---

        final: list[AttributeValueMapping] = []

        for task_id, data in raw_data.items():
            avms = tuple(
                MappingProxyType(
                    {
                        type_id_and_id_to_attribute[(typ.type_id, attr_id)]: value
                        for attr_id, value in data[typ.type_id].items()
                    }
                )
                for typ in ATTRIBUTES_TYPES_TO_HANDLE
            )

            static_and_task_avm: tuple[AvmT[StaticAttribute], AvmT[TaskAttribute]] = (
                avms[:2]
            )  # pyright: ignore[reportAssignmentType]
            user_avm: tuple[CommunityUser, AvmT[UserAttribute]] | None = None

            if community_user is not None:
                user_avm = (
                    community_user,
                    avms[2],
                )  # pyright: ignore[reportAssignmentType]

            final.append(
                AttributeValueMapping(
                    id_to_task[task_id], *static_and_task_avm, user_avm
                )
            )

        return list(type_id_and_id_to_attribute.values()), final

    def create_task(
        self,
        slot_name: SlotStr,
        slot_aliases: t.Iterable[SlotStr],
        raw_task_attribute_value_mapping: t.Mapping[int, t.Sequence[RealStr]],
    ) -> Task:
        (slot_name, *slot_aliases), (norm_name, *norm_aliases) = (
            NormStr.unique_reals_and_norms((slot_name, *slot_aliases))
        )

        with self.locked:
            self._validate_task_syns(norm_name, {*norm_aliases})

            all_tasks = self.get_tasks()

            if len(all_tasks) >= self.community.limits.list_task_count_max:
                raise errors.LimitOfStructuresReachedError(
                    self.community.limits.list_task_count_max, Task
                )

            task_attribute_value_mapping = self._cook_raw_task_attribute_value_mapping(
                raw_task_attribute_value_mapping
            )

            with self.connector.cursor() as c:
                execute_data = c.execute(
                    db.Task.insert(
                        db.Task.list_id.bind(self.id),
                        db.Task.norm_name.bind(norm_name),
                        db.Task.slot_name.bind(slot_name),
                    ),
                    get_last_generated_id=True,
                )

                task_id = execute_data.last_generated_id
                assert task_id is not None

                self._insert_task_aliases(c, task_id, slot_aliases, norm_aliases)
                self._insert_task_attribute_value_mapping(
                    c, task_id, task_attribute_value_mapping
                )

            return Task(list=self, id=task_id, slot_name=slot_name, norm_name=norm_name)

    def delete_task(self, id: int) -> None:
        from . import errors

        with self.locked, self.connector.cursor() as c:
            execute_data = c.execute(
                db.Task.delete().where(
                    (db.Task.list_id, orm.Operator.EQ, self.id),
                    (db.Task.id, orm.Operator.EQ, id),
                ),
                get_affected_row_count=True,
            )

            if execute_data.affected_row_count == 0:
                raise errors.StructureNotFoundError(Task)

            assert execute_data.affected_row_count == 1

    def edit_task_name(self, id: int, slot_name: SlotStr) -> None:
        norm_name = NormStr(slot_name)

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)

            if slot_name == task.slot_name:
                return

            self._validate_task_syns(norm_name, allowed_tasks={task})

            with self.connector.cursor() as c:
                c.execute(
                    db.Task.update(
                        db.Task.norm_name.set(norm_name),
                        db.Task.slot_name.set(slot_name),
                    ).where(
                        (db.Task.list_id, orm.Operator.EQ, self.id),
                        (db.Task.id, orm.Operator.EQ, task.id),
                    )
                )

                # If the new name is an alias, remove the alias
                execute_data = c.execute(
                    db.TaskAlias.delete().where(
                        (db.TaskAlias.list_id, orm.Operator.EQ, self.id),
                        (db.TaskAlias.task_id, orm.Operator.EQ, task.id),
                        (db.TaskAlias.norm_alias, orm.Operator.EQ, norm_name),
                    ),
                    get_affected_row_count=True,
                )

                assert execute_data.affected_row_count in (0, 1)

    def edit_task_aliases(self, id: int, slot_aliases: t.Iterable[SlotStr]) -> None:
        slot_aliases, norm_aliases = NormStr.unique_reals_and_norms(slot_aliases)

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)

            self._validate_task_syns(
                norm_aliases=set(norm_aliases), allowed_tasks={task}
            )

            norm_name = task.norm_name

            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(norm_name)
            except ValueError:
                pass
            else:
                slot_aliases = slot_aliases[:idx] + slot_aliases[idx + 1 :]
                norm_aliases = norm_aliases[:idx] + norm_aliases[idx + 1 :]

            del norm_name

            with self.connector.cursor() as c:
                # Delete all aliases
                c.execute(
                    db.TaskAlias.delete().where(
                        (db.TaskAlias.list_id, orm.Operator.EQ, self.id),
                        (db.TaskAlias.task_id, orm.Operator.EQ, task.id),
                    )
                )

                self._insert_task_aliases(c, task.id, slot_aliases, norm_aliases)

    def edit_task_attribute_value_mapping(
        self,
        id: int,
        raw_task_attribute_value_mapping: t.Mapping[int, t.Sequence[SlotStr]],
    ) -> None:
        from . import errors

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)

            task_attribute_value_mapping = self._cook_raw_task_attribute_value_mapping(
                raw_task_attribute_value_mapping
            )

            AttributeTaskValueTable = TaskAttribute.tables.attribute_task_value

            with self.connector.cursor() as c:
                c.execute(
                    AttributeTaskValueTable.delete().where(
                        (AttributeTaskValueTable.list_id, orm.Operator.EQ, self.id),
                        (AttributeTaskValueTable.task_id, orm.Operator.EQ, task.id),
                    )
                )

                self._insert_task_attribute_value_mapping(
                    c, task.id, task_attribute_value_mapping
                )

    def _fetch_tasks_from_table(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[db.Task]:
        with self.connector.cursor() as c:
            return c.fetch_all(
                db.Task.select("*").where(
                    (db.Task.list_id, orm.Operator.EQ, self.id), *where
                )
            )

    def _task_row_to_obj(self, row: db.Task) -> Task:
        return Task(
            list=self, id=row.id, slot_name=row.slot_name, norm_name=row.norm_name
        )

    def _insert_task_aliases(
        self,
        c: orm.Cursor,
        task_id: int,
        slot_aliases: t.Sequence[SlotStr],
        norm_aliases: t.Sequence[NormStr],
    ) -> None:
        if not norm_aliases:
            return

        count = len(norm_aliases)

        c.execute(
            db.TaskAlias.insert(
                db.TaskAlias.task_id.bind(*itertools.repeat(task_id, count)),
                db.TaskAlias.list_id.bind(*itertools.repeat(self.id, count)),
                db.TaskAlias.norm_alias.bind(*norm_aliases),
                db.TaskAlias.slot_alias.bind(*slot_aliases),
            )
        )

    def _insert_task_attribute_value_mapping(
        self,
        c: orm.Cursor,
        task_id: int,
        task_attribute_value_mapping: dict[TaskAttribute, list[SlotStr]],
    ) -> None:
        if not task_attribute_value_mapping:
            return

        # This is so clean I'm UwU-ing
        attribute_id_args: list[int] = []
        index_args: list[int] = []
        slot_args: list[SlotStr] = []

        for attr, v in task_attribute_value_mapping.items():
            for i, slot in enumerate(v):
                attribute_id_args.append(attr.id)
                index_args.append(i)
                slot_args.append(slot)

        AttributeTaskValueTable = t.cast(
            type[db.AbstractAttributeTaskValueTable],
            TaskAttribute.tables.attribute_task_value,
        )

        c.execute(
            AttributeTaskValueTable.insert(
                AttributeTaskValueTable.task_id.bind(
                    *itertools.repeat(task_id, len(attribute_id_args))
                ),
                AttributeTaskValueTable.attribute_id.bind(*attribute_id_args),
                AttributeTaskValueTable.index.bind(*index_args),
                AttributeTaskValueTable.slot_slot.bind(*slot_args),
            )
        )

    def _validate_task_syns(
        self,
        norm_name: NormStr | None = None,
        norm_aliases: t.AbstractSet[NormStr] = frozenset(),
        allowed_tasks: t.AbstractSet[Task] = frozenset(),
    ) -> None:
        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)

        if norm_aliases:
            norm_syns.update(norm_aliases)

        if (
            len(norm_aliases)
            > self.community.jumpedia.limits.attribute_task_value_slot_count_max
        ):
            raise feedbacks.temp("Too many aliases")

        for normed_syn in norm_syns:
            if (
                len(normed_syn)
                > self.community.jumpedia.limits.attribute_task_value_slot_length_max
            ):
                raise feedbacks.temp("Too long syn")

            task = self.get_task_by_syn(normed_syn)

            if task not in allowed_tasks:
                raise feedbacks.temp(f"Task syn {normed_syn!r} already taken!")

    def _validate_attribute_syns(
        self,
        norm_name: NormStr | None = None,
        norm_aliases: t.AbstractSet[NormStr] = frozenset(),
        allowed_attributes: t.AbstractSet[BaseAttribute] = frozenset(),
    ) -> None:
        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)

        if norm_aliases:
            norm_syns.update(norm_aliases)

        if len(norm_aliases) > self.community.limits.attribute_alias_count_max:
            raise feedbacks.temp("Too many aliases")

        for normed_syn in norm_syns:
            if (
                len(normed_syn)
                > self.community.jumpedia.limits.attribute_syn_length_max
            ):
                raise feedbacks.temp("Too long syn")

            attribute = self.get_any_attribute_by_syn(normed_syn)

            if attribute not in allowed_attributes:
                raise feedbacks.temp(f"Attribute syn {normed_syn!r} already taken!")
