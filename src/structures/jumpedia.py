import json
import typing as t
from dataclasses import InitVar

from utils import orm, text
from utils.rank import CommunityRank, JumpediaRank

from . import BaseStructure, db, errors
from .community import Community, CommunityLimits
from .errors import StructureNotFoundError, SynsAlreadyTakenError
from .user import JumpediaUser


class JumpediaLimits(t.NamedTuple):
    """Global limits for Jumpedia.

    A limit should only be a Jumpedia limit if it has
    a good reason to be so, otherwise it should be a
    community wide limit.
    """

    # All here are currently length limits, simply because it is one giant shared table
    # and so they share the same VARCHAR(N)
    community_name_length_max: int  # By nature a Jumpedia limit
    list_name_length_max: int
    user_name_length_max: int  # Discord limit
    attribute_syn_length_max: int
    attribute_task_value_slot_length_max: int


class Jumpedia(BaseStructure):
    limits: JumpediaLimits
    db_name: InitVar[str]
    meta_c: InitVar[orm.Cursor]
    get_c: InitVar[t.Callable[[], orm.Cursor]]

    @property
    def name(self) -> str:
        return self.__class__.type_name

    def __post_init__(
        self, db_name: str, meta_c: orm.Cursor, get_c: t.Callable[[], orm.Cursor]
    ) -> None:
        db.create_database(self, db_name, meta_c, get_c)

    # --- Communities ---

    def create_community(
        self,
        c: orm.Cursor,
        name: text.RealStr,
        server_id: int,
        creator: JumpediaUser,
        limits: CommunityLimits,
    ) -> Community:
        norm_name = text.NormStr(name)

        comm = self.get_community_by_server_id(c, server_id)

        if comm is not None:
            raise errors.ServerAlreadyConnectedToCommunityError(server_id, comm)

        comm = self.get_community_by_name(c, norm_name)

        if comm is not None:
            raise SynsAlreadyTakenError({comm.real_name: comm})

        execute_data = c.execute(
            db.Community.insert(
                db.Community.norm_name.bind(norm_name),
                db.Community.real_name.bind(name),
                db.Community.limits.bind(json.dumps(limits._asdict())),
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
            c, creator, CommunityRank.OWNER, None, True, True
        )

        return comm

    def delete_community(self, c: orm.Cursor, id: int) -> None:
        execute_data = c.execute(
            (db.Community.delete().where((db.Community.id, orm.Operator.EQ, id))),
            get_affected_row_count=True,
        )

        if execute_data.affected_row_count < 1:
            raise StructureNotFoundError(Community)

    def _get_communities_inner(
        self, c: orm.Cursor, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[Community]:
        query = db.Community.select("*")

        if where:
            query = query.where(*where)

        return list(map(self._community_row_to_obj, c.fetch_all(query)))

    def _community_row_to_obj(self, row: db.Community) -> Community:
        return Community(
            jumpedia=self,
            id=row.id,
            real_name=text.RealStr(row.real_name, check=False),
            norm_name=text.NormStr(row.norm_name, check=False),
            limits=CommunityLimits(**json.loads(row.limits)),
        )

    def get_communities(
        self, c: orm.Cursor, /, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[Community]:
        return self._get_communities_inner(c)

    def get_community_by_id(self, c: orm.Cursor, id: int, /) -> Community | None:
        communities = self._get_communities_inner(
            c, (db.Community.id, orm.Operator.EQ, id)
        )
        return communities[0] if communities else None

    def get_community_by_name(
        self, c: orm.Cursor, name: text.NormStr, /
    ) -> Community | None:
        communities = self._get_communities_inner(
            c, (db.Community.norm_name, orm.Operator.EQ, name)
        )
        return communities[0] if communities else None

    def get_community_by_server_id(
        self, c: orm.Cursor, server_id: int, /
    ) -> Community | None:
        row = c.fetch_one(
            db.Server.select(db.Server.community_id).where(
                (db.Server.id, orm.Operator.EQ, server_id)
            )
        )

        if row is None:
            return None

        return self.get_community_by_id(c, row.community_id)

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
        existing_community = self.get_community_by_server_id(c, server_id)

        if existing_community is not None:
            raise errors.ServerAlreadyConnectedToCommunityError(
                server_id, existing_community
            )

        c.execute(
            db.Server.insert(
                db.Server.id.bind(server_id),
                db.Server.community_id.bind(community_id),
            )
        )

        # Community must now be connected
        community = self.get_community_by_server_id(c, server_id)
        assert community is not None

        return community

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

        return community
