import itertools
import typing as t
from string.templatelib import Template
from types import MappingProxyType

from src.database import queries, typed
from src.database.simple_orm import Arg, Raw, Rows
from src.structures import BaseStructure
from src.structures.attribute import (ALL_ATTRIBUTE_TYPES, AnyAttributeT,
                                      BaseAttribute, BaseNonStaticAttribute,
                                      RawCollectionEntryItem, StaticAttribute,
                                      TaskAttribute, UserAttribute)
from src.structures.attribute.slot_type import SlotStr, SlotType, SlotTypeT
from src.structures.task import Task
from src.utils.text import NormStr, RealStr
from structures import errors
from structures.task.attribute_value_mapping import AttributeValueMapping, AvmT
from structures.user.community_user import CommunityUser

if t.TYPE_CHECKING:
    from src.structures.community import Community


STATIC_ATTRIBUTE_KIND_OF_ID: t.Final = 1
STATIC_ATTRIBUTE_KIND_OF_NAME: t.Final = 2
STATIC_ATTRIBUTE_KIND_OF_ALIASES: t.Final = 3

type KindT = t.Literal[1, 2, 3]
KINDS: tuple[t.Literal[1], t.Literal[2], t.Literal[3]] = t.get_args(KindT.__value__)

type _RawAvmT = dict[int, list[SlotStr]]


class List(BaseStructure):
    community: 'Community'
    id: int
    real_name: RealStr
    norm_name: NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.community.identity)

    @property
    def name(self) -> str:
        return self.real_name

    # --- All Attributes ---

    def get_attributes[T: BaseAttribute](self, type: type[T]) -> list[T]:
        return [
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute, None)
        ]

    def get_attribute_by_id[T: BaseAttribute](self, type: type[T], id: int) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.id} = {arg(id)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_name[T: BaseAttribute](self, type: type[T], norm_name: NormStr) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.norm_name} = {arg(norm_name)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None
    
    def get_attribute_by_alias[T: BaseAttribute](self, type: type[T], norm_alias: NormStr) -> T | None:
        alias_table_type = type.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {alias_table_type.attribute_id}
                FROM {alias_table_type}
                WHERE 
                    {alias_table_type.list_id} = {arg(self.id)}
                    AND {alias_table_type.norm_alias} = {arg(norm_alias)}
            """)

            row = c.fetchone(alias_table_type)

        if row is None:
            return None
        
        return self.get_attribute_by_id(type, row.attribute_id)
    
    def get_attribute_by_syn[T: BaseAttribute](self, type: type[T], norm_syn: NormStr) -> T | None:
        return (
            self.get_attribute_by_name(type, norm_syn)
            or self.get_attribute_by_alias(type, norm_syn)
        )

    def get_all_attributes_flat(self) -> tuple[AnyAttributeT, ...]:
        return tuple(
            attr
            for type in ALL_ATTRIBUTE_TYPES
                for attr in self.get_attributes(type)
        )
    
    def get_all_attributes(self) -> tuple[list[StaticAttribute], list[TaskAttribute], list[UserAttribute]]:
        return tuple(
            self.get_attributes(type)
            for type in ALL_ATTRIBUTE_TYPES
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
        StaticAttributeTbl = typed.StaticAttribute

        if kind not in KINDS:
            raise ValueError(f"Kind {kind} is not valid")
        
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT * FROM {StaticAttributeTbl}
                WHERE
                    {StaticAttributeTbl.list_id} = {arg(self.id)}
                    AND {StaticAttributeTbl.kind} = {arg(kind)}
            """)

            row = c.fetchone(StaticAttributeTbl)

        if row is None:
            raise RuntimeError(f"Critical error! Could not find static attribute with kind {kind}")
        
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
        kind: KindT
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
        collection: t.Iterable[tuple[RealStr, t.Iterable[RealStr]]] = ()
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
        collection: t.Iterable[tuple[RealStr, t.Iterable[RealStr]]] = ()
    ) -> T:  # Higher kinded attributes not supported yet, otherwise T[TSlot]
        from . import errors

        assert (min_slots or kind) != issubclass(type, BaseNonStaticAttribute), "Typing not followed on attribute creation #1"
        assert (not collection) != issubclass(type, BaseNonStaticAttribute), "Typing not followed on attribute creation #2"

        (real_name, *real_aliases), (norm_name, *norm_aliases) = NormStr.unique_reals_and_norms((real_name, *real_aliases))

        with self.locked:
            attrs = self.get_all_attributes_flat()

            if len(attrs) >= self.community.limits.list_attribute_count_max:
                raise errors.LimitOfStructuresReachedError(self.community.limits.list_attribute_count_max, type)
            
            for syn in (norm_name, *norm_aliases):
                if len(syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                    raise errors.SynTooLongError(len(syn), self.community.jumpedia.limits.attribute_syn_length_max, type)
                
                attr_ = self.get_any_attribute_by_syn(syn)
                if attr_ is not None:
                    raise errors.SynAlreadyTakenError(syn, attr_)
                
            if not (min_slots <= max_slots <= self.community.jumpedia.limits.attribute_task_value_slot_count_max):
                raise errors.ElementCountOutOfRangeError(min_slots, self.community.jumpedia.limits.attribute_task_value_slot_count_max, type)
            
            position = max(attr.position for attr in attrs) + 1 if attrs else 1

            AttributeTbl = type.tables.attribute

            with queries.connected() as c:
                if issubclass(AttributeTbl, typed.StaticAttribute):
                    c.execute(lambda arg: t"""
                        INSERT INTO {AttributeTbl} (
                            {AttributeTbl.list_id},
                            {AttributeTbl.norm_name},
                            {AttributeTbl.real_name},
                            {AttributeTbl.slot_type},
                            {AttributeTbl.position},
                            {AttributeTbl.min_slots},
                            {AttributeTbl.max_slots},
                            {AttributeTbl.kind}
                        )
                        VALUES (
                            {arg(self.id)},
                            {arg(norm_name)},
                            {arg(real_name)},
                            {arg(slot_type.id)},
                            {arg(position)},
                            {arg(min_slots)},
                            {arg(max_slots)},
                            {arg(kind)}
                        )
                    """)
                else:
                    c.execute(lambda arg: t"""
                        INSERT INTO {AttributeTbl} (
                            {AttributeTbl.list_id},
                            {AttributeTbl.norm_name},
                            {AttributeTbl.real_name},
                            {AttributeTbl.slot_type},
                            {AttributeTbl.position},
                            {AttributeTbl.min_slots},
                            {AttributeTbl.max_slots}
                        )
                        VALUES (
                            {arg(self.id)},
                            {arg(norm_name)},
                            {arg(real_name)},
                            {arg(slot_type.id)},
                            {arg(position)},
                            {arg(min_slots)},
                            {arg(max_slots)}
                        )
                    """)

                attribute_id = c.last_generated_id

                self._insert_attribute_aliases(
                    c,
                    type,
                    attribute_id,
                    real_aliases,
                    norm_aliases
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
                    kind=kind
                )

                if collection:
                    assert isinstance(attribute, BaseNonStaticAttribute), "Typing not followed on attribute creation #3"
                    attribute.set_collection(collection)
                    
                return attribute

    def delete_attribute(self, type: type[BaseAttribute], id: int) -> None:
        from . import errors

        AttributeTbl = type.tables.attribute

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {AttributeTbl}
                WHERE {AttributeTbl.list_id} = {arg(self.id)}
                AND {AttributeTbl.id} = {arg(id)}
            """)

            if c.affected_row_count <= 0:
                raise errors.StructureNotFoundError(type)

    def edit_attribute_name(
        self, 
        type: type[BaseAttribute], 
        id: int, 
        real_name: RealStr
    ) -> None:
        norm_name = NormStr(real_name)

        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise errors.StructureNotFoundError(type)

            if real_name == attribute.real_name:
                return
            
            self._validate_attribute_syns(norm_name, allowed_attributes={attribute})
            
            AttributeTbl = type.tables.attribute

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    UPDATE {AttributeTbl}
                    SET
                        {AttributeTbl.norm_name} = {arg(norm_name)},
                        {AttributeTbl.real_name} = {arg(real_name)}
                    WHERE 
                        {AttributeTbl.list_id} = {arg(self.id)}
                        AND {AttributeTbl.id} = {arg(attribute.id)}
                """)
                
                # If the new name is an alias, remove the alias
                if norm_name in attribute.get_real_aliases():
                    AttributeAliasTbl = attribute.__class__.tables.attribute_alias

                    c.execute(lambda arg: t"""
                        DELETE FROM {AttributeAliasTbl}
                        WHERE
                            {AttributeAliasTbl.list_id} = {arg(self.id)}
                            AND {AttributeAliasTbl.attribute_id} = {arg(attribute.id)}
                            AND {AttributeAliasTbl.norm_alias} = {arg(norm_name)}
                    """)

                    assert c.affected_row_count == 1
    
    def edit_attribute_aliases(
        self,
        type: type[BaseAttribute],
        id: int, 
        aliases: t.Iterable[RealStr]
    ) -> None:
        (*real_aliases,), (*norm_aliases,) = NormStr.unique_reals_and_norms(aliases)
            
        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise errors.StructureNotFoundError(type)

            self._validate_attribute_syns(
                norm_aliases={*norm_aliases}, 
                allowed_attributes={attribute}
            )
            
            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(attribute.norm_name)
            except ValueError:
                pass
            else:
                real_aliases.pop(idx)
                norm_aliases.pop(idx)
            
            AttributeAliasTbl = type.tables.attribute_alias

            with queries.connected() as c:
                # Delete all aliases
                c.execute(lambda arg: t"""
                    DELETE FROM {AttributeAliasTbl}
                    WHERE 
                        {AttributeAliasTbl.list_id} = {arg(self.id)}
                        AND {AttributeAliasTbl.attribute_id} = {arg(attribute.id)}
                """)

                self._insert_attribute_aliases(c, type, attribute.id, real_aliases, norm_aliases)

    def _fetch_from_attribute_table[T: typed.BaseAttribute](
        self, 
        table_type: type[T], 
        where: t.Callable[[Arg], str] | None
    ) -> Rows[T]:
        order = t"ORDER BY {table_type.kind}" if issubclass(table_type, StaticAttribute) else t""

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {table_type}
                WHERE 
                    {table_type.list_id} = {arg(self.id)}
                    {Raw(f"AND {where(arg)}" if where is not None else "")}
            """ + order)

            return c.fetchall(table_type)
        
    def _attribute_row_to_obj[T: BaseAttribute](
        self, 
        type: type[T], 
        row: typed.BaseAttribute
    ) -> T:
        if issubclass(type, StaticAttribute):
            assert isinstance(row, typed.StaticAttribute)

            return type(
                list=self,
                id=row.id,
                real_name=row.real_name,
                norm_name=row.norm_name,
                slot_type=SlotType.get_by_id(row.slot_type),
                position=row.position,
                min_slots=row.min_slots,
                max_slots=row.max_slots,
                kind=row.kind
            )
        
        return type(
            list=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name,
            slot_type=SlotType.get_by_id(row.slot_type),
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots
        )
    
    def _cook_raw_task_attribute_value_mapping(
        self, 
        raw_task_attribute_value_mapping: t.Mapping[int, t.Sequence[str]]
    ) -> dict[TaskAttribute, list[SlotStr]]:
        id_to_attr = {attr.id: attr for attr in self.get_attributes(TaskAttribute)}
            
        # Check if all required attributes are given
        for attr in id_to_attr.values():
            if attr.required and attr.id not in raw_task_attribute_value_mapping:
                raise feedbacks.temp(f"Attribute {attr} is required (min >= 1 slots) but it received no values")
        
        if not raw_task_attribute_value_mapping:
            return {}
        
        attribute_value_mapping: dict[TaskAttribute, list[SlotStr]] = {}
        
        # Convert ids to attributes and validate value
        for attr_id, v in raw_task_attribute_value_mapping.items():
            if attr_id not in id_to_attr:
                raise errors.StructureNotFoundError(TaskAttribute)
            
            attr = id_to_attr[attr_id]
            val = attr.raw_to_value(v)

            attribute_value_mapping[attr] = val

        return attribute_value_mapping
    
    
    def _insert_attribute_aliases(
        self, 
        c: queries.CursorWrapper, 
        type: type[BaseAttribute], 
        attribute_id: int, 
        real_aliases: t.Sequence[RealStr],
        norm_aliases: t.Sequence[NormStr]
    ) -> None:
        if not norm_aliases:
            return
        
        AttributeAliasTbl = type.tables.attribute_alias
        count = len(norm_aliases)

        c.executemany(lambda args: t"""
            INSERT INTO {AttributeAliasTbl} (
                {AttributeAliasTbl.attribute_id},
                {AttributeAliasTbl.list_id},
                {AttributeAliasTbl.norm_alias},
                {AttributeAliasTbl.real_alias}
            ) 
            VALUES (
                {args(itertools.repeat(attribute_id, count))},
                {args(itertools.repeat(self.id, count))},
                {args(norm_aliases)},
                {args(real_aliases)} 
            )
        """)


    # --- Tasks ---

    def get_tasks(self, where: t.Callable[[Arg], str] | None = None) -> list[Task]:
        return [
            self._task_row_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.id} = {arg(id)}")
        return self._task_row_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, norm_name: NormStr) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.norm_name} = {arg(norm_name)}")
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_alias(self, norm_alias: NormStr) -> Task | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.task_id}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.id)}
                    AND {typed.TaskAlias.norm_alias} = {arg(norm_alias)}
            """)

            row = c.fetchone(typed.TaskAlias)

        if row is None:
            return None
        
        return self.get_task_by_id(row.task_id)
    
    def get_task_by_syn(self, norm_syn: NormStr) -> Task | None:
        return (
            self.get_task_by_name(norm_syn) or
            self.get_task_by_alias(norm_syn)
        )
    

    def _get_attributes_and_data_for_non_static_attribute_value_mapping[T: BaseNonStaticAttribute](self, c: queries.CursorWrapper, type: type[T], community_user_id: int) -> tuple[dict[tuple[int, int], T], dict[int, dict[int, _RawAvmT]]]:
        task_attrs = self.get_attributes(type)
        id_to_attr = {(attr.type_id, attr.id): attr for attr in task_attrs}
        del task_attrs

        AtvTable = type.tables.attribute_task_value

        query_lambda: t.Callable[[Arg], Template]
        
        if issubclass(AtvTable, typed.UserAttributeTaskValue):
            query_lambda = lambda arg: t"""
                SELECT 
                    {AtvTable.task_id},
                    {AtvTable.attribute_id},
                    {AtvTable.slot_slot},
                    {AtvTable.index}
                FROM {AtvTable}
                WHERE {AtvTable.list_id} = {arg(self.id)} AND {AtvTable.user_id} = {arg(community_user_id)}
                ORDER BY 
                    {AtvTable.task_id} ASC, 
                    {AtvTable.attribute_id} ASC, 
                    {AtvTable.index} ASC
            """
        else:
            query_lambda = lambda arg: t"""
                SELECT 
                    {AtvTable.task_id},
                    {AtvTable.attribute_id},
                    {AtvTable.slot_slot},
                    {AtvTable.index}
                FROM {AtvTable}
                WHERE {AtvTable.list_id} = {arg(self.id)}
                ORDER BY 
                    {AtvTable.task_id} ASC, 
                    {AtvTable.attribute_id} ASC, 
                    {AtvTable.index} ASC
            """
            
        c.execute(query_lambda)

        raw_data: dict[int, dict[int, _RawAvmT]] = {}
        value: list[SlotStr] = []
        prev_ta: tuple[int, int] = (-1, -1)

        for row in c.fetchall(AtvTable):
            ta = (row.task_id, row.attribute_id)

            if prev_ta == ta:
                value.append(row.slot_slot)
            else:
                raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = value
                value = [row.slot_slot]  # DO NOT CLEAR (or at least copy for data if so), otherwise list is in data is affected
                prev_ta = ta

        if value:
            raw_data[prev_ta[0]][type.type_id][prev_ta[1]] = value

        return (id_to_attr, raw_data)

    def get_tasks_attribute_value_mapping(self, user_id: int | None) -> tuple[list[AnyAttributeT], list[AttributeValueMapping]]:
        id_to_task: dict[int, Task] = {task.id: task for task in self.get_tasks()}
        type_id_and_id_to_attribute: dict[tuple[int, int], AnyAttributeT] = {}

        raw_data: dict[int, dict[int, _RawAvmT]] = {}

        ATTRIBUTES_TYPES_TO_HANDLE = (StaticAttribute, TaskAttribute) if user_id is None else ALL_ATTRIBUTE_TYPES

        with queries.connected() as c:
            user: CommunityUser | None = None

            if user_id is not None:
                jumpedia_user = self.community.jumpedia.get_jumpedia_user_by_id(user_id)

                jumpedia_user.get_community_user_by_id(user_id)
                if user is None:
                    raise errors.StructureNotFoundError(CommunityUser)
            
            del user_id
                
            # --- Static Attribute ---
            static_attrs = self.get_attributes(StaticAttribute)
            
            type_id_and_id_to_attribute |= {(attr.type_id, attr.id): attr for attr in static_attrs}

            id_attr, name_attr, aliases_attr = static_attrs
            del static_attrs

            for id, task in id_to_task.items():
                # Set all nested dictionaries once here
                raw_data[id] = {typ.type_id: {} for typ in ATTRIBUTES_TYPES_TO_HANDLE}

                static_avm: _RawAvmT = raw_data[id][StaticAttribute.type_id]

                static_avm[id_attr.id] = id_attr.raw_to_value([str(id)])
                static_avm[name_attr.id] = [task.slot_name]

            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.slot_alias}, {typed.TaskAlias.task_id}
                FROM {typed.TaskAlias}
                WHERE {typed.TaskAlias.list_id} = {arg(self.id)}
            """)

            task_id_to_aliases = itertools.groupby(c.fetchall(typed.TaskAlias), lambda row: row.task_id)

            for task_id, aliases in task_id_to_aliases:
                raw_data[task_id][StaticAttribute.type_id][aliases_attr.id] = list(alias.slot_alias for alias in aliases)

            # --- Task Attribute ---
            
            attr_mapping, new_data = self._get_attributes_and_data_for_non_static_attribute_value_mapping(c, TaskAttribute, -1)
        
            type_id_and_id_to_attribute |= attr_mapping
            raw_data.update(new_data)

            # --- User Attribute ---

            if user is not None:
                attr_mapping, new_data = self._get_attributes_and_data_for_non_static_attribute_value_mapping(c, UserAttribute, user.jumpedia_user.id)

                type_id_and_id_to_attribute |= attr_mapping
                raw_data.update(new_data)

        # --- Final Conversion ---

        final: list[AttributeValueMapping] = []

        for task_id, data in raw_data.items():
            avms = tuple(
                MappingProxyType({
                    type_id_and_id_to_attribute[(typ.type_id, attr_id)]: value 
                    for attr_id, value in data[typ.type_id].items()
                }) for typ in ATTRIBUTES_TYPES_TO_HANDLE
            )
            
            static_and_task_avm: tuple[AvmT[StaticAttribute], AvmT[TaskAttribute]] = avms[:2] # pyright: ignore[reportAssignmentType]
            user_avm: tuple[CommunityUser, AvmT[UserAttribute]] | None = None

            if user is not None:
                user_avm = (user, avms[2]) # pyright: ignore[reportAssignmentType]

            final.append(AttributeValueMapping(
                id_to_task[task_id],
                *static_and_task_avm,
                user_avm
            ))
        
        return list(type_id_and_id_to_attribute.values()), final      

    def create_task(
        self, 
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        raw_task_attribute_value_mapping: t.Mapping[int, t.Sequence[str]]
    ) -> Task:
        (real_name, *real_aliases), (norm_name, *norm_aliases) = NormStr.unique_reals_and_norms((real_name, *real_aliases))

        with self.locked:
            self._validate_task_syns(norm_name, {*norm_aliases})

            all_tasks = self.get_tasks()

            if len(all_tasks) >= self.community.limits.list_task_count_max:
                raise errors.LimitOfStructuresReachedError(self.community.limits.list_task_count_max, Task)
            
            task_attribute_value_mapping = self._cook_raw_task_attribute_value_mapping(raw_task_attribute_value_mapping)
                
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Task} (
                        {typed.Task.list_id},
                        {typed.Task.norm_name},
                        {typed.Task.slot_name}
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(norm_name)},
                        {arg(real_name)}
                    )
                """)

                task_id = c.last_generated_id 
                
                self._insert_task_aliases(c, task_id, real_aliases, norm_aliases)
                self._insert_task_attribute_value_mapping(c, task_id, task_attribute_value_mapping)

            return Task(
                list=self,
                id=task_id,
                slot_name=real_name,
                norm_name=norm_name
            )
        
    def delete_task(self, id: int):
        from . import errors

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    AND {typed.Task.id} = {arg(id)}
            """)

            if c.affected_row_count < 1:
                raise errors.StructureNotFoundError(Task)

    def edit_task_name(
        self,
        id: int,
        real_name: RealStr
    ) -> None:
        norm_name = NormStr(real_name)

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)

            if real_name == task.slot_name:
                return
            
            self._validate_task_syns(norm_name, allowed_tasks={task})

            TaskTbl = typed.Task

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    UPDATE {TaskTbl}
                    SET
                        {TaskTbl.norm_name} = {arg(norm_name)},
                        {TaskTbl.slot_name} = {arg(real_name)}
                    WHERE 
                        {TaskTbl.list_id} = {arg(self.id)}
                        AND {TaskTbl.id} = {arg(task.id)}
                """)
                
                # If the new name is an alias, remove the alias
                if norm_name in task.get_norm_aliases():
                    TaskAliasTbl = typed.TaskAlias

                    c.execute(lambda arg: t"""
                        DELETE FROM {TaskAliasTbl}
                        WHERE
                            {TaskAliasTbl.list_id} = {arg(self.id)}
                            AND {TaskAliasTbl.task_id} = {arg(task.id)}
                            AND {TaskAliasTbl.norm_alias} = {arg(norm_name)}
                    """)

                    assert c.affected_row_count == 1
            
    def edit_task_aliases(
        self, 
        id: int,
        slot_aliases: t.Iterable[SlotStr]
    ) -> None:
        slot_aliases, norm_aliases = NormStr.unique_reals_and_norms(slot_aliases)

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)

            self._validate_task_syns(
                norm_aliases=set(norm_aliases), 
                allowed_tasks={task}
            )
            
            norm_name = task.norm_name
            
            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(norm_name)
            except ValueError:
                pass
            else:
                slot_aliases = slot_aliases[:idx] + slot_aliases[idx + 1:]
                norm_aliases = norm_aliases[:idx] + norm_aliases[idx + 1:]
            
            del norm_name
            
            TaskAliasTbl = typed.TaskAlias

            with queries.connected() as c:
                # Delete all aliases
                c.execute(lambda arg: t"""
                    DELETE FROM {TaskAliasTbl}
                    WHERE 
                        {TaskAliasTbl.list_id} = {arg(self.id)}
                        AND {TaskAliasTbl.task_id} = {arg(task.id)}
                """)

                self._insert_task_aliases(c, task.id, slot_aliases, norm_aliases)

    def edit_task_attribute_value_mapping(
        self,
        id: int,
        raw_task_attribute_value_mapping: t.Mapping[int, t.Sequence[str]]
    ):
        from . import errors

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise errors.StructureNotFoundError(Task)
            
            task_attribute_value_mapping = self._cook_raw_task_attribute_value_mapping(
                raw_task_attribute_value_mapping
            )

            AttrTaskValueTbl = TaskAttribute.tables.attribute_task_value

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    DELETE FROM {AttrTaskValueTbl}
                    WHERE
                        {AttrTaskValueTbl.task_id} = {arg(task.id)}
                """)

                self._insert_task_attribute_value_mapping(c, task.id, task_attribute_value_mapping)
        
    def _fetch_tasks_from_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.Task]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result = c.fetchall(typed.Task)

        return result
    
    def _task_row_to_obj(self, row: typed.Task) -> Task:
        return Task(
            list=self,
            id=row.id,
            slot_name=row.slot_name,
            norm_name=row.norm_name
        )
    
    def _insert_task_aliases(
        self, 
        c: queries.CursorWrapper, 
        task_id: int,
        slot_aliases: t.Sequence[SlotStr], 
        norm_aliases: t.Sequence[NormStr]
    ) -> None:
        if not norm_aliases:
            return
        
        count = len(norm_aliases)
        TaskAliasTbl = typed.TaskAlias

        c.executemany(lambda args: t"""
            INSERT INTO {TaskAliasTbl} (
                {TaskAliasTbl.task_id},
                {TaskAliasTbl.list_id},
                {TaskAliasTbl.norm_alias},
                {TaskAliasTbl.slot_alias},
            ) 
            VALUES (
                {args(itertools.repeat(task_id, count))}, 
                {args(itertools.repeat(self.id, count))}, 
                {args(norm_aliases)},
                {args(slot_aliases)}
            )
        """)

    def _insert_task_attribute_value_mapping(
        self,
        c: queries.CursorWrapper,
        task_id: int,
        task_attribute_value_mapping: dict[TaskAttribute, list[SlotStr]]
    ) -> None:
        if not task_attribute_value_mapping:
            return
        
        TaskValueTbl = TaskAttribute.tables.attribute_task_value

        # This is so clean I'm UwU-ing
        attribute_id_args: list[int] = []
        index_args: list[int] = []
        slot_args: list[SlotTypeT] = []

        for attr, v in task_attribute_value_mapping.items():
            for i, slot in enumerate(v):
                attribute_id_args.append(attr.id)
                index_args.append(i)
                slot_args.append(slot)

        c.executemany(lambda args: t"""
            INSERT INTO {TaskValueTbl} (
                {TaskValueTbl.task_id},
                {TaskValueTbl.attribute_id},
                {TaskValueTbl.index},
                {TaskValueTbl.slot_slot}
            )
            VALUES (
                {args(itertools.repeat(task_id, len(attribute_id_args)))},
                {args(attribute_id_args)},
                {args(index_args)},
                {args(slot_args)}
            )
        """)

    def _validate_task_syns(
        self, 
        norm_name: NormStr | None = None, 
        norm_aliases: t.AbstractSet[NormStr] = frozenset(), 
        allowed_tasks: t.AbstractSet[Task] = frozenset()
    ) -> None:
        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)
        
        if norm_aliases:
            norm_syns.update(norm_aliases)
        
        if len(norm_aliases) > self.community.jumpedia.limits.attribute_task_value_slot_count_max:
            raise feedbacks.temp("Too many aliases")
        
        for normed_syn in norm_syns:
            if len(normed_syn) > self.community.jumpedia.limits.attribute_task_value_slot_length_max:
                raise feedbacks.temp("Too long syn")
            
            task = self.get_task_by_syn(normed_syn)

            if task not in allowed_tasks:
                raise feedbacks.temp(f"Task syn {normed_syn!r} already taken!")
            
    def _validate_attribute_syns(
        self, 
        norm_name: NormStr | None = None, 
        norm_aliases: t.AbstractSet[NormStr] = frozenset(), 
        allowed_attributes: t.AbstractSet[BaseAttribute] = frozenset()
    ) -> None:
        norm_syns: set[NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)
        
        if norm_aliases:
            norm_syns.update(norm_aliases)
        
        if len(norm_aliases) > self.community.limits.attribute_alias_count_max:
            raise feedbacks.temp("Too many aliases")
        
        for normed_syn in norm_syns:
            if len(normed_syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                raise feedbacks.temp("Too long syn")
            
            attribute = self.get_any_attribute_by_syn(normed_syn)

            if attribute not in allowed_attributes:
                raise feedbacks.temp(f"Attribute syn {normed_syn!r} already taken!")