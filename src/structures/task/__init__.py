import itertools
import typing as t
from dataclasses import field
from types import MappingProxyType

from structures.attribute import StaticAttribute, TaskAttribute, UserAttribute
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from structures.user import CommunityUser
from utils import orm, text

from .. import BaseStructure, db
from ..attribute.slot_str import SlotStr

if t.TYPE_CHECKING:
    from ..list import List


class Task(BaseStructure, naming=("task", "tasks")):
    list: List
    slot_name: SlotStr
    norm_name: text.NormStr

    @property
    def name(self) -> str:
        return self.slot_name

    def get_slot_aliases(self, c: orm.Cursor, /) -> frozenset[SlotStr]:
        rows = c.fetch_all(
            db.TaskAlias.select(db.TaskAlias.slot_alias).where(
                (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
            )
        )

        return frozenset(row.slot_alias for row in rows)

    def get_norm_aliases(self, c: orm.Cursor, /) -> frozenset[text.NormStr]:
        rows = c.fetch_all(
            db.TaskAlias.select(db.TaskAlias.norm_alias).where(
                (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
            )
        )

        return frozenset(text.NormStr(row.norm_alias, check=False) for row in rows)

    @t.overload
    def get_attribute_value_mapping(
        self, c: orm.Cursor, community_user_id: None = ..., /
    ) -> AttributeValueMapping:
        pass

    @t.overload
    def get_attribute_value_mapping(
        self, c: orm.Cursor, community_user_id: int, /
    ) -> UserAttributeValueMapping:
        pass

    def get_attribute_value_mapping(
        self, c: orm.Cursor, community_user_id: int | None = None, /
    ) -> AttributeValueMapping | UserAttributeValueMapping:
        community_user: CommunityUser | None = None

        if community_user_id is not None:
            community_user = self.list.community.get_community_user_by_id(
                c, community_user_id
            )

        id = self.id
        name = self.slot_name
        aliases = self.get_slot_aliases(c)

        static_attrs = self.list.get_attributes(c, type=StaticAttribute)
        static_attrs.sort(key=lambda attr: attr.kind)

        id_attr, name_attr, alias_attr = static_attrs

        static_mapping: MappingProxyType[StaticAttribute, tuple[SlotStr, ...]] = (
            MappingProxyType(
                {
                    id_attr: id_attr.real_to_slot_value(
                        c, (text.RealStr(str(id), check=False),)
                    ),
                    name_attr: (name,),
                    alias_attr: tuple(aliases),
                }
            )
        )

        id_to_task_attr = {
            attr.id: attr for attr in self.list.get_attributes(c, type=TaskAttribute)
        }

        rows = c.fetch_all(
            db.TaskAttributeValue.select(
                db.TaskAttributeValue.slot_slot,
                db.TaskAttributeValue.index,
                db.TaskAttributeValue.attribute_id,
            )
            .where(
                (db.TaskAttributeValue.list_id, orm.Operator.EQ, self.list.id),
                (db.TaskAttributeValue.task_id, orm.Operator.EQ, self.id),
            )
            .order_by(db.TaskAttributeValue.attribute_id, db.TaskAttributeValue.index)
        )

        task_mapping: dict[TaskAttribute, tuple[SlotStr, ...]] = {}

        # Sorted indices above, so just iterate
        for k, g in itertools.groupby(rows, lambda r: r.attribute_id):
            task_mapping[id_to_task_attr[k]] = tuple(row.slot_slot for row in g)

        if community_user_id is None:
            return AttributeValueMapping(
                self, static_mapping, MappingProxyType(task_mapping)
            )

        id_to_user_attr = self.list.get_attributes_by_id(c, ..., type=UserAttribute)

        rows = c.fetch_all(
            db.CommunityUserTaskAttributeValue.select(
                db.CommunityUserTaskAttributeValue.slot_slot,
                db.CommunityUserTaskAttributeValue.index,
                db.CommunityUserTaskAttributeValue.attribute_id,
            )
            .where(
                (
                    db.CommunityUserTaskAttributeValue.list_id,
                    orm.Operator.EQ,
                    self.list.id,
                ),
                (db.CommunityUserTaskAttributeValue.task_id, orm.Operator.EQ, self.id),
                (
                    db.CommunityUserTaskAttributeValue.community_user_id,
                    orm.Operator.EQ,
                    community_user_id,
                ),
            )
            .order_by(
                db.CommunityUserTaskAttributeValue.attribute_id,
                db.CommunityUserTaskAttributeValue.index,
            )
        )

        assert community_user is not None

        user_mapping: dict[UserAttribute, tuple[SlotStr, ...]] = {}

        # Indices sorted above
        for k, g in itertools.groupby(rows, lambda r: r.attribute_id):
            user_mapping[id_to_user_attr[k]] = tuple(row.slot_slot for row in g)

        return UserAttributeValueMapping(
            self,
            static_mapping,
            MappingProxyType(task_mapping),
            MappingProxyType(user_mapping),
            community_user,
        )
