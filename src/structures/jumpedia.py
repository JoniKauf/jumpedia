from threading import RLock
import time
from typing import TYPE_CHECKING, Callable, Final, TypedDict
import logging

import mariadb
from discordtools import feedbackerrors as fbe
from structures.attribute import TaskAttribute, UserAttribute
from structures.list import List
from structures.ranks import MetaRank, UserRank
from structures.task import Task
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

class MetaRankResultT(TypedDict):
    user_id: int
    power: int

class GuildResultT(TypedDict):
    community_id: int


@dataclass(frozen=True, kw_only=True)
class Jumpedia(metaclass=metautils.Singleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default='jumpedia')
    edit_lock: RLock = field(init=False, default_factory=RLock)
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Jumpedia) and self.id == value.id
    
    def _init(self) -> None:
        with queries.connected(no_db=True) as (conn, cursor):
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
                
        with queries.connected() as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE TABLE community (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
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

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE community
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY (default_selected_list_id)
                    REFERENCES list(id)
                    ON DELETE SET NULL;
                """)

                cursor.execute(f"""
                    CREATE TABLE meta_rank (
                        user_id BIGINT UNSIGNED PRIMARY KEY,
                        power INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE list (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        community_id INT NOT NULL,
                        name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY (community_id)
                            REFERENCES community(id)
                            ON DELETE CASCADE,

                        UNIQUE (community_id, name)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE user (
                        id BIGINT UNSIGNED PRIMARY KEY,
                        community_id INT NOT NULL,
                        power INT NOT NULL,
                        selected_list_id INT,
                        
                        FOREIGN KEY (community_id)
                            REFERENCES community(id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (selected_list_id) 
                            REFERENCES list(id) 
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task_attribute (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        list_id INT NOT NULL,
                        name VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,
                        value_type INT NOT NULL,
                        `index` INT NOT NULL,
                        collection BLOB NOT NULL,
                        min_slots INT NOT NULL,
                        max_slots INT NOT NULL,
                        unique_slots BOOL NOT NULL,
                        unique_value_per_list BOOL NOT NULL,

                        FOREIGN KEY (list_id)
                            REFERENCES list(id)
                            ON DELETE CASCADE,

                        UNIQUE (list_id, name),
                        UNIQUE (list_id, `index`)
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task_attribute_alias (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        task_attribute_id INT NOT NULL,
                        list_id INT NOT NULL,
                        alias VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY (task_attribute_id) 
                            REFERENCES task_attribute(id) 
                            ON DELETE CASCADE,
                        FOREIGN KEY (list_id) 
                            REFERENCES list(id) 
                            ON DELETE CASCADE,

                        UNIQUE (list_id, alias)
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE user_attribute (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        list_id INT NOT NULL,
                        name VARCHAR({UserAttribute.MAX_SYN_LEN}) NOT NULL,
                        `index` INT NOT NULL,
                        value_type INT NOT NULL,
                        collection BLOB NOT NULL,
                        min_slots INT NOT NULL,
                        max_slots INT NOT NULL,
                        unique_slots BOOL NOT NULL,

                        FOREIGN KEY (list_id)
                            REFERENCES list(id)
                            ON DELETE CASCADE,

                        UNIQUE (list_id, name),
                        UNIQUE (list_id, `index`)
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE user_attribute_alias (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_attribute_id INT NOT NULL,
                        list_id INT NOT NULL,
                        alias VARCHAR({UserAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY (user_attribute_id)
                            REFERENCES user_attribute(id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (list_id) 
                            REFERENCES list(id) 
                            ON DELETE CASCADE,

                        UNIQUE (list_id, alias)
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        list_id INT NOT NULL,
                        name VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,
                            
                        FOREIGN KEY (list_id)
                            REFERENCES list(id)
                            ON DELETE CASCADE,

                        UNIQUE (list_id, name)
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task_alias (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        task_id INT NOT NULL,
                        list_id INT NOT NULL,
                        alias VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY (task_id)
                            REFERENCES task(id)
                            ON DELETE CASCADE,

                        FOREIGN KEY (list_id) 
                            REFERENCES list(id) 
                            ON DELETE CASCADE,

                        UNIQUE (list_id, alias)
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task_attribute_value (
                        task_id INT NOT NULL,
                        task_attribute_id INT NOT NULL,
                        value BLOB NOT NULL,

                        PRIMARY KEY (task_id, task_attribute_id),

                        FOREIGN KEY (task_id)
                            REFERENCES task(id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (task_attribute_id)
                            REFERENCES task_attribute(id)
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE task_user_attribute_value (
                        task_id INT NOT NULL,
                        user_id BIGINT UNSIGNED NOT NULL,
                        user_attribute_id INT NOT NULL,
                        value BLOB NOT NULL,

                        PRIMARY KEY (task_id, user_id, user_attribute_id),

                        FOREIGN KEY (task_id)
                            REFERENCES task(id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (user_attribute_id)
                            REFERENCES user_attribute(id)
                            ON DELETE CASCADE,
                        FOREIGN KEY (user_id)
                            REFERENCES user(id)
                            ON DELETE CASCADE
                    )
                """)
            except Exception as e:
                try:
                    cursor.execute(f"""
                        DROP DATABASE `{self.database_name}`
                    """)
                finally:
                    raise e
            
        LOGGER.info("Meta database successfully created!")
    

    # --- Communities ---

    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[CommunityResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
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
    
    def _community_data_to_obj(self, data: CommunityResultT) -> 'Community':
        return Community(
            jumpedia=self,
            id=data['id'],
            name=data['name'],
            default_selected_list_id=data['default_selected_list_id']
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
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT community_id
                FROM guild
                WHERE id = {h|guild_id}
            """, h.steal())

            result: GuildResultT | None = cursor.fetchone()

        if result is None:
            return None

        return self.get_community_by_id(result['community_id'])
    

    # --- Meta Users ---

    def _fetch_from_meta_rank_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[MetaRankResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM meta_rank
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list['MetaRankResultT'] = cursor.fetchall()

        return result
    
    def _meta_rank_data_to_obj(self, data: MetaRankResultT) -> tuple[int, MetaRank]:
        return (data['user_id'], MetaRank.get(data['power']))
    
    def get_meta_ranks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> dict[int, 'MetaRank']:
        result: dict[int, 'MetaRank'] = {}

        for data in self._fetch_from_meta_rank_table(where):
            tup = self._meta_rank_data_to_obj(data)
            result[tup[0]] = tup[1]
        
        return result

    def get_meta_rank_by_user_id(self, user_id: int) -> MetaRank:
        data = self._fetch_from_meta_rank_table(lambda h: f"user_id = {h|user_id}")
        return self._meta_rank_data_to_obj(data[0])[1] if data else MetaRank.DEFAULT

Jumpedia()._init()