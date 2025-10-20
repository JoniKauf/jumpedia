
import time
import typing as t
from functools import cached_property

from structures import errors

from ..database import queries, typed
from ..database.simple_orm import Arg, BaseModel, Raw, Rows, column
from ..ranks.community_rank import CommunityRank
from ..ranks.jumpedia_rank import JumpediaRank
from ..utils import text
from . import BaseStructure, user
from .attribute import slot_type
from .community import Community, CommunityLimits
from .errors import (ServerAlreadyConnectedToCommunityError,
                     StructureNotFoundError, SynAlreadyTakenError)
from .user import JumpediaUser


class JumpediaLimits(t.NamedTuple):
    community_name_length_max: int
    list_name_length_max: int
    user_name_length_max: int  # Discord limit
    attribute_syn_length_max: int
    attribute_task_value_slot_count_max: int
    attribute_task_value_slot_length_max: int


# Moved out of class to reduce line length at least a bit
def _create_db_tables(j: Jumpedia, c: queries.CursorWrapper) -> None:
    try:
        c.execute_raw(f"""
            CREATE TABLE {typed.Community} (
                {typed.Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.Community.norm_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                {typed.Community.real_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                {typed.Community.default_selected_list_id} INT DEFAULT NULL
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.Server} (
                {typed.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                {typed.Server.community_id} INT NOT NULL,

                FOREIGN KEY ({typed.Server.community_id}) 
                    REFERENCES {typed.Community}({typed.Community.id}) 
                    ON DELETE CASCADE
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.List} (
                {typed.List.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.List.community_id} INT NOT NULL,
                {typed.List.norm_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,
                {typed.List.real_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,

                FOREIGN KEY ({typed.List.community_id})
                    REFERENCES {typed.Community}({typed.Community.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.List.community_id}, {typed.List.norm_name})
            )
        """)

        # Add foreign key to community, otherwise we would have circular dependency
        c.execute_raw(f"""
            ALTER TABLE {typed.Community}
            ADD CONSTRAINT fk_community_default_list
            FOREIGN KEY ({typed.Community.default_selected_list_id})
                REFERENCES {typed.List}({typed.List.id})
                ON DELETE SET NULL
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.JumpediaUser} (
                {typed.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                {typed.JumpediaUser.norm_name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                {typed.JumpediaUser.raw_name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                {typed.JumpediaUser.power} INT NOT NULL
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.CommunityUser} (
                {typed.CommunityUser.community_id} INT NOT NULL,
                {typed.CommunityUser.jumpedia_user_id} BIGINT UNSIGNED NOT NULL,
                {typed.CommunityUser.power} INT NOT NULL,
                {typed.CommunityUser.selected_list_id} INT,

                PRIMARY KEY ({typed.CommunityUser.community_id}, {typed.CommunityUser.jumpedia_user_id}),

                FOREIGN KEY ({typed.CommunityUser.community_id})
                    REFERENCES {typed.Community}({typed.Community.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.CommunityUser.jumpedia_user_id})
                    REFERENCES {typed.JumpediaUser}({typed.JumpediaUser.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.CommunityUser.selected_list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE SET NULL
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.StaticAttribute} (
                {typed.StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.StaticAttribute.list_id} INT NOT NULL,
                {typed.StaticAttribute.kind} TINYINT NOT NULL,
                {typed.StaticAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.StaticAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.StaticAttribute.slot_type} INT NOT NULL,
                {typed.StaticAttribute.position} INT NOT NULL,
                {typed.StaticAttribute.min_slots} INT NOT NULL,
                {typed.StaticAttribute.max_slots} INT NOT NULL,

                FOREIGN KEY ({typed.StaticAttribute.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.StaticAttribute.list_id}, {typed.StaticAttribute.kind}),
                UNIQUE ({typed.StaticAttribute.list_id}, {typed.StaticAttribute.norm_name}),
                UNIQUE ({typed.StaticAttribute.list_id}, {typed.StaticAttribute.position})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.StaticAttributeAlias} (
                {typed.StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.StaticAttributeAlias.attribute_id} INT NOT NULL,
                {typed.StaticAttributeAlias.list_id} INT NOT NULL,
                {typed.StaticAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.StaticAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                FOREIGN KEY ({typed.StaticAttributeAlias.attribute_id})
                    REFERENCES {typed.StaticAttribute}({typed.StaticAttribute.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.StaticAttributeAlias.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.StaticAttributeAlias.list_id}, {typed.StaticAttributeAlias.norm_alias})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAttribute} (
                {typed.TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.TaskAttribute.list_id} INT NOT NULL,
                {typed.TaskAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.TaskAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.TaskAttribute.slot_type} INT NOT NULL,
                {typed.TaskAttribute.position} INT NOT NULL,
                {typed.TaskAttribute.min_slots} INT NOT NULL,
                {typed.TaskAttribute.max_slots} INT NOT NULL,

                FOREIGN KEY ({typed.TaskAttribute.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.TaskAttribute.list_id}, {typed.TaskAttribute.norm_name}),
                UNIQUE ({typed.TaskAttribute.list_id}, {typed.TaskAttribute.position})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAttributeAlias} (
                {typed.TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.TaskAttributeAlias.attribute_id} INT NOT NULL,
                {typed.TaskAttributeAlias.list_id} INT NOT NULL,
                {typed.TaskAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.TaskAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                FOREIGN KEY ({typed.TaskAttributeAlias.attribute_id})
                    REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.TaskAttributeAlias.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.TaskAttributeAlias.list_id}, {typed.TaskAttributeAlias.norm_alias})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAttributeCollectionSlot} (
                {typed.TaskAttributeCollectionSlot.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.TaskAttributeCollectionSlot.attribute_id} INT NOT NULL,
                {typed.TaskAttributeCollectionSlot.index} INT UNSIGNED NOT NULL,
                {typed.TaskAttributeCollectionSlot.norm_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,
                {typed.TaskAttributeCollectionSlot.slot_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({typed.TaskAttributeCollectionSlot.attribute_id})
                    REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                    ON DELETE CASCADE,

                UNIQUE (
                    {typed.TaskAttributeCollectionSlot.attribute_id},
                    {typed.TaskAttributeCollectionSlot.norm_slot}
                ),
                UNIQUE (
                    {typed.TaskAttributeCollectionSlot.attribute_id},
                    {typed.TaskAttributeCollectionSlot.index}
                )
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAttributeCollectionSlotAlias} (
                {typed.TaskAttributeCollectionSlotAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.TaskAttributeCollectionSlotAlias.attribute_id} INT NOT NULL,
                {typed.TaskAttributeCollectionSlotAlias.attribute_collection_entry_id} INT NOT NULL,
                {typed.TaskAttributeCollectionSlotAlias.norm_alias} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,
                {typed.TaskAttributeCollectionSlotAlias.slot_alias} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({typed.TaskAttributeCollectionSlotAlias.attribute_collection_entry_id})
                    REFERENCES {typed.TaskAttributeCollectionSlot}({typed.TaskAttributeCollectionSlot.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.TaskAttributeCollectionSlotAlias.attribute_id})
                    REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                    ON DELETE CASCADE,

                UNIQUE (
                    {typed.TaskAttributeCollectionSlotAlias.attribute_id},
                    {typed.TaskAttributeCollectionSlotAlias.norm_alias}
                )
            )
        """)

        
        c.execute_raw(f"""
            CREATE TABLE {typed.UserAttribute} (
                {typed.UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.UserAttribute.list_id} INT NOT NULL,
                {typed.UserAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.UserAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.UserAttribute.position} INT NOT NULL,
                {typed.UserAttribute.slot_type} INT NOT NULL,
                {typed.UserAttribute.min_slots} INT NOT NULL,
                {typed.UserAttribute.max_slots} INT NOT NULL,

                FOREIGN KEY ({typed.UserAttribute.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.UserAttribute.list_id}, {typed.UserAttribute.norm_name}),
                UNIQUE ({typed.UserAttribute.list_id}, {typed.UserAttribute.position})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.UserAttributeAlias} (
                {typed.UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.UserAttributeAlias.attribute_id} INT NOT NULL,
                {typed.UserAttributeAlias.list_id} INT NOT NULL,
                {typed.UserAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {typed.UserAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                FOREIGN KEY ({typed.UserAttributeAlias.attribute_id})
                    REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.UserAttributeAlias.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.UserAttributeAlias.list_id}, {typed.UserAttributeAlias.norm_alias})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.UserAttributeCollectionSlot} (
                {typed.UserAttributeCollectionSlot.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.UserAttributeCollectionSlot.attribute_id} INT NOT NULL,
                {typed.UserAttributeCollectionSlot.index} INT UNSIGNED NOT NULL,
                {typed.UserAttributeCollectionSlot.norm_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,
                {typed.UserAttributeCollectionSlot.slot_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({typed.UserAttributeCollectionSlot.attribute_id})
                    REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                    ON DELETE CASCADE,

                UNIQUE (
                    {typed.UserAttributeCollectionSlot.attribute_id},
                    {typed.UserAttributeCollectionSlot.norm_slot}
                ),
                UNIQUE (
                    {typed.UserAttributeCollectionSlot.attribute_id},
                    {typed.UserAttributeCollectionSlot.index}
                )
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.UserAttributeCollectionSlotAlias} (
                {typed.UserAttributeCollectionSlotAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.UserAttributeCollectionSlotAlias.attribute_id} INT NOT NULL,
                {typed.UserAttributeCollectionSlotAlias.attribute_collection_entry_id} INT NOT NULL,
                {typed.UserAttributeCollectionSlotAlias.norm_alias} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,
                {typed.UserAttributeCollectionSlotAlias.slot_alias} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({typed.UserAttributeCollectionSlotAlias.attribute_collection_entry_id})
                    REFERENCES {typed.UserAttributeCollectionSlot}({typed.UserAttributeCollectionSlot.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.UserAttributeCollectionSlotAlias.attribute_id})
                    REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                    ON DELETE CASCADE,

                UNIQUE (
                    {typed.UserAttributeCollectionSlotAlias.attribute_id},
                    {typed.UserAttributeCollectionSlotAlias.norm_alias}
                )
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.Task} (
                {typed.Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.Task.list_id} INT NOT NULL,
                {typed.Task.norm_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                {typed.Task.slot_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                FOREIGN KEY ({typed.Task.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.Task.list_id}, {typed.Task.norm_name})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAlias} (
                {typed.TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                {typed.TaskAlias.task_id} INT NOT NULL,
                {typed.TaskAlias.list_id} INT NOT NULL,
                {typed.TaskAlias.norm_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                {typed.TaskAlias.slot_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                FOREIGN KEY ({typed.TaskAlias.task_id})
                    REFERENCES {typed.Task}({typed.Task.id})
                    ON DELETE CASCADE,

                FOREIGN KEY ({typed.TaskAlias.list_id})
                    REFERENCES {typed.List}({typed.List.id})
                    ON DELETE CASCADE,

                UNIQUE ({typed.TaskAlias.list_id}, {typed.TaskAlias.norm_alias})
            )
        """)

        c.execute_raw(f"""
            CREATE TABLE {typed.TaskAttributeTaskValue} (
                {typed.TaskAttributeTaskValue.task_id} INT NOT NULL,
                {typed.TaskAttributeTaskValue.attribute_id} INT NOT NULL,
                {typed.TaskAttributeTaskValue.index} TINYINT UNSIGNED NOT NULL,
                {typed.TaskAttributeTaskValue.slot_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                PRIMARY KEY (
                    {typed.TaskAttributeTaskValue.task_id}, 
                    {typed.TaskAttributeTaskValue.attribute_id},
                    {typed.TaskAttributeTaskValue.index}
                ),
                
                FOREIGN KEY ({typed.TaskAttributeTaskValue.task_id})
                    REFERENCES {typed.Task}({typed.Task.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.TaskAttributeTaskValue.attribute_id})
                    REFERENCES {typed.TaskAttribute}({typed.TaskAttribute.id})
                    ON DELETE CASCADE
            )
        """)
        
        c.execute_raw(f"""
            CREATE TABLE {typed.UserAttributeTaskValue} (
                {typed.UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                {typed.UserAttributeTaskValue.task_id} INT NOT NULL,
                {typed.UserAttributeTaskValue.attribute_id} INT NOT NULL,
                {typed.UserAttributeTaskValue.index} TINYINT UNSIGNED NOT NULL,
                {typed.UserAttributeTaskValue.slot_slot} VARCHAR({slot_type.STR_MAX_LEN}) NOT NULL,

                PRIMARY KEY (
                    {typed.UserAttributeTaskValue.user_id},
                    {typed.UserAttributeTaskValue.task_id}, 
                    {typed.UserAttributeTaskValue.attribute_id},
                    {typed.UserAttributeTaskValue.index}
                ),

                FOREIGN KEY ({typed.UserAttributeTaskValue.user_id})
                    REFERENCES {typed.JumpediaUser}({typed.JumpediaUser.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.UserAttributeTaskValue.task_id})
                    REFERENCES {typed.Task}({typed.Task.id})
                    ON DELETE CASCADE,
                FOREIGN KEY ({typed.UserAttributeTaskValue.attribute_id})
                    REFERENCES {typed.UserAttribute}({typed.UserAttribute.id})
                    ON DELETE CASCADE
            )
        """)
    except Exception as e:
        try:
            c.execute_raw(f"""
                DROP DATABASE `{j.database_name}`
            """)
        finally:
            raise e
    
    print("Jumpedia database successfully created!")

class Jumpedia(BaseStructure):
    id: int
    database_name: str
    limits: JumpediaLimits

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)
    
    @cached_property
    def name(self) -> str:
        return self.__class__.type_name

    def __post_init__(self) -> None:
        class SCHEMATA(BaseModel, table_name="SCHEMATA"):
            @column(str)
            def SCHEMA_NAME(self): pass

        with queries.connected(no_db=True) as c:
            c.execute_raw(f"""
                SELECT {SCHEMATA.SCHEMA_NAME}
                FROM INFORMATION_SCHEMA.{SCHEMATA}
                WHERE {SCHEMATA.SCHEMA_NAME} = '{self.database_name}';
            """)

            exists = c.fetchone(SCHEMATA) is not None

            if exists:
                return

            print("Jumpedia database does NOT exist, creating new in 5 seconds!")

            time.sleep(5)

            c.execute_raw(f"""
                CREATE DATABASE `{self.database_name}`
                    CHARACTER SET = utf8mb4
                """)

        with queries.connected() as c:
            _create_db_tables(self, c)
    

    # --- Communities ---

    def create_community(self, *, real_name: text.RealStr, server_id: int, jumpedia_user: JumpediaUser) -> 'Community':
        norm_name = text.NormStr(real_name)
        
        with self.locked:
            comm = self.get_community_by_server_id(server_id)

            if comm is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, comm)
            
            comm = self.get_community_by_name(norm_name)

            if comm is not None:
                raise SynAlreadyTakenError(norm_name, comm)

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Community} (
                        {typed.Community.norm_name},
                        {typed.Community.real_name}
                    )
                    VALUES (
                        {arg(norm_name)},
                        {arg(real_name)}
                    )
                """)

                community_id = c.last_generated_id

                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id}, 
                        {typed.Server.community_id}
                    )
                    VALUES (
                        {arg(server_id)},
                        {arg(community_id)}
                    )
                """)
                
                comm = Community(
                    jumpedia=self,
                    id=community_id,
                    real_name=real_name,
                    norm_name=norm_name,
                    limits=CommunityLimits(
                        community_list_count_max=2,
                        list_attribute_count_max=3,
                        list_task_count_max=2,
                        attribute_collection_entry_alias_count_max=2,
                        attribute_collection_entry_count_max=2,
                        attribute_alias_count_max=2
                    )
                )  
                
                jumpedia_user.get_or_create_community_user(
                    comm.id,
                    CommunityRank.OWNER,
                    None,
                    True,
                    True
                )

                return comm
    
    def delete_community(self, id: int) -> None:
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {typed.Community}
                WHERE {typed.Community.id} = {arg(id)}
            """)
                
            if c.affected_row_count < 1:
                raise StructureNotFoundError(Community)
    
    def _fetch_from_community_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.Community]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.Community}
                {Raw(f"WHERE {where(arg)}" if where is not None else "")}
            """)

            result = c.fetchall(typed.Community)

        return result
    
    def _community_row_to_obj(self, row: typed.Community) -> Community:
        return Community(
            jumpedia=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name,
            limits=CommunityLimits(
                community_list_count_max=2,
                list_attribute_count_max=3,
                list_task_count_max=2,
                attribute_collection_entry_alias_count_max=2,
                attribute_collection_entry_count_max=2,
                attribute_alias_count_max=2
            )
        )
    
    def get_communities(self, where: t.Callable[[Arg], str] | None = None) -> list[Community]:
        return [
            self._community_row_to_obj(data) 
            for data in self._fetch_from_community_table(where)
        ]
        
    def get_community_by_id(self, id: int) -> Community | None:
        data = self._fetch_from_community_table(lambda arg: f"{typed.Community.id} = {arg(id)}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_name(self, norm_name: text.NormStr) -> Community | None:
        data = self._fetch_from_community_table(lambda arg: f"{typed.Community.norm_name} = {arg(norm_name)}")
        return self._community_row_to_obj(data[0]) if data else None
    
    def get_community_by_server_id(self, server_id: int) -> Community | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.Server.community_id}
                FROM {typed.Server}
                WHERE {typed.Server.id} = {arg(server_id)}
            """)

            result = c.fetchone(typed.Server)

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
        norm_name = text.NormStr(name)

        with self.locked:
            user = self.get_jumpedia_user_by_id(id)

            with queries.connected() as c:
                if user is None:
                    c.execute(lambda arg: t"""
                        INSERT INTO {typed.JumpediaUser} (
                            {typed.JumpediaUser.id},
                            {typed.JumpediaUser.power},
                            {typed.JumpediaUser.norm_name},
                            {typed.JumpediaUser.raw_name}
                        )
                        VALUES (
                            {arg(id)},
                            {arg(jumpedia_rank.power)},
                            {arg(norm_name)},
                            {arg(name)}
                        )
                    """)

                else:
                    jumpedia_rank = jumpedia_rank if override_jumpedia_rank_if_user_exists else user.jumpedia_rank
                    real_name = name if override_name_if_user_exists else user.user_name

                    if real_name != user.user_name or jumpedia_rank != user.jumpedia_rank:
                        c.execute(lambda arg: t"""
                            UPDATE {typed.JumpediaUser} 
                            SET 
                                {typed.JumpediaUser.norm_name} = {arg(norm_name)},
                                {typed.JumpediaUser.raw_name} = {arg(real_name)},
                                {typed.JumpediaUser.power} = {arg(jumpedia_rank.power)}
                            WHERE 
                                {typed.JumpediaUser.id} = {arg(user.id)}
                        """)
                        
                return JumpediaUser(
                    jumpedia=self,
                    id=id,
                    user_name=real_name,
                    jumpedia_rank=jumpedia_rank
                )

    def _fetch_from_user_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.JumpediaUser]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.JumpediaUser}
                {Raw(f"WHERE {where(arg)}" if where is not None else "")}
            """)

            result = c.fetchall(typed.JumpediaUser)

        return result
    
    def _user_row_to_obj(self, row: typed.JumpediaUser) -> JumpediaUser:
        return JumpediaUser(
            jumpedia=self,
            user_name=row.raw_name,
            id=row.id,
            jumpedia_rank=JumpediaRank.get(row.power)
        )
    
    def get_users(self, where: t.Callable[[Arg], str] | None = None) -> list[JumpediaUser]:
        return [
            self._user_row_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_jumpedia_user_by_id(self, id: int) -> JumpediaUser | None:
        data = self._fetch_from_user_table(lambda arg: f"{typed.JumpediaUser.id} = {arg(id)}")
        return self._user_row_to_obj(data[0]) if data else None

    def add_community_to_server(self, community_id: int, server_id: int) -> Community:
        with self.locked:
            existing_community = self.get_community_by_server_id(server_id)

            if existing_community is not None:
                raise errors.ServerAlreadyConnectedToCommunityError(server_id, existing_community)     
            
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Server} (
                        {typed.Server.id},
                        {typed.Server.community_id}
                    )
                    VALUES (
                        {arg(server_id)},
                        {arg(community_id)}
                    )
                """)

            # Community must now be connected
            community = self.get_community_by_server_id(server_id)
            assert community is not None

            return community

    def remove_community_from_server(self, server_id: int) -> Community:
        with self.locked:
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    DELETE FROM {typed.Server}
                    WHERE {typed.Server.id} = {arg(server_id)}
                    RETURNING {typed.Server.community_id}
                """)
                
                row = c.fetchone(typed.Server)

            if row is None:
                raise errors.ServerNotConnectedToACommunityError(server_id)

            community = self.get_community_by_id(row.community_id)
            assert community is not None

            return community



# THE ONE PIECE IS REAAAAAAAAAAAAAAAAAAAAAAAAAAAAL
THE_ONE_AND_ONLY_JUMPEDIA_OBJECT_ONE_MIGHT_EVEN_CALL_IT_THE_ONE_PIECE: t.Final[Jumpedia] = Jumpedia(
    id=1,
    database_name=typed.DATABASE_NAME,
    limits=JumpediaLimits(
        community_name_length_max=64,
        list_name_length_max=64,
        user_name_length_max=32,  # Discord limit
        attribute_syn_length_max=64,
        attribute_task_value_slot_length_max=255,
        attribute_task_value_slot_count_max=32
    )
)

JUMPEDIA = THE_ONE_AND_ONLY_JUMPEDIA_OBJECT_ONE_MIGHT_EVEN_CALL_IT_THE_ONE_PIECE