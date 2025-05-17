from threading import RLock
import time
from typing import TYPE_CHECKING, Callable, Final, TypedDict
import logging

import mariadb
from discordtools import feedbackerrors as fbe
from structures.ranks import UserRank
from structures.user import User
from utils import metautils, text
from database import queries
from dataclasses import dataclass, field

# -> Jumpedia has many:
#  -> Community has many:
#   -> User
#   -> List has many:
#    -> Task
#    -> Attribute

from structures.community import Community

LOGGER = logging.getLogger(__name__)

class CommunityResultT(TypedDict):
    id: int
    name: str
    default_selected_list_id: int | None
    guild_ids: str | None

class MetaUserResultT(TypedDict):
    id: int
    power: int


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
        with queries.connected(None) as (conn, cursor):
            cursor.execute(f"""
                SELECT SCHEMA_NAME
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = '{self.database_name}';
            """)

            exists = cursor.fetchone() is not None

            if exists:
                LOGGER.info("Meta database already exists, not creating new")
                return

            LOGGER.warning("Meta database does NOT exist, creating new in 5 seconds")

            time.sleep(5)

            cursor.execute(f"""
                CREATE DATABASE `{self.database_name}`
                    CHARACTER SET = utf8mb4
                    COLLATE = utf8mb4_unicode_ci
                """)
                
        with queries.connected(self) as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE TABLE community (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE,
                        default_selected_list_id INT DEFAULT NULL
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

                cursor.execute(f"""
                    CREATE TABLE meta_user (
                        id BIGINT UNSIGNED PRIMARY KEY,
                        power INT NOT NULL
                    )
                """)
            except Exception:
                try:
                    cursor.execute(f"""
                        DROP DATABASE `{self.database_name}`
                    """)
                finally:
                    exit()
            
        LOGGER.info("Meta database successfully created!")
    

    # --- Communities ---

    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[CommunityResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT
                    c.*,
                    GROUP_CONCAT(g.id) AS guild_ids
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
                    GROUP_CONCAT(g.id) AS guild_ids
                FROM community c
                JOIN guild g ON g.community_id = c.id
                WHERE c.id = (
                    SELECT community_id
                    FROM guild
                    {f"WHERE {where(h)}" if where is not None else ""}
                    LIMIT 1
                )
                GROUP BY c.id
            """, h.steal())

            result: list[CommunityResultT] = cursor.fetchall()
            
        return result
    
    def _community_data_to_obj(self, data: CommunityResultT) -> 'Community':
        guild_ids = data['guild_ids']

        if guild_ids is not None:
            guild_ids = frozenset(int(id) for id in guild_ids.split(','))

        return Community(
            jumpedia=self,
            id=data['id'],
            name=data['name'],
            default_selected_list_id=data['default_selected_list_id'],
            guild_ids=guild_ids or frozenset()
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list['Community']:
        return [
            self._community_data_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"id = {h|id}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> 'Community | None':
        name = text.norm(name)
        data = self._fetch_from_community_table(lambda h: f"name = {h|name}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_guild_id(self, guild_id: int) -> 'Community | None':
        data = self._fetch_from_guild_table(lambda h: f"id = {h|guild_id}")
        return self._community_data_to_obj(data[0]) if data else None
    

    # --- Meta Users ---

    def _fetch_from_meta_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[MetaUserResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM meta_user
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list['MetaUserResultT'] = cursor.fetchall()

        return result
    
    def _meta_user_data_to_obj(self, community: Community, data: MetaUserResultT) -> 'User':
        return User(
            community=community,
            id=data['id'],
            user_rank=UserRank.get(data['power']),
            selected_list=community.get_default_selected_list()
        )
    
    def get_meta_users(self, community: Community, where: Callable[[queries.ArgHelper], str] | None = None) -> list['User']:
        return [
            self._meta_user_data_to_obj(community, data) 
            for data in self._fetch_from_meta_user_table(where)
        ]

    def get_meta_user_by_id(self, community: Community, id: int) -> 'User | None':
        data = self._fetch_from_meta_user_table(lambda h: f"id = {h|id}")
        return self._meta_user_data_to_obj(community, data[0]) if data else None
    
    def get_meta_user_by_name(self, community: Community, name: str) -> 'User | None':
        name = text.norm(name)
        data = self._fetch_from_meta_user_table(lambda h: f"name = {h|name}")
        return self._meta_user_data_to_obj(community, data[0]) if data else None

Jumpedia()._init()