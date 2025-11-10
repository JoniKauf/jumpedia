import enum
import itertools
import typing as t
from ast import alias
from types import MappingProxyType

from src.utils import orm, text
from src.utils.text import NormStr, RealStr

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
from .attribute.slot_str import SLOT_TYPES, SlotStr, SlotTypeT
from .jumpedia import StructureNotFoundError, db
from .task import Task
from .task.attribute_value_mapping import AttributeValueMapping, AvmT, UserAttributeValueMapping
from .user import CommunityUser, JumpediaUser

if t.TYPE_CHECKING:
    from .community import Community


class Kind(enum.IntEnum):
    ID = 1
    NAME = 2
    ALIAS = 3


type _RawAvmT = dict[int, tuple[SlotStr, ...]]


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

    def get_attributes[T: BaseAttribute](self, type: type[T], /) -> list[T]:
        return [
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute)
        ]

    def get_attributes_by_id[T: BaseAttribute](
        self, type: type[T], id: int, /, *ids: int
    ) -> list[T]:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(
            table_type, (table_type.id, orm.Operator.IN, (id, *ids))
        )
        return list(self._attribute_row_to_obj(type, row) for row in rows)

    def get_attributes_by_name[T: BaseAttribute](
        self, type: type[T], name: NormStr, /, *names: NormStr
    ) -> list[T]:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(
            table_type, (table_type.norm_name, orm.Operator.IN, (name, *names))
        )
        return list(self._attribute_row_to_obj(type, row) for row in rows)

    def get_attributes_by_alias[T: BaseAttribute](
        self, type: type[T], alias: NormStr, /, *aliases: NormStr
    ) -> list[T]:
        AttributeAliasTable: db.AbstractAttributeAliasTable = type.tables.attribute_alias  # type: ignore

        with self.connector.cursor() as c:
            rows = c.fetch_all(
                AttributeAliasTable.select(
                    "*",
                ).where(
                    (AttributeAliasTable.list_id, orm.Operator.EQ, self.id),
                    (
                        AttributeAliasTable.norm_alias,
                        orm.Operator.IN,
                        (alias, *aliases),
                    ),
                )
            )

        if not rows:
            return []

        return self.get_attributes_by_id(type, *rows)  # type: ignore

    def get_attributes_by_syn[T: BaseAttribute](
        self, type: type[T], syn: NormStr, /, *syns: NormStr
    ) -> list[T]:
        return self.get_attributes_by_name(
            type, syn, *syns
        ) or self.get_attributes_by_alias(type, syn, *syns)

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

    def get_any_attributes_by_id(self, id: int, /, *ids: int) -> list[AnyAttributeT]:
        return [
            attr
            for type in ALL_ATTRIBUTE_TYPES
            for attr in self.get_attributes_by_id(type, id, *ids)
        ]

    def get_any_attributes_by_name(
        self, name: NormStr, /, *names: NormStr
    ) -> list[AnyAttributeT]:
        return [
            attr
            for type in ALL_ATTRIBUTE_TYPES
            for attr in self.get_attributes_by_name(type, name, *names)
        ]

    def get_any_attributes_by_alias(
        self, alias: NormStr, /, *aliases: NormStr
    ) -> list[AnyAttributeT]:
        return [
            attr
            for type in ALL_ATTRIBUTE_TYPES
            for attr in self.get_attributes_by_alias(type, alias, *aliases)
        ]

    def get_any_attributes_by_syn(
        self, syn: NormStr, /, *syns: NormStr
    ) -> list[AnyAttributeT]:
        return [
            attr
            for type in ALL_ATTRIBUTE_TYPES
            for attr in self.get_attributes_by_syn(type, syn, *syns)
        ]

    def get_static_attribute_by_kind(self, kind: Kind, /) -> StaticAttribute:
        if kind not in Kind:
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

    def _get_default_static_attribute(
        self, kind: Kind, id: int = -1, /
    ) -> StaticAttribute:
        if kind.value == 1:
            real_name = RealStr("Id")

            return StaticAttribute(
                list=self,
                id=id,
                real_name=real_name,
                norm_name=NormStr(real_name),
                slot_type=int,
                position=0,
                min_slots=1,
                max_slots=1,
                kind=kind,
            )

        if kind.value == 2:
            real_name = RealStr("Name")

            return StaticAttribute(
                list=self,
                id=id,
                real_name=real_name,
                norm_name=NormStr(real_name),
                slot_type=str,
                position=1,
                min_slots=1,
                max_slots=1,
                kind=kind,
            )

        if kind.value == 3:
            real_name = RealStr("Alias")

            return StaticAttribute(
                list=self,
                id=id,
                real_name=real_name,
                norm_name=NormStr(real_name),
                slot_type=str,
                position=1,
                min_slots=0,
                max_slots=self.community.limits.attribute_task_value_slot_count_max,
                kind=kind,
            )

        t.assert_never(kind.value)

    @t.overload
    def create_attribute[T: StaticAttribute](
        self,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: type[SlotTypeT],
        max_slots: int,
        *,
        min_slots: int,
        kind: Kind,
    ) -> T:
        pass

    @t.overload
    def create_attribute[T: BaseNonStaticAttribute](
        self,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: type[SlotTypeT],
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
        slot_type: type[SlotTypeT],
        max_slots: int,
        *,
        min_slots: int = 0,
        kind: Kind | None = None,
        collection: t.Sequence[tuple[RealStr, t.Iterable[RealStr]]] = (),
    ) -> T:
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

        attrs = self.get_all_attributes_flat()

        if len(attrs) >= self.community.limits.list_attribute_count_max:
            raise errors.LimitReachedError(
                self.community.limits.list_attribute_count_max, type
            )

        for syn in (norm_name, *norm_aliases):
            if len(syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                raise errors.TooLongSynError(
                    syn,
                    self.community.jumpedia.limits.attribute_syn_length_max,
                    type,
                )

            try:
                _ = self.get_any_attributes_by_syn(syn)[0]
            except IndexError:
                raise errors.StructureNotFoundError(type)

        if not (
            0
            <= min_slots
            <= max_slots
            <= self.community.limits.attribute_task_value_slot_count_max
        ):
            raise errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError(
                min_slots,
                max_slots,
                0,
                self.community.limits.attribute_task_value_slot_count_max,
            )

        position = max(attr.position for attr in attrs) + 1 if attrs else 1

        AttributeTable = t.cast(
            type[db.AbstractAttributeTable], type.tables.attribute
        )

        with self.connector.cursor() as c:
            additional: tuple[orm.ColumnBind[t.Any, t.Any], ...] = ()

            if issubclass(AttributeTable, db.StaticAttribute):
                assert kind is not None
                additional = (AttributeTable.kind.bind(kind.value),)

            execute_data = c.execute(
                AttributeTable.insert(
                    AttributeTable.list_id.bind(self.id),
                    AttributeTable.norm_name.bind(norm_name),
                    AttributeTable.real_name.bind(real_name),
                    AttributeTable.slot_type.bind(SLOT_TYPES.index(slot_type)),
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

        with self.connector.cursor() as c:
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

        try:
            attribute = self.get_attributes_by_id(type, id)[0]
        except IndexError:
            raise errors.StructureNotFoundError(type)

        if real_name == attribute.real_name:
            return

        self._validate_attribute_syns(
            type, norm_name, allowed_attributes=frozenset([attribute])
        )

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

        try:
            attribute = self.get_attributes_by_id(type, id)[0]
        except IndexError:
            raise errors.StructureNotFoundError(type)

        self._validate_attribute_syns(
            type,
            norm_aliases=frozenset(norm_aliases),
            allowed_attributes=frozenset([attribute]),
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
                slot_type=SLOT_TYPES[row.slot_type],
                position=row.position,
                min_slots=row.min_slots,
                max_slots=row.max_slots,
                kind=Kind(row.kind),
            )

        return type(
            list=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name,
            slot_type=SLOT_TYPES[row.slot_type],
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots,
        )

    def _calc_attribute_value_mapping[T: TaskAttribute | UserAttribute](
        self, type: type[T], attribute_value_mapping: dict[int, t.Sequence[RealStr]]
    ) -> dict[T, tuple[SlotStr, ...]]:
        id_to_attr = {attr.id: attr for attr in self.get_attributes(type)}

        for id in attribute_value_mapping:
            if id not in id_to_attr:
                raise StructureNotFoundError(type)
            
        for attr in id_to_attr.values():
            attribute_value_mapping.setdefault(attr.id, ())

        avm: dict[T, tuple[SlotStr, ...]] = {}

        # Convert ids to attributes and validate value
        for attr_id, v in attribute_value_mapping.items():
            attr = id_to_attr[attr_id]
            val = attr.real_to_slot_value(v)

            avm[attr] = val

        return avm

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

        AttributeAliasTable: type[db.AbstractAttributeAliasTable] = type.tables.attribute_alias  # type: ignore
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

    def _task_id_to_slot(self, id: int) -> SlotStr:
        return self._get_default_static_attribute(Kind.ID).real_to_slot_value((RealStr(str(id)),))[0]
    def _task_real_name_to_slot(self, name: RealStr) -> SlotStr:
        return self._get_default_static_attribute(Kind.NAME).real_to_slot_value((name,))[0]
    
    def _task_real_aliases_to_slot_value(self, aliases: t.Sequence[RealStr]) -> tuple[SlotStr, ...]:
        return self._get_default_static_attribute(Kind.ALIAS).real_to_slot_value(aliases)
    
    def get_tasks(self, *where: tuple[t.Any, orm.Operator, t.Any]) -> list[Task]:
        return [
            self._task_row_to_obj(data) for data in self._fetch_tasks_from_table(*where)
        ]

    def get_tasks_by_id(self, id: int, /, *ids: int) -> list[Task]:
        rows = self._fetch_tasks_from_table((db.Task.id, orm.Operator.IN, (id, *ids)))
        return list(map(self._task_row_to_obj, rows))

    def get_tasks_by_name(self, name: NormStr, /, *names: NormStr) -> list[Task]:
        rows = self._fetch_tasks_from_table(
            (db.Task.norm_name, orm.Operator.IN, (name, *names))
        )
        return list(map(self._task_row_to_obj, rows))

    def get_tasks_by_alias(self, alias: NormStr, /, *aliases: NormStr) -> list[Task]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.TaskAlias.select(db.TaskAlias.task_id).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.id),
                    (db.TaskAlias.norm_alias, orm.Operator.IN, (alias, *aliases)),
                )
            )

        if not rows:
            return []

        return self.get_tasks_by_id(*(row.task_id for row in rows))

    def get_tasks_by_syn(self, norm_syn: NormStr, /, *norm_syns: NormStr) -> list[Task]:
        return self.get_tasks_by_name(norm_syn, *norm_syns) + self.get_tasks_by_alias(
            norm_syn, *norm_syns
        )

    def _get_attributes_and_data_for_non_static_attribute_value_mapping[
        T: BaseNonStaticAttribute
    ](
        self, c: orm.Cursor, type: type[T], community_user_id: int
    ) -> tuple[dict[tuple[int, int], T], dict[int, dict[int, _RawAvmT]]]:
        task_attrs = self.get_attributes(type)
        id_to_attr = {(attr.type_id, attr.id): attr for attr in task_attrs}
        del task_attrs

        AttributeTaskValueTable = type.tables.attribute_task_value

        if issubclass(AttributeTaskValueTable, db.TaskAttributeTaskValue):
            rows = c.fetch_all(
                AttributeTaskValueTable.select(
                    AttributeTaskValueTable.task_id,
                    AttributeTaskValueTable.attribute_id,
                    AttributeTaskValueTable.slot_slot,
                )
                .where(
                    (AttributeTaskValueTable.list_id, orm.Operator.EQ, self.id),
                )
                .order_by(
                    (AttributeTaskValueTable.task_id, orm.Order.ASC),
                    (AttributeTaskValueTable.attribute_id, orm.Order.ASC),
                    (AttributeTaskValueTable.index, orm.Order.ASC),
                )
            )
        elif issubclass(AttributeTaskValueTable, db.UserAttributeTaskValue):
            rows = c.fetch_all(
                AttributeTaskValueTable.select(
                    AttributeTaskValueTable.task_id,
                    AttributeTaskValueTable.attribute_id,
                    AttributeTaskValueTable.slot_slot,
                ).where(
                    (AttributeTaskValueTable.list_id, orm.Operator.EQ, self.id),
                    (AttributeTaskValueTable.community_user_id, orm.Operator.EQ, community_user_id)
                ).order_by(
                    AttributeTaskValueTable.task_id,
                    AttributeTaskValueTable.attribute_id,
                    AttributeTaskValueTable.index,
                )
            )
        else:
            t.assert_never(AttributeTaskValueTable)

        raw_data: dict[int, dict[int, _RawAvmT]] = {}
        value: list[SlotStr] = []
        prev_ta: tuple[int, int] = (-1, -1)

        for row in rows:
            ta = (row.task_id, row.attribute_id)

            if prev_ta == ta:
                value.append(row.slot_slot)
            else:
                raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = tuple(value)
                value = [
                    row.slot_slot
                ]  # DO NOT CLEAR (or at least copy for data if so), otherwise list is in data is affected
                prev_ta = ta

        if value:
            raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = tuple(value)

        return (id_to_attr, raw_data)

    @t.overload
    def get_task_attribute_value_mappings(
        self, /
    ) -> tuple[list[StaticAttribute | TaskAttribute], list[AttributeValueMapping]]:
        pass

    @t.overload
    def get_task_attribute_value_mappings(
        self, community_user: CommunityUser, /
    ) -> tuple[list[AnyAttributeT], list[UserAttributeValueMapping]]:
        pass

    def get_task_attribute_value_mappings(
        self, community_user: CommunityUser | None = None, /
    ) -> tuple[list[t.Any], list[t.Any]]:
        id_to_task: dict[int, Task] = {task.id: task for task in self.get_tasks()}
        type_id_and_id_to_attribute: dict[tuple[int, int], AnyAttributeT] = {}

        raw_data: dict[int, dict[int, _RawAvmT]] = {}

        ATTRIBUTES_TYPES_TO_HANDLE = (
            (StaticAttribute, TaskAttribute)
            if community_user is None
            else ALL_ATTRIBUTE_TYPES
        )

        with self.connector.cursor() as c:
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

                static_avm[id_attr.id] = (SlotStr(RealStr(str(id)), int),)
                static_avm[name_attr.id] = (task.slot_name,)

            rows = c.fetch_all(
                db.TaskAlias.select(
                    db.TaskAlias.slot_alias, db.TaskAlias.task_id
                ).where((db.TaskAlias.list_id, orm.Operator.EQ, self.id))
            )

            task_id_to_aliases = itertools.groupby(rows, lambda row: row.task_id)

            for task_id, aliases in task_id_to_aliases:
                raw_data[task_id][StaticAttribute.type_id][aliases_attr.id] = tuple(
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
                        c, UserAttribute, community_user.jumpedia_user.id
                    )
                )

                type_id_and_id_to_attribute |= attr_mapping
                raw_data.update(new_data)

        # --- Final Conversion ---

        final: list[AttributeValueMapping | UserAttributeValueMapping] = []

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

            avm = AttributeValueMapping(
                id_to_task[task_id], *static_and_task_avm
            )
            
            if community_user is None:
                final.append(avm)
            else:
                final.append(UserAttributeValueMapping(avm, community_user, avms[2]))  # type: ignore

        return list(type_id_and_id_to_attribute.values()), final

    def create_task(
        self,
        name: RealStr,
        aliases: t.Sequence[RealStr],
        task_attribute_value_mapping: dict[int, t.Sequence[RealStr]],
    ) -> Task:
        (real_name, *real_aliases), (norm_name, *norm_aliases) = (
            NormStr.unique_reals_and_norms((name, *aliases))
        )

        del name, aliases

        slot_name = self._task_real_name_to_slot(real_name)
        slot_aliases = self._task_real_aliases_to_slot_value(real_aliases)

        del real_name, real_aliases

        self._validate_task_syns(norm_name, frozenset(norm_aliases))

        all_tasks = self.get_tasks()

        if len(all_tasks) >= self.community.limits.list_task_count_max:
            raise errors.LimitReachedError(
                self.community.limits.list_task_count_max, Task
            )

        avm = self._calc_attribute_value_mapping(
            TaskAttribute,
            task_attribute_value_mapping
        )

        del task_attribute_value_mapping

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
            self._insert_task_attribute_value_mapping(c, task_id, avm)

        return Task(list=self, id=task_id, slot_name=slot_name, norm_name=norm_name)

    def delete_task(self, id: int) -> None:
        from . import errors

        with self.connector.cursor() as c:
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

    def edit_task_name(self, id: int, name: text.RealStr) -> None:
        slot_name = self._task_real_name_to_slot(name)
        norm_name = NormStr(slot_name)

        del name

        try:
            task = self.get_tasks_by_id(id)[0]
        except IndexError:
            raise errors.StructureNotFoundError(Task)

        if slot_name == task.slot_name:
            return

        self._validate_task_syns(norm_name, allowed_tasks=frozenset([task]))

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

    def edit_task_aliases(self, id: int, aliases: t.Sequence[RealStr]) -> None:
        real_aliases, norm_aliases = NormStr.unique_reals_and_norms(aliases)

        del aliases

        slot_aliases = self._task_real_aliases_to_slot_value(real_aliases)

        del real_aliases

        try:
            task = self.get_tasks_by_id(id)[0]
        except IndexError:
            raise errors.StructureNotFoundError(Task)

        self._validate_task_syns(
            norm_aliases=frozenset(norm_aliases), allowed_tasks=frozenset([task])
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
        task: Task,
        task_attribute_value_mapping: dict[int, t.Sequence[RealStr]],
    ) -> None:
        tavm = self._calc_attribute_value_mapping(
            TaskAttribute,
            task_attribute_value_mapping
        )

        del task_attribute_value_mapping

        AttributeTaskValueTable = TaskAttribute.tables.attribute_task_value

        with self.connector.cursor() as c:
            c.execute(
                AttributeTaskValueTable.delete().where(
                    (AttributeTaskValueTable.list_id, orm.Operator.EQ, self.id),
                    (AttributeTaskValueTable.task_id, orm.Operator.EQ, task.id),
                )
            )

            self._insert_task_attribute_value_mapping(c, task.id, tavm)

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
        task_attribute_value_mapping: dict[TaskAttribute, tuple[SlotStr, ...]],
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
        norm_aliases: frozenset[NormStr] = frozenset(),
        allowed_tasks: frozenset[Task] = frozenset(),
    ) -> None:
        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)

        if norm_aliases:
            norm_syns.update(norm_aliases)

        alias_copycat = self.get_default_static_attribute(Kind.ALIAS, -1)

        if not (
            alias_copycat.min_slots <= len(norm_aliases) <= alias_copycat.max_slots
        ):
            raise errors.TooManyAliasesError(
                norm_aliases, alias_copycat.max_slots, Task
            )

        if not norm_syns:
            return

        for normed_syn in norm_syns:
            if (
                len(normed_syn)
                > self.community.jumpedia.limits.attribute_task_value_slot_length_max
            ):
                raise errors.TooLongSynError(
                    normed_syn,
                    self.community.jumpedia.limits.attribute_task_value_slot_length_max,
                    Task,
                )

        taken = frozenset(self.get_tasks_by_syn(*norm_syns))
        taken -= allowed_tasks

        if taken:
            raise errors.SynsAlreadyTakenError(taken)

    def _validate_attribute_syns(
        self,
        type: type[BaseAttribute],
        norm_name: NormStr | None = None,
        norm_aliases: frozenset[NormStr] = frozenset(),
        allowed_attributes: frozenset[BaseAttribute] = frozenset(),
    ) -> None:
        if len(norm_aliases) > self.community.limits.attribute_alias_count_max:
            raise errors.TooManyAliasesError(
                norm_aliases, self.community.limits.attribute_alias_count_max, type
            )

        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)

        norm_syns.update(norm_aliases)

        if not norm_syns:
            return

        for norm_syn in norm_syns:
            if len(norm_syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                raise errors.TooLongSynError(
                    norm_syn,
                    self.community.jumpedia.limits.attribute_syn_length_max,
                    type,
                )

        taken: frozenset[BaseAttribute] = frozenset(
            self.get_any_attributes_by_syn(*norm_syns)
        )
        taken -= allowed_attributes

        if taken:
            raise errors.SynsAlreadyTakenError(taken)

    def give_task_to_community_user(
        self,
        task_id: int,
        community_user_id: int,
        user_attribute_value_mapping: dict[int, t.Sequence[text.RealStr]],
    ) -> None:
        uavm = self._calc_attribute_value_mapping(UserAttribute, user_attribute_value_mapping)

        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.CommunityUserListTask.select(
                    '*'
                ).where(
                    (db.CommunityUserListTask.community_user_id, orm.Operator.EQ, community_user_id),
                    (db.CommunityUserListTask.list_id, orm.Operator.EQ, self.id),
                    (db.CommunityUserListTask.task_id, orm.Operator.EQ, task_id)
                )
            )

            if row is not None:
                raise errors.TaskAlreadyGivenToUserError(
                    task_id,
                    community_user_id
                )

            execute_data = c.execute(
                db.CommunityUserListTask.insert(
                    db.CommunityUserListTask.community_user_id.bind(community_user_id),
                    db.CommunityUserListTask.list_id.bind(self.id),
                    db.CommunityUserListTask.task_id.bind(task_id)
                ), get_last_generated_id=True
            )
            
            if not uavm:
                return
            
            total_row_count: int = sum(len(v) for v in uavm.values())

            if not total_row_count:
                return
            
            assert execute_data.last_generated_id is not None

            c.execute(
                db.UserAttributeTaskValue.insert(
                    db.UserAttributeTaskValue.community_user_list_task_id.bind(*itertools.repeat(execute_data.last_generated_id, total_row_count)),
                    db.UserAttributeTaskValue.community_user_id.bind(*itertools.repeat(community_user_id, total_row_count)),
                    db.UserAttributeTaskValue.list_id.bind(*itertools.repeat(self.id, total_row_count)),
                    db.UserAttributeTaskValue.task_id.bind(*itertools.repeat(task_id, total_row_count)),
                    db.UserAttributeTaskValue.attribute_id.bind(*(attr.id for attr, v in uavm.items() for _ in v)),
                    db.UserAttributeTaskValue.index.bind(*(i for v in uavm.values() for i in range(len(v)))),
                    db.UserAttributeTaskValue.slot_slot.bind(*(slot for v in uavm.values() for slot in v))
                )
            )

    def remove_task_from_community_user(self, task_id: int, community_user_id: int) -> None:
        with self.connector.cursor() as c:
            execute_data = c.execute(
                db.CommunityUserListTask.delete().where(
                    (db.CommunityUserListTask.community_user_id, orm.Operator.EQ, community_user_id),
                    (db.CommunityUserListTask.list_id, orm.Operator.EQ, self.id),
                    (db.CommunityUserListTask.task_id, orm.Operator.EQ, task_id)
                ), get_affected_row_count=True
            )

            raise StructureNotF