
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
from structures.user import User
from utils import metautils, text
from database import queries, typed as typed
from database.typed import Tables as TBL
from dataclasses import dataclass, field
from discordtools import messaging as msg, users
from structures import list as list_

LOGGER = logging.getLogger(__name__)

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
                    CREATE TABLE {TBL.Community} (
                        {TBL.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.Community.name} VARCHAR({community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
                        {TBL.Community.default_selected_list_id} INT DEFAULT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.Server} (
                        {TBL.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                        {TBL.Server.community_id} INT NOT NULL,

                        FOREIGN KEY ({TBL.Server.community_id}) 
                            REFERENCES {TBL.Community}({TBL.Community.id}) 
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.List} (
                        {TBL.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.List.community_id} INT NOT NULL,
                        {TBL.List.name} VARCHAR({list_.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY ({TBL.List.community_id})
                            REFERENCES {TBL.Community}({TBL.Community.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.List.community_id}, {TBL.List.name})
                    )
                """)

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE {TBL.Community}
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY ({TBL.Community.default_selected_list_id})
                        REFERENCES {TBL.List}({TBL.List.id})
                        ON DELETE SET NULL
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.JumpediaUser} (
                        {TBL.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                        {TBL.JumpediaUser.name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                        {TBL.JumpediaUser.power} INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.CommunityUser} (
                        {TBL.CommunityUser.community_id} INT NOT NULL,
                        {TBL.CommunityUser.user_id} BIGINT UNSIGNED NOT NULL,
                        {TBL.CommunityUser.power} INT NOT NULL,
                        {TBL.CommunityUser.selected_list_id} INT,

                        PRIMARY KEY ({TBL.CommunityUser.community_id}, {TBL.CommunityUser.user_id}),

                        FOREIGN KEY ({TBL.CommunityUser.community_id})
                            REFERENCES {TBL.Community}({TBL.Community.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.CommunityUser.user_id})
                            REFERENCES {TBL.JumpediaUser}({TBL.JumpediaUser.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.CommunityUser.selected_list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.StaticAttribute} (
                        {TBL.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.StaticAttribute.list_id} INT NOT NULL,
                        {TBL.StaticAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {TBL.StaticAttribute.value_type} INT NOT NULL,
                        {TBL.StaticAttribute.index} INT NOT NULL,
                        {TBL.StaticAttribute.min_slots} INT NOT NULL,
                        {TBL.StaticAttribute.max_slots} INT NOT NULL,
                        {TBL.StaticAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({TBL.StaticAttribute.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.StaticAttribute.list_id}, {TBL.StaticAttribute.name}),
                        UNIQUE ({TBL.StaticAttribute.list_id}, {TBL.StaticAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.StaticAttributeAlias} (
                        {TBL.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.StaticAttributeAlias.static_attribute_id} INT NOT NULL,
                        {TBL.StaticAttributeAlias.list_id} INT NOT NULL,
                        {TBL.StaticAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({TBL.StaticAttributeAlias.static_attribute_id})
                            REFERENCES {TBL.StaticAttribute}({TBL.StaticAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.StaticAttributeAlias.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.StaticAttributeAlias.list_id}, {TBL.StaticAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAttribute} (
                        {TBL.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.TaskAttribute.list_id} INT NOT NULL,
                        {TBL.TaskAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {TBL.TaskAttribute.value_type} INT NOT NULL,
                        {TBL.TaskAttribute.index} INT NOT NULL,
                        {TBL.TaskAttribute.min_slots} INT NOT NULL,
                        {TBL.TaskAttribute.max_slots} INT NOT NULL,
                        {TBL.TaskAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({TBL.TaskAttribute.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.TaskAttribute.list_id}, {TBL.TaskAttribute.name}),
                        UNIQUE ({TBL.TaskAttribute.list_id}, {TBL.TaskAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAttributeAlias} (
                        {TBL.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.TaskAttributeAlias.task_attribute_id} INT NOT NULL,
                        {TBL.TaskAttributeAlias.list_id} INT NOT NULL,
                        {TBL.TaskAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({TBL.TaskAttributeAlias.task_attribute_id})
                            REFERENCES {TBL.TaskAttribute}({TBL.TaskAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.TaskAttributeAlias.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.TaskAttributeAlias.list_id}, {TBL.TaskAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAttributeCollectionNode} (
                        {TBL.TaskAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.TaskAttributeCollectionNode.root_id} INT,
                        {TBL.TaskAttributeCollectionNode.task_attribute_id} INT NOT NULL,
                        {TBL.TaskAttributeCollectionNode.value} BLOB NOT NULL,
                        {TBL.TaskAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({TBL.TaskAttributeCollectionNode.root_id})
                            REFERENCES {TBL.TaskAttributeCollectionNode}({TBL.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.TaskAttributeCollectionNode.task_attribute_id})
                            REFERENCES {TBL.TaskAttribute}({TBL.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAttributeCollectionNodeAlias} (
                        {TBL.TaskAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id} INT NOT NULL,
                        {TBL.TaskAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({TBL.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id})
                            REFERENCES {TBL.TaskAttributeCollectionNode}({TBL.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE
                    )
                """)

                
                cursor.execute(f"""
                    CREATE TABLE {TBL.UserAttribute} (
                        {TBL.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.UserAttribute.list_id} INT NOT NULL,
                        {TBL.UserAttribute.name} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,
                        {TBL.UserAttribute.index} INT NOT NULL,
                        {TBL.UserAttribute.value_type} INT NOT NULL,
                        {TBL.UserAttribute.min_slots} INT NOT NULL,
                        {TBL.UserAttribute.max_slots} INT NOT NULL,
                        {TBL.UserAttribute.uniqueness} TINYINT UNSIGNED NOT NULL,

                        FOREIGN KEY ({TBL.UserAttribute.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.UserAttribute.list_id}, {TBL.UserAttribute.name}),
                        UNIQUE ({TBL.UserAttribute.list_id}, {TBL.UserAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.UserAttributeAlias} (
                        {TBL.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.UserAttributeAlias.user_attribute_id} INT NOT NULL,
                        {TBL.UserAttributeAlias.list_id} INT NOT NULL,
                        {TBL.UserAttributeAlias.alias} VARCHAR({attributes.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({TBL.UserAttributeAlias.user_attribute_id})
                            REFERENCES {TBL.UserAttribute}({TBL.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.UserAttributeAlias.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.UserAttributeAlias.list_id}, {TBL.UserAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.UserAttributeCollectionNode} (
                        {TBL.UserAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.UserAttributeCollectionNode.root_id} INT,
                        {TBL.UserAttributeCollectionNode.user_attribute_id} INT NOT NULL,
                        {TBL.UserAttributeCollectionNode.value} BLOB NOT NULL,
                        {TBL.UserAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({TBL.UserAttributeCollectionNode.root_id})
                            REFERENCES {TBL.UserAttributeCollectionNode}({TBL.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.UserAttributeCollectionNode.user_attribute_id})
                            REFERENCES {TBL.UserAttribute}({TBL.UserAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.UserAttributeCollectionNodeAlias} (
                        {TBL.UserAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id} INT NOT NULL,
                        {TBL.UserAttributeCollectionNodeAlias.alias} BLOB NOT NULL,

                        FOREIGN KEY ({TBL.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id})
                            REFERENCES {TBL.UserAttributeCollectionNode}({TBL.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.Task} (
                        {TBL.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.Task.list_id} INT NOT NULL,
                        {TBL.Task.name} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({TBL.Task.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.Task.list_id}, {TBL.Task.name})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAlias} (
                        {TBL.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.TaskAlias.task_id} INT NOT NULL,
                        {TBL.TaskAlias.list_id} INT NOT NULL,
                        {TBL.TaskAlias.alias} VARCHAR({task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({TBL.TaskAlias.task_id})
                            REFERENCES {TBL.Task}({TBL.Task.id})
                            ON DELETE CASCADE,

                        FOREIGN KEY ({TBL.TaskAlias.list_id})
                            REFERENCES {TBL.List}({TBL.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({TBL.TaskAlias.list_id}, {TBL.TaskAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.StaticAttributeTaskValue} (
                        {TBL.StaticAttributeTaskValue.task_id} INT NOT NULL,
                        {TBL.StaticAttributeTaskValue.static_attribute_id} INT NOT NULL,
                        {TBL.StaticAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY ({TBL.StaticAttributeTaskValue.task_id}, {TBL.StaticAttributeTaskValue.static_attribute_id}),

                        FOREIGN KEY ({TBL.StaticAttributeTaskValue.task_id})
                            REFERENCES {TBL.Task}({TBL.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.StaticAttributeTaskValue.static_attribute_id})
                            REFERENCES {TBL.StaticAttribute}({TBL.StaticAttribute.id})
                            ON DELETE CASCADE
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE {TBL.TaskAttributeTaskValue} (
                        {TBL.TaskAttributeTaskValue.task_id} INT NOT NULL,
                        {TBL.TaskAttributeTaskValue.task_attribute_id} INT NOT NULL,
                        {TBL.TaskAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {TBL.TaskAttributeTaskValue.task_id}, 
                            {TBL.TaskAttributeTaskValue.task_attribute_id}
                        ),

                        FOREIGN KEY ({TBL.TaskAttributeTaskValue.task_id})
                            REFERENCES {TBL.Task}({TBL.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.TaskAttributeTaskValue.task_attribute_id})
                            REFERENCES {TBL.TaskAttribute}({TBL.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {TBL.UserAttributeTaskValue} (
                        {TBL.UserAttributeTaskValue.task_id} INT NOT NULL,
                        {TBL.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                        {TBL.UserAttributeTaskValue.user_attribute_id} INT NOT NULL,
                        {TBL.UserAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {TBL.UserAttributeTaskValue.task_id}, 
                            {TBL.UserAttributeTaskValue.user_id}, 
                            {TBL.UserAttributeTaskValue.user_attribute_id}
                        ),

                        FOREIGN KEY ({TBL.UserAttributeTaskValue.task_id})
                            REFERENCES {TBL.Task}({TBL.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.UserAttributeTaskValue.user_attribute_id})
                            REFERENCES {TBL.UserAttribute}({TBL.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({TBL.UserAttributeTaskValue.user_id})
                            REFERENCES {TBL.JumpediaUser}({TBL.JumpediaUser.id})
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

    def create_community(self, user: User, server_id: int, bad_name: str) -> 'Community':
        with self.locked:
            community_ = self.get_community_by_server_id(server_id)

            if community_ is not None:
                raise feedbacks.server_already_connected_to_community(community_)
            
            communities = self.get_communities()

            name = text.validate_and_sanitize_name(
                bad_name,
                community.MAX_NAME_LENGTH,
                (c.name for c in communities)
            )
            
            if text.norm(name).endswith(text.norm(Community.structure_name())):
                raise feedbacks.name_ends_in_structure_name(name, Community)

            h = queries.ArgHelper()
            
            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TBL.Community} (
                        {TBL.Community.name}
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {TBL.Server} (
                        {TBL.Server.id}, 
                        {TBL.Server.community_id}
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

                community_.add_or_create_community_user(user.id, user.name, CommunityRank.OWNER)

                list = community_.create_list('Main')

                cursor.execute(f"""
                    UPDATE {TBL.Community}
                    SET {TBL.Community.default_selected_list_id} = {h|list.id}
                    WHERE {TBL.Community.id} = {h|community_.id}
                """, h.steal())

                community_ = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=list.id,
                    name=name
                )

                # Rollback if anything goes wrong up to this point
                return community_
    
    def delete_community(self, bad_name: str) -> None:
        name = text.sanitize(bad_name)

        with self.locked:
            community = self.get_community_by_name(name)

            # Already deleted
            if community is None:
                return
            
            h = queries.ArgHelper()

            with community.locked, queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {TBL.Community}
                    WHERE {TBL.Community.id} = {h|community.id}
                """, h.steal())
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.Community}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _community_data_to_obj(self, data: typed.SingleTableRowT) -> 'Community':
        return Community(
            jumpedia=self,
            id=data[TBL.Community.id],
            name=data[TBL.Community.name],
            default_selected_list_id=data[TBL.Community.default_selected_list_id]
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Community]:
        return [
            self._community_data_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{TBL.Community.id} = {h|id}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{TBL.Community.name} = {h|name}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> 'Community | None':
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.Server.community_id}
                FROM {TBL.Server}
                WHERE {TBL.Server.id} = {h|server_id}
            """, h.steal())

            result: typed.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None

        return self.get_community_by_id(result[TBL.Server.community_id])
    

    # --- Jumpedia Users ---

    def get_or_create_user(
        self, 
        id: int, 
        name: str, 
        jumpedia_rank: JumpediaRank, 
        override_name_if_user_exists: bool,
        override_jumpedia_rank_if_user_exists: bool
    ) -> User:
        h = queries.ArgHelper()

        with self.locked:
            user = self.get_user_by_id(id)

            with queries.connected() as (conn, cursor):
                if user is None:
                    cursor.execute(f"""
                        INSERT INTO {TBL.JumpediaUser} (
                            {TBL.JumpediaUser.id},
                            {TBL.JumpediaUser.power},
                            {TBL.JumpediaUser.name}
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
                            UPDATE {TBL.JumpediaUser} 
                            SET 
                                {TBL.JumpediaUser.name} = {h|name}
                                {TBL.JumpediaUser.power} = {h|jumpedia_rank.power}
                            WHERE 
                                {TBL.JumpediaUser.id} = {h|user.id}
                        """, h.steal())
                        
                return User(
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
                FROM {TBL.JumpediaUser}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: typed.SingleTableRowT) -> User:
        return User(
            jumpedia=self,
            name=data[TBL.JumpediaUser.name],
            id=data[TBL.JumpediaUser.id],
            jumpedia_rank=JumpediaRank.get(data[TBL.JumpediaUser.power])
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[User]:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> User | None:
        data = self._fetch_from_user_table(lambda h: f"{TBL.JumpediaUser.id} = {h|id}")
        return self._user_data_to_obj(data[0]) if data else None

Jumpedia()._init()