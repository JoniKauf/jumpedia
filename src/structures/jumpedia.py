from threading import RLock
from typing import Any, Callable, ClassVar, overload

import mariadb
from structures import community
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute
from structures.community import Community, CommunityTableT
from structures.list import List
from utils import metautils, text
from database import queries

# -> Jumpedia
#    -> Collection of Communities
#       -> Collection of Lists
#          -> Collection of Trickjumps

from dataclasses import dataclass, field

@dataclass(frozen=True, kw_only=True)
class Jumpedia(metaclass=metautils.Singleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default='meta')
    edit_lock: RLock = field(init=False, default_factory=RLock)
    
    def _init(self) -> None:
        with queries.connected(self) as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE DATABASE `{self.database_name}`
                """)
            except mariadb.Error:
                return

            h = queries.ArgHelper()

            try:
                cursor.execute(f"""
                    CREATE TABLE {h|Community.META_TABLE_NAME} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        guild_id BIGINT UNSIGNED NOT NULL,
                        name VARCHAR({h|Community.MAX_NAME_LENGTH}) UNIQUE,
                        display_name VARCHAR({h|Community.MAX_NAME_LENGTH}) UNIQUE,
                        database_name VARCHAR({h|Community.MAX_NAME_LENGTH + len(Community.DATABASE_PREFIX)}) UNIQUE
                    )
                """, h.steal())
            except Exception:
                exit()

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Jumpedia) and self.id == value.id
    
    def _fetch_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[CommunityTableT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {h|Community.META_TABLE_NAME}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[CommunityTableT] = cursor.fetchall()

        return result
    
    def _data_to_obj(self, data: community.CommunityTableT | None) -> Community:
        if data is None:
            raise fbe.TemporaryFeedbackError("Community does not exist!")
        
        return Community(
            jumpedia=self,
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            display_name=data['display_name'],
            database_name=data['database_name']
        )
    
    def get_communities(self) -> list[Community]:
        return [self._data_to_obj(data) for data in self._fetch_from_table(None)]
        
    def get_community_by_id(self, id: int) -> Community:
        data = self._fetch_from_table(lambda h: f"id = {h|id}")
        return self._data_to_obj(data[0] if data else None)
    
    def get_community_by_name(self, name: str) -> Community:
        name = text.norm(name)
        data = self._fetch_from_table(lambda h: f"id = {h|name}")
        return self._data_to_obj(data[0] if data else None)
    
    def get_community_by_guild_id(self, guild_id: int) -> Community:
        data = self._fetch_from_table(lambda h: f"guild_id = {h|guild_id}")
        return self._data_to_obj(data[0] if data else None)
    
Jumpedia()._init()