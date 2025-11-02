import time
import typing as t

from src.utils import orm, text

from .. import BaseStructure, errors, user
from ..attribute import slot_str
from ..community import Community, CommunityLimits
from ..errors import StructureNotFoundError, SynAlreadyTakenError
from ..user import JumpediaUser
from ..user.rank import CommunityRank, JumpediaRank
from . import db


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
    id: int
    limits: JumpediaLimits
    connector: orm.Connector
    meta_connector: orm.Connector

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)

    @property
    def name(self) -> str:
        return self.__class__.type_name

    def __post_init__(self) -> None:
        if self.connector.database_name is None:
            raise ValueError("connector must have database_name")

        if self.meta_connector.database_name is not None:
            raise ValueError("meta_connector must not have database_name")

        db.create_database(self)

    # --- Communities ---

    def create_community(
        self, real_name: text.RealStr, server_id: int, jumpedia_user: JumpediaUser
    ) -> Community:
        norm_name = text.NormStr(real_name)

        with self.locked:
            comm = self.get_community_by_server_id(server_id)

            if comm is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, comm)

            comm = self.get_community_by_name(norm_name)

            if comm is not None:
                raise SynAlreadyTakenError(norm_name, comm)

            with self.connector.cursor() as c:
                execute_data = c.execute(
                    db.Community.insert(
                        db.Community.norm_name.bind(norm_name),
                        db.Community.real_name.bind(real_name),
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
                    real_name=real_name,
                    norm_name=norm_name,
                    limits=CommunityLimits(
                        community_list_count_max=2,
                        list_attribute_count_max=3,
                        list_task_count_max=2,
                        attribute_collection_entry_alias_count_max=2,
                        attribute_collection_entry_count_max=2,
                        attribute_alias_count_max=2,
                    ),
                )

                comm.get_or_create_community_user(
                    jumpedia_user, CommunityRank.OWNER, None, True, True
                )

                return comm

    def delete_community(self, id: int) -> None:
        with self.locked, self.connector.cursor() as c:
            execute_data = c.execute(
                (db.Community.delete().where((db.Community.id, orm.Operator.EQ, id))),
                get_affected_row_count=True,
            )

            if execute_data.affected_row_count < 1:
                raise StructureNotFoundError(Community)

    def _fetch_from_community_table(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[db.Community]:
        with self.connector.cursor() as c:
            query = db.Community.select("*")

            if where is not None:
                query = query.where(*where)

            return c.fetch_all(query)

    def _community_row_to_obj(self, row: db.Community) -> Community:
        return Community(
            jumpedia=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name,
            limits=CommunityLimits(
                community_list_count_max=2,
                list_attribute_count_max=3,
                list_task_count_max=2,
                attribute_collection_entry_alias_count_max=2,
                attribute_collection_entry_count_max=2,
                attribute_alias_count_max=2,
            ),
        )

    def get_communities(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[Community]:
        return [
            self._community_row_to_obj(data)
            for data in self._fetch_from_community_table(*where)
        ]

    def get_community_by_id(self, id: int) -> Community | None:
        data = self._fetch_from_community_table((db.Community.id, orm.Operator.EQ, id))
        return self._community_row_to_obj(data[0]) if data else None

    def get_community_by_name(self, norm_name: text.NormStr) -> Community | None:
        data = self._fetch_from_community_table(
            (db.Community.norm_name, orm.Operator.EQ, norm_name)
        )
        return self._community_row_to_obj(data[0]) if data else None

    def get_community_by_server_id(self, server_id: int) -> Community | None:
        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.Server.select(db.Server.community_id).where(
                    (db.Server.id, orm.Operator.EQ, server_id)
                )
            )

        if row is None:
            return None

        return self.get_community_by_id(row.community_id)

    # --- Jumpedia Users ---

    def get_or_create_jumpedia_user(
        self,
        id: int,
        name: str,
        jumpedia_rank: JumpediaRank,
        override_name_if_user_exists: bool,
        override_jumpedia_rank_if_user_exists: bool,
    ) -> JumpediaUser:
        norm_name = text.NormStr(name)

        with self.locked:
            user = self.get_jumpedia_user_by_id(id)

            with self.connector.cursor() as c:
                if user is None:
                    c.execute(
                        db.JumpediaUser.insert(
                            db.JumpediaUser.id.bind(id),
                            db.JumpediaUser.power.bind(jumpedia_rank.power),
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

                    if name != user.user_name or jumpedia_rank != user.jumpedia_rank:
                        c.execute(
                            db.JumpediaUser.update(
                                db.JumpediaUser.norm_name.set(norm_name),
                                db.JumpediaUser.raw_name.set(name),
                                db.JumpediaUser.power.set(jumpedia_rank.power),
                            ).where((db.JumpediaUser.id, orm.Operator.EQ, user.id))
                        )

                return JumpediaUser(
                    jumpedia=self, id=id, user_name=name, jumpedia_rank=jumpedia_rank
                )

    def _fetch_from_user_table(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[db.JumpediaUser]:
        with self.connector.cursor() as c:
            query = db.JumpediaUser.select("*")

            if where:
                query = query.where(*where)

            return c.fetch_all(query)

    def _user_row_to_obj(self, row: db.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            user_name=row.raw_name,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power),
        )

    def get_users(
        self, *where: tuple[t.Any, orm.Operator, t.Any]
    ) -> list[JumpediaUser]:
        return [
            self._user_row_to_obj(data) for data in self._fetch_from_user_table(*where)
        ]

    def get_jumpedia_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table((db.JumpediaUser.id, orm.Operator.EQ, id))
        return self._user_row_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> Community:
        with self.locked:
            existing_community = self.get_community_by_server_id(server_id)

            if existing_community is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(
                    server_id, existing_community
                )

            with self.connector.cursor() as c:
                c.execute(
                    db.Server.insert(
                        db.Server.id.bind(server_id),
                        db.Server.community_id.bind(community_id),
                    )
                )

            # Community must now be connected
            community = self.get_community_by_server_id(server_id)
            assert community is not None

            return community

    def remove_community_from_server(self, server_id: int) -> Community:
        with self.locked:
            with self.connector.cursor() as c:
                row = c.fetch_one(
                    db.Server.delete()
                    .where((db.Server.id, orm.Operator.EQ, server_id))
                    .returning(db.Server.community_id)
                )

            if row is None:
                raise errors.ServerNotConnectedToACommunityError(server_id)

            community = self.get_community_by_id(row.community_id)
            assert community is not None

            return community
