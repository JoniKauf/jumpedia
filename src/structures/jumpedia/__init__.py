
import time
from typing import TYPE_CHECKING, Any, Callable, Final, Self, TypedDict
import logging
import discord as dc

from database.simple_orm import Rows
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
from database import queries, typed
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
                    CREATE TABLE {typed.Community} (
                        {typed.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.Community.__table_name__} VARCHAR({community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
                        {typed.Community.default_selected_list_id} INT DEFAULT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.Server} (
                        {typed.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                        {typed.Server.community_id} INT NOT NULL,

                        FOREIGN KEY ({typed.Server.community_id}) 
                            REFERENCES {typed.Community}({typed.Community.id}) 
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.List} (
                        {typed.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.List.community_id} INT NOT NULL,
                        {typed.List.__table_name__} VARCHAR({list_.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY ({typed.List.community_id})
                            REFERENCES {typed.Community}({typed.Community.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.List.community_id}, {typed.List.__table_name__})
                    )
                """)

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE {typed.Community}
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY ({typed.Community.default_selected_list_id})
                        REFERENCES {typed.List}({typed.List.id})
                        ON DELETE SET NULL
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.JumpediaUser} (
                        {typed.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                        {typed.JumpediaUser.__table_name__} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                        {typed.JumpediaUser.power} INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.CommunityUser} (
                        {typed.CommunityUser.community_id} INT NOT NULL,
                        {typed.CommunityUser.user_id} BIGINT UNSIGNED NOT NULL,
                        {typed.CommunityUser.power} INT NOT NULL,
                        {typed.CommunityUser.selected_list_id} INT,

                        PRIMARY KEY ({typed.CommunityUser.community_id}, {typed.CommunityUser.user_id}),

                        FOREIGN KEY ({typed.CommunityUser.community_id})
                            REFERENCES {typed.Community}({typed.Community.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.CommunityUser.user_id})
                            REFERENCES {typed.JumpediaUser}({typed.JumpediaUser.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.CommunityUser.selected_list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.StaticAttribute} (
                        {typed.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.StaticAttribute.list_id} INT NOT NULL,
                        {typed.StaticAttribute.__table_name__} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {typed.StaticAttribute.slot_type} INT NOT NULL,
                        {typed.StaticAttribute.position} INT NOT NULL,
                        {typed.StaticAttribute.min_slots} INT NOT NULL,
                        {typed.StaticAttribute.max_slots} INT NOT NULL,
                        {typed.StaticAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({typed.StaticAttribute.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.StaticAttribute.list_id}, {typed.StaticAttribute.__table_name__}),
                        UNIQUE ({typed.StaticAttribute.list_id}, {typed.StaticAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.StaticAttributeAlias} (
                        {typed.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.StaticAttributeAlias.attribute_id} INT NOT NULL,
                        {typed.StaticAttributeAlias.list_id} INT NOT NULL,
                        {typed.StaticAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({typed.StaticAttributeAlias.attribute_id})
                            REFERENCES {typed.StaticAttribute}({typed.StaticAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.StaticAttributeAlias.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.StaticAttributeAlias.list_id}, {typed.StaticAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAttribute} (
                        {typed.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.TaskAttribute.list_id} INT NOT NULL,
                        {typed.TaskAttribute.__table_name__} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {typed.TaskAttribute.slot_type} INT NOT NULL,
                        {typed.TaskAttribute.position} INT NOT NULL,
                        {typed.TaskAttribute.min_slots} INT NOT NULL,
                        {typed.TaskAttribute.max_slots} INT NOT NULL,
                        {typed.TaskAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({typed.TaskAttribute.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.TaskAttribute.list_id}, {typed.TaskAttribute.__table_name__}),
                        UNIQUE ({typed.TaskAttribute.list_id}, {typed.TaskAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAttributeAlias} (
                        {typed.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.TaskAttributeAlias.attribute_id} INT NOT NULL,
                        {typed.TaskAttributeAlias.list_id} INT NOT NULL,
                        {typed.TaskAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({typed.TaskAttributeAlias.attribute_id})
                            REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.TaskAttributeAlias.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.TaskAttributeAlias.list_id}, {typed.TaskAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAttributeCollectionNode} (
                        {typed.TaskAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.TaskAttributeCollectionNode.parent_id} INT,
                        {typed.TaskAttributeCollectionNode.attribute_id} INT NOT NULL,
                        {typed.TaskAttributeCollectionNode.value} BLOB NOT NULL,
                        {typed.TaskAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({typed.TaskAttributeCollectionNode.parent_id})
                            REFERENCES {typed.TaskAttributeCollectionNode}({typed.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.TaskAttributeCollectionNode.attribute_id})
                            REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAttributeCollectionNodeAlias} (
                        {typed.TaskAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.TaskAttributeCollectionNodeAlias.attribute_id} INT NOT NULL,
                        {typed.TaskAttributeCollectionNodeAlias.attribute_collection_node_id} INT NOT NULL,
                        {typed.TaskAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({typed.TaskAttributeCollectionNodeAlias.attribute_collection_node_id})
                            REFERENCES {typed.TaskAttributeCollectionNode}({typed.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.TaskAttributeCollectionNodeAlias.attribute_id})
                            REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                
                cursor.execute(f"""
                    CREATE TABLE {typed.UserAttribute} (
                        {typed.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.UserAttribute.list_id} INT NOT NULL,
                        {typed.UserAttribute.__table_name__} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {typed.UserAttribute.position} INT NOT NULL,
                        {typed.UserAttribute.slot_type} INT NOT NULL,
                        {typed.UserAttribute.min_slots} INT NOT NULL,
                        {typed.UserAttribute.max_slots} INT NOT NULL,
                        {typed.UserAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({typed.UserAttribute.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.UserAttribute.list_id}, {typed.UserAttribute.__table_name__}),
                        UNIQUE ({typed.UserAttribute.list_id}, {typed.UserAttribute.position})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.UserAttributeAlias} (
                        {typed.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.UserAttributeAlias.attribute_id} INT NOT NULL,
                        {typed.UserAttributeAlias.list_id} INT NOT NULL,
                        {typed.UserAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({typed.UserAttributeAlias.attribute_id})
                            REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.UserAttributeAlias.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.UserAttributeAlias.list_id}, {typed.UserAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.UserAttributeCollectionNode} (
                        {typed.UserAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.UserAttributeCollectionNode.parent_id} INT,
                        {typed.UserAttributeCollectionNode.attribute_id} INT NOT NULL,
                        {typed.UserAttributeCollectionNode.value} BLOB NOT NULL,
                        {typed.UserAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({typed.UserAttributeCollectionNode.parent_id})
                            REFERENCES {typed.UserAttributeCollectionNode}({typed.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.UserAttributeCollectionNode.attribute_id})
                            REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.UserAttributeCollectionNodeAlias} (
                        {typed.UserAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.UserAttributeCollectionNodeAlias.attribute_id} INT NOT NULL,
                        {typed.UserAttributeCollectionNodeAlias.attribute_collection_node_id} INT NOT NULL,
                        {typed.UserAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({typed.UserAttributeCollectionNodeAlias.attribute_collection_node_id})
                            REFERENCES {typed.UserAttributeCollectionNode}({typed.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.UserAttributeCollectionNodeAlias.attribute_id})
                            REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.Task} (
                        {typed.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.Task.list_id} INT NOT NULL,
                        {typed.Task.__table_name__} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({typed.Task.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.Task.list_id}, {typed.Task.__table_name__})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAlias} (
                        {typed.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {typed.TaskAlias.task_id} INT NOT NULL,
                        {typed.TaskAlias.list_id} INT NOT NULL,
                        {typed.TaskAlias.alias} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({typed.TaskAlias.task_id})
                            REFERENCES {typed.Task}({typed.Task.id})
                            ON DELETE CASCADE,

                        FOREIGN KEY ({typed.TaskAlias.list_id})
                            REFERENCES {typed.List}({typed.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({typed.TaskAlias.list_id}, {typed.TaskAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.StaticAttributeTaskValue} (
                        {typed.StaticAttributeTaskValue.task_id} INT NOT NULL,
                        {typed.StaticAttributeTaskValue.attribute_id} INT NOT NULL,
                        {typed.StaticAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY ({typed.StaticAttributeTaskValue.task_id}, {typed.StaticAttributeTaskValue.attribute_id}),

                        FOREIGN KEY ({typed.StaticAttributeTaskValue.task_id})
                            REFERENCES {typed.Task}({typed.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.StaticAttributeTaskValue.attribute_id})
                            REFERENCES {typed.StaticAttribute}({typed.StaticAttribute.id})
                            ON DELETE CASCADE
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE {typed.TaskAttributeTaskValue} (
                        {typed.TaskAttributeTaskValue.task_id} INT NOT NULL,
                        {typed.TaskAttributeTaskValue.attribute_id} INT NOT NULL,
                        {typed.TaskAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {typed.TaskAttributeTaskValue.task_id}, 
                            {typed.TaskAttributeTaskValue.attribute_id}
                        ),

                        FOREIGN KEY ({typed.TaskAttributeTaskValue.task_id})
                            REFERENCES {typed.Task}({typed.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.TaskAttributeTaskValue.attribute_id})
                            REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {typed.UserAttributeTaskValue} (
                        {typed.UserAttributeTaskValue.task_id} INT NOT NULL,
                        {typed.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                        {typed.UserAttributeTaskValue.attribute_id} INT NOT NULL,
                        {typed.UserAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {typed.UserAttributeTaskValue.task_id}, 
                            {typed.UserAttributeTaskValue.user_id}, 
                            {typed.UserAttributeTaskValue.attribute_id}
                        ),

                        FOREIGN KEY ({typed.UserAttributeTaskValue.task_id})
                            REFERENCES {typed.Task}({typed.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.UserAttributeTaskValue.attribute_id})
                            REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({typed.UserAttributeTaskValue.user_id})
                            REFERENCES {typed.JumpediaUser}({typed.JumpediaUser.id})
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
                    INSERT INTO {typed.Community} (
                        {typed.Community.__table_name__},
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id}, 
                        {typed.Server.community_id}
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
                DELETE FROM {typed.Community}
                WHERE {typed.Community.id} = {h|community.id}
            """, h.steal())

            return cursor.rowcount > 0
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> Rows[typed.Community]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {typed.Community}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result = Rows(cursor.fetchall(), typed.Community)

        return result
    
    def _community_row_to_obj(self, row: typed.Community) -> Community:
        return Community(
            jumpedia=self,
            id=row.id,
            name=row.__table_name__,
            default_selected_list_id=row.default_selected_list_id
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Community]:
        return [
            self._community_row_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> Community | None:
        data = self._fetch_from_community_table(lambda h: f"{typed.Community.id} = {h|id}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> Community | None:
        data = self._fetch_from_community_table(lambda h: f"{typed.Community.__table_name__} = {h|name}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> Community | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {+typed._Blocks.Server_CommunityId}
                FROM {typed.Server}
                WHERE {typed.Server.id} = {h|server_id}
            """, h.steal())

            result: typed._Blocks.Server_CommunityId | None = cursor.fetchone()

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
        h = queries.ArgHelper()

        with self.locked:
            user = self.get_user_by_id(id)

            with queries.connected() as (conn, cursor):
                if user is None:
                    cursor.execute(f"""
                        INSERT INTO {typed.JumpediaUser} (
                            {typed.JumpediaUser.id},
                            {typed.JumpediaUser.power},
                            {typed.JumpediaUser.__table_name__}
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
                            UPDATE {typed.JumpediaUser} 
                            SET 
                                {typed.JumpediaUser.__table_name__} = {h|name}
                                {typed.JumpediaUser.power} = {h|jumpedia_rank.power}
                            WHERE 
                                {typed.JumpediaUser.id} = {h|user.id}
                        """, h.steal())
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    jumpedia_rank=jumpedia_rank,
                    name=name
                )

    def _fetch_from_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> Rows[typed.JumpediaUser]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {+typed.JumpediaUser}
                FROM {typed.JumpediaUser}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result = Rows(cursor.fetchall(), typed.JumpediaUser)

        return result
    
    def _user_row_to_obj(self, row: typed.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            name=row.__table_name__,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power)
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[JumpediaUser]:
        return [
            self._user_row_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda h: f"{typed.JumpediaUser.id} = {h|id}")
        return self._user_row_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> Community:
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

            with queries.connected() as (_, cursor):
                cursor.execute(f"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id},
                        {typed.Server.community_id}
                    )
                    VALUES (
                        {h|server_id},
                        {h|community_id}
                    )
                """, h.steal())

            # Community must now be connected
            community = self.get_community_by_server_id(server_id)
            assert community is not None
            return community

    def remove_community_from_server(self, server_id: int) -> Community:
        h = queries.ArgHelper()

        with self.locked, queries.connected() as (_, cursor):
            cursor.execute(f"""
                SELECT {+typed._Blocks.Server_CommunityId}
                FROM {typed.Server}
                WHERE
                    {typed.Server.id} = {h|server_id}
            """, h.steal())

            result = cursor.fetchone()
            community_id = ()
            cursor.execute(f"""
                DELETE FROM {typed.Server}
                WHERE 
                    {typed.Server.id} = {h|server_id}
            """, h.steal())

            if cursor.rowcount < 1:
                raise NotInServerError

            community_id: int = cursor.lastrowid
        # Community must exist
        return self.get_community_by_id()  # type: ignore  
        
    


Jumpedia()._init()