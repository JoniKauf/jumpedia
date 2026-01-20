from asyncio import taskgroups
import enum
import itertools
import operator
import typing as t
from types import EllipsisType, MappingProxyType

from structures import attribute
from utils import orm, text
from utils.text import NormStr, RealStr

from . import BaseStructure, db, errors, utils_
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
from .task import Task
from .task.attribute_value_mapping import (
    AttributeValueMapping,
    AvmT,
    UserAttributeValueMapping,
)
from .user import CommunityUser

if t.TYPE_CHECKING:
    from .community import Community

from . import utils_


class Kind(enum.IntEnum):
    ID = 0
    NAME = 1
    ALIAS = 2


class _StaticAttributePredefinedData(t.NamedTuple):
    real_name: RealStr
    norm_name: NormStr
    slot_type: type[SlotTypeT]
    position: int
    min_slots: int
    max_slots: int
    kind: Kind


KIND_TO_PREDEFINED_DATA: t.Final[
    MappingProxyType[Kind, _StaticAttributePredefinedData]
] = MappingProxyType(
    {
        Kind.ID: _StaticAttributePredefinedData(
            real_name=RealStr(real_name := "Id"),
            norm_name=NormStr(real_name),
            slot_type=int,
            position=0,
            min_slots=1,
            max_slots=1,
            kind=Kind.ID,
        ),
        Kind.NAME: _StaticAttributePredefinedData(
            real_name=RealStr(real_name := "Name"),
            norm_name=NormStr(real_name),
            slot_type=str,
            position=1,
            min_slots=1,
            max_slots=1,
            kind=Kind.NAME,
        ),
        Kind.ALIAS: _StaticAttributePredefinedData(
            real_name=RealStr(real_name := "Alias"),
            norm_name=NormStr(real_name),
            slot_type=str,
            position=2,
            min_slots=0,
            max_slots=32,
            kind=Kind.ALIAS,
        ),
    }
)

type _RawAvmT = dict[int, tuple[SlotStr, ...]]


AttributeTable = db.Attribute
AttributeAliasTable = db.AttributeAlias
AttributeCollectionEntryTable = db.AttributeCollectionEntry
AttributeCollectionEntryAliasTable = db.AttributeCollectionEntryAlias
TaskAttributeValueTable = db.TaskAttributeValue
CommunityUserTaskTable = db.CommunityUserTask
CommunityUserTaskAttributeValueTable = db.CommunityUserTaskAttributeValue

type _AttributeTypeT[T: AnyAttributeT = AnyAttributeT] = type[T] | tuple[type[T], ...]


def _attribute_type_to_where(
    type: _AttributeTypeT | None,
) -> tuple[()] | tuple[tuple[t.Any, orm.Operator, t.Any]] | None:
    where: (
        tuple[orm.Column[db.Attribute, int], t.Literal[orm.Operator.EQ], int]
        | tuple[
            orm.Column[db.Attribute, int], t.Literal[orm.Operator.IN], t.Iterable[int]
        ]
        | None
    )

    if type is None:
        where = None

    elif not isinstance(type, tuple):
        where = (db.Attribute.type_id, orm.Operator.EQ, type.type_id)

    elif len(type) == 0:
        return None

    elif len(type) == 1:
        where = (db.Attribute.type_id, orm.Operator.EQ, type[0].type_id)

    else:
        where = (
            db.Attribute.type_id,
            orm.Operator.IN,
            (attr_type.type_id for attr_type in type),
        )

    return () if where is None else (where,)


class List(BaseStructure):
    community: Community
    real_name: RealStr
    norm_name: NormStr

    @property
    def name(self) -> str:
        return self.real_name

    def _where_this_list[T: orm.Column[t.Any, int]](
        self, col: T
    ) -> tuple[T, t.Literal[orm.Operator.EQ], int]:
        return (col, orm.Operator.EQ, self.id)

    @t.overload
    def _get_attributes_from_this_list_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any], type: None = ...
    ) -> map[AnyAttributeT]:
        pass

    @t.overload
    def _get_attributes_from_this_list_inner[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        *where: tuple[t.Any, orm.Operator, t.Any],
        type: type[T] | tuple[type[T], ...],
    ) -> map[T]:
        pass

    def _get_attributes_from_this_list_inner(
        self,
        c: orm.Cursor,
        *where: tuple[t.Any, orm.Operator, t.Any],
        type: type[AnyAttributeT] | tuple[type[AnyAttributeT], ...] | None = None,
    ) -> map[AnyAttributeT]:
        type_where = _attribute_type_to_where(type)

        if type_where is None:
            return map(lambda _: _, ())

        return map(
            self._attribute_row_to_obj,
            c.fetch_all(
                db.Attribute.select("*").where(
                    self._where_this_list(db.Attribute.list_id),
                    *type_where,
                    *where,
                )
            ),
        )

    @t.overload
    def _attribute_row_to_obj(
        self, row: db.Attribute, expected_type: None = ...
    ) -> AnyAttributeT:
        pass

    @t.overload
    def _attribute_row_to_obj[T: AnyAttributeT](
        self, row: db.Attribute, expected_type: type[T]
    ) -> T:
        pass

    def _attribute_row_to_obj(
        self, row: db.Attribute, expected_type: type[AnyAttributeT] | None = None
    ) -> AnyAttributeT:
        found_type = attribute.type_id_to_type(row.type_id)  # type: ignore

        assert expected_type is None or expected_type is found_type

        return found_type(
            list=self,
            id=row.id,
            real_name=text.RealStr(row.real_name, check=False),
            norm_name=text.NormStr(row.norm_name, check=False),
            slot_type=SLOT_TYPES[row.slot_type],
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots,
            kind=None if row.kind is None else Kind(row.kind),  # type: ignore
        )

    def get_attributes_grouped(
        self, c: orm.Cursor, /
    ) -> tuple[list[StaticAttribute], list[TaskAttribute], list[UserAttribute]]:
        result: tuple[
            list[StaticAttribute], list[TaskAttribute], list[UserAttribute]
        ] = ([], [], [])

        for attr in self._get_attributes_from_this_list_inner(c):
            result[type(attr).type_id].append(attr)  # type: ignore

        return result

    @t.overload
    def get_attributes(self, c: orm.Cursor, /, type: None = ...) -> list[AnyAttributeT]:
        pass

    @t.overload
    def get_attributes[T: AnyAttributeT](
        self, c: orm.Cursor, /, type: _AttributeTypeT[T]
    ) -> list[T]:
        pass

    def get_attributes(
        self, c: orm.Cursor, /, type: _AttributeTypeT | None = None
    ) -> list[AnyAttributeT]:
        return list(self._get_attributes_from_this_list_inner(c, type=type))

    @t.overload
    def get_attribute_by_id(
        self, c: orm.Cursor, id: int, /, type: None = ...
    ) -> tuple[AnyAttributeT, int] | None:
        pass

    @t.overload
    def get_attribute_by_id[T: AnyAttributeT](
        self, c: orm.Cursor, id: int, /, type: type[T]
    ) -> tuple[T, int] | None:
        pass

    def get_attribute_by_id(
        self, c: orm.Cursor, id: int, /, type: _AttributeTypeT | None = None
    ) -> tuple[AnyAttributeT, int] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_attributes_by_id(c, (id,), type=type)
        )

    @t.overload
    def get_attributes_by_id(
        self, c: orm.Cursor, ids: t.Collection[int] | EllipsisType, /, type: None = ...
    ) -> dict[int, AnyAttributeT]:
        pass

    @t.overload
    def get_attributes_by_id[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        ids: t.Collection[int] | EllipsisType,
        /,
        type: _AttributeTypeT[T],
    ) -> dict[int, T]:
        pass

    def get_attributes_by_id(
        self,
        c: orm.Cursor,
        ids: t.Collection[int] | EllipsisType,
        /,
        type: _AttributeTypeT | None = None,
    ) -> dict[int, AnyAttributeT]:
        return {
            attr.id: attr
            for attr in (
                self._get_attributes_from_this_list_inner(c, type=type)
                if ids is ...
                else self._get_attributes_from_this_list_inner(
                    c, (db.Attribute.id, orm.Operator.IN, ids), type=type
                )
            )
        }

    @t.overload
    def get_attribute_by_name(
        self, c: orm.Cursor, name: NormStr, /, type: None = ...
    ) -> tuple[AnyAttributeT, RealStr] | None:
        pass

    @t.overload
    def get_attribute_by_name[T: AnyAttributeT](
        self, c: orm.Cursor, name: NormStr, /, type: _AttributeTypeT[T]
    ) -> tuple[T, RealStr] | None:
        pass

    def get_attribute_by_name(
        self, c: orm.Cursor, name: NormStr, /, type: _AttributeTypeT | None = None
    ) -> tuple[AnyAttributeT, RealStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_attributes_by_name(c, (name,), type=type)
        )

    @t.overload
    def get_attributes_by_name(
        self,
        c: orm.Cursor,
        names: t.Collection[NormStr] | EllipsisType,
        /,
        type: None = ...,
    ) -> dict[RealStr, AnyAttributeT]:
        pass

    @t.overload
    def get_attributes_by_name[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        names: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT[T],
    ) -> dict[RealStr, T]:
        pass

    def get_attributes_by_name(
        self,
        c: orm.Cursor,
        names: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT | None = None,
    ) -> dict[RealStr, AnyAttributeT]:
        return {
            attr.real_name: attr
            for attr in (
                self._get_attributes_from_this_list_inner(c, type=type)
                if names is ...
                else self._get_attributes_from_this_list_inner(
                    c, (db.Attribute.norm_name, orm.Operator.IN, names), type=type
                )
            )
        }

    @t.overload
    def get_attribute_by_alias(
        self, c: orm.Cursor, alias: NormStr, /, type: None = ...
    ) -> tuple[AnyAttributeT, RealStr] | None:
        pass

    @t.overload
    def get_attribute_by_alias[T: AnyAttributeT](
        self, c: orm.Cursor, alias: NormStr, /, type: _AttributeTypeT[T]
    ) -> tuple[T, RealStr] | None:
        pass

    def get_attribute_by_alias(
        self, c: orm.Cursor, alias: NormStr, /, type: _AttributeTypeT | None = None
    ) -> tuple[AnyAttributeT, RealStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_attributes_by_alias(c, (alias,), type=type)
        )

    @t.overload
    def get_attributes_by_alias(
        self,
        c: orm.Cursor,
        aliases: t.Collection[NormStr] | EllipsisType,
        /,
        type: None = ...,
    ) -> dict[text.RealStr, AnyAttributeT]:
        pass

    @t.overload
    def get_attributes_by_alias[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        aliases: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT[T],
    ) -> dict[text.RealStr, T]:
        pass

    def get_attributes_by_alias(
        self,
        c: orm.Cursor,
        aliases: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT | None = None,
    ) -> dict[text.RealStr, AnyAttributeT]:
        type_where = _attribute_type_to_where(type)

        if type_where is None:
            return {}

        rows = c.fetch_all(
            db.AttributeAlias.select(
                db.AttributeAlias.attribute_id,
                db.AttributeAlias.real_alias,
            ).where(
                self._where_this_list(db.AttributeAlias.list_id),
                *type_where,
                *(
                    ()
                    if aliases is ...
                    else (
                        (
                            db.AttributeAlias.norm_alias,
                            orm.Operator.IN,
                            aliases,
                        ),
                    )
                ),
            )
        )

        if not rows:
            return {}

        attr_id_to_real_str_aliases: dict[int, tuple[text.RealStr, ...]] = {
            attr_id: tuple(text.RealStr(row.real_alias, check=False) for row in rows)
            for attr_id, rows in itertools.groupby(rows, lambda row: row.attribute_id)
        }

        attrs = self.get_attributes_by_id(c, attr_id_to_real_str_aliases)

        return {
            real_alias: attr
            for attr in attrs.values()
            for real_alias in attr_id_to_real_str_aliases[attr.id]
        }

    @t.overload
    def get_attribute_by_syn(
        self, c: orm.Cursor, syn: NormStr, /, type: None = ...
    ) -> tuple[AnyAttributeT, RealStr] | None:
        pass

    @t.overload
    def get_attribute_by_syn[T: AnyAttributeT](
        self, c: orm.Cursor, syn: NormStr, /, type: _AttributeTypeT[T]
    ) -> tuple[T, RealStr] | None:
        pass

    def get_attribute_by_syn(
        self, c: orm.Cursor, syn: NormStr, /, type: _AttributeTypeT | None = None
    ) -> tuple[AnyAttributeT, RealStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_attributes_by_syn(c, (syn,), type=type)
        )

    @t.overload
    def get_attributes_by_syn(
        self,
        c: orm.Cursor,
        syns: t.Collection[NormStr] | EllipsisType,
        /,
        type: None = ...,
    ) -> dict[text.RealStr, AnyAttributeT]:
        pass

    @t.overload
    def get_attributes_by_syn[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        syns: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT[T],
    ) -> dict[text.RealStr, T]:
        pass

    def get_attributes_by_syn(
        self,
        c: orm.Cursor,
        syns: t.Collection[NormStr] | EllipsisType,
        /,
        type: _AttributeTypeT | None = None,
    ) -> dict[text.RealStr, AnyAttributeT]:
        by_name = self.get_attributes_by_name(c, syns, type=type)

        if syns is not ... and len(by_name) >= len(syns):
            return by_name  # type: ignore

        return by_name | self.get_attributes_by_alias(c, syns, type=type)  # type: ignore

    print("uwu")

    def get_static_attribute_by_kind(
        self, c: orm.Cursor, kind: Kind, /
    ) -> StaticAttribute:
        if kind not in Kind:
            raise ValueError(f"Kind {kind} is not valid")

        rows = tuple(
            self._get_attributes_from_this_list_inner(
                c, (AttributeTable.kind, orm.Operator.EQ, kind), type=StaticAttribute
            )
        )

        assert len(rows) == 1

        return rows[0]

    def _get_default_static_attribute(
        self, kind: Kind, id: int = -1, /
    ) -> StaticAttribute:
        if kind in (Kind.ID, Kind.NAME, Kind.ALIAS):
            return StaticAttribute(
                list=self, id=id, **KIND_TO_PREDEFINED_DATA[kind]._asdict()
            )

        t.assert_never(kind.value)

    @t.overload
    def create_attribute[T: StaticAttribute](
        self,
        c: orm.Cursor,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: type[SlotTypeT],
        max_slots: int,
        *,
        position: int,
        min_slots: int,
        kind: Kind,
    ) -> T:
        pass

    @t.overload
    def create_attribute[T: TaskAttribute | UserAttribute](
        self,
        c: orm.Cursor,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: type[SlotTypeT],
        max_slots: int,
        *,
        collection: t.Sequence[tuple[RealStr, t.Iterable[RealStr]]] = (),
    ) -> T:
        pass

    def create_attribute[T: AnyAttributeT](
        self,
        c: orm.Cursor,
        type: type[T],
        real_name: RealStr,
        real_aliases: t.Iterable[RealStr],
        slot_type: type[SlotTypeT],
        max_slots: int,
        *,
        position: int = -1,
        min_slots: int = 0,
        kind: Kind | None = None,
        collection: t.Sequence[tuple[RealStr, t.Iterable[RealStr]]] = (),
    ) -> T:
        assert position >= -1

        assert (position >= 0) == issubclass(
            type, StaticAttribute
        ), "Typing not followed on attribute creation #1"

        assert (min_slots or kind) != issubclass(
            type, BaseNonStaticAttribute
        ), "Typing not followed on attribute creation #2"
        assert not (
            issubclass(type, StaticAttribute) and collection
        ), "Typing not followed on attribute creation #3"

        (real_name, *real_aliases), (norm_name, *norm_aliases) = (
            utils_.handled_unique_reals_and_norms((real_name, *real_aliases))
        )

        attrs = self.get_attributes(c)

        self._validate_attribute_syns(c, type, norm_name, frozenset(norm_aliases))

        if not (
            0
            <= min_slots
            <= max_slots
            <= self.community.limits.attribute_task_value_slot_count_max
            and max_slots >= 1
        ):
            raise errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError(
                min_slots,
                max_slots,
                0,
                self.community.limits.attribute_task_value_slot_count_max,
            )

        if position == -1:
            position = max(attr.position for attr in attrs) + 1 if attrs else 0

        AttributeTable = db.Attribute

        execute_data = c.execute(
            AttributeTable.insert(
                AttributeTable.list_id.bind(self.id),
                AttributeTable.type_id.bind(type.type_id),
                AttributeTable.norm_name.bind(norm_name),
                AttributeTable.real_name.bind(real_name),
                AttributeTable.slot_type.bind(SLOT_TYPES.index(slot_type)),
                AttributeTable.position.bind(position),
                AttributeTable.min_slots.bind(min_slots),
                AttributeTable.max_slots.bind(max_slots),
                AttributeTable.kind.bind(None if kind is None else kind.value),
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
            kind=kind,  # type: ignore
        )

        if collection:
            assert isinstance(
                attribute, BaseNonStaticAttribute
            ), "Typing not followed on attribute creation #4"
            attribute.set_collection(c, collection)

        return attribute

    def delete_attribute(
        self, c: orm.Cursor, type: type[AnyAttributeT], id: int
    ) -> None:
        if issubclass(type, StaticAttribute):
            raise RuntimeError(
                "Static Attributes have no business being deleted manually!! Wtf did you cook?!"
            )

        AttributeTable = db.Attribute

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
        self, c: orm.Cursor, type: type[AnyAttributeT], id: int, real_name: RealStr
    ) -> None:
        norm_name = NormStr(real_name)

        tup = self.get_attribute_by_id(c, id, type=type)

        if tup is None:
            raise errors.StructureNotFoundError(type)

        attr, _ = tup
        del tup

        if real_name == attr.real_name:
            return

        self._validate_attribute_syns(
            c, type, norm_name, allowed_attributes=frozenset([attr])
        )

        AttributeTable = db.Attribute

        execute_data = c.execute(
            AttributeTable.update(
                AttributeTable.norm_name.set(norm_name),
                AttributeTable.real_name.set(real_name),
            ).where(
                self._where_this_list(AttributeTable.list_id),
                (AttributeTable.id, orm.Operator.EQ, attr.id),
            ),
            get_affected_row_count=True,
        )

        assert execute_data.affected_row_count == 1

        # If the new name is an alias, remove the alias
        if norm_name in attr.get_norm_aliases(c):
            AttributeAliasTable = db.AttributeAlias

            c.execute(
                AttributeAliasTable.delete().where(
                    self._where_this_list(AttributeAliasTable.list_id),
                    (
                        AttributeAliasTable.attribute_type_id,
                        orm.Operator.EQ,
                        type.type_id,
                    ),
                    (
                        AttributeAliasTable.attribute_id,
                        orm.Operator.EQ,
                        attr.id,
                    ),
                    (
                        AttributeAliasTable.norm_alias,
                        orm.Operator.EQ,
                        norm_name,
                    ),
                )
            )

    def edit_attribute_aliases(
        self,
        c: orm.Cursor,
        type: type[AnyAttributeT],
        id: int,
        aliases: t.Iterable[RealStr],
    ) -> None:
        (*real_aliases,), (*norm_aliases,) = utils_.handled_unique_reals_and_norms(
            aliases
        )

        tup = self.get_attribute_by_id(c, id, type=type)

        if tup is None:
            raise errors.StructureNotFoundError(type)

        attr, _ = tup
        del tup

        self._validate_attribute_syns(
            c,
            type,
            norm_aliases=frozenset(norm_aliases),
            allowed_attributes=frozenset([attr]),
        )

        # If an alias is the name already, remove it
        try:
            idx = norm_aliases.index(attr.norm_name)
        except ValueError:
            pass
        else:
            real_aliases.pop(idx)
            norm_aliases.pop(idx)

        # Delete all aliases
        c.execute(
            AttributeAliasTable.delete().where(
                self._where_this_list(AttributeAliasTable.list_id),
                (AttributeAliasTable.attribute_type_id, orm.Operator.EQ, type.type_id),
                (
                    AttributeAliasTable.attribute_id,
                    orm.Operator.EQ,
                    attr.id,
                ),
            )
        )

        self._insert_attribute_aliases(c, type, attr.id, real_aliases, norm_aliases)

    def _calc_attribute_value_mapping[T: TaskAttribute | UserAttribute](
        self,
        c: orm.Cursor,
        type: type[T],
        attribute_value_mapping: t.Mapping[int, t.Sequence[RealStr]],
    ) -> MappingProxyType[T, tuple[SlotStr, ...]]:
        id_to_attr = self.get_attributes_by_id(c, ..., type=type)

        for attr_id in attribute_value_mapping:
            if attr_id not in id_to_attr:
                raise errors.StructureNotFoundError(type)
            
        avm: dict[T, tuple[SlotStr, ...]] = {}

        # Convert ids to attributes and validate value
        for attr in id_to_attr.values():
            v = attribute_value_mapping.get(attr.id, ())
            
            avm[attr] = attr.real_to_slot_value(c, v)

        return MappingProxyType(avm)

    def _insert_attribute_aliases(
        self,
        c: orm.Cursor,
        type: type[AnyAttributeT],
        attribute_id: int,
        real_aliases: t.Sequence[RealStr],
        norm_aliases: t.Sequence[NormStr],
    ) -> None:
        if not norm_aliases:
            return

        AttributeAliasTable = db.AttributeAlias
        count = len(norm_aliases)

        c.execute(
            AttributeAliasTable.insert(
                AttributeAliasTable.attribute_id.bind(
                    *itertools.repeat(attribute_id, count)
                ),
                AttributeAliasTable.list_id.bind(*itertools.repeat(self.id, count)),
                AttributeAliasTable.attribute_type_id.bind(
                    *itertools.repeat(type.type_id, count)
                ),
                AttributeAliasTable.norm_alias.bind(*norm_aliases),
                AttributeAliasTable.real_alias.bind(*real_aliases),
            )
        )

    # --- Tasks ---

    def _task_id_to_slot(self, c: orm.Cursor, id: int) -> SlotStr:
        return self._get_default_static_attribute(Kind.ID).real_to_slot_value(
            c, (RealStr(str(id)),)
        )[0]

    def _task_real_name_to_slot(self, c: orm.Cursor, name: RealStr) -> SlotStr:
        return self._get_default_static_attribute(Kind.NAME).real_to_slot_value(
            c, (name,)
        )[0]

    def _task_real_aliases_to_slot_value(
        self, c: orm.Cursor, aliases: t.Sequence[RealStr]
    ) -> tuple[SlotStr, ...]:
        return self._get_default_static_attribute(Kind.ALIAS).real_to_slot_value(
            c, aliases
        )

    def get_tasks(self, c: orm.Cursor) -> list[Task]:
        return list(self._get_tasks_from_this_list_inner(c))

    def get_tasks_of_user(self, c: orm.Cursor, community_user_id: int) -> list[Task]:
        rows = c.fetch_all(
            db.CommunityUserTask.select(db.CommunityUserTask.task_id).where(
                self._where_this_list(db.CommunityUserTask.list_id),
                (
                    db.CommunityUserTask.community_user_id,
                    orm.Operator.EQ,
                    community_user_id,
                ),
            )
        )

        if not rows:
            return []

        return list(
            self.get_tasks_by_id(c, tuple(row.task_id for row in rows)).values()
        )

    def get_task_by_id(self, c: orm.Cursor, id: int) -> tuple[Task, int] | None:
        return utils_.first_or_none_of_mapping_vk_item(self.get_tasks_by_id(c, (id,)))

    def get_tasks_by_id(
        self, c: orm.Cursor, ids: t.Collection[int] | EllipsisType, /
    ) -> dict[int, Task]:
        return {
            task.id: task
            for task in (
                self._get_tasks_from_this_list_inner(c)
                if ids is ...
                else self._get_tasks_from_this_list_inner(
                    c, (db.Task.id, orm.Operator.IN, ids)
                )
            )
        }

    def get_task_by_name(
        self, c: orm.Cursor, name: NormStr, /
    ) -> tuple[Task, RealStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_tasks_by_name(c, (name,))
        )

    def get_tasks_by_name(
        self, c: orm.Cursor, names: t.Collection[NormStr] | EllipsisType, /
    ) -> dict[SlotStr, Task]:
        return {
            task.slot_name: task
            for task in (
                self._get_tasks_from_this_list_inner(c)
                if names is ...
                else self._get_tasks_from_this_list_inner(
                    c, (db.Task.norm_name, orm.Operator.IN, names)
                )
            )
        }

    def get_task_by_alias(
        self,
        c: orm.Cursor,
        alias: NormStr,
        /,
        task_ids: t.Collection[int] | EllipsisType = ...,
    ) -> tuple[Task, SlotStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(
            self.get_tasks_by_alias(c, (alias,), task_ids=task_ids)
        )

    def get_tasks_by_alias(
        self,
        c: orm.Cursor,
        aliases: t.Collection[NormStr] | EllipsisType,
        /,
        task_ids: t.Collection[int] | EllipsisType = ...,
    ) -> dict[SlotStr, Task]:
        rows = c.fetch_all(
            db.TaskAlias.select(db.TaskAlias.task_id, db.TaskAlias.slot_alias).where(
                self._where_this_list(db.TaskAlias.list_id),
                *(
                    ()
                    if task_ids is ...
                    else ((db.TaskAlias.task_id, orm.Operator.IN, task_ids),)
                ),
                *(
                    ()
                    if aliases is ...
                    else ((db.TaskAlias.norm_alias, orm.Operator.IN, aliases),)
                ),
            )
        )

        if not rows:
            return {}

        task_id_to_slot_aliases: dict[int, tuple[SlotStr, ...]] = {
            task_id: tuple(row.slot_alias for row in rows)
            for task_id, rows in itertools.groupby(rows, lambda row: row.task_id)
        }

        tasks = self.get_tasks_by_id(c, task_id_to_slot_aliases)

        assert len(tasks) == len(task_id_to_slot_aliases)

        return {
            slot_alias: task
            for task in tasks.values()
            for slot_alias in task_id_to_slot_aliases[task.id]
        }

    def get_task_by_syn(
        self, c: orm.Cursor, syn: NormStr, /
    ) -> tuple[Task, SlotStr] | None:
        return utils_.first_or_none_of_mapping_vk_item(self.get_tasks_by_syn(c, (syn,)))

    def get_tasks_by_syn(
        self, c: orm.Cursor, syns: t.Collection[NormStr] | EllipsisType, /
    ) -> dict[SlotStr, Task]:
        by_name = self.get_tasks_by_name(c, syns)

        if syns is not ... and len(by_name) >= len(syns):
            return by_name

        return by_name | self.get_tasks_by_alias(c, syns)

    def _fill_data_for_non_static_attribute_value_mapping[
        T: TaskAttribute | UserAttribute
    ](
        self,
        c: orm.Cursor,
        data: dict[int, _RawAvmT],
        task_ids: t.Collection[int] | EllipsisType,
        community_user_id: int,
        type: type[T],
    ) -> None:
        where_task_id = (
            ()
            if task_ids is ...
            else ((TaskAttributeValueTable.task_id, orm.Operator.IN, task_ids),)
        )

        if issubclass(type, TaskAttribute):
            rows = c.fetch_all(
                TaskAttributeValueTable.select(
                    TaskAttributeValueTable.task_id,
                    TaskAttributeValueTable.attribute_id,
                    TaskAttributeValueTable.slot_slot,
                )
                .where(
                    self._where_this_list(TaskAttributeValueTable.list_id),
                    *where_task_id,
                )
                .order_by(
                    (TaskAttributeValueTable.task_id, orm.Order.ASC),
                    (TaskAttributeValueTable.attribute_id, orm.Order.ASC),
                    (TaskAttributeValueTable.index, orm.Order.ASC),
                )
            )
        elif issubclass(type, UserAttribute):
            rows = c.fetch_all(
                CommunityUserTaskAttributeValueTable.select(
                    CommunityUserTaskAttributeValueTable.task_id,
                    CommunityUserTaskAttributeValueTable.attribute_id,
                    CommunityUserTaskAttributeValueTable.slot_slot,
                )
                .where(
                    self._where_this_list(CommunityUserTaskAttributeValueTable.list_id),
                    *where_task_id,
                    (
                        CommunityUserTaskAttributeValueTable.community_user_id,
                        orm.Operator.EQ,
                        community_user_id,
                    ),
                )
                .order_by(
                    CommunityUserTaskAttributeValueTable.task_id,
                    CommunityUserTaskAttributeValueTable.attribute_id,
                    CommunityUserTaskAttributeValueTable.index,
                )
            )
        else:
            t.assert_never(type)

        for k, g in itertools.groupby(
            rows, lambda row: (row.task_id, row.attribute_id)
        ):
            data[k[0]][k[1]] = tuple(row.slot_slot for row in g)

    @t.overload
    def get_task_attribute_value_mappings(
        self,
        c: orm.Cursor,
        community_user_id: None = ...,
        task_ids: t.Collection[int] | EllipsisType = ...,
        /,
    ) -> tuple[
        list[AttributeValueMapping],
        list[StaticAttribute | TaskAttribute],
        tuple[type[StaticAttribute], type[TaskAttribute]],
    ]:
        pass

    @t.overload
    def get_task_attribute_value_mappings(
        self,
        c: orm.Cursor,
        community_user_id: int,
        task_ids: t.Collection[int] | EllipsisType = ...,
        /,
    ) -> tuple[
        list[UserAttributeValueMapping],
        list[AnyAttributeT],
        tuple[type[StaticAttribute], type[TaskAttribute], type[UserAttribute]],
    ]:
        pass

    def get_task_attribute_value_mappings(
        self,
        c: orm.Cursor,
        community_user_id: int | None = None,
        task_ids: t.Collection[int] | EllipsisType = ...,
        /,
    ) -> tuple[list[t.Any], list[t.Any], tuple[t.Any, ...]]:
        community_user: CommunityUser | None = None

        if community_user_id is not None:
            community_user = self.community.get_community_user_by_id(
                c, community_user_id
            )

            if community_user is None:
                raise errors.StructureNotFoundError(CommunityUser)

        del community_user_id

        ATTRIBUTE_TYPES_TO_HANDLE = (
            (StaticAttribute, TaskAttribute)
            if community_user is None
            else ALL_ATTRIBUTE_TYPES
        )

        if task_ids:
            id_to_task: dict[int, Task] = self.get_tasks_by_id(c, task_ids)
        else:
            return (
                [],
                self.get_attributes(c, type=ATTRIBUTE_TYPES_TO_HANDLE),
                ATTRIBUTE_TYPES_TO_HANDLE,
            )

        id_to_attribute: dict[int, AnyAttributeT] = self.get_attributes_by_id(
            c, ..., type=ATTRIBUTE_TYPES_TO_HANDLE
        )
        attr_type_id_to_attrs: dict[int, tuple[AnyAttributeT, ...]] = {
            k: tuple(it)
            for k, it in itertools.groupby(
                id_to_attribute.values(), lambda attr: attr.type_id
            )
        }

        raw_avms: dict[int, _RawAvmT] = {}

        # --- Static Attribute ---

        id_attr, name_attr, aliases_attr = sorted(
            attr_type_id_to_attrs[StaticAttribute.type_id],
            key=lambda attr: attr.kind,  # type: ignore
        )  # type: ignore

        for id, task in id_to_task.items():
            # Set all nested dictionaries once here
            raw_avms[id] = {id: () for id in id_to_attribute}

            task_static_attr_data = raw_avms[id]

            task_static_attr_data[id_attr.id] = (self._task_id_to_slot(c, id),)
            task_static_attr_data[name_attr.id] = (
                self._task_real_name_to_slot(c, task.slot_name),
            )

        task_id_to_aliases = itertools.groupby(
            self.get_tasks_by_alias(c, ..., task_ids=task_ids).items(),
            lambda item: item[1].id,
        )

        for task_id, aliases_tasks in task_id_to_aliases:
            raw_avms[task_id][aliases_attr.id] = tuple(
                pair[0] for pair in aliases_tasks
            )

        del task_id_to_aliases

        # --- Task Attribute ---

        self._fill_data_for_non_static_attribute_value_mapping(
            c, raw_avms, task_ids, -1, TaskAttribute
        )

        # --- User Attribute ---

        if community_user is not None:
            self._fill_data_for_non_static_attribute_value_mapping(
                c, raw_avms, task_ids, community_user.id, UserAttribute
            )

        # --- Final Conversion ---

        final: list[AttributeValueMapping | UserAttributeValueMapping] = []

        for task_id, data in raw_avms.items():
            avms = tuple(
                MappingProxyType(
                    {attr: data[attr.id] for attr in attr_type_id_to_attrs[typ.type_id]}
                )
                for typ in ATTRIBUTE_TYPES_TO_HANDLE
            )

            static_and_task_avm: tuple[AvmT[StaticAttribute], AvmT[TaskAttribute]] = (
                avms[:2]
            )  # pyright: ignore[reportAssignmentType]

            avm = AttributeValueMapping(id_to_task[task_id], *static_and_task_avm)

            if community_user is None:
                final.append(avm)
            else:
                user_avm: AvmT[UserAttribute] = avms[2]  # type: ignore
                final.append(
                    UserAttributeValueMapping(
                        id_to_task[task_id],
                        *static_and_task_avm,
                        user_avm,
                        community_user,
                    )
                )

        return (final, list(id_to_attribute.values()), ATTRIBUTE_TYPES_TO_HANDLE)

    def create_task(
        self,
        c: orm.Cursor,
        name: RealStr,
        aliases: t.Sequence[RealStr],
        task_attribute_value_mapping: t.Mapping[int, t.Sequence[RealStr]],
    ) -> Task:
        (real_name, *real_aliases), (norm_name, *norm_aliases) = (
            utils_.handled_unique_reals_and_norms((name, *aliases))
        )

        del name, aliases

        slot_name = self._task_real_name_to_slot(c, real_name)
        slot_aliases = self._task_real_aliases_to_slot_value(c, real_aliases)

        del real_name, real_aliases

        existing_tasks = self.get_tasks_by_syn(c, (norm_name, *norm_aliases))

        if existing_tasks:
            raise errors.SynsAlreadyTakenError(existing_tasks)

        del existing_tasks

        all_tasks = self.get_tasks(c)

        if len(all_tasks) >= self.community.limits.list_task_count_max:
            raise errors.StructureCountLimitReachedError(
                self.community.limits.list_task_count_max, Task
            )

        avm = self._calc_attribute_value_mapping(
            c, TaskAttribute, task_attribute_value_mapping
        )

        del task_attribute_value_mapping

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

    def delete_task(self, c: orm.Cursor, id: int) -> None:
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

    def edit_task_name(self, c: orm.Cursor, task_id: int, name: text.RealStr) -> None:
        tup = self.get_task_by_id(c, task_id)
        del task_id

        if tup is None:
            raise errors.StructureNotFoundError(Task)

        task, _ = tup
        del tup

        slot_name = self._task_real_name_to_slot(c, name)
        norm_name = NormStr(slot_name)
        del name

        tup = self.get_task_by_syn(c, norm_name)

        if tup is not None and (existing_task := tup[0]) != task:
            raise errors.SynsAlreadyTakenError({existing_task.slot_name: existing_task})

        del tup

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

    def edit_task_aliases(
        self, c: orm.Cursor, task_id: int, aliases: t.Sequence[RealStr]
    ) -> None:
        real_aliases, norm_aliases = utils_.handled_unique_reals_and_norms(aliases)
        del aliases

        slot_aliases = self._task_real_aliases_to_slot_value(c, real_aliases)
        del real_aliases

        tup = self.get_task_by_id(c, task_id)
        del task_id

        if tup is None:
            raise errors.StructureNotFoundError(Task)

        task, _ = tup

        existing_tasks = {
            k: v for k, v in self.get_tasks_by_syn(c, norm_aliases).items() if v != task
        }

        if existing_tasks:
            raise errors.SynsAlreadyTakenError(existing_tasks)

        del existing_tasks

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
        c: orm.Cursor,
        task_id: int,
        task_attribute_value_mapping: t.MutableMapping[int, t.Sequence[RealStr]],
    ) -> None:
        tavm = self._calc_attribute_value_mapping(
            c, TaskAttribute, task_attribute_value_mapping
        )

        del task_attribute_value_mapping

        tup = self.get_task_by_id(c, task_id)

        if tup is None:
            raise errors.StructureNotFoundError(Task)

        task, _ = tup
        del tup

        TaskAttributeValueTable = db.TaskAttributeValue

        c.execute(
            TaskAttributeValueTable.delete().where(
                (TaskAttributeValueTable.list_id, orm.Operator.EQ, self.id),
                (TaskAttributeValueTable.task_id, orm.Operator.EQ, task_id),
            )
        )

        self._insert_task_attribute_value_mapping(c, task.id, tavm)

    def _get_tasks_from_this_list_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> map[Task]:
        return map(
            self._task_row_to_obj,
            c.fetch_all(
                db.Task.select("*").where(
                    self._where_this_list(db.Task.list_id), *where
                )
            ),
        )

    def _task_row_to_obj(self, row: db.Task) -> Task:
        return Task(
            list=self,
            id=row.id,
            slot_name=row.slot_name,
            norm_name=text.NormStr(row.norm_name, check=False),
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
        task_attribute_value_mapping: MappingProxyType[
            TaskAttribute, tuple[SlotStr, ...]
        ],
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

        if not attribute_id_args:
            return

        TaskAttributeValueTable = db.TaskAttributeValue

        c.execute(
            TaskAttributeValueTable.insert(
                TaskAttributeValueTable.list_id.bind(
                    *itertools.repeat(self.id, len(attribute_id_args))
                ),
                TaskAttributeValueTable.task_id.bind(
                    *itertools.repeat(task_id, len(attribute_id_args))
                ),
                TaskAttributeValueTable.attribute_id.bind(*attribute_id_args),
                TaskAttributeValueTable.index.bind(*index_args),
                TaskAttributeValueTable.slot_slot.bind(*slot_args),
            )
        )

    def _validate_attribute_syns(
        self,
        c: orm.Cursor,
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

        taken = {
            k: v
            for k, v in self.get_attributes_by_syn(c, norm_syns).items()
            if v not in allowed_attributes
        }

        if taken:
            raise errors.SynsAlreadyTakenError(taken)

    def _insert_user_attribute_task_values(
        self,
        c: orm.Cursor,
        *,
        uavm: MappingProxyType[UserAttribute, tuple[SlotStr, ...]],
        list_task_community_user_id: int,
        task_id: int,
        community_user_id: int,
    ) -> None:
        total_uavm_row_count: int = sum(len(v) for v in uavm.values())

        if not total_uavm_row_count:
            return

        c.execute(
            db.CommunityUserTaskAttributeValue.insert(
                db.CommunityUserTaskAttributeValue.community_user_task_id.bind(
                    *itertools.repeat(list_task_community_user_id, total_uavm_row_count)
                ),
                db.CommunityUserTaskAttributeValue.list_id.bind(
                    *itertools.repeat(self.id, total_uavm_row_count)
                ),
                db.CommunityUserTaskAttributeValue.task_id.bind(
                    *itertools.repeat(task_id, total_uavm_row_count)
                ),
                db.CommunityUserTaskAttributeValue.attribute_id.bind(
                    *(attr.id for attr, v in uavm.items() for _ in v)
                ),
                db.CommunityUserTaskAttributeValue.community_user_id.bind(
                    *itertools.repeat(community_user_id, total_uavm_row_count)
                ),
                db.CommunityUserTaskAttributeValue.index.bind(
                    *(i for v in uavm.values() for i in range(len(v)))
                ),
                db.CommunityUserTaskAttributeValue.slot_slot.bind(
                    *(slot for v in uavm.values() for slot in v)
                ),
            )
        )

    def _where_single_community_user_list_task_from_table(
        self, task_id: int, community_user_id: int
    ) -> tuple[tuple[t.Any, orm.Operator, t.Any], ...]:
        return (
            (
                db.CommunityUserTask.community_user_id,
                orm.Operator.EQ,
                community_user_id,
            ),
            (db.CommunityUserTask.list_id, orm.Operator.EQ, self.id),
            (db.CommunityUserTask.task_id, orm.Operator.EQ, task_id),
        )

    def give_task_to_community_user(
        self,
        c: orm.Cursor,
        task_id: int,
        community_user_id: int,
        user_attribute_value_mapping: t.MutableMapping[int, t.Sequence[text.RealStr]],
    ) -> None:
        uavm = self._calc_attribute_value_mapping(
            c, UserAttribute, user_attribute_value_mapping
        )

        row = c.fetch_one(
            db.CommunityUserTask.select("*").where(
                *self._where_single_community_user_list_task_from_table(
                    task_id, community_user_id
                )
            )
        )

        if row is not None:
            raise errors.CommunityUserAlreadyHasTaskError(task_id, community_user_id)

        execute_data = c.execute(
            db.CommunityUserTask.insert(
                db.CommunityUserTask.community_user_id.bind(community_user_id),
                db.CommunityUserTask.list_id.bind(self.id),
                db.CommunityUserTask.task_id.bind(task_id),
            ),
            get_last_generated_id=True,
        )

        assert execute_data.last_generated_id is not None

        self._insert_user_attribute_task_values(
            c=c,
            uavm=uavm,
            list_task_community_user_id=execute_data.last_generated_id,
            task_id=task_id,
            community_user_id=community_user_id,
        )

    def remove_task_from_community_user(
        self, c: orm.Cursor, task_id: int, community_user_id: int
    ) -> None:
        execute_data = c.execute(
            db.CommunityUserTask.delete().where(
                *self._where_single_community_user_list_task_from_table(
                    task_id, community_user_id
                )
            ),
            get_affected_row_count=True,
        )

        assert execute_data.affected_row_count <= 1

        if execute_data.affected_row_count < 1:
            raise errors.CommunityUserDoesNotHaveTaskError(task_id, community_user_id)

    def edit_task_user_attribute_value_mapping(
        self,
        c: orm.Cursor,
        task_id: int,
        community_user_id: int,
        user_attribute_value_mapping: t.MutableMapping[int, t.Sequence[text.RealStr]],
    ) -> None:
        uavm = self._calc_attribute_value_mapping(
            c, UserAttribute, user_attribute_value_mapping
        )

        row = c.fetch_one(
            db.CommunityUserTask.select("*").where(
                *self._where_single_community_user_list_task_from_table(
                    task_id, community_user_id
                )
            )
        )

        if row is None:
            raise errors.CommunityUserDoesNotHaveTaskError(task_id, community_user_id)

        c.execute(
            db.CommunityUserTaskAttributeValue.delete().where(
                (db.CommunityUserTaskAttributeValue.list_id, orm.Operator.EQ, self.id),
                (
                    db.CommunityUserTaskAttributeValue.community_user_task_id,
                    orm.Operator.EQ,
                    row.id,
                ),
            )
        )

        self._insert_user_attribute_task_values(
            c=c,
            uavm=uavm,
            list_task_community_user_id=row.id,
            task_id=task_id,
            community_user_id=community_user_id,
        )
