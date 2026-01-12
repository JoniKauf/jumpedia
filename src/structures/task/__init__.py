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

from .. import BaseStructure, db, errors
from ..attribute.slot_str import SlotStr

if t.TYPE_CHECKING:
    from ..list import List


class Task(BaseStructure):
    list: List
    slot_name: SlotStr
    norm_name: text.NormStr

    @property
    def name(self) -> str:
        return self.slot_name

    @property
    def connector(self) -> orm.Connector:
        return self.list.connector

    def get_slot_aliases(self) -> frozenset[SlotStr]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.TaskAlias.select(db.TaskAlias.slot_alias).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                    (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
                )
            )

        return frozenset(row.slot_alias for row in rows)

    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.TaskAlias.select(db.TaskAlias.norm_alias).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                    (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
                )
            )

        return frozenset(row.norm_alias for row in rows)

    @t.overload
    def get_attribute_value_mapping(
        self, community_user_id: None = ..., /
    ) -> AttributeValueMapping:
        pass

    @t.overload
    def get_attribute_value_mapping(
        self, community_user_id: int, /
    ) -> UserAttributeValueMapping:
        pass

    def get_attribute_value_mapping(
        self, community_user_id: int | None = None, /
    ) -> AttributeValueMapping | UserAttributeValueMapping:
        community_user: CommunityUser | None = None

        if community_user_id is not None:
            community_user = self.list.community.get_community_user_by_id(
                community_user_id
            )

        id = self.id
        name = self.slot_name
        aliases = self.get_slot_aliases()

        static_attrs = self.list.get_attributes_of_type(StaticAttribute)
        static_attrs.sort(key=lambda attr: attr.kind)

        id_attr, name_attr, alias_attr = static_attrs

        static_mapping: MappingProxyType[StaticAttribute, tuple[SlotStr, ...]] = (
            MappingProxyType(
                {
                    id_attr: id_attr.real_to_slot_value((text.RealStr(str(id)),)),
                    name_attr: (name,),
                    alias_attr: tuple(aliases),
                }
            )
        )

        with self.connector.cursor() as c:
            id_to_task_attr = {
                attr.id: attr for attr in self.list.get_attributes_of_type(TaskAttribute)
            }

            rows = c.fetch_all(
                db.TaskTaskAttributeValue.select(
                    db.TaskTaskAttributeValue.slot_slot,
                    db.TaskTaskAttributeValue.index,
                    db.TaskTaskAttributeValue.attribute_id,
                ).where(
                    (db.TaskTaskAttributeValue.list_id, orm.Operator.EQ, self.list.id),
                    (db.TaskTaskAttributeValue.task_id, orm.Operator.EQ, self.id),
                )
            )

            task_mapping: dict[TaskAttribute, tuple[SlotStr, ...]] = {}

            for k, g in itertools.groupby(rows, lambda r: r.attribute_id):
                g = list(g)

                g.sort(key=lambda row: row.index)

                task_mapping[id_to_task_attr[k]] = tuple(row.slot_slot for row in g)

            avm = AttributeValueMapping(
                self, static_mapping, MappingProxyType(task_mapping)
            )

            if community_user_id is None:
                return avm

            id_to_user_attr = {
                attr.id: attr for attr in self.list.get_attributes_of_type(UserAttribute)
            }

            rows = c.fetch_all(
                db.CommunityUserTaskAttributeValue.select(
                    db.CommunityUserTaskAttributeValue.slot_slot,
                    db.CommunityUserTaskAttributeValue.index,
                    db.CommunityUserTaskAttributeValue.attribute_id,
                ).where(
                    (db.CommunityUserTaskAttributeValue.list_id, orm.Operator.EQ, self.list.id),
                    (db.CommunityUserTaskAttributeValue.task_id, orm.Operator.EQ, self.id),
                    (
                        db.CommunityUserTaskAttributeValue.community_user_id,
                        orm.Operator.EQ,
                        community_user_id,
                    ),
                )
            )

        assert community_user is not None

        user_mapping: dict[UserAttribute, tuple[SlotStr, ...]] = {}

        for k, g in itertools.groupby(rows, lambda r: r.attribute_id):
            g = list(g)

            g.sort(key=lambda row: row.index)

            user_mapping[id_to_user_attr[k]] = tuple(row.slot_slot for row in g)

        return UserAttributeValueMapping(
            avm, community_user, MappingProxyType(user_mapping)
        )
