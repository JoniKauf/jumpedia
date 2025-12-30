import builtins
import typing as t

from utils import orm, text
from utils.orm import Cursor
from utils.rank import CommunityRank

from . import BaseStructure, db, errors, list
from .attribute import StaticAttribute
from .list import Kind, List
from .user import CommunityUser, JumpediaUser

if t.TYPE_CHECKING:
    from .jumpedia import Jumpedia


class CommunityLimits(t.NamedTuple):
    community_list_count_max: int = 1
    list_attribute_count_max: int = 16
    list_task_count_max: int = 100
    attribute_alias_count_max: int = (
        8  # Don't confuse with task alias count max, which is retrieved via the static attribute
    )
    attribute_task_value_slot_count_max: int = 32
    attribute_collection_entry_count_max: int = 32
    attribute_collection_entry_alias_count_max: int = 8


class Community(BaseStructure):
    jumpedia: Jumpedia
    real_name: text.RealStr
    norm_name: text.NormStr
    limits: CommunityLimits

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

    def create_list(self, name: text.RealStr) -> List:
        norm_name = text.NormStr(name)

        list_obj = self.get_list_by_name(norm_name)

        if list_obj is not None:
            raise errors.SynsAlreadyTakenError({list_obj.real_name: list_obj})

        count = len(self.get_lists())

        if count >= self.limits.community_list_count_max:
            raise errors.StructureCountLimitReachedError(
                self.limits.community_list_count_max, List
            )

        with self.connector.cursor() as c:
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

            list_obj = List(
                community=self, id=list_id, real_name=name, norm_name=norm_name
            )

            static_attr_id_data = list.KIND_TO_PREDEFINED_DATA[Kind.ID]

            list_obj.create_attribute(
                StaticAttribute,
                static_attr_id_data.real_name,
                (),
                static_attr_id_data.slot_type,
                static_attr_id_data.max_slots,
                min_slots=static_attr_id_data.min_slots,
                kind=static_attr_id_data.kind,
            )

            del static_attr_id_data

            static_attr_name_data = list.KIND_TO_PREDEFINED_DATA[Kind.NAME]

            list_obj.create_attribute(
                StaticAttribute,
                static_attr_name_data.real_name,
                (),
                static_attr_name_data.slot_type,
                static_attr_name_data.max_slots,
                min_slots=static_attr_name_data.min_slots,
                kind=static_attr_name_data.kind,
            )

            del static_attr_name_data

            static_attr_alias_data = list.KIND_TO_PREDEFINED_DATA[Kind.ALIAS]

            list_obj.create_attribute(
                StaticAttribute,
                static_attr_alias_data.real_name,
                (),
                static_attr_alias_data.slot_type,
                static_attr_alias_data.max_slots,
                min_slots=static_attr_alias_data.min_slots,
                kind=static_attr_alias_data.kind,
            )

            del static_attr_alias_data

        return list_obj

    def delete_list(self, id: int) -> None:
        with self.connector.cursor() as c:
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

    def get_list_by_name(self, norm_name: text.NormStr) -> List | None:
        data = self._fetch_from_list_table(
            (db.List.norm_name, orm.Operator.EQ, norm_name)
        )
        return self._list_row_to_obj(data[0]) if data else None

    def get_default_selected_list(self) -> List | None:
        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.Community.select(db.Community.default_selected_list_id).where(
                    (db.Community.id, orm.Operator.EQ, self.id)
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
        *,
        c: Cursor | None = None,
    ) -> CommunityUser:
        community_user = self.get_community_user_by_jumpedia_user(jumpedia_user)

        with self.connector.cursor(c) as c:
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
            id=row.id,
            community_rank=CommunityRank.get(row.power),
            selected_list_id=row.selected_list_id,
        )

    def get_community_user_by_id(self, id: int, /) -> CommunityUser | None:
        with self.connector.cursor() as c:
            community_user_row = c.fetch_one(
                db.CommunityUser.select("*").where(
                    (db.CommunityUser.id, orm.Operator.EQ, id)
                )
            )

            if community_user_row is None:
                return None

            jumpedia_user = self.jumpedia.get_jumpedia_user_by_id(
                community_user_row.jumpedia_user_id
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
