
import time
import typing as t

from src.utils.orm.query.select import Select, Where

from . import db
from src.utils import text

from src.utils.orm import *
from .. import BaseStructure, errors, user
from ..attribute import slot_type
from ..community import Community, CommunityLimits
from ..errors import StructureNotFoundError, SynAlreadyTakenError
from ..user import JumpediaUser
from ..user.ranks import CommunityRank, JumpediaRank

class JumpediaLimits(t.NamedTuple):
    community_name_length_max: int
    list_name_length_max: int
    user_name_length_max: int  # Discord limit
    attribute_syn_length_max: int
    attribute_task_value_slot_count_max: int
    attribute_task_value_slot_length_max: int

class Jumpedia(BaseStructure):
    id: int
    limits: JumpediaLimits
    connector: Connector
    meta_connector: Connector

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)
    
    @property
    def name(self) -> str:
        return self.__class__.type_name

    def __post_init__(self) -> None:
        if self.connector.database_name is None:
            raise ValueError('connector must have database_name')
        
        if self.meta_connector.database_name is not None:
            raise ValueError('meta_connector must not have database_name')
        
        db.create_database(self)
    

    # --- Communities ---

    def create_community(self, *, real_name: text.RealStr, server_id: int, jumpedia_user: JumpediaUser) -> 'Community':
        norm_name = text.NormStr(real_name)
        
        with self.locked:
            comm = self.get_community_by_server_id(server_id)

            if comm is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, comm)
            
            comm = self.get_community_by_name(norm_name)

            if comm is not None:
                raise SynAlreadyTakenError(norm_name, comm)

            with self.connector.cursor() as c:
                execute_data = c.insert(
                    db.Community.norm_name.bind_n(norm_name),
                    db.Community.real_name.bind_n(real_name),
                    into=db.Community
                ).query().execute(
                    get_last_generated_id=True
                )

                community_id = execute_data.last_generated_id

                assert community_id is not None
                
                c.insert(
                    db.Server.id.bind_n(server_id),
                    db.Server.community_id.bind_n(community_id),
                    into=db.Server
                ).query().execute()
                
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
                        attribute_alias_count_max=2
                    )
                )  
                
                jumpedia_user.get_or_create_community_user(
                    comm.id,
                    CommunityRank.OWNER,
                    None,
                    True,
                    True
                )

                return comm
    
    def delete_community(self, id: int) -> None:
        with self.locked, self.connector.cursor() as c:
            execute_data = c.delete(
                from_=db.Community
            ).where(
                (db.Community.id, Operator.EQ, id)
            ).query().execute(
                get_affected_row_count=True
            )
                
            if execute_data.affected_row_count < 1:
                raise StructureNotFoundError(Community)
    
    def _fetch_from_community_table(self, where: t.Callable[[Select[db.Community]], Where[db.Community]] | None) -> list[db.Community]:
        with self.connector.cursor() as c:
            select = c.select(
                '*', from_=db.Community
            )

            if where is not None:
                query = where(select).query()
            else:
                query = select.query()

            return query.fetchall()
    
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
                attribute_alias_count_max=2
            )
        )
    
    def get_communities(self, where: t.Callable[[Select[db.Community]], Where[db.Community]] | None = None) -> list[Community]:
        return [
            self._community_row_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> Community | None:
        data = self._fetch_from_community_table(lambda select: select.where((db.Community.id, Operator.EQ, id)))
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, norm_name: text.NormStr) -> Community | None:
        data = self._fetch_from_community_table(lambda select: select.where((db.Community.norm_name, Operator.EQ, norm_name)))
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> Community | None:
        with self.connector.cursor() as c:
            row = c.select(
                db.Server.community_id,
                from_=db.Server
            ).where(
                (db.Server.id, Operator.EQ, server_id)
            ).query().fetchone()

        if row is None:
            return None

        return self.get_community_by_id(row.community_id)
    

    # --- Jumpedia Users ---

    def create_or_get_jumpedia_user(
        self, 
        id: int, 
        name: str, 
        jumpedia_rank: JumpediaRank, 
        override_name_if_user_exists: bool,
        override_jumpedia_rank_if_user_exists: bool
    ) -> JumpediaUser:
        norm_name = text.NormStr(name)

        with self.locked:
            user = self.get_jumpedia_user_by_id(id)

            with self.connector.cursor() as c:
                if user is None:
                    c.insert(
                        db.JumpediaUser.id.bind_n(id),
                        db.JumpediaUser.power.bind_n(jumpedia_rank.power),
                        db.JumpediaUser.norm_name.bind_n(norm_name),
                        db.JumpediaUser.raw_name.bind_n(name),
                        into=db.JumpediaUser
                    ).query().execute()

                else:
                    jumpedia_rank = jumpedia_rank if override_jumpedia_rank_if_user_exists else user.jumpedia_rank
                    name = name if override_name_if_user_exists else user.user_name

                    if name != user.user_name or jumpedia_rank != user.jumpedia_rank:
                        c.update(
                            db.JumpediaUser.norm_name.bind_one(norm_name),
                            db.JumpediaUser.raw_name.bind_one(name),
                            db.JumpediaUser.power.bind_one(jumpedia_rank.power),
                            table=db.JumpediaUser
                        ).where(
                            (db.JumpediaUser.id, Operator.EQ, user.id)
                        ).query().execute()
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    user_name=name,
                    jumpedia_rank=jumpedia_rank
                )

    def _fetch_from_user_table(self, where: t.Callable[[Select[db.JumpediaUser]], Where[db.JumpediaUser]] | None) -> list[db.JumpediaUser]:
        with self.connector.cursor() as c:
            select = c.select(
                '*',
                from_=db.JumpediaUser
            )

            if where is not None:
                query = where(select).query()
            else:
                query = select.query()

            result = query.fetchall()

        return result
    
    def _user_row_to_obj(self, row: db.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            user_name=row.raw_name,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power)
        )
    
    def get_users(self, where: t.Callable[[Select[db.JumpediaUser]], Where[db.JumpediaUser]] | None) -> list[JumpediaUser]:
        return [
            self._user_row_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_jumpedia_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda select: select.where((db.JumpediaUser.id, Operator.EQ, id)))
        return self._user_row_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> Community:
        with self.locked:
            existing_community = self.get_community_by_server_id(server_id)

            if existing_community is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, existing_community)     
            
            with self.connector.cursor() as c:
                c.insert(
                    db.Server.id.bind_n(server_id),
                    db.Server.community_id.bind_n(community_id),
                    into=db.Server
                ).query().execute()

            # Community must now be connected
            community = self.get_community_by_server_id(server_id)
            assert community is not None

            return community

    def remove_community_from_server(self, server_id: int) -> Community:
        with self.locked:
            with self.connector.cursor() as c:
                row = c.delete(
                    from_=db.Server
                ).where(
                    (db.Server.id, Operator.EQ, server_id)
                ).returning(
                    db.Server.community_id
                ).query().fetchone()

            if row is None:
                raise errors.ServerNotConnectedToACommunityError(server_id)

            community = self.get_community_by_id(row.community_id)
            assert community is not None

            return community