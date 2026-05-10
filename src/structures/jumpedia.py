import json
import typing as t
from dataclasses import InitVar

from structures import utils_
from utils import orm, text
from domain.enum.rank import CommunityRank, JumpediaRank

from . import BaseStructure, db, errors
from .community import Community, CommunityLimits
from .errors import StructureNotFoundError, SynsAlreadyTakenError
from .user import JumpediaUser


class JumpediaLimits(t.TypedDict):
    """Global limits for Jumpedia.

    A limit should only be a Jumpedia limit if it has
    a good reason to be so, otherwise it should be a
    community wide limit.
    """

    # DO NOT RENAME KEYS!! This is a TypedDict on purpose
    # to accidentally rename keys without going unnoticed

    # All here are currently length limits, simply because it is one giant shared table
    # and so they share the same VARCHAR(N)
    community_name_length_max: int  # By nature a Jumpedia limit
    list_name_length_max: int  # Db needs a maximum varchar
    user_name_length_max: int  # Discord limit
    attribute_syn_length_max: int  # Db needs a maximum varchar
    attribute_task_value_slot_length_max: int  # Db needs a maximum varchar


class Jumpedia(BaseStructure, naming=("jumpedia", "jumpedias")):
    limits: JumpediaLimits

    @property
    def name(self) -> str:
        return self.__class__.type_name

    # --- Communities ---

    def create_community(
        self,
        c: orm.Cursor,
        name: text.RealStr,
        server_id: int,
        owner: JumpediaUser,
        limits: CommunityLimits,
    ) -> Community:
        if len(name) > self.limits["community_name_length_max"]:
            raise errors.TooLongSynError(
                name, True, self.limits["community_name_length_max"], Community
            )

        norm_name = text.NormStr(name)

        tup = self.get_community_by_server_id(c, server_id)

        if tup is not None:
            comm, server_id = tup

            raise errors.ServerAlreadyConnectedToCommunityError(server_id, comm)

        tup = self.get_community_by_name(c, norm_name)

        if tup is not None:
            comm, real_name = tup
            raise SynsAlreadyTakenError({real_name: comm})

        del tup

        execute_data = c.execute(
            db.Community.insert(
                db.Community.norm_name.bind(norm_name),
                db.Community.real_name.bind(name),
                db.Community.limits.bind(json.dumps(limits)),
            ),
            get_last_generated_id=True,
        )

        community_id = execute_data.last_generated_id

        assert community_id is not None

        c.execute(
            db.Server.insert(
                db.Server.id.bind(server_id),
                db.Server.community_id.bind(community_id),
            )
        )

        comm = Community(
            jumpedia=self,
            id=community_id,
            real_name=name,
            norm_name=norm_name,
            limits=limits,
        )

        comm.get_or_create_community_user(
            c, owner, CommunityRank.OWNER, None, True, True
        )

        return comm

    def delete_community(self, c: orm.Cursor, id: int) -> None:
        execute_data = c.execute(
            (db.Community.delete().where((db.Community.id, orm.Operator.EQ, id))),
            get_affected_row_count=True,
        )

        if execute_data.affected_row_count < 1:
            raise StructureNotFoundError(id, Community)

    def _get_communities_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> map[Community]:
        query = db.Community.select("*")

        if where:
            query = query.where(*where)

        return map(self._community_row_to_obj, c.fetch_all(query))

    def _community_row_to_obj(self, row: db.Community) -> Community:
        return Community(
            jumpedia=self,
            id=row.id,
            real_name=text.RealStr(row.real_name, check=False),
            norm_name=text.NormStr(row.norm_name, check=False),
            limits=CommunityLimits(**json.loads(row.limits)),
        )

    def get_communities(self, c: orm.Cursor) -> list[Community]:
        return list(self._get_communities_inner(c))

    def get_community_by_id(
        self, c: orm.Cursor, id: int, /
    ) -> tuple[Community, int] | None:
        return utils_.first_or_none_of_item_vk_of_mapping(
            self.get_communities_by_id(c, (id,))
        )

    def get_communities_by_id(
        self, c: orm.Cursor, ids: t.Collection[int], /
    ) -> dict[int, Community]:
        return {
            comm.id: comm
            for comm in self._get_communities_inner(
                c, (db.Community.id, orm.Operator.IN, ids)
            )
        }

    def get_community_by_name(
        self, c: orm.Cursor, name: text.NormStr, /
    ) -> tuple[Community, text.RealStr] | None:
        return utils_.first_or_none_of_item_vk_of_mapping(
            self.get_communities_by_name(c, (name,))
        )

    def get_communities_by_name(
        self, c: orm.Cursor, names: t.Collection[text.NormStr], /
    ) -> dict[text.RealStr, Community]:
        return {
            comm.real_name: comm
            for comm in self._get_communities_inner(
                c, (db.Community.norm_name, orm.Operator.IN, names)
            )
        }

    def get_community_by_server_id(
        self, c: orm.Cursor, server_id: int, /
    ) -> tuple[Community, int] | None:
        return utils_.first_or_none_of_item_vk_of_mapping(
            self.get_communities_by_server_id(c, (server_id,))
        )

    def get_communities_by_server_id(
        self, c: orm.Cursor, server_ids: t.Collection[int], /
    ) -> dict[int, Community]:
        rows = c.fetch_all(
            db.Server.select(db.Server.id, db.Server.community_id).where(
                (db.Server.id, orm.Operator.IN, server_ids)
            )
        )

        if not rows:
            return {}

        community_id_to_server_id = {row.community_id: row.id for row in rows}

        return {
            community_id_to_server_id[comm.id]: comm
            for comm in self.get_communities_by_id(
                c, community_id_to_server_id
            ).values()
        }

    # --- Jumpedia Users ---

    def get_or_create_jumpedia_user(
        self,
        c: orm.Cursor,
        id: int,
        name: str,
        jumpedia_rank: JumpediaRank,
        override_name_if_user_exists: bool,
        override_jumpedia_rank_if_user_exists: bool,
    ) -> JumpediaUser:
        norm_name = text.NormStr(name)

        user = self.get_jumpedia_user_by_id(c, id)

        if user is None:
            c.execute(
                db.JumpediaUser.insert(
                    db.JumpediaUser.id.bind(id),
                    db.JumpediaUser.power.bind(jumpedia_rank.value),
                    db.JumpediaUser.norm_name.bind(norm_name),
                    db.JumpediaUser.raw_name.bind(name),
                )
            )

        else:
            jumpedia_rank = (
                jumpedia_rank
                if override_jumpedia_rank_if_user_exists
                else user.jumpedia_rank
            )
            name = name if override_name_if_user_exists else user.user_name

            if name != user.user_name or jumpedia_rank is not user.jumpedia_rank:
                c.execute(
                    db.JumpediaUser.update(
                        db.JumpediaUser.norm_name.set(norm_name),
                        db.JumpediaUser.raw_name.set(name),
                        db.JumpediaUser.power.set(jumpedia_rank.value),
                    ).where((db.JumpediaUser.id, orm.Operator.EQ, user.id))
                )

        return JumpediaUser(
            jumpedia=self, id=id, user_name=name, jumpedia_rank=jumpedia_rank
        )

    def _get_jumpedia_users_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[JumpediaUser]:
        query = db.JumpediaUser.select("*")

        if where:
            query = query.where(*where)

        return list(map(self._jumpedia_user_row_to_obj, c.fetch_all(query)))

    def _jumpedia_user_row_to_obj(self, row: db.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            user_name=row.raw_name,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power),
        )

    def get_jumpedia_users(self, c: orm.Cursor) -> list[JumpediaUser]:
        return self._get_jumpedia_users_inner(c)

    def get_jumpedia_user_by_id(self, c: orm.Cursor, id: int, /) -> JumpediaUser | None:
        users = self._get_jumpedia_users_inner(
            c, (db.JumpediaUser.id, orm.Operator.EQ, id)
        )
        return users[0] if users else None

    def add_community_to_server(
        self, c: orm.Cursor, community_id: int, server_id: int, /
    ) -> Community:
        tup = self.get_community_by_server_id(c, server_id)

        if tup is not None:
            existing_community, server_id = tup

            raise errors.ServerAlreadyConnectedToCommunityError(
                server_id, existing_community
            )

        del tup

        c.execute(
            db.Server.insert(
                db.Server.id.bind(server_id),
                db.Server.community_id.bind(community_id),
            )
        )

        # Community must now be connected
        community = self.get_community_by_server_id(c, server_id)
        assert community is not None

        return community[0]

    def remove_community_from_server(
        self, c: orm.Cursor, server_id: int, /
    ) -> Community:
        row = c.fetch_one(
            db.Server.delete()
            .where((db.Server.id, orm.Operator.EQ, server_id))
            .returning(db.Server.community_id)
        )

        if row is None:
            raise errors.ServerNotConnectedToACommunityError(server_id)

        community = self.get_community_by_id(c, row.community_id)
        assert community is not None

        return community[0]
