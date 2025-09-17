from dataclasses import dataclass
import itertools
from string.templatelib import Template
from typing import TYPE_CHECKING, AbstractSet, Callable, ClassVar, Final, Literal, NamedTuple, Sequence, get_args, overload

from database import queries 
from database.simple_orm import Arg, Rows
from errors.feedback import feedbacks
from structures.attribute.slot_type import SlotType, SlotTypeT
from structures import BaseStructure
from structures.attribute import ANY_ATTRIBUTE, AnyAttributeT, AttributeValueParseTypesT, BaseAttribute, BaseNonStaticAttribute, RawCollectionT
from structures.attribute.static_attribute import StaticAttribute
from structures.attribute.task_attribute import TaskAttribute
from structures.attribute.user_attribute import UserAttribute
from structures.errors import StructureNotFoundError
from structures.task import Task
from utils import text
from database import typed

if TYPE_CHECKING:
    from structures.community import Community


STATIC_ATTRIBUTE_KIND_OF_ID: Final = 1
STATIC_ATTRIBUTE_KIND_OF_NAME: Final = 2
STATIC_ATTRIBUTE_KIND_OF_ALIASES: Final = 3

type KindsT = Literal[1, 2, 3]
KINDS: tuple[Literal[1], Literal[2], Literal[3]] = get_args(KindsT.__value__)


@dataclass(frozen=True, kw_only=True)
class List(BaseStructure):
    community: 'Community'
    id: int
    real_name: text.RealStr
    norm_name: text.NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.community.identity)


    # --- All Attributes ---

    def get_attributes[T: BaseAttribute](self, type: type[T]) -> set[T]:
        return {
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute, None)
        }

    def get_attribute_by_id[T: BaseAttribute](self, type: type[T], id: int) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.id} = {arg(id)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_name[T: BaseAttribute](self, type: type[T], norm_name: text.NormStr) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.norm_name} = {arg(norm_name)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None
    
    def get_attribute_by_alias[T: BaseAttribute](self, type: type[T], norm_alias: text.NormStr) -> T | None:
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
    
    def get_attribute_by_syn[T: BaseAttribute](self, type: type[T], norm_syn: text.NormStr) -> T | None:
        return (
            self.get_attribute_by_name(type, norm_syn)
            or self.get_attribute_by_alias(type, norm_syn)
        )

    def get_all_attributes_flat(self) -> tuple[AnyAttributeT, ...]:
        return tuple(
            attr
            for type in ANY_ATTRIBUTE
                for attr in self.get_attributes(type)
        )
    
    def get_all_attributes(self) -> tuple[set[StaticAttribute], set[TaskAttribute], set[UserAttribute]]:
        return tuple(
            self.get_attributes(type)
            for type in ANY_ATTRIBUTE
        )  # type: ignore

    def get_any_attribute_by_id(self, id: int) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_id(type, id)

            if attr is not None:
                return attr
        
    def get_any_attribute_by_name(self, norm_name: text.NormStr) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_name(type, norm_name)
            
            if attr is not None:
                return attr
        
    def get_any_attribute_by_alias(self, norm_alias: text.NormStr) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_alias(type, norm_alias)
            
            if attr is not None:
                return attr

    def get_any_attribute_by_syn(self, norm_syn: text.NormStr) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_syn(type, norm_syn)
            
            if attr is not None:
                return attr
            
    def get_static_attribute_by_kind(self, kind: KindsT) -> StaticAttribute:
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

    @overload
    def create_attribute[T: StaticAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        min_slots: int,
        kind: int
    ) -> T:
        pass

    @overload
    def create_attribute[T: BaseNonStaticAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        raw_collection: RawCollectionT
    ) -> T:
        pass

    def create_attribute[T: BaseAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        min_slots: int = 0,
        kind: int = 0,
        raw_collection: RawCollectionT | None = None
    ) -> T:  # Higher kinded attributes not supported yet, otherwise T[TSlot]
        if (min_slots or kind) == issubclass(type, BaseNonStaticAttribute):
            raise ValueError("Typing not followed on attribute creation #1")
        
        if (raw_collection is None) == issubclass(type, BaseNonStaticAttribute):
            raise ValueError("Typing not followed on attribute creation #2")

        (real_name, *real_aliases), (norm_name, *norm_aliases) = text.raws_to_unique_reals_and_norms({raw_name, *raw_aliases})

        del raw_name
        del raw_aliases

        with self.locked:
            attrs = self.get_all_attributes_flat()

            if len(attrs) >= self.community.limits.list_attribute_count_max:
                raise feedbacks.temp("Max attributes reached")
            
            for syn in (norm_name, *norm_aliases):
                if len(syn) > self.community.jumpedia.limits.attribute_syn_length_max:
                    raise feedbacks.temp("Max syn length exceeded")
                
                if self.get_any_attribute_by_syn(syn) is not None:
                    raise feedbacks.temp(f"Attribute name or alias `{syn}` already used as name or alias of different attribute")
                
            if not (min_slots <= max_slots <= self.community.limits.attribute_task_value_slot_count_max):
                raise feedbacks.temp("Max slots must be between 1 and 32 inclusive")
            
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
                    max_slots=max_slots
                )

                if raw_collection:
                    assert isinstance(attribute, BaseNonStaticAttribute)
                    attribute.set_collection(raw_collection)
                    
                return attribute

    def delete_attribute(self, type: type[BaseAttribute], id: int) -> None:
        AttributeTbl = type.tables.attribute

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {AttributeTbl}
                WHERE {AttributeTbl.list_id} = {arg(self.id)}
                AND {AttributeTbl.id} = {arg(id)}
            """)

            if c.affected_row_count <= 0:
                raise StructureNotFoundError(type)

    def edit_attribute_name(
        self, 
        type: type[BaseAttribute], 
        id: int, 
        raw_name: str
    ) -> None:
        real_name, norm_name = text.raw_to_real_and_norm(raw_name)
        del raw_name

        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise StructureNotFoundError(type)

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
        raw_aliases: frozenset[str]
    ) -> None:
        (*real_aliases,), (*norm_aliases,) = text.raws_to_unique_reals_and_norms(raw_aliases)
        del raw_aliases
        
        with self.locked:
            attribute = self.get_attribute_by_id(type, id)

            if attribute is None:
                raise StructureNotFoundError(type)

            self._validate_attribute_syns(
                norm_aliases={*norm_aliases}, 
                allowed_attributes={attribute}
            )
            
            norm_name = text.real_to_norm(attribute.real_name)
            
            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(norm_name)
            except ValueError:
                pass
            else:
                real_aliases.pop(idx)
                norm_aliases.pop(idx)
            
            del norm_name
            
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
        where: Callable[[Arg], str] | None
    ) -> Rows[T]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {table_type}
                WHERE 
                    {table_type.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

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
        raw_task_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ) -> dict[TaskAttribute, list[SlotTypeT]]:
        id_to_attr = {attr.id: attr for attr in self.get_attributes(TaskAttribute)}
            
        # Check if all required attributes are given
        for attr in id_to_attr.values():
            if attr.required and attr.id not in raw_task_attribute_value_mapping:
                raise feedbacks.temp(f"Attribute {attr} is required (min >= 1 slots) but it received no values")
        
        if not raw_task_attribute_value_mapping:
            return {}
        
        attribute_value_mapping: dict[TaskAttribute, list[SlotTypeT]] = {}
        
        # Convert ids to attributes and validate value
        for attr_id, v in raw_task_attribute_value_mapping.items():
            if attr_id not in id_to_attr:
                raise feedbacks.temp("Attribute id not found")
            
            attr = id_to_attr[attr_id]
            v = attr.value_from_loaded(v)

            attribute_value_mapping[attr] = v

        return attribute_value_mapping
    
    
    def _insert_attribute_aliases(
        self, 
        c: queries.CursorWrapper, 
        type: type[BaseAttribute], 
        attribute_id: int, 
        real_aliases: Sequence[text.RealStr],
        norm_aliases: Sequence[text.NormStr]
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

    def get_tasks(self, where: Callable[[Arg], str] | None = None) -> set[Task]:
        return {
            self._task_row_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        }

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.id} = {arg(id)}")
        return self._task_row_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, norm_name: text.NormStr) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.norm_name} = {arg(norm_name)}")
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_alias(self, norm_alias: text.NormStr) -> Task | None:
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
    
    def get_task_by_syn(self, norm_syn: text.NormStr) -> Task | None:
        return (
            self.get_task_by_name(norm_syn) or
            self.get_task_by_alias(norm_syn)
        )
    
    def create_task(
        self, 
        raw_name: str, 
        raw_aliases: frozenset[str], 
        raw_task_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ) -> Task:
        (real_name, *real_aliases), (norm_name, *norm_aliases) = text.raws_to_unique_reals_and_norms((raw_name, *raw_aliases))
        del raw_name, raw_aliases

        with self.locked:
            self._validate_task_syns(norm_name, {*norm_aliases})

            all_tasks = self.get_tasks()

            if len(all_tasks) >= self.community.limits.list_task_count_max:
                raise feedbacks.temp("Task limit reached")
            
            task_attribute_value_mapping = self._cook_raw_task_attribute_value_mapping(raw_task_attribute_value_mapping)
                
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Task} (
                        {typed.Task.list_id},
                        {typed.Task.norm_name},
                        {typed.Task.real_name}
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
                real_name=real_name,
                norm_name=norm_name
            )
        
    def delete_task(self, id: int):
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    AND {typed.Task.id} = {arg(id)}
            """)

            if c.affected_row_count < 1:
                raise StructureNotFoundError(Task)

    def edit_task_name(
        self,
        id: int,
        raw_name: str
    ) -> None:
        real_name, norm_name = text.raw_to_real_and_norm(raw_name)
        del raw_name

        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise StructureNotFoundError(Task)

            if real_name == task.real_name:
                return
            
            self._validate_task_syns(norm_name, allowed_tasks={task})

            TaskTbl = typed.Task

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    UPDATE {TaskTbl}
                    SET
                        {TaskTbl.norm_name} = {arg(norm_name)},
                        {TaskTbl.real_name} = {arg(real_name)}
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
        raw_aliases: frozenset[str]
    ) -> None:
        (*real_aliases,), (*norm_aliases,) = text.raws_to_unique_reals_and_norms(raw_aliases)
        del raw_aliases
        
        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise StructureNotFoundError(Task)

            self._validate_task_syns(
                norm_aliases={*norm_aliases}, 
                allowed_tasks={task}
            )
            
            norm_name = text.real_to_norm(task.real_name)
            
            # If an alias is the name already, remove it
            try:
                idx = norm_aliases.index(norm_name)
            except ValueError:
                pass
            else:
                real_aliases.pop(idx)
                norm_aliases.pop(idx)
            
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

                self._insert_task_aliases(c, task.id, real_aliases, norm_aliases)

    def edit_task_attribute_value_mapping(
        self,
        id: int,
        raw_task_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ):
        with self.locked:
            task = self.get_task_by_id(id)

            if task is None:
                raise StructureNotFoundError(Task)
            
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
        
    def _fetch_tasks_from_table(self, where: Callable[[Arg], str] | None) -> Rows[typed.Task]:
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
            real_name=row.real_name,
            norm_name=row.norm_name
        )
    
    def _insert_task_aliases(
        self, 
        c: queries.CursorWrapper, 
        task_id: int,
        real_aliases: Sequence[text.RealStr], 
        norm_aliases: Sequence[text.NormStr]
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
                {TaskAliasTbl.real_alias},
            ) 
            VALUES (
                {args(itertools.repeat(task_id, count))}, 
                {args(itertools.repeat(self.id, count))}, 
                {args(norm_aliases)},
                {args(real_aliases)}
            )
        """)

    def _insert_task_attribute_value_mapping(
        self,
        c: queries.CursorWrapper,
        task_id: int,
        task_attribute_value_mapping: dict[TaskAttribute, list[SlotTypeT]]
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
                {TaskValueTbl.real_slot}
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
        norm_name: text.NormStr | None = None, 
        norm_aliases: AbstractSet[text.NormStr] = frozenset(), 
        allowed_tasks: AbstractSet[Task] = frozenset()
    ) -> None:
        norm_syns: set[text.NormStr] = set()

        if norm_name is not None:
            norm_syns.add(norm_name)
        
        if norm_aliases:
            norm_syns.update(norm_aliases)
        
        if len(norm_aliases) > self.community.limits.attribute_task_value_slot_count_max:
            raise feedbacks.temp("Too many aliases")
        
        for normed_syn in norm_syns:
            if len(normed_syn) > self.community.jumpedia.limits.attribute_task_value_slot_length_max:
                raise feedbacks.temp("Too long syn")
            
            task = self.get_task_by_syn(normed_syn)

            if task not in allowed_tasks:
                raise feedbacks.temp(f"Task syn {normed_syn!r} already taken!")
            
    def _validate_attribute_syns(
        self, 
        norm_name: text.NormStr | None = None, 
        norm_aliases: AbstractSet[text.NormStr] = frozenset(), 
        allowed_attributes: AbstractSet[BaseAttribute] = frozenset()
    ) -> None:
        norm_syns: set[text.NormStr] = set()

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