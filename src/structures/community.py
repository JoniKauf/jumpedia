import itertools
import typing as t
from types import EllipsisType

from structures.task import Task
from utils import orm, text
from utils.rank import CommunityRank

from . import BaseStructure, db, errors, utils_
from .attribute import StaticAttribute
from .list import KIND_TO_PREDEFINED_DATA, Kind, List
from .user import CommunityUser, JumpediaUser

if t.TYPE_CHECKING:
    from .jumpedia import Jumpedia


class CommunityLimits(t.TypedDict):
    # DO NOT RENAME KEYS!! This is a TypedDict on purpose
    # to accidentally rename keys without going unnoticed

    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max: int
    attribute_task_value_slot_count_max: int
    attribute_collection_entry_count_max: int
    attribute_collection_entry_alias_count_max: int


DEFAULT_COMMUNITY_LIMITS: CommunityLimits = {
    "community_list_count_max": 1,
    "list_attribute_count_max": 16,
    "list_task_count_max": 100,
    "attribute_alias_count_max": 8,
    "attribute_task_value_slot_count_max": 32,  # DO NOT DECREASE! If increased, make sure to update database!! Important for alias static attribute!!
    "attribute_collection_entry_count_max": 32,
    "attribute_collection_entry_alias_count_max": 8,
}


class Community(BaseStructure, naming=("community", "communities")):
    jumpedia: Jumpedia
    real_name: text.RealStr
    norm_name: text.NormStr
    limits: CommunityLimits

    @property
    def name(self) -> str:
        return self.real_name

    def get_server_ids(self, c: orm.Cursor, /) -> frozenset[int]:
        rows = c.fetch_all(
            db.Server.select(db.Server.id).where(
                (db.Server.community_id, orm.Operator.EQ, self.id)
            )
        )

        return frozenset(row.id for row in rows)

    def create_list(self, c: orm.Cursor, name: text.RealStr, /) -> List:
        norm_name = text.NormStr(name)

        tup = self.get_list_by_name(c, norm_name)

        if tup is not None:
            raise errors.SynsAlreadyTakenError({tup[1]: tup[0]})

        count = len(self.get_lists(c))

        if count >= self.limits["community_list_count_max"]:
            raise errors.StructureCountLimitReachedError(
                self.limits["community_list_count_max"], List
            )

        execute_data = c.execute(
            db.List.insert(
                db.List.community_id.bind(self.id),
                db.List.norm_name.bind(norm_name),
                db.List.real_name.bind(name),
            ),
            get_last_generated_id=True,
        )

        list_id = execute_data.last_generated_id
        assert list_id is not None

        tup = List(community=self, id=list_id, real_name=name, norm_name=norm_name)

        for kind in Kind:
            static_attr_data = KIND_TO_PREDEFINED_DATA[kind]

            tup.create_attribute(
                c,
                StaticAttribute,
                static_attr_data.real_name,
                (),
                static_attr_data.slot_type,
                static_attr_data.max_slot_count,
                min_slot_count=static_attr_data.min_slot_count,
                kind=static_attr_data.kind,
                position=static_attr_data.position,
            )

        return tup

    def delete_list(self, c: orm.Cursor, id: int, /) -> None:
        execute_data = c.execute(
            db.List.delete().where(
                (db.List.community_id, orm.Operator.EQ, self.id),
                (db.List.id, orm.Operator.EQ, id),
            ),
            get_affected_row_count=True,
        )

        if execute_data.affected_row_count == 0:
            raise errors.StructureNotFoundError(id, List)

        assert execute_data.affected_row_count == 1

    def _get_lists_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> map[List]:
        return map(
            self._list_row_to_obj,
            c.fetch_all(
                db.List.select(
                    "*",
                ).where((db.List.community_id, orm.Operator.EQ, self.id), *where)
            ),
        )

    def _list_row_to_obj(self, row: db.List) -> List:
        return List(
            community=self,
            id=row.id,
            real_name=text.RealStr(row.real_name, check=False),
            norm_name=text.NormStr(row.norm_name, check=False),
        )

    def get_lists(self, c: orm.Cursor, /) -> list[List]:
        return list(self._get_lists_inner(c))

    def get_list_by_id(self, c: orm.Cursor, id: int, /) -> tuple[List, int] | None:
        return utils_.first_or_none_of_item_vk_of_mapping(
            self.get_lists_by_id(c, (id,))
        )

    def get_lists_by_id(
        self, c: orm.Cursor, ids: t.Collection[int] | EllipsisType, /
    ) -> dict[int, List]:
        return {
            list.id: list
            for list in self._get_lists_inner(
                c, *(() if ids is ... else ((db.List.id, orm.Operator.IN, ids),))
            )
        }

    def get_list_by_name(
        self, c: orm.Cursor, name: text.NormStr, /
    ) -> tuple[List, text.RealStr] | None:
        return utils_.first_or_none_of_item_vk_of_mapping(
            self.get_lists_by_name(c, (name,))
        )

    def get_lists_by_name(
        self, c: orm.Cursor, names: t.Collection[text.NormStr], /
    ) -> dict[text.RealStr, List]:
        return {
            list.real_name: list
            for list in self._get_lists_inner(
                c, (db.List.norm_name, orm.Operator.IN, names)
            )
        }

    def get_default_selected_list(self, c: orm.Cursor, /) -> List | None:
        row = c.fetch_one(
            db.Community.select(db.Community.default_selected_list_id).where(
                (db.Community.id, orm.Operator.EQ, self.id)
            )
        )

        if row is None or row.default_selected_list_id is None:
            return None

        tup = self.get_list_by_id(c, row.default_selected_list_id)

        assert tup is not None

        return tup[0]

    def set_default_selected_list(self, c: orm.Cursor, list_id: int | None, /) -> None:
        execute_data = c.execute(
            db.Community.update(
                db.Community.default_selected_list_id.set(list_id)
            ).where((db.Community.id, orm.Operator.EQ, self.id)),
            get_affected_row_count=True,
        )

        if execute_data.affected_row_count == 0:
            raise errors.StructureNotFoundError(-1, Community)

        assert execute_data.affected_row_count == 1

    def rename_list(self, c: orm.Cursor, list_id: int, name: text.RealStr) -> None:
        norm_name = text.NormStr(name)
        tup = self.get_list_by_name(c, norm_name)

        if tup is not None and tup[0].id != list_id:
            raise errors.SynsAlreadyTakenError({tup[1]: tup[0]})

        c.execute(
            db.List.update(
                db.List.real_name.set(name), db.List.norm_name.set(norm_name)
            ).where(
                (db.List.community_id, orm.Operator.EQ, self.id),
                (db.List.id, orm.Operator.EQ, list_id),
            )
        )

    def get_or_create_community_user(
        self,
        c: orm.Cursor,
        jumpedia_user: JumpediaUser,
        community_rank: CommunityRank,
        selected_list_id: int | None,
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool,
    ) -> CommunityUser:
        community_user = self.get_community_user_by_jumpedia_user(c, jumpedia_user)

        # Community user doesn't exist yet
        if community_user is None:
            execute_data = c.execute(
                db.CommunityUser.insert(
                    db.CommunityUser.community_id.bind(self.id),
                    db.CommunityUser.jumpedia_user_id.bind(jumpedia_user.id),
                    db.CommunityUser.power.bind(community_rank.value),
                    db.CommunityUser.selected_list_id.bind(selected_list_id),
                ),
                get_last_generated_id=True,
            )

            assert execute_data.last_generated_id is not None

            return CommunityUser(
                id=execute_data.last_generated_id,
                community=self,
                jumpedia_user=jumpedia_user,
                community_rank=community_rank,
                selected_list_id=selected_list_id,
            )

        community_rank = (
            community_rank
            if override_community_rank_if_user_exists
            else community_user.community_rank
        )

        selected_list_id = (
            selected_list_id
            if override_selected_list_if_user_exists
            else community_user.selected_list_id
        )

        if (
            community_rank is not community_user.community_rank
            or selected_list_id != selected_list_id
        ):
            execute_data = c.execute(
                db.CommunityUser.update(
                    db.CommunityUser.power.set(community_rank.value),
                    db.CommunityUser.selected_list_id.set(selected_list_id),
                ).where(
                    (
                        db.CommunityUser.community_id,
                        orm.Operator.EQ,
                        self.id,
                    ),
                    (
                        db.CommunityUser.jumpedia_user_id,
                        orm.Operator.EQ,
                        jumpedia_user.id,
                    ),
                ),
                get_affected_row_count=True,
            )

            assert execute_data.affected_row_count == 1

        return CommunityUser(
            community=community_user.community,
            jumpedia_user=jumpedia_user,
            id=community_user.id,
            community_rank=community_rank,
            selected_list_id=selected_list_id,
        )

    def get_community_user_by_jumpedia_user(
        self, c: orm.Cursor, jumpedia_user: JumpediaUser, /
    ) -> CommunityUser | None:
        row = c.fetch_one(
            db.CommunityUser.select(
                "*",
            ).where(
                (db.CommunityUser.community_id, orm.Operator.EQ, self.id),
                (
                    db.CommunityUser.jumpedia_user_id,
                    orm.Operator.EQ,
                    jumpedia_user.id,
                ),
            )
        )

        if row is None:
            return None

        return CommunityUser(
            community=self,
            jumpedia_user=jumpedia_user,
            id=row.id,
            community_rank=CommunityRank.get(row.power),
            selected_list_id=row.selected_list_id,
        )

    def get_community_user_by_id(
        self, c: orm.Cursor, id: int, /
    ) -> CommunityUser | None:
        community_user_row = c.fetch_one(
            db.CommunityUser.select("*").where(
                (db.CommunityUser.id, orm.Operator.EQ, id)
            )
        )

        if community_user_row is None:
            return None

        jumpedia_user = self.jumpedia.get_jumpedia_user_by_id(
            c, community_user_row.jumpedia_user_id
        )

        if jumpedia_user is None:  # Should not be the case due to foreign key
            return None

        return CommunityUser(
            jumpedia_user=jumpedia_user,
            community=self,
            id=community_user_row.id,
            community_rank=CommunityRank.get(community_user_row.power),
            selected_list_id=community_user_row.selected_list_id,
        )

    def get_tasks_by_list(self, c: orm.Cursor) -> dict[List, tuple[Task, ...]]:
        id_to_list = self.get_lists_by_id(c, ...)

        rows = c.fetch_all(
            db.Task.select("*")
            .where((db.Task.list_id, orm.Operator.IN, id_to_list))
            .order_by(db.Task.list_id)
        )

        return {
            (lst := id_to_list[list_id]): tuple(map(lst._task_row_to_obj, rows))
            for list_id, rows in itertools.groupby(rows, lambda row: row.list_id)
        }
