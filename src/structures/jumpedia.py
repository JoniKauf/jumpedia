from threading import RLock
from typing import Any, ClassVar, overload

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
        
    def get_communities(self) -> list[Community]:
        h = queries.ArgHelper()

        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT * 
                FROM {h|Community.META_TABLE_NAME}
            """, h.steal())
            
            result: list[CommunityTableT] = cursor.fetchall()

        communities: list[Community] = []

        for c_data in result:
            communities.append(Community(
                self,
                c_data['id'],
                c_data['guild_id'],
                c_data['name'],
                c_data['display_name'],
                c_data['database_name'],
            ))

        return communities
    
    def _get_community(self, data: community.CommunityTableT | None) -> Community:
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
    
    def get_community_by_id(self, id: int) -> Community:
        h = queries.ArgHelper()

        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT * 
                FROM {h|Community.META_TABLE_NAME} 
                WHERE id = {h|id}
            """, h.steal())

            result: community.CommunityTableT | None = cursor.fetchone()

        return self._get_community(result)
        
    def get_community_by_name(self, name: str) -> Community:
        name = text.norm(name)
        h = queries.ArgHelper()

        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT * 
                FROM {h|Community.META_TABLE_NAME} 
                WHERE name = {h|name}
            """, h.steal())

            result: community.CommunityTableT | None = cursor.fetchone()

        return self._get_community(result)
    
    def get_community_by_guild_id(self, guild_id: int) -> Community:
        h = queries.ArgHelper()

        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT * 
                FROM {h|Community.META_TABLE_NAME} 
                WHERE guild_id = {h|guild_id}
            """, h.steal())

            result: CommunityTableT | None = cursor.fetchone()

        return self._get_community(result)
    
Jumpedia()._init()