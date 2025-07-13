
import time
from typing import TYPE_CHECKING, Any, Callable, Final, Self, TypedDict
import logging
import discord as dc

from errors.feedback import FeedbackError, feedbacks
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from structures import BaseStructure, attributes, task, user
from structures import community
from structures.community import Community
from structures.list import List
from structures.task import Task
from structures.user import JumpediaUser
from utils import metautils, text
from database import queries, typed as typed
from database.typed import Tables as Tables
from dataclasses import dataclass, field
from discordtools import messaging as msg, users
from structures import list as list_

LOGGER = logging.getLogger(__name__)

class NotInServerError(ValueError):
    pass

class AbstractStructureAndSingleton(type(BaseStructure), metautils.Singleton):
    pass

@dataclass(frozen=True, kw_only=True)
class Jumpedia(BaseStructure, metaclass=AbstractStructureAndSingleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default=typed.DATABASE_NAME)
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)

    def _init(self) -> None:
        with queries.connected(no_db=True) as (conn, cursor):
            cursor.execute(f"""
                SELECT SCHEMA_NAME
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = '{self.database_name}';
            """)

            exists = cursor.fetchone() is not None

            if exists:
                LOGGER.info("Jumpedia database already exists, not creating new")
                return

            LOGGER.warning("Jumpedia database does NOT exist, creating new in 5 seconds")

            time.sleep(5)

            cursor.execute(f"""
                CREATE DATABASE `{self.database_name}`
                    CHARACTER SET = utf8mb4
                    COLLATE = utf8mb4_unicode_ci
                """)
                
        with queries.connected() as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE TABLE {Tables.Community} (
                        {Tables.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.Community.name} VARCHAR({community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
                        {Tables.Community.default_selected_list_id} INT DEFAULT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.Server} (
                        {Tables.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                        {Tables.Server.community_id} INT NOT NULL,

                        FOREIGN KEY ({Tables.Server.community_id}) 
                            REFERENCES {Tables.Community}({Tables.Community.id}) 
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.List} (
                        {Tables.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.List.community_id} INT NOT NULL,
                        {Tables.List.name} VARCHAR({list_.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY ({Tables.List.community_id})
                            REFERENCES {Tables.Community}({Tables.Community.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.List.community_id}, {Tables.List.name})
                    )
                """)

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE {Tables.Community}
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY ({Tables.Community.default_selected_list_id})
                        REFERENCES {Tables.List}({Tables.List.id})
                        ON DELETE SET NULL
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.JumpediaUser} (
                        {Tables.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                        {Tables.JumpediaUser.name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                        {Tables.JumpediaUser.power} INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.CommunityUser} (
                        {Tables.CommunityUser.community_id} INT NOT NULL,
                        {Tables.CommunityUser.user_id} BIGINT UNSIGNED NOT NULL,
                        {Tables.CommunityUser.power} INT NOT NULL,
                        {Tables.CommunityUser.selected_list_id} INT,

                        PRIMARY KEY ({Tables.CommunityUser.community_id}, {Tables.CommunityUser.user_id}),

                        FOREIGN KEY ({Tables.CommunityUser.community_id})
                            REFERENCES {Tables.Community}({Tables.Community.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.CommunityUser.user_id})
                            REFERENCES {Tables.JumpediaUser}({Tables.JumpediaUser.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.CommunityUser.selected_list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.StaticAttribute} (
                        {Tables.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.StaticAttribute.list_id} INT NOT NULL,
                        {Tables.StaticAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {Tables.StaticAttribute.slot_type} INT NOT NULL,
                        {Tables.StaticAttribute.position} INT NOT NULL,
                        {Tables.StaticAttribute.min_slots} INT NOT NULL,
                        {Tables.StaticAttribute.max_slots} INT NOT NULL,
                        {Tables.StaticAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({Tables.StaticAttribute.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.StaticAttribute.list_id}, {Tables.StaticAttribute.name}),
                        UNIQUE ({Tables.StaticAttribute.list_id}, {Tables.StaticAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.StaticAttributeAlias} (
                        {Tables.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.StaticAttributeAlias.static_attribute_id} INT NOT NULL,
                        {Tables.StaticAttributeAlias.list_id} INT NOT NULL,
                        {Tables.StaticAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({Tables.StaticAttributeAlias.static_attribute_id})
                            REFERENCES {Tables.StaticAttribute}({Tables.StaticAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.StaticAttributeAlias.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.StaticAttributeAlias.list_id}, {Tables.StaticAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAttribute} (
                        {Tables.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.TaskAttribute.list_id} INT NOT NULL,
                        {Tables.TaskAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {Tables.TaskAttribute.slot_type} INT NOT NULL,
                        {Tables.TaskAttribute.position} INT NOT NULL,
                        {Tables.TaskAttribute.min_slots} INT NOT NULL,
                        {Tables.TaskAttribute.max_slots} INT NOT NULL,
                        {Tables.TaskAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({Tables.TaskAttribute.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.TaskAttribute.list_id}, {Tables.TaskAttribute.name}),
                        UNIQUE ({Tables.TaskAttribute.list_id}, {Tables.TaskAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAttributeAlias} (
                        {Tables.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.TaskAttributeAlias.task_attribute_id} INT NOT NULL,
                        {Tables.TaskAttributeAlias.list_id} INT NOT NULL,
                        {Tables.TaskAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({Tables.TaskAttributeAlias.task_attribute_id})
                            REFERENCES {Tables.TaskAttribute}({Tables.TaskAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.TaskAttributeAlias.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.TaskAttributeAlias.list_id}, {Tables.TaskAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAttributeCollectionNode} (
                        {Tables.TaskAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.TaskAttributeCollectionNode.parent_id} INT,
                        {Tables.TaskAttributeCollectionNode.task_attribute_id} INT NOT NULL,
                        {Tables.TaskAttributeCollectionNode.value} BLOB NOT NULL,
                        {Tables.TaskAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({Tables.TaskAttributeCollectionNode.parent_id})
                            REFERENCES {Tables.TaskAttributeCollectionNode}({Tables.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.TaskAttributeCollectionNode.task_attribute_id})
                            REFERENCES {Tables.TaskAttribute}({Tables.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAttributeCollectionNodeAlias} (
                        {Tables.TaskAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.TaskAttributeCollectionNodeAlias.task_attribute_id} INT NOT NULL,
                        {Tables.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id} INT NOT NULL,
                        {Tables.TaskAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({Tables.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id})
                            REFERENCES {Tables.TaskAttributeCollectionNode}({Tables.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.TaskAttributeCollectionNodeAlias.task_attribute_id})
                            REFERENCES {Tables.TaskAttribute}({Tables.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                
                cursor.execute(f"""
                    CREATE TABLE {Tables.UserAttribute} (
                        {Tables.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.UserAttribute.list_id} INT NOT NULL,
                        {Tables.UserAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {Tables.UserAttribute.position} INT NOT NULL,
                        {Tables.UserAttribute.slot_type} INT NOT NULL,
                        {Tables.UserAttribute.min_slots} INT NOT NULL,
                        {Tables.UserAttribute.max_slots} INT NOT NULL,
                        {Tables.UserAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({Tables.UserAttribute.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.UserAttribute.list_id}, {Tables.UserAttribute.name}),
                        UNIQUE ({Tables.UserAttribute.list_id}, {Tables.UserAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.UserAttributeAlias} (
                        {Tables.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.UserAttributeAlias.user_attribute_id} INT NOT NULL,
                        {Tables.UserAttributeAlias.list_id} INT NOT NULL,
                        {Tables.UserAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({Tables.UserAttributeAlias.user_attribute_id})
                            REFERENCES {Tables.UserAttribute}({Tables.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.UserAttributeAlias.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.UserAttributeAlias.list_id}, {Tables.UserAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.UserAttributeCollectionNode} (
                        {Tables.UserAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.UserAttributeCollectionNode.parent_id} INT,
                        {Tables.UserAttributeCollectionNode.user_attribute_id} INT NOT NULL,
                        {Tables.UserAttributeCollectionNode.value} BLOB NOT NULL,
                        {Tables.UserAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({Tables.UserAttributeCollectionNode.parent_id})
                            REFERENCES {Tables.UserAttributeCollectionNode}({Tables.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.UserAttributeCollectionNode.user_attribute_id})
                            REFERENCES {Tables.UserAttribute}({Tables.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.UserAttributeCollectionNodeAlias} (
                        {Tables.UserAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.UserAttributeCollectionNodeAlias.user_attribute_id} INT NOT NULL,
                        {Tables.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id} INT NOT NULL,
                        {Tables.UserAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({Tables.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id})
                            REFERENCES {Tables.UserAttributeCollectionNode}({Tables.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.UserAttributeCollectionNodeAlias.user_attribute_id})
                            REFERENCES {Tables.UserAttribute}({Tables.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.Task} (
                        {Tables.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.Task.list_id} INT NOT NULL,
                        {Tables.Task.name} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({Tables.Task.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.Task.list_id}, {Tables.Task.name})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAlias} (
                        {Tables.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {Tables.TaskAlias.task_id} INT NOT NULL,
                        {Tables.TaskAlias.list_id} INT NOT NULL,
                        {Tables.TaskAlias.alias} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({Tables.TaskAlias.task_id})
                            REFERENCES {Tables.Task}({Tables.Task.id})
                            ON DELETE CASCADE,

                        FOREIGN KEY ({Tables.TaskAlias.list_id})
                            REFERENCES {Tables.List}({Tables.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({Tables.TaskAlias.list_id}, {Tables.TaskAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.StaticAttributeTaskValue} (
                        {Tables.StaticAttributeTaskValue.task_id} INT NOT NULL,
                        {Tables.StaticAttributeTaskValue.static_attribute_id} INT NOT NULL,
                        {Tables.StaticAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY ({Tables.StaticAttributeTaskValue.task_id}, {Tables.StaticAttributeTaskValue.static_attribute_id}),

                        FOREIGN KEY ({Tables.StaticAttributeTaskValue.task_id})
                            REFERENCES {Tables.Task}({Tables.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.StaticAttributeTaskValue.static_attribute_id})
                            REFERENCES {Tables.StaticAttribute}({Tables.StaticAttribute.id})
                            ON DELETE CASCADE
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE {Tables.TaskAttributeTaskValue} (
                        {Tables.TaskAttributeTaskValue.task_id} INT NOT NULL,
                        {Tables.TaskAttributeTaskValue.task_attribute_id} INT NOT NULL,
                        {Tables.TaskAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {Tables.TaskAttributeTaskValue.task_id}, 
                            {Tables.TaskAttributeTaskValue.task_attribute_id}
                        ),

                        FOREIGN KEY ({Tables.TaskAttributeTaskValue.task_id})
                            REFERENCES {Tables.Task}({Tables.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.TaskAttributeTaskValue.task_attribute_id})
                            REFERENCES {Tables.TaskAttribute}({Tables.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {Tables.UserAttributeTaskValue} (
                        {Tables.UserAttributeTaskValue.task_id} INT NOT NULL,
                        {Tables.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                        {Tables.UserAttributeTaskValue.user_attribute_id} INT NOT NULL,
                        {Tables.UserAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {Tables.UserAttributeTaskValue.task_id}, 
                            {Tables.UserAttributeTaskValue.user_id}, 
                            {Tables.UserAttributeTaskValue.user_attribute_id}
                        ),

                        FOREIGN KEY ({Tables.UserAttributeTaskValue.task_id})
                            REFERENCES {Tables.Task}({Tables.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.UserAttributeTaskValue.user_attribute_id})
                            REFERENCES {Tables.UserAttribute}({Tables.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({Tables.UserAttributeTaskValue.user_id})
                            REFERENCES {Tables.JumpediaUser}({Tables.JumpediaUser.id})
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
            
        LOGGER.info("Jumpedia database successfully created!")
    

    # --- Communities ---

    def create_community(self, *, name: str, server_id: int, jumpedia_user: JumpediaUser) -> 'Community':
        with self.locked:
            community_ = self.get_community_by_server_id(server_id)

            if community_ is not None:
                raise feedbacks.temp("Server already connected to a community")
            
            community_ = self.get_community_by_name(name)

            if community_ is not None:
                raise feedbacks.temp("Community with that name exists")

            h = queries.ArgHelper()
            
            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {Tables.Community} (
                        {Tables.Community.name},
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {Tables.Server} (
                        {Tables.Server.id}, 
                        {Tables.Server.community_id}
                    )
                    VALUES (
                        {h|server_id},
                        {h|community_id}
                    )
                """, h.steal())
                
                community_ = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=None,
                    name=name
                )  

                community_.get_or_create_community_user(
                    self.create_or_get_jumpedia_user(
                        jumpedia_user.id, 
                        jumpedia_user.name,
                        JumpediaRank.DEFAULT,
                        True,
                        False
                    ), 
                    CommunityRank.OWNER, 
                    None,
                    True, 
                    True
                )

                community_ = Community(
                    jumpedia=self,
                    id=community_id,
                    name=name,
                    default_selected_list_id=None
                )

                # Rollback if anything goes wrong up to this point
                return community_
    
    def delete_community(self, community: Community) -> bool:
        h = queries.ArgHelper()

        with self.locked, community.locked, queries.connected() as (conn, cursor):
            cursor.execute(f"""
                DELETE FROM {Tables.Community}
                WHERE {Tables.Community.id} = {h|community.id}
            """, h.steal())

            return cursor.rowcount > 0
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.Community}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _community_data_to_obj(self, data: typed.SingleTableRowT) -> 'Community':
        return Community(
            jumpedia=self,
            id=data[Tables.Community.id],
            name=data[Tables.Community.name],
            default_selected_list_id=data[Tables.Community.default_selected_list_id]
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Community]:
        return [
            self._community_data_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{Tables.Community.id} = {h|id}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{Tables.Community.name} = {h|name}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> 'Community | None':
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tables.Server.community_id}
                FROM {Tables.Server}
                WHERE {Tables.Server.id} = {h|server_id}
            """, h.steal())

            result: typed.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None

        return self.get_community_by_id(result[Tables.Server.community_id])
    

    # --- Jumpedia Users ---

    def create_or_get_jumpedia_user(
        self, 
        id: int, 
        name: str, 
        jumpedia_rank: JumpediaRank, 
        override_name_if_user_exists: bool,
        override_jumpedia_rank_if_user_exists: bool
    ) -> JumpediaUser:
        h = queries.ArgHelper()

        with self.locked:
            user = self.get_user_by_id(id)

            with queries.connected() as (conn, cursor):
                if user is None:
                    cursor.execute(f"""
                        INSERT INTO {Tables.JumpediaUser} (
                            {Tables.JumpediaUser.id},
                            {Tables.JumpediaUser.power},
                            {Tables.JumpediaUser.name}
                        )
                        VALUES (
                            {h|id},
                            {h|jumpedia_rank.power},
                            {h|name}
                        )
                    """, h.steal())

                else:
                    jumpedia_rank = jumpedia_rank if override_jumpedia_rank_if_user_exists else user.jumpedia_rank
                    name = name if override_name_if_user_exists else user.name

                    if name != user.name or jumpedia_rank != user.jumpedia_rank:
                        cursor.execute(f"""
                            UPDATE {Tables.JumpediaUser} 
                            SET 
                                {Tables.JumpediaUser.name} = {h|name}
                                {Tables.JumpediaUser.power} = {h|jumpedia_rank.power}
                            WHERE 
                                {Tables.JumpediaUser.id} = {h|user.id}
                        """, h.steal())
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    jumpedia_rank=jumpedia_rank,
                    name=name
                )

    def _fetch_from_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.JumpediaUser}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: typed.SingleTableRowT) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            name=data[Tables.JumpediaUser.name],
            id=data[Tables.JumpediaUser.id],
            jumpedia_rank=JumpediaRank.get(data[Tables.JumpediaUser.power])
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[JumpediaUser]:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda h: f"{Tables.JumpediaUser.id} = {h|id}")
        return self._user_data_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> 'Community':
        with self.locked:
            existing_community = self.get_community_by_server_id(server_id)

            if existing_community is not None:
                if community_id == existing_community.id:
                    raise feedbacks.temp("Community is already in this server!")
                
                import cogs.jumpedia
                
                connect_cmd = cogs.jumpedia.JumpediaCog.connect_community.qualified_name
                disconnect_cmd = cogs.jumpedia.JumpediaCog.disconnect_community.qualified_name

                raise FeedbackError(
                    "Server Already Connected To A Community",
                    f"This server is already connected to a different community called {msg.code(existing_community.name)}!",
                    additional="A server can only be connected to one community at a time.",
                    paragraphs=[
                        f"If you want to change the community for this server, see the commands "
                        f"{msg.code(connect_cmd)} and {msg.code(disconnect_cmd)}."
                    ]
                )     
            
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {Tables.Server} (
                        {Tables.Server.id},
                        {Tables.Server.community_id}
                    )
                    VALUES (
                        {h|server_id},
                        {h|community_id}
                    )
                """, h.steal())

            # Community must now be connected
            return self.get_community_by_server_id(server_id)  # type: ignore

    def remove_community_from_server(self, server_id: int) -> 'Community':
        with self.locked:
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {Tables.Server}
                    WHERE 
                        {Tables.Server.id} = {h|server_id}
                """, h.steal())

                if cursor.rowcount < 1:
                    raise NotInServerError
            
            # Community must exist
            return self.get_community_by_id(community_id)  # type: ignore  
        
    


Jumpedia()._init()