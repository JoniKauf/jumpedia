from threading import RLock
from typing import Callable, Final

import mariadb
from structures import community
from discordtools import feedbackerrors as fbe
from structures.community import Community, CommunityResultT
from utils import metautils, text
from database import queries
from dataclasses import dataclass, field

# -> Jumpedia has many:
#  -> Community has many:
#   -> User
#   -> List has many:
#    -> Task
#    -> Attribute

@dataclass(frozen=True, kw_only=True)
class Jumpedia(metaclass=metautils.Singleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default='meta')
    edit_lock: RLock = field(init=False, default_factory=RLock)
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Jumpedia) and self.id == value.id
    
    def _init(self) -> None:
        with queries.connected(self) as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE DATABASE `{self.database_name}`
                        CHARACTER SET = utf8mb4
                        COLLATE = utf8mb4_unicode_ci
                    """)
            except mariadb.Error:
                return

            try:
                cursor.execute(f"""
                    CREATE TABLE community (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE,
                        display_name VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE,
                        database_name VARCHAR({Community.MAX_NAME_LENGTH}) 
                            AS (CONCAT({Community.DATABASE_PREFIX}, id)) VIRTUAL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE guild (
                        id BIGINT UNSIGNED PRIMARY KEY,
                        community_id INT NOT NULL,

                        FOREIGN KEY (community_id) 
                            REFERENCES community(id) 
                            ON DELETE CASCADE
                    )
                """)

            except Exception:
                try:
                    cursor.execute(f"""
                        DROP DATABASE `{self.database_name}`
                    """)
                finally:
                    exit()
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[CommunityResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT
                    c.*,
                    GROUP_CONCAT(g.guild_id) AS guild_ids
                FROM community c
                LEFT JOIN guild g ON c.id = g.community_id
                {f"WHERE {where(h)}" if where is not None else ""}
                GROUP BY c.id
            """, h.steal())

            result: list[CommunityResultT] = cursor.fetchall()

        return result
    
    def _fetch_from_guild_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[CommunityResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    c.*,
                    GROUP_CONCAT(g.guild_id) AS guild_ids
                FROM community c
                JOIN guild g ON g.community_id = c.id
                WHERE c.id = (
                    SELECT community_id
                    FROM guild
                    {f"WHERE {where(h)}" if where is not None else ""}
                )
                GROUP BY c.id  
            """, h.steal())

            result: list[CommunityResultT] = cursor.fetchall()

        return result
    
    def _community_data_to_obj(self, data: community.CommunityResultT | None) -> Community:
        if data is None:
            raise fbe.TemporaryFeedbackError("Community does not exist!")
        
        return Community(
            jumpedia=self,
            id=data['id'],
            guild_ids=frozenset(int(id) for id in data['guild_ids'].split(',')),
            name=data['name'],
            display_name=data['display_name']
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Community]:
        return [self._community_data_to_obj(data) for data in self._fetch_from_community_table(where)]
        
    def get_community_by_id(self, id: int) -> Community:
        data = self._fetch_from_community_table(lambda h: f"id = {h|id}")
        return self._community_data_to_obj(data[0] if data else None)
    
    def get_community_by_name(self, name: str) -> Community:
        name = text.norm(name)
        data = self._fetch_from_community_table(lambda h: f"name = {h|name}")
        return self._community_data_to_obj(data[0] if data else None)
    
    def get_community_by_guild_id(self, guild_id: int) -> Community:
        data = self._fetch_from_guild_table(lambda h: f"id = {h|guild_id}")
        return self._community_data_to_obj(data[0] if data else None)
    
Jumpedia()._init()