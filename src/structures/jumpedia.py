
import time
from typing import TYPE_CHECKING, Any, Callable, Final, TypedDict
import logging

from discordtools import feedbackerrors as fbe, utils
from structures import attributes
from structures.list import List
from structures.ranks import MetaRank, CommunityRank
from structures.tasks.task import Task
from structures.users import MetaUser
from utils import metautils, text
from database import queries, typed as typed
from database.typed import Tables as TBL
from dataclasses import dataclass, field
import discord as dc

# -> Jumpedia has many:
#  -> Community has many:
#   -> User
#   -> List has many:
#    -> Task
#    -> Attribute

from structures.community import Community
from utils.locked import equality_locked

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Jumpedia(metaclass=metautils.Singleton):
    id: int = field(init=False, default=1)
    database_name: str = field(init=False, default=typed.DATABASE_NAME)
    
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
                    CREATE TABLE {TBL.Community} (
                        {TBL.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {TBL.Community.name} VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
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
                        {TBL.List.name} VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL,

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
                    CREATE TABLE {TBL.User} (
                        {TBL.User.id} BIGINT UNSIGNED PRIMARY KEY,
                        {TBL.User.name} VARCHAR({MetaUser.MAX_NAME_LENGTH}) NOT NULL,
                        {TBL.User.meta_power} INT NOT NULL
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
                            REFERENCES {TBL.User}({TBL.User.id})
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
                        {TBL.StaticAttribute.unique_slots} BOOL NOT NULL,
                        {TBL.StaticAttribute.unique_value_per_list} BOOL NOT NULL,

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
                        {TBL.TaskAttribute.unique_slots} BOOL NOT NULL,
                        {TBL.TaskAttribute.unique_value_per_list} BOOL NOT NULL,

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
                        {TBL.UserAttribute.unique_slots} BOOL NOT NULL,

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
                        {TBL.Task.name} VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,

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
                        {TBL.TaskAlias.alias} VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,

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
                            REFERENCES {TBL.User}({TBL.User.id})
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

    def create_community(self, dc_user: dc.User | dc.Member, server_id: int, bad_name: str) -> 'Community':
        with equality_locked(self):
            community = self.get_community_by_server_id(server_id)

            if community is not None:
                raise fbe.TemporaryFeedbackError(
                    f"This server is already hosting the community `{community.name}`."
                )
            
            communities = self.get_communities()

            name = text.validate_and_sanitize_name(
                bad_name,
                Community.MAX_NAME_LENGTH,
                (c.name for c in communities)
            )
            
            if text.norm_syn(name).endswith(Community.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{Community.INVALID_ENDING}' from the name as it is redundant!")

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
                
                community = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=None,
                    name=name
                )  

                community.create_or_get_community_user(dc_user.id, utils.get_user_name(dc_user), CommunityRank.OWNER)

                list = community.create_list('Main')

                cursor.execute(f"""
                    UPDATE {TBL.Community}
                    SET {TBL.Community.default_selected_list_id} = {h|list.id}
                    WHERE {TBL.Community.id} = {h|community.id}
                """, h.steal())

                community = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=list.id,
                    name=name
                )

                # Rollback if anything goes wrong up to this point
                return community
    
    def delete_community(self, bad_name: str) -> None:
        name = text.sanitize(bad_name)

        with equality_locked(self):
            community = self.get_community_by_name(name)

            # Already deleted
            if community is None:
                return
            
            h = queries.ArgHelper()

            with equality_locked(community), queries.connected() as (conn, cursor):
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
        name = text.norm(name)
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
    

    # --- Meta Users ---

    def create_or_get_user(self, user_id: int, user_name: str | None) -> MetaUser:
        with equality_locked(self):
            user = self.get_user_by_id(user_id)
            
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                if user is None:
                    if user_name is None:
                        raise fbe.TemporaryFeedbackError("A user must have used Jumpedia at least once before to be registered.")

                    meta_rank = MetaRank.DEFAULT

                    cursor.execute(f"""
                        INSERT INTO {TBL.User} (
                            {TBL.User.id},
                            {TBL.User.meta_power},
                            {TBL.User.name}
                        )
                        VALUES (
                            {h|user_id},
                            {h|meta_rank.power},
                            {h|user_name}
                        )
                    """, h.steal())

                else:
                    meta_rank = user.meta_rank
                    
                    if user_name is None:
                        user_name = user.name

                    elif user.name != user_name:
                        cursor.execute(f"""
                            UPDATE {TBL.User} 
                            SET {TBL.User.name} = {h|user_name}
                            WHERE {TBL.User.id} = {h|user.id}
                        """, h.steal())
                        
                return MetaUser(
                    id=user_id,
                    meta_rank=meta_rank,
                    name=user_name
                )
            
    def change_user_meta_rank(self, user_id: int, user_name: str, meta_rank: MetaRank) -> None:
        with equality_locked(self):
            self.create_or_get_user(user_id, user_name)

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    UPDATE {TBL.User} 
                    SET {TBL.User.meta_power} = {h|meta_rank.power}
                    WHERE {TBL.User.id} = {h|user_id}
                """, h.steal())

    def _fetch_from_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.User}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: typed.SingleTableRowT) -> MetaUser:
        return MetaUser(
            id=data[TBL.User.id],
            meta_rank=MetaRank.get(data[TBL.User.meta_power]),
            name=data[TBL.User.name]
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[MetaUser]:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> MetaUser | None:
        data = self._fetch_from_user_table(lambda h: f"{TBL.User.id} = {h|id}")
        return self._user_data_to_obj(data[0]) if data else None

Jumpedia()._init()