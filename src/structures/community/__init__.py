from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
import mariadb
from mariadb.constants import ERR
from database.simple_orm import Arg, Rows
from errors.feedback import FeedbackError, feedbacks
from ranks.community_rank import CommunityRank
from structures import attributes, task
from structures.attributes.slot_type import SlotType
from structures.base_structure import BaseStructure
from structures.attributes import Uniqueness
from structures.list import List
from structures.user import JumpediaUser
from structures.user.community_user import CommunityUser
from utils import text
from database import queries, typed

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
 

ListTbl = typed.List
CommunityTbl = typed.Community
CommunityUserTbl = typed.CommunityUser

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
        
        ServerTbl = typed.Server
        
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {ServerTbl.id}
                FROM {ServerTbl}
                WHERE {ServerTbl.community_id} = {arg(self.id)}
            """)

            result = c.fetchall(ServerTbl)

        self._cache.server_ids = frozenset(row.id for row in result)

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
            
            with queries.connected() as c:
                c.execute(lambda arg: f"""
                    INSERT INTO {ListTbl} (
                        {ListTbl.community_id},
                        {ListTbl.name}
                    ) 
                    VALUES (
                        {arg(self.id)},
                        {arg(name)}
                    )
                """)
                
                list_id = c.last_generated_id

                list = List(
                    community=self,
                    id=list_id,
                    name=name
                )

                list.create_static_attribute(
                    task.STATIC_NAME_ATTRIBUTE_NAME,
                    frozenset(),
                    SlotType.get_by_type(str),
                    1,
                    1,
                    Uniqueness.PER_LIST,
                )

                list.create_static_attribute(
                    task.STATIC_ALIASES_ATTRIBUTE_NAME,
                    frozenset(),
                    SlotType.get_by_type(str),
                    1,
                    attributes.MAX_SLOTS,
                    Uniqueness.PER_LIST
                )

            return list
            
            
    def delete_list(self, list_id: int) -> bool:
        

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: f"""
                DELETE FROM {ListTbl}
                WHERE 
                    {ListTbl.community_id} = {arg(self.id)}
                    AND {ListTbl.id} = {arg(list_id)}
            """)

            return c.affected_row_count > 0


    def _fetch_from_list_table(self, where: Callable[[Arg], str] | None) -> Rows[ListTbl]:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {ListTbl}
                WHERE 
                    {ListTbl.community_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result = c.fetchall(ListTbl)

        return result
    
    def _list_row_to_obj(self, row: ListTbl) -> List:
        return List(
            community=self,
            id=row.id,
            name=row.name
        )
    
    def get_lists(self, where: Callable[[Arg], str] | None = None) -> list[List]:
        return [
            self._list_row_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{ListTbl.id} = {arg(id)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, name: str) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{ListTbl.id} = {arg(name)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        if self.default_selected_list_id is None:
            return None
        
        return self.get_list_by_id(self.default_selected_list_id)
    
    def set_default_selected_list(self, list_id: int | None) -> bool:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                UPDATE {CommunityTbl} 
                SET {CommunityTbl.default_selected_list_id} = {arg(list_id)}
                WHERE {CommunityTbl.id} = {arg(self.id)}
            """)
            
            return c.affected_row_count > 0 
                
    def get_or_create_community_user(
        self, 
        jumpedia_user: JumpediaUser, 
        community_rank: CommunityRank, 
        selected_list_id: int | None, 
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool
    ) -> CommunityUser:
        with self.locked:
            community_user = self.get_community_user(jumpedia_user)
            
            with queries.connected() as c:
                # User doesn't exist yet
                if community_user is None:
                    c.execute(lambda arg: f"""
                        INSERT INTO {CommunityUserTbl} (
                            {CommunityUserTbl.community_id},
                            {CommunityUserTbl.user_id},
                            {CommunityUserTbl.power},
                            {CommunityUserTbl.selected_list_id}
                        )
                        VALUES (
                            {arg(self.id)},
                            {arg(jumpedia_user.id)},
                            {arg(community_rank.power)},
                            {arg(selected_list_id)}
                        )
                    """)

                else:
                    community_rank = community_rank if override_community_rank_if_user_exists else community_user.community_rank
                    selected_list_id = selected_list_id if override_selected_list_if_user_exists else community_user.selected_list_id

                    if community_rank != community_user or selected_list_id != selected_list_id:
                        c.execute(lambda arg: f"""
                            UPDATE {CommunityUserTbl}
                            SET 
                                {CommunityUserTbl.power} = {arg(community_rank.power)}
                                {CommunityUserTbl.selected_list_id} = {arg((None if selected_list_id is None else selected_list_id))}
                            WHERE 
                                {CommunityUserTbl.community_id} = {arg(self.id)}
                                AND {CommunityUserTbl.user_id} = {arg(jumpedia_user.id)}
                        """) 

                return CommunityUser(
                    community=self,
                    jumpedia_user=jumpedia_user,
                    community_rank=community_rank,
                    selected_list_id=selected_list_id
                )

    
    def get_community_user(self, jumpedia_user: JumpediaUser) -> CommunityUser | None:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {CommunityUserTbl}
                WHERE 
                    {CommunityUserTbl.community_id} = {arg(self.id)}
                    AND {CommunityUserTbl.user_id} = {arg(jumpedia_user.id)}
            """)

            result = c.fetchone(CommunityUserTbl)

        if result is None:
            return None
        
        return CommunityUser(
            community=self,
            jumpedia_user=jumpedia_user,
            community_rank=CommunityRank.get(result.power),
            selected_list_id=result.selected_list_id
        )