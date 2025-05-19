
import time
from typing import TYPE_CHECKING, Any, Callable, Final, TypedDict
import logging

from discordtools import feedbackerrors as fbe
from structures.attribute import TaskAttribute, UserAttribute
from structures.list import List
from structures.ranks import MetaRank, UserRank
from structures.task import Task
from structures.user import User
from utils import metautils, text
from database import queries, strong as S
from database.strong import Tables as T
from dataclasses import dataclass, field

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
    database_name: str = field(init=False, default=S.DATABASE_NAME)
    
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
                    CREATE TABLE {T.Community} (
                        {T.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.Community.name} VARCHAR({Community.MAX_NAME_LENGTH}) UNIQUE NOT NULL,
                        {T.Community.default_selected_list_id} INT DEFAULT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.Guild} (
                        {T.Guild.id} BIGINT UNSIGNED PRIMARY KEY,
                        {T.Guild.community_id} INT NOT NULL,

                        FOREIGN KEY ({T.Guild.community_id}) 
                            REFERENCES {T.Community}({T.Community.id}) 
                            ON DELETE CASCADE
                    )
                """)

                # Add foreign key to community, otherwise we would have circular dependency
                cursor.execute(f"""
                    ALTER TABLE {T.Community}
                    ADD CONSTRAINT fk_community_default_list
                    FOREIGN KEY ({T.Community.default_selected_list_id})
                    REFERENCES {T.List}({T.List.id})
                    ON DELETE SET NULL;
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.MetaRank} (
                        {T.MetaRank.user_id} BIGINT UNSIGNED PRIMARY KEY,
                        {T.MetaRank.power} INT NOT NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.List} (
                        {T.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.List.community_id} INT NOT NULL,
                        {T.List.name} VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL,

                        FOREIGN KEY ({T.List.community_id})
                            REFERENCES {T.Community}({T.Community.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.List.community_id}, {T.List.name})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.User} (
                        {T.User.id} BIGINT UNSIGNED PRIMARY KEY,
                        {T.User.community_id} INT NOT NULL,
                        {T.User.power} INT NOT NULL,
                        {T.User.selected_list_id} INT,

                        FOREIGN KEY ({T.User.community_id})
                            REFERENCES {T.Community}({T.Community.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.User.selected_list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE SET NULL
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.StaticAttribute} (
                        {T.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.StaticAttribute.list_id} INT NOT NULL,
                        {T.StaticAttribute.name} VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,
                        {T.StaticAttribute.value_type} INT NOT NULL,
                        {T.StaticAttribute.index} INT NOT NULL,
                        {T.StaticAttribute.min_slots} INT NOT NULL,
                        {T.StaticAttribute.max_slots} INT NOT NULL,
                        {T.StaticAttribute.unique_slots} BOOL NOT NULL,
                        {T.StaticAttribute.unique_value_per_list} BOOL NOT NULL,

                        FOREIGN KEY ({T.StaticAttribute.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.StaticAttribute.list_id}, {T.StaticAttribute.name}),
                        UNIQUE ({T.StaticAttribute.list_id}, {T.StaticAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.StaticAttributeAlias} (
                        {T.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.StaticAttributeAlias.static_attribute_id} INT NOT NULL,
                        {T.StaticAttributeAlias.list_id} INT NOT NULL,
                        {T.StaticAttributeAlias.alias} VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.StaticAttributeAlias.static_attribute_id})
                            REFERENCES {T.StaticAttribute}({T.StaticAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.StaticAttributeAlias.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.StaticAttributeAlias.list_id}, {T.StaticAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.TaskAttribute} (
                        {T.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.TaskAttribute.list_id} INT NOT NULL,
                        {T.TaskAttribute.name} VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,
                        {T.TaskAttribute.value_type} INT NOT NULL,
                        {T.TaskAttribute.index} INT NOT NULL,
                        {T.TaskAttribute.min_slots} INT NOT NULL,
                        {T.TaskAttribute.max_slots} INT NOT NULL,
                        {T.TaskAttribute.unique_slots} BOOL NOT NULL,
                        {T.TaskAttribute.unique_value_per_list} BOOL NOT NULL,

                        FOREIGN KEY ({T.TaskAttribute.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.TaskAttribute.list_id}, {T.TaskAttribute.name}),
                        UNIQUE ({T.TaskAttribute.list_id}, {T.TaskAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.TaskAttributeAlias} (
                        {T.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.TaskAttributeAlias.task_attribute_id} INT NOT NULL,
                        {T.TaskAttributeAlias.list_id} INT NOT NULL,
                        {T.TaskAttributeAlias.alias} VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.TaskAttributeAlias.task_attribute_id})
                            REFERENCES {T.TaskAttribute}({T.TaskAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.TaskAttributeAlias.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.TaskAttributeAlias.list_id}, {T.TaskAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.TaskAttributeCollectionNode} (
                        {T.TaskAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.TaskAttributeCollectionNode.root_id} INT,
                        {T.TaskAttributeCollectionNode.task_id} INT NOT NULL,
                        {T.TaskAttributeCollectionNode.value} BLOB NOT NULL,
                        {T.TaskAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({T.TaskAttributeCollectionNode.root_id})
                            REFERENCES {T.TaskAttributeCollectionNode}({T.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.TaskAttributeCollectionNode.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.TaskAttributeCollectionNodeAlias} (
                        {T.TaskAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id} INT NOT NULL,
                        {T.TaskAttributeCollectionNodeAlias.alias} VARCHAR({TaskAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.TaskAttributeCollectionNodeAlias.task_attribute_collection_node_id})
                            REFERENCES {T.TaskAttributeCollectionNode}({T.TaskAttributeCollectionNode.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.TaskAttributeCollectionNodeAlias.alias})
                    )
                """)

                
                cursor.execute(f"""
                    CREATE TABLE {T.UserAttribute} (
                        {T.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.UserAttribute.list_id} INT NOT NULL,
                        {T.UserAttribute.name} VARCHAR({UserAttribute.MAX_SYN_LEN}) NOT NULL,
                        {T.UserAttribute.index} INT NOT NULL,
                        {T.UserAttribute.value_type} INT NOT NULL,
                        {T.UserAttribute.min_slots} INT NOT NULL,
                        {T.UserAttribute.max_slots} INT NOT NULL,
                        {T.UserAttribute.unique_slots} BOOL NOT NULL,

                        FOREIGN KEY ({T.UserAttribute.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.UserAttribute.list_id}, {T.UserAttribute.name}),
                        UNIQUE ({T.UserAttribute.list_id}, {T.UserAttribute.index})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.UserAttributeAlias} (
                        {T.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.UserAttributeAlias.user_attribute_id} INT NOT NULL,
                        {T.UserAttributeAlias.list_id} INT NOT NULL,
                        {T.UserAttributeAlias.alias} VARCHAR({UserAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.UserAttributeAlias.user_attribute_id})
                            REFERENCES {T.UserAttribute}({T.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.UserAttributeAlias.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.UserAttributeAlias.list_id}, {T.UserAttributeAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.UserAttributeCollectionNode} (
                        {T.UserAttributeCollectionNode.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.UserAttributeCollectionNode.root_id} INT,
                        {T.UserAttributeCollectionNode.task_id} INT NOT NULL,
                        {T.UserAttributeCollectionNode.value} BLOB NOT NULL,
                        {T.UserAttributeCollectionNode.sort_value} INT NOT NULL,

                        FOREIGN KEY ({T.UserAttributeCollectionNode.root_id})
                            REFERENCES {T.UserAttributeCollectionNode}({T.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.UserAttributeCollectionNode.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.UserAttributeCollectionNodeAlias} (
                        {T.UserAttributeCollectionNodeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id} INT NOT NULL,
                        {T.UserAttributeCollectionNodeAlias.alias} VARCHAR({UserAttribute.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.UserAttributeCollectionNodeAlias.user_attribute_collection_node_id})
                            REFERENCES {T.UserAttributeCollectionNode}({T.UserAttributeCollectionNode.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.UserAttributeCollectionNodeAlias.alias})
                    )
                """)



                cursor.execute(f"""
                    CREATE TABLE {T.Task} (
                        {T.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.Task.list_id} INT NOT NULL,
                        {T.Task.name} VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.Task.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.Task.list_id}, {T.Task.name})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.TaskAlias} (
                        {T.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                        {T.TaskAlias.task_id} INT NOT NULL,
                        {T.TaskAlias.list_id} INT NOT NULL,
                        {T.TaskAlias.alias} VARCHAR({Task.MAX_SYN_LEN}) NOT NULL,

                        FOREIGN KEY ({T.TaskAlias.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE,

                        FOREIGN KEY ({T.TaskAlias.list_id})
                            REFERENCES {T.List}({T.List.id})
                            ON DELETE CASCADE,

                        UNIQUE ({T.TaskAlias.list_id}, {T.TaskAlias.alias})
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.StaticAttributeTaskValue} (
                        {T.StaticAttributeTaskValue.task_id} INT NOT NULL,
                        {T.StaticAttributeTaskValue.static_attribute_id} INT NOT NULL,
                        {T.StaticAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY ({T.StaticAttributeTaskValue.task_id}, {T.StaticAttributeTaskValue.static_attribute_id}),

                        FOREIGN KEY ({T.StaticAttributeTaskValue.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.StaticAttributeTaskValue.static_attribute_id})
                            REFERENCES {T.StaticAttribute}({T.StaticAttribute.id})
                            ON DELETE CASCADE
                    )
                """)
                
                cursor.execute(f"""
                    CREATE TABLE {T.TaskAttributeTaskValue} (
                        {T.TaskAttributeTaskValue.task_id} INT NOT NULL,
                        {T.TaskAttributeTaskValue.task_attribute_id} INT NOT NULL,
                        {T.TaskAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {T.TaskAttributeTaskValue.task_id}, 
                            {T.TaskAttributeTaskValue.task_attribute_id}
                        ),

                        FOREIGN KEY ({T.TaskAttributeTaskValue.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.TaskAttributeTaskValue.task_attribute_id})
                            REFERENCES {T.TaskAttribute}({T.TaskAttribute.id})
                            ON DELETE CASCADE
                    )
                """)

                cursor.execute(f"""
                    CREATE TABLE {T.UserAttributeTaskValue} (
                        {T.UserAttributeTaskValue.task_id} INT NOT NULL,
                        {T.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                        {T.UserAttributeTaskValue.user_attribute_id} INT NOT NULL,
                        {T.UserAttributeTaskValue.value} BLOB NOT NULL,

                        PRIMARY KEY (
                            {T.UserAttributeTaskValue.task_id}, 
                            {T.UserAttributeTaskValue.user_id}, 
                            {T.UserAttributeTaskValue.user_attribute_id}
                        ),

                        FOREIGN KEY ({T.UserAttributeTaskValue.task_id})
                            REFERENCES {T.Task}({T.Task.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.UserAttributeTaskValue.user_attribute_id})
                            REFERENCES {T.UserAttribute}({T.UserAttribute.id})
                            ON DELETE CASCADE,
                        FOREIGN KEY ({T.UserAttributeTaskValue.user_id})
                            REFERENCES {T.User}({T.User.id})
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

    def create_community(self, user_id: int, guild_id: int, bad_name: str) -> 'Community':
        with equality_locked(self):
            community = self.get_community_by_guild_id(guild_id)

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
                    INSERT INTO {T.Community} (
                        {T.Community.name}
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {T.Guild} (
                        {T.Guild.id}, 
                        {T.Guild.community_id}
                    )
                    VALUES (
                        {h|guild_id},
                        {h|community_id}
                    )
                """, h.steal())

                cursor.execute(f"""
                    INSERT INTO {T.User} (
                        {T.User.id},
                        {T.User.community_id},
                        {T.User.power}
                    )
                    VALUES (
                        {h|user_id},
                        {h|community_id},
                        {h|UserRank.OWNER.power}     
                    )
                """, h.steal())

                obj = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=None,
                    name=name
                )  

                list = obj.create_list('Main')

                cursor.execute(f"""
                    UPDATE {T.Community}
                    SET {T.Community.default_selected_list_id} = {h|list.id}
                    WHERE {T.Community.id} = {h|obj.id}
                """, h.steal())

                obj = Community(
                    jumpedia=self,
                    id=community_id,
                    default_selected_list_id=list.id,
                    name=name
                )

                # Rollback if anything goes wrong up to this point
                return obj
    
    def delete_community(self, bad_name: str) -> None:
        with equality_locked(self):
            community = self.get_community_by_name(bad_name)

            # Already deleted
            if community is None:
                return
            
            h = queries.ArgHelper()

            with equality_locked(community), queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {T.Community}
                    WHERE {T.Community.id} = {h|self.id}
                """, h.steal())
    
    def _fetch_from_community_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[S.TableResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {T.Community}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[S.TableResultT] = cursor.fetchall()

        return result
    
    def _community_data_to_obj(self, data: S.TableResultT) -> 'Community':
        return Community(
            jumpedia=self,
            id=data[T.Community.id],
            name=data[T.Community.name],
            default_selected_list_id=data[T.Community.default_selected_list_id]
        )
    
    def get_communities(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list['Community']:
        return [
            self._community_data_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> 'Community | None':
        data = self._fetch_from_community_table(lambda h: f"{T.Community.id} = {h|id}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, name: str) -> 'Community | None':
        name = text.norm(name)
        data = self._fetch_from_community_table(lambda h: f"{T.Community.name} = {h|name}")
        return self._community_data_to_obj(data[0]) if data else None
    
    def get_community_by_guild_id(self, guild_id: int) -> 'Community | None':
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {T.Guild.community_id}
                FROM {T.Guild}
                WHERE {T.Guild.id} = {h|guild_id}
            """, h.steal())

            result: S.TableResultT | None = cursor.fetchone()

        if result is None:
            return None

        return self.get_community_by_id(result[T.Guild.community_id])
    

    # --- Meta Users ---

    def _fetch_from_meta_rank_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[S.TableResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {T.MetaRank}
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[S.TableResultT] = cursor.fetchall()

        return result
    
    def _meta_rank_data_to_obj(self, data: S.TableResultT) -> tuple[int, MetaRank]:
        return (data[T.MetaRank.user_id], MetaRank.get(data[T.MetaRank.power]))
    
    def get_meta_ranks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> dict[int, 'MetaRank']:
        result: dict[int, 'MetaRank'] = {}

        for data in self._fetch_from_meta_rank_table(where):
            tup = self._meta_rank_data_to_obj(data)
            result[tup[0]] = tup[1]
        
        return result

    def get_meta_rank_by_user_id(self, user_id: int) -> MetaRank:
        data = self._fetch_from_meta_rank_table(lambda h: f"{T.MetaRank.user_id} = {h|user_id}")
        return self._meta_rank_data_to_obj(data[0])[1] if data else MetaRank.DEFAULT

Jumpedia()._init()