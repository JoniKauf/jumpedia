import builtins
import typing as t

from src.structures.attribute import slot_str

from .user import CommunityUser, JumpediaUser
from .user.rank import CommunityRank

from src.utils import orm
from src.utils.text import NormStr, RealStr
from . import BaseStructure, errors, list
from .attribute import StaticAttribute
from .jumpedia import db
from .list import List

if t.TYPE_CHECKING:
    from .jumpedia import Jumpedia


class CommunityLimits(t.NamedTuple):
    community_list_count_max: int = 1
    list_attribute_count_max: int = 16
    list_task_count_max: int = 100
    attribute_task_value_slot_count_max: int = 32
    attribute_collection_entry_count_max: int = 32
    attribute_collection_entry_alias_count_max: int = 8


class Community(BaseStructure):
    __structure_name__ = "community"

    jumpedia: "Jumpedia"
    id: int
    real_name: RealStr
    norm_name: NormStr
    limits: CommunityLimits

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity

    @property
    def name(self) -> str:
        return self.real_name

    @property
    def connector(self) -> orm.Connector:
        return self.jumpedia.connector

    def get_server_ids(self) -> frozenset[int]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.Server.select(db.Server.id).where(
                    (db.Server.community_id, orm.Operator.EQ, self.id)
                )
            )

        return frozenset(row.id for row in rows)

    def create_list(self, real_name: RealStr) -> "List":
        norm_name = NormStr(real_name)

        with self.locked:
            list_ = self.get_list_by_name(norm_name)

            if list_ is not None:
                raise errors.SynAlreadyTakenError(real_name, list_)

            count = len(self.get_lists())

            if count >= self.limits.community_list_count_max:
                raise errors.LimitReachedError(
                    self.limits.community_list_count_max, List
                )

            with self.connector.cursor() as c:
                execute_data = c.execute(
                    db.List.insert(
                        db.List.community_id.bind(self.id),
                        db.List.norm_name.bind(norm_name),
                        db.List.real_name.bind(real_name),
                    ),
                    get_last_generated_id=True,
                )

                list_id = execute_data.last_generated_id
                assert list_id is not None

                list_ = List(
                    community=self, id=list_id, real_name=real_name, norm_name=norm_name
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr("Id"),
                    frozenset(),
                    int,
                    1,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_ID,
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr("Name"),
                    frozenset(),
                    str,
                    1,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_NAME,
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr("Aliases"),
                    frozenset(),
                    str,
                    self.limits.attribute_task_value_slot_count_max,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_ALIASES,
                )

            return list_

    def delete_list(self, id: int) -> None:
        with self.locked, self.connector.cursor() as c:
            execute_data = c.execute(
                db.List.delete().where(
                    (db.List.community_id, orm.Operator.EQ, self.id),
                    (db.List.id, orm.Operator.EQ, id),
                ),
                get_affected_row_count=True,
            )

            if execute_data.affected_row_count == 0:
                raise errors.StructureNotFoundError(List)

            assert execute_data.affected_row_count == 1

    def _fetch_from_list_table(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> builtins.list[db.List]:
        with self.connector.cursor() as c:
            return c.fetch_all(
                db.List.select(
                    "*",
                ).where((db.List.community_id, orm.Operator.EQ, self.id), *where)
            )

    def _list_row_to_obj(self, row: db.List) -> List:
        return List(
            community=self, id=row.id, real_name=row.real_name, norm_name=row.norm_name
        )

    def get_lists(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> builtins.list[List]:
        return [
            self._list_row_to_obj(data) for data in self._fetch_from_list_table(*where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table((db.List.id, orm.Operator.EQ, id))
        return self._list_row_to_obj(data[0]) if data else None

    def get_list_by_name(self, norm_name: NormStr) -> List | None:
        data = self._fetch_from_list_table(
            (db.List.norm_name, orm.Operator.EQ, norm_name)
        )
        return self._list_row_to_obj(data[0]) if data else None

    def get_default_selected_list(self) -> List | None:
        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.Community.select(db.Community.default_selected_list_id).where(
                    (db.Community, orm.Operator.EQ, self.id)
                )
            )

        if row is None or row.default_selected_list_id is None:
            return None

        return self.get_list_by_id(row.default_selected_list_id)

    def set_default_selected_list(self, list_id: int | None) -> None:
        with self.connector.cursor() as c:
            execute_data = c.execute(
                db.Community.update(
                    db.Community.default_selected_list_id.set(list_id)
                ).where((db.Community.id, orm.Operator.EQ, self.id)),
                get_affected_row_count=True,
            )

            if execute_data.affected_row_count == 0:
                raise errors.StructureNotFoundError(Community)

            assert execute_data.affected_row_count == 1

    def get_or_create_community_user(
        self,
        jumpedia_user: JumpediaUser,
        community_rank: CommunityRank,
        selected_list_id: int | None,
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool,
    ) -> CommunityUser:
        with self.locked:
            community_user = self.get_community_user_by_jumpedia_user(jumpedia_user)

            with self.connector.cursor() as c:
                # Community user doesn't exist yet
                if community_user is None:
                    row = c.fetch_one(
                        db.CommunityUser.insert(
                            db.CommunityUser.community_id.bind(self.id),
                            db.CommunityUser.jumpedia_user_id.bind(jumpedia_user.id),
                            db.CommunityUser.power.bind(community_rank.power),
                            db.CommunityUser.selected_list_id.bind(selected_list_id),
                        ).returning("*")
                    )

                    assert row is not None

                    community_user = CommunityUser(
                        community=self,
                        jumpedia_user=jumpedia_user,
                        community_rank=community_rank,
                        selected_list_id=selected_list_id,
                    )

                else:
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
                        community_rank != community_user.community_rank
                        or selected_list_id != selected_list_id
                    ):
                        execute_data = c.execute(
                            db.CommunityUser.update(
                                db.CommunityUser.power.set(community_rank.power),
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
                community_rank=community_rank,
                selected_list_id=selected_list_id,
            )

    # TODO synchronize both cursors so data could in theory not have dirty reads
    def get_community_user_by_jumpedia_user(
        self, jumpedia_user: JumpediaUser
    ) -> CommunityUser | None:
        with self.connector.cursor() as c:
            self.jumpedia
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
            community_rank=CommunityRank.get(row.power),
            selected_list_id=row.selected_list_id,
        )
