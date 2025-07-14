
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
from database import queries, layout
from dataclasses import dataclass, field
from discordtools import messaging as msg, users
from structures import list as list_

LOGGER = logging.getLogger(__name__)
DATABASE_NAME: str = 'jumpedia'


class NotInServerError(ValueError):
    pass

class AbstractStructureAndSingleton(type(BaseStructure), metautils.Singleton):
    pass

@dataclass(frozen=True, kw_only=True)
class Jumpedia(BaseStructure, metaclass=AbstractStructureAndSingleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default=DATABASE_NAME)
    
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
                    CREATE TABLE {layout.Community} (
                        {layout.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.Community.name} VARCHAR({community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
                        {layout.Community.default_selected_list_id} INT DEFAULT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.Server} (
                        {layout.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                        {layout.Server.community_id} INT NOT NULL,

                        FOREIGN KEY ({layout.Server.community_id}) 
                            REFERENCES {layout.Community}({layout.Community.id}) 
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.List} (
                        {layout.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.List.community_id} INT NOT NULL,
                        {layout.List.name} VARCHAR({list_.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY ({layout.List.community_id})
                            REFERENCES {layout.Community}({layout.Community.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.List.community_id}, {layout.List.name})
                    )
                """)

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE {layout.Community}
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY ({layout.Community.default_selected_list_id})
                        REFERENCES {layout.List}({layout.List.id})
                        ON DELETE SET NULL
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.JumpediaUser} (
                        {layout.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                        {layout.JumpediaUser.name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                        {layout.JumpediaUser.power} INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.CommunityUser} (
                        {layout.CommunityUser.community_id} INT NOT NULL,
                        {layout.CommunityUser.user_id} BIGINT UNSIGNED NOT NULL,
                        {layout.CommunityUser.power} INT NOT NULL,
                        {layout.CommunityUser.selected_list_id} INT,

                        PRIMARY KEY ({layout.CommunityUser.community_id}, {layout.CommunityUser.user_id}),

                        FOREIGN KEY ({layout.CommunityUser.community_id})
                            REFERENCES {layout.Community}({layout.Community.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.CommunityUser.user_id})
                            REFERENCES {layout.JumpediaUser}({layout.JumpediaUser.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.CommunityUser.selected_list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.StaticAttribute} (
                        {layout.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.StaticAttribute.list_id} INT NOT NULL,
                        {layout.StaticAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {layout.StaticAttribute.slot_type} INT NOT NULL,
                        {layout.StaticAttribute.position} INT NOT NULL,
                        {layout.StaticAttribute.min_slots} INT NOT NULL,
                        {layout.StaticAttribute.max_slots} INT NOT NULL,
                        {layout.StaticAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({layout.StaticAttribute.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.StaticAttribute.list_id}, {layout.StaticAttribute.name}),
                        UNIQUE ({layout.StaticAttribute.list_id}, {layout.StaticAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.StaticAttributeAlias} (
                        {layout.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.StaticAttributeAlias.attribute_id} INT NOT NULL,
                        {layout.StaticAttributeAlias.list_id} INT NOT NULL,
                        {layout.StaticAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({layout.StaticAttributeAlias.attribute_id})
                            REFERENCES {layout.StaticAttribute}({layout.StaticAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.StaticAttributeAlias.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.StaticAttributeAlias.list_id}, {layout.StaticAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAttribute} (
                        {layout.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.TaskAttribute.list_id} INT NOT NULL,
                        {layout.TaskAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {layout.TaskAttribute.slot_type} INT NOT NULL,
                        {layout.TaskAttribute.position} INT NOT NULL,
                        {layout.TaskAttribute.min_slots} INT NOT NULL,
                        {layout.TaskAttribute.max_slots} INT NOT NULL,
                        {layout.TaskAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({layout.TaskAttribute.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.TaskAttribute.list_id}, {layout.TaskAttribute.name}),
                        UNIQUE ({layout.TaskAttribute.list_id}, {layout.TaskAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAttributeAlias} (
                        {layout.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.TaskAttributeAlias.attribute_id} INT NOT NULL,
                        {layout.TaskAttributeAlias.list_id} INT NOT NULL,
                        {layout.TaskAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({layout.TaskAttributeAlias.attribute_id})
                            REFERENCES {layout.TaskAttribute}({layout.TaskAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.TaskAttributeAlias.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.TaskAttributeAlias.list_id}, {layout.TaskAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAttributeCollectionNode} (
                        {layout.TaskAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.TaskAttributeCollectionNode.parent_id} INT,
                        {layout.TaskAttributeCollectionNode.attribute_id} INT NOT NULL,
                        {layout.TaskAttributeCollectionNode.value} BLOB NOT NULL,
                        {layout.TaskAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({layout.TaskAttributeCollectionNode.parent_id})
                            REFERENCES {layout.TaskAttributeCollectionNode}({layout.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.TaskAttributeCollectionNode.attribute_id})
                            REFERENCES {layout.TaskAttribute}({layout.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAttributeCollectionNodeAlias} (
                        {layout.TaskAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.TaskAttributeCollectionNodeAlias.attribute_id} INT NOT NULL,
                        {layout.TaskAttributeCollectionNodeAlias.attribute_collection_node_id} INT NOT NULL,
                        {layout.TaskAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({layout.TaskAttributeCollectionNodeAlias.attribute_collection_node_id})
                            REFERENCES {layout.TaskAttributeCollectionNode}({layout.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.TaskAttributeCollectionNodeAlias.attribute_id})
                            REFERENCES {layout.TaskAttribute}({layout.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                
                cursor.execute(f"""
                    CREATE TABLE {layout.UserAttribute} (
                        {layout.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.UserAttribute.list_id} INT NOT NULL,
                        {layout.UserAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {layout.UserAttribute.position} INT NOT NULL,
                        {layout.UserAttribute.slot_type} INT NOT NULL,
                        {layout.UserAttribute.min_slots} INT NOT NULL,
                        {layout.UserAttribute.max_slots} INT NOT NULL,
                        {layout.UserAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({layout.UserAttribute.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.UserAttribute.list_id}, {layout.UserAttribute.name}),
                        UNIQUE ({layout.UserAttribute.list_id}, {layout.UserAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.UserAttributeAlias} (
                        {layout.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.UserAttributeAlias.attribute_id} INT NOT NULL,
                        {layout.UserAttributeAlias.list_id} INT NOT NULL,
                        {layout.UserAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({layout.UserAttributeAlias.attribute_id})
                            REFERENCES {layout.UserAttribute}({layout.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.UserAttributeAlias.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.UserAttributeAlias.list_id}, {layout.UserAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.UserAttributeCollectionNode} (
                        {layout.UserAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.UserAttributeCollectionNode.parent_id} INT,
                        {layout.UserAttributeCollectionNode.attribute_id} INT NOT NULL,
                        {layout.UserAttributeCollectionNode.value} BLOB NOT NULL,
                        {layout.UserAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({layout.UserAttributeCollectionNode.parent_id})
                            REFERENCES {layout.UserAttributeCollectionNode}({layout.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.UserAttributeCollectionNode.attribute_id})
                            REFERENCES {layout.UserAttribute}({layout.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.UserAttributeCollectionNodeAlias} (
                        {layout.UserAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.UserAttributeCollectionNodeAlias.attribute_id} INT NOT NULL,
                        {layout.UserAttributeCollectionNodeAlias.attribute_collection_node_id} INT NOT NULL,
                        {layout.UserAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({layout.UserAttributeCollectionNodeAlias.attribute_collection_node_id})
                            REFERENCES {layout.UserAttributeCollectionNode}({layout.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.UserAttributeCollectionNodeAlias.attribute_id})
                            REFERENCES {layout.UserAttribute}({layout.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.Task} (
                        {layout.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.Task.list_id} INT NOT NULL,
                        {layout.Task.name} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({layout.Task.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.Task.list_id}, {layout.Task.name})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAlias} (
                        {layout.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {layout.TaskAlias.task_id} INT NOT NULL,
                        {layout.TaskAlias.list_id} INT NOT NULL,
                        {layout.TaskAlias.alias} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({layout.TaskAlias.task_id})
                            REFERENCES {layout.Task}({layout.Task.id})
                            ON DELETE CASCADE,

                        FOREIGN KEY ({layout.TaskAlias.list_id})
                            REFERENCES {layout.List}({layout.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({layout.TaskAlias.list_id}, {layout.TaskAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.StaticAttributeTaskValue} (
                        {layout.StaticAttributeTaskValue.task_id} INT NOT NULL,
                        {layout.StaticAttributeTaskValue.attribute_id} INT NOT NULL,
                        {layout.StaticAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY ({layout.StaticAttributeTaskValue.task_id}, {layout.StaticAttributeTaskValue.attribute_id}),

                        FOREIGN KEY ({layout.StaticAttributeTaskValue.task_id})
                            REFERENCES {layout.Task}({layout.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.StaticAttributeTaskValue.attribute_id})
                            REFERENCES {layout.StaticAttribute}({layout.StaticAttribute.id})
                            ON DELETE CASCADE
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE {layout.TaskAttributeTaskValue} (
                        {layout.TaskAttributeTaskValue.task_id} INT NOT NULL,
                        {layout.TaskAttributeTaskValue.attribute_id} INT NOT NULL,
                        {layout.TaskAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {layout.TaskAttributeTaskValue.task_id}, 
                            {layout.TaskAttributeTaskValue.attribute_id}
                        ),

                        FOREIGN KEY ({layout.TaskAttributeTaskValue.task_id})
                            REFERENCES {layout.Task}({layout.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.TaskAttributeTaskValue.attribute_id})
                            REFERENCES {layout.TaskAttribute}({layout.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {layout.UserAttributeTaskValue} (
                        {layout.UserAttributeTaskValue.task_id} INT NOT NULL,
                        {layout.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                        {layout.UserAttributeTaskValue.attribute_id} INT NOT NULL,
                        {layout.UserAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {layout.UserAttributeTaskValue.task_id}, 
                            {layout.UserAttributeTaskValue.user_id}, 
                            {layout.UserAttributeTaskValue.attribute_id}
                        ),

                        FOREIGN KEY ({layout.UserAttributeTaskValue.task_id})
                            REFERENCES {layout.Task}({layout.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.UserAttributeTaskValue.attribute_id})
                            REFERENCES {layout.UserAttribute}({layout.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({layout.UserAttributeTaskValue.user_id})
                            REFERENCES {layout.JumpediaUser}({layout.JumpediaUser.id})
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
                    INSERT INTO {layout.Community} (
                        {layout.Community.name},
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {layout.Server} (
                        {layout.Server.id}, 
                        {layout.Server.community_id}
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
                DELETE FROM {layout.Community}
                WHERE {layout.Community.id} = {h|community.id}
            """, h.steal())

            return cursor.rowcount > 0
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> layout.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {layout.Community}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: layout.ManyTableRowT = cursor.fetchall()

        return result
    
    def _community_data_to_obj(self, data: layout.SingleTableRowT) -> 'Community':
        return Community(
            jumpedia=self,
            id=data[layout.Community.id],
            name=data[layout.Community.name],
            default_selected_list_id=data[layout.Community.default_selected_list_id]
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Community]:
        return [
            self._community_data_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{layout.Community.id} = {h|id}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{layout.Community.name} = {h|name}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> 'Community | None':
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {layout.Server.community_id}
                FROM {layout.Server}
                WHERE {layout.Server.id} = {h|server_id}
            """, h.steal())

            result: layout.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None

        return self.get_community_by_id(result[layout.Server.community_id])
    

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
                        INSERT INTO {layout.JumpediaUser} (
                            {layout.JumpediaUser.id},
                            {layout.JumpediaUser.power},
                            {layout.JumpediaUser.name}
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
                            UPDATE {layout.JumpediaUser} 
                            SET 
                                {layout.JumpediaUser.name} = {h|name}
                                {layout.JumpediaUser.power} = {h|jumpedia_rank.power}
                            WHERE 
                                {layout.JumpediaUser.id} = {h|user.id}
                        """, h.steal())
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    jumpedia_rank=jumpedia_rank,
                    name=name
                )

    def _fetch_from_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> layout.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {layout.JumpediaUser}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: layout.ManyTableRowT = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: layout.SingleTableRowT) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            name=data[layout.JumpediaUser.name],
            id=data[layout.JumpediaUser.id],
            jumpedia_rank=JumpediaRank.get(data[layout.JumpediaUser.power])
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[JumpediaUser]:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda h: f"{layout.JumpediaUser.id} = {h|id}")
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
                    INSERT INTO {layout.Server} (
                        {layout.Server.id},
                        {layout.Server.community_id}
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
                    DELETE FROM {layout.Server}
                    WHERE 
                        {layout.Server.id} = {h|server_id}
                """, h.steal())

                if cursor.rowcount < 1:
                    raise NotInServerError
            
            # Community must exist
            return self.get_community_by_id(community_id)  # type: ignore  
        
    


Jumpedia()._init()