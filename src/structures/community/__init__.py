from contextlib import _GeneratorContextManager
from dataclasses import dataclass, field
from functools import cached_property
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
import discord as dc
import mariadb
import mariadb.constants
from mariadb.constants import ERR
from errors.feedback import FeedbackError, feedbacks
from ranks.community_rank import CommunityRank
from structures import attributes, task
from structures.base_structure import BaseStructure
from structures.attributes import AttributeValueType, Uniqueness, UniquenessExtended
from structures.attributes.static_attribute import StaticAttribute
from structures.list import List
from structures.user import JumpediaUser
from structures.user.community_user import CommunityUser
from utils import text
from database import queries, typed as typed
from database.typed import SingleTableRowT, Tables as TBL
from typing import Optional as Opt
import structures.list as list_package
from discordtools import messaging as msg

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
 

@dataclass
class CommunityDataCache:
    server_ids: frozenset[int] | None = None


MAX_NAME_LENGTH: int = 64
MIN_NAME_LENGTH: int = 2

@dataclass(frozen=True, kw_only=True)
class Community(BaseStructure):
    __structure_name__ = "community"

    MAX_LISTS: ClassVar[int] = 1

    jumpedia: 'Jumpedia'
    id: int
    name: str
    default_selected_list_id: int | None

    _cache: CommunityDataCache = field(init=False, default_factory=CommunityDataCache)

    def get_server_ids(self) -> frozenset[int]:
        if self._cache.server_ids is not None:
            return self._cache.server_ids
        
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.Server.id}
                FROM {TBL.Server}
                WHERE {TBL.Server.community_id} = {h|self.id}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        self._cache.server_ids = frozenset(row[TBL.Server.id] for row in result)

        return self._cache.server_ids
        
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    def create_list(self, name: str) -> 'List':
        with self.locked:
            if self.get_list_by_name(name) is not None:
                raise feedbacks.temp("A list with that name already exists")
            
            if (count := len(self.get_lists())) >= Community.MAX_LISTS:
                raise feedbacks.temp("Limit of lists reached", count)
            
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TBL.List} (
                        {TBL.List.community_id},
                        {TBL.List.name}
                    ) 
                    VALUES (
                        {h|self.id},
                        {h|name}
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid  # type: ignore

                list = List(
                    community=self,
                    id=id,
                    name=name
                )

                list.create_static_attribute(
                    task.STATIC_NAME_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    1,
                    UniquenessExtended.PER_LIST,
                )

                list.create_static_attribute(
                    task.STATIC_ALIASES_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    attributes.MAX_SLOTS,
                    UniquenessExtended.PER_LIST
                )

            return list
            
            
    def delete_list(self, list_id: int) -> bool:
        h = queries.ArgHelper()

        with self.locked, queries.connected() as (conn, cursor):
            cursor.execute(f"""
                DELETE FROM {TBL.List}
                WHERE 
                    {TBL.List.community_id} = {h|self.id}
                    AND {TBL.List.id} = {h|list_id}
            """, h.steal())

            return cursor.rowcount > 0


    def _fetch_from_list_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.List}
                WHERE 
                    {TBL.List.community_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _list_data_to_obj(self, data: typed.SingleTableRowT) -> List:
        return List(
            community=self,
            id=data[TBL.List.id],
            name=data[TBL.List.name]
        )
    
    def get_lists(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[List]:
        return [
            self._list_data_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda h: f"{TBL.List.id} = {h|id}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, name: str) -> List | None:
        name = text.norm(name)
        data = self._fetch_from_list_table(lambda h: f"{TBL.List.name} = {h|name}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        if self.default_selected_list_id is None:
            return None
        
        return self.get_list_by_id(self.default_selected_list_id)
    
    def set_default_selected_list(self, list_id: int | None) -> bool:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            try:
                cursor.execute(f"""
                    UPDATE {TBL.Community} 
                    SET {TBL.Community.default_selected_list_id} = {h|list_id}
                    WHERE {TBL.Community.id} = {h|self.id}
                """, h.steal())
            except mariadb.IntegrityError as e:
                # list_id doesn't exist
                if e.errno == ERR.ER_NO_REFERENCED_ROW_2:
                    return False
                
                raise e
            
            return True
                
    def get_or_create_community_user(
        self, 
        jumpedia_user: JumpediaUser, 
        community_rank: CommunityRank, 
        selected_list_id: int | None, 
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool
    ) -> CommunityUser:
        h = queries.ArgHelper()
        with self.locked:
            community_user = self.get_community_user(jumpedia_user)
            
            with queries.connected() as (conn, cursor):
                # User doesn't exist yet
                if community_user is None:
                    cursor.execute(f"""
                        INSERT INTO {TBL.CommunityUser} (
                            {TBL.CommunityUser.community_id},
                            {TBL.CommunityUser.user_id},
                            {TBL.CommunityUser.power},
                            {TBL.CommunityUser.selected_list_id}
                        )
                        VALUES (
                            {h|self.id},
                            {h|jumpedia_user.id},
                            {h|community_rank.power},
                            {h|(None if selected_list_id is None else selected_list_id)}
                        )
                    """, h.steal())

                else:
                    community_rank = community_rank if override_community_rank_if_user_exists else community_user.community_rank
                    selected_list_id = selected_list_id if override_selected_list_if_user_exists else community_user.selected_list_id

                    if community_rank != community_user or selected_list_id != selected_list_id:
                        cursor.execute(f"""
                            UPDATE {TBL.CommunityUser}
                            SET 
                                {TBL.CommunityUser.power} = {h|community_rank.power}
                                {TBL.CommunityUser.selected_list_id} = {h|(None if selected_list_id is None else selected_list_id)}
                            WHERE 
                                {TBL.CommunityUser.community_id} = {h|self.id}
                                AND {TBL.CommunityUser.user_id} = {h|jumpedia_user.id}
                        """, h.steal()) 

                return CommunityUser(
                    community=self,
                    jumpedia_user=jumpedia_user,
                    community_rank=community_rank,
                    selected_list_id=selected_list_id
                )

    
    def get_community_user(self, jumpedia_user: JumpediaUser) -> CommunityUser | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.CommunityUser}
                WHERE 
                    {TBL.CommunityUser.community_id} = {h|self.id}
                    AND {TBL.CommunityUser.user_id} = {h|jumpedia_user.id}
            """)

            result: SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return CommunityUser(
            community=self,
            jumpedia_user=jumpedia_user,
            community_rank=CommunityRank.get(result[TBL.CommunityUser.power]),
            selected_list_id=result[TBL.CommunityUser.selected_list_id]
        )