
import time
import typing as t

from . import db
from src.utils import text

from ...utils.orm import *
from .. import BaseStructure, errors, user
from ..attribute import slot_type
from ..community import Community, CommunityLimits
from ..errors import StructureNotFoundError, SynAlreadyTakenError
from ..user import JumpediaUser


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
                c.insert(
                    db.Community.norm_name.bind(norm_name),
                    db.Community.real_name.bind(real_name),
                    into=db.Community
                ).query().execute()

                community_id = c.last_generated_id

                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id}, 
                        {typed.Server.community_id}
                    )
                    VALUES (
                        {arg(server_id)},
                        {arg(community_id)}
                    )
                """)
                
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
            c.execute(lambda arg: t"""
                DELETE FROM {typed.Community}
                WHERE {typed.Community.id} = {arg(id)}
            """)
                
            if c.affected_row_count < 1:
                raise StructureNotFoundError(Community)
    
    def _fetch_from_community_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.Community]:
        with self.connector.cursor() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.Community}
                {Raw(f"WHERE {where(arg)}" if where is not None else "")}
            """)

            result = c.fetchall(typed.Community)

        return result
    
    def _community_row_to_obj(self, row: typed.Community) -> Community:
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
    
    def get_communities(self, where: t.Callable[[Arg], str] | None = None) -> list[Community]:
        return [
            self._community_row_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> Community | None:
        data = self._fetch_from_community_table(lambda arg: f"{typed.Community.id} = {arg(id)}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, norm_name: text.NormStr) -> Community | None:
        data = self._fetch_from_community_table(lambda arg: f"{typed.Community.norm_name} = {arg(norm_name)}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> Community | None:
        with self.connector.cursor() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.Server.community_id}
                FROM {typed.Server}
                WHERE {typed.Server.id} = {arg(server_id)}
            """)

            result = c.fetchone(typed.Server)

        if result is None:
            return None

        return self.get_community_by_id(result.community_id)
    

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
                    c.execute(lambda arg: t"""
                        INSERT INTO {typed.JumpediaUser} (
                            {typed.JumpediaUser.id},
                            {typed.JumpediaUser.power},
                            {typed.JumpediaUser.norm_name},
                            {typed.JumpediaUser.raw_name}
                        )
                        VALUES (
                            {arg(id)},
                            {arg(jumpedia_rank.power)},
                            {arg(norm_name)},
                            {arg(name)}
                        )
                    """)

                else:
                    jumpedia_rank = jumpedia_rank if override_jumpedia_rank_if_user_exists else user.jumpedia_rank
                    real_name = name if override_name_if_user_exists else user.user_name

                    if real_name != user.user_name or jumpedia_rank != user.jumpedia_rank:
                        c.execute(lambda arg: t"""
                            UPDATE {typed.JumpediaUser} 
                            SET 
                                {typed.JumpediaUser.norm_name} = {arg(norm_name)},
                                {typed.JumpediaUser.raw_name} = {arg(real_name)},
                                {typed.JumpediaUser.power} = {arg(jumpedia_rank.power)}
                            WHERE 
                                {typed.JumpediaUser.id} = {arg(user.id)}
                        """)
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    user_name=real_name,
                    jumpedia_rank=jumpedia_rank
                )

    def _fetch_from_user_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.JumpediaUser]:
        with self.connector.cursor() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.JumpediaUser}
                {Raw(f"WHERE {where(arg)}" if where is not None else "")}
            """)

            result = c.fetchall(typed.JumpediaUser)

        return result
    
    def _user_row_to_obj(self, row: typed.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            user_name=row.raw_name,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power)
        )
    
    def get_users(self, where: t.Callable[[Arg], str] | None = None) -> list[JumpediaUser]:
        return [
            self._user_row_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_jumpedia_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda arg: f"{typed.JumpediaUser.id} = {arg(id)}")
        return self._user_row_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> Community:
        with self.locked:
            existing_community = self.get_community_by_server_id(server_id)

            if existing_community is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, existing_community)     
            
            with self.connector.cursor() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id},
                        {typed.Server.community_id}
                    )
                    VALUES (
                        {arg(server_id)},
                        {arg(community_id)}
                    )
                """)

            # Community must now be connected
            community = self.get_community_by_server_id(server_id)
            assert community is not None

            return community

    def remove_community_from_server(self, server_id: int) -> Community:
        with self.locked:
            with self.connector.cursor() as c:
                c.execute(lambda arg: t"""
                    DELETE FROM {typed.Server}
                    WHERE {typed.Server.id} = {arg(server_id)}
                    RETURNING {typed.Server.community_id}
                """)
                
                row = c.fetchone(typed.Server)

            if row is None:
                raise errors.ServerNotConnectedToACommunityError(server_id)

            community = self.get_community_by_id(row.community_id)
            assert community is not None

            return community