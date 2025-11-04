from email.policy import default
import types
import typing as t

from ..attribute import KindT
from src.utils.orm import *
from src.utils.text import NormStr, RealStr

from ..attribute.slot_str import SlotStr

if t.TYPE_CHECKING:
    from . import Jumpedia


class Community(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(RealStr)
    def real_name(self):
        pass

    @column(int, types.NoneType)
    def default_selected_list_id(self):
        pass


class CommunityLimits(Model, table_name=SNAKE):
    @column(int)
    def community_id(self):
        pass

    @column(int)
    def community_list_count_max(self):
        pass

    @column(int)
    def list_attribute_count_max(self):
        pass

    @column(int)
    def list_task_count_max(self):
        pass

    @column(int)
    def attribute_task_value_slot_count_max(self):
        pass

    @column(int)
    def attribute_collection_entry_count_max(self):
        pass

    @column(int)
    def attribute_collection_entry_alias_count_max(self):
        pass


class Server(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_id(self):
        pass


class JumpediaUser(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(str)
    def raw_name(self):
        pass

    @column(int)
    def power(self):
        pass


# --- Per Community ---


class List(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(RealStr)
    def real_name(self):
        pass


class CommunityUser(Model, table_name=SNAKE):
    @column(int)
    def community_id(self):
        pass

    @column(int)
    def jumpedia_user_id(self):
        pass

    @column(int)
    def power(self):
        pass

    @column(int, types.NoneType)
    def selected_list_id(self):
        pass


# --- Static Attribute ---


class StaticAttribute(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(RealStr)
    def real_name(self):
        pass

    @column(int)
    def slot_type(self):
        pass

    @column(int)
    def position(self):
        pass

    @column(int)
    def min_slots(self):
        pass

    @column(int)
    def max_slots(self):
        pass

    @column(KindT)  # type: ignore
    def kind(self):
        pass


class StaticAttributeAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(RealStr)
    def real_alias(self):
        pass


# --- Task Attribute ---


class TaskAttribute(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(RealStr)
    def real_name(self):
        pass

    @column(int)
    def slot_type(self):
        pass

    @column(int)
    def position(self):
        pass

    @column(int)
    def min_slots(self):
        pass

    @column(int)
    def max_slots(self):
        pass


class TaskAttributeAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(RealStr)
    def real_alias(self):
        pass


class TaskAttributeCollectionEntry(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(NormStr)
    def norm_slot(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class TaskAttributeCollectionEntryAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_collection_entry_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


# --- User Attribute ---


class UserAttribute(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(RealStr)
    def real_name(self):
        pass

    @column(int)
    def slot_type(self):
        pass

    @column(int)
    def position(self):
        pass

    @column(int)
    def min_slots(self):
        pass

    @column(int)
    def max_slots(self):
        pass


class UserAttributeAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(RealStr)
    def real_alias(self):
        pass


class UserAttributeCollectionEntry(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(NormStr)
    def norm_slot(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class UserAttributeCollectionEntryAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_collection_entry_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


# --- Task ---


class Task(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_name(self):
        pass

    @column(SlotStr)
    def slot_name(self):
        pass


class TaskAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(NormStr)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


class TaskAttributeTaskValue(Model, table_name=SNAKE):
    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class UserAttributeTaskValue(Model, table_name=SNAKE):
    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def user_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


# Union types to represent attribute tables
type AnyAttributeTable = StaticAttribute | TaskAttribute | UserAttribute
type AnyAttributeAliasTable = StaticAttributeAlias | TaskAttributeAlias | UserAttributeAlias
type AnyAttributeCollectionEntryTable = TaskAttributeCollectionEntry | UserAttributeCollectionEntry
type AnyAttributeCollectionEntryAliasTable = TaskAttributeCollectionEntryAlias | UserAttributeCollectionEntryAlias
type AnyAttributeTaskValueTable = TaskAttributeTaskValue | UserAttributeTaskValue


if t.TYPE_CHECKING:
    # Intersection types to be type safe and make type checker shut up for queries
    class AbstractAttributeTable(
        StaticAttribute, TaskAttribute, UserAttribute, table_name=""
    ):
        pass

    class AbstractAttributeAliasTable(
        StaticAttributeAlias, TaskAttributeAlias, UserAttributeAlias, table_name=""
    ):
        pass

    class AbstractAttributeCollectionEntryTable(
        TaskAttributeCollectionEntry, UserAttributeCollectionEntry, table_name=""
    ):
        pass

    class AbstractAttributeCollectionEntryAliasTable(
        TaskAttributeCollectionEntryAlias,
        UserAttributeCollectionEntryAlias,
        table_name="",
    ):
        pass

    class AbstractAttributeTaskValueTable(
        TaskAttributeTaskValue, UserAttributeTaskValue, table_name=""
    ):
        pass


def create_database(j: Jumpedia) -> None:
    import time

    db_name = j.connector.database_name

    with j.meta_connector.cursor() as c:
        c.raw_execute("SHOW SCHEMAS")

        rows = c.raw_fetchall()

        for row in rows:
            if db_name in row.values():
                print("Database exists!")
                return

        print("Jumpedia database does NOT exist, creating new in 5 seconds!")

        time.sleep(5)

        c.raw_execute(
            f"""
            CREATE DATABASE `{db_name}`
            CHARACTER SET = utf8mb4
        """
        )

    with j.connector.cursor() as c:
        try:
            c.raw_execute(
                f"""
                CREATE TABLE {Community} (
                    {Community.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {Community.norm_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                    {Community.real_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                    {Community.default_selected_list_id} INT DEFAULT NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {CommunityLimits} (
                    {CommunityLimits.community_id} INT PRIMARY KEY,
                    {', '.join(f"{col.name} INT" for col in CommunityLimits._columns)},

                    FOREIGN KEY ({CommunityLimits.community_id})
                        REFERENCES {Community}({Community.id})
                        ON DELETE CASCADE
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {Server} (
                    {Server.id} BIGINT UNSIGNED PRIMARY KEY,
                    {Server.community_id} INT NOT NULL,

                    FOREIGN KEY ({Server.community_id}) 
                        REFERENCES {Community}({Community.id}) 
                        ON DELETE CASCADE
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {List} (
                    {List.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {List.community_id} INT NOT NULL,
                    {List.norm_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,
                    {List.real_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,

                    FOREIGN KEY ({List.community_id})
                        REFERENCES {Community}({Community.id})
                        ON DELETE CASCADE,

                    UNIQUE ({List.community_id}, {List.norm_name})
                )
            """
            )

            # Add foreign key to community, otherwise we would have circular dependency
            c.raw_execute(
                f"""
                ALTER TABLE {Community}
                ADD CONSTRAINT fk_community_default_list
                FOREIGN KEY ({Community.default_selected_list_id})
                    REFERENCES {List}({List.id})
                    ON DELETE SET NULL
            """
            )

            from .. import user

            c.raw_execute(
                f"""
                CREATE TABLE {JumpediaUser} (
                    {JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                    {JumpediaUser.norm_name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                    {JumpediaUser.raw_name} VARCHAR({user.MAX_NAME_LENGTH}) NOT NULL,
                    {JumpediaUser.power} INT NOT NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {CommunityUser} (
                    {CommunityUser.community_id} INT NOT NULL,
                    {CommunityUser.jumpedia_user_id} BIGINT UNSIGNED NOT NULL,
                    {CommunityUser.power} INT NOT NULL,
                    {CommunityUser.selected_list_id} INT,

                    PRIMARY KEY ({CommunityUser.community_id}, {CommunityUser.jumpedia_user_id}),

                    FOREIGN KEY ({CommunityUser.community_id})
                        REFERENCES {Community}({Community.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({CommunityUser.jumpedia_user_id})
                        REFERENCES {JumpediaUser}({JumpediaUser.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({CommunityUser.selected_list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE SET NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {StaticAttribute} (
                    {StaticAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {StaticAttribute.list_id} INT NOT NULL,
                    {StaticAttribute.kind} TINYINT NOT NULL,
                    {StaticAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttribute.slot_type} INT NOT NULL,
                    {StaticAttribute.position} INT NOT NULL,
                    {StaticAttribute.min_slots} INT NOT NULL,
                    {StaticAttribute.max_slots} INT NOT NULL,

                    FOREIGN KEY ({StaticAttribute.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({StaticAttribute.list_id}, {StaticAttribute.kind}),
                    UNIQUE ({StaticAttribute.list_id}, {StaticAttribute.norm_name}),
                    UNIQUE ({StaticAttribute.list_id}, {StaticAttribute.position})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {StaticAttributeAlias} (
                    {StaticAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {StaticAttributeAlias.attribute_id} INT NOT NULL,
                    {StaticAttributeAlias.list_id} INT NOT NULL,
                    {StaticAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({StaticAttributeAlias.attribute_id})
                        REFERENCES {StaticAttribute}({StaticAttribute.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({StaticAttributeAlias.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({StaticAttributeAlias.list_id}, {StaticAttributeAlias.norm_alias})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttribute} (
                    {TaskAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttribute.list_id} INT NOT NULL,
                    {TaskAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttribute.slot_type} INT NOT NULL,
                    {TaskAttribute.position} INT NOT NULL,
                    {TaskAttribute.min_slots} INT NOT NULL,
                    {TaskAttribute.max_slots} INT NOT NULL,

                    FOREIGN KEY ({TaskAttribute.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAttribute.list_id}, {TaskAttribute.norm_name}),
                    UNIQUE ({TaskAttribute.list_id}, {TaskAttribute.position})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeAlias} (
                    {TaskAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeAlias.attribute_id} INT NOT NULL,
                    {TaskAttributeAlias.list_id} INT NOT NULL,
                    {TaskAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeAlias.attribute_id})
                        REFERENCES {TaskAttribute}({TaskAttribute.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskAttributeAlias.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAttributeAlias.list_id}, {TaskAttributeAlias.norm_alias})
                )
            """
            )

            from ..attribute import slot_str

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeCollectionEntry} (
                    {TaskAttributeCollectionEntry.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeCollectionEntry.attribute_id} INT NOT NULL,
                    {TaskAttributeCollectionEntry.index} INT UNSIGNED NOT NULL,
                    {TaskAttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {TaskAttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeCollectionEntry.attribute_id})
                        REFERENCES {TaskAttribute}({TaskAttribute.id})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {TaskAttributeCollectionEntry.attribute_id},
                        {TaskAttributeCollectionEntry.norm_slot}
                    ),
                    UNIQUE (
                        {TaskAttributeCollectionEntry.attribute_id},
                        {TaskAttributeCollectionEntry.index}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeCollectionEntryAlias} (
                    {TaskAttributeCollectionEntryAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeCollectionEntryAlias.attribute_id} INT NOT NULL,
                    {TaskAttributeCollectionEntryAlias.attribute_collection_entry_id} INT NOT NULL,
                    {TaskAttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {TaskAttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeCollectionEntryAlias.attribute_collection_entry_id})
                        REFERENCES {TaskAttributeCollectionEntry}({TaskAttributeCollectionEntry.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskAttributeCollectionEntryAlias.attribute_id})
                        REFERENCES {TaskAttribute}({TaskAttribute.id})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {TaskAttributeCollectionEntryAlias.attribute_id},
                        {TaskAttributeCollectionEntryAlias.norm_alias}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttribute} (
                    {UserAttribute.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {UserAttribute.list_id} INT NOT NULL,
                    {UserAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttribute.position} INT NOT NULL,
                    {UserAttribute.slot_type} INT NOT NULL,
                    {UserAttribute.min_slots} INT NOT NULL,
                    {UserAttribute.max_slots} INT NOT NULL,

                    FOREIGN KEY ({UserAttribute.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({UserAttribute.list_id}, {UserAttribute.norm_name}),
                    UNIQUE ({UserAttribute.list_id}, {UserAttribute.position})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeAlias} (
                    {UserAttributeAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeAlias.attribute_id} INT NOT NULL,
                    {UserAttributeAlias.list_id} INT NOT NULL,
                    {UserAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({UserAttributeAlias.attribute_id})
                        REFERENCES {UserAttribute}({UserAttribute.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeAlias.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({UserAttributeAlias.list_id}, {UserAttributeAlias.norm_alias})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeCollectionEntry} (
                    {UserAttributeCollectionEntry.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeCollectionEntry.attribute_id} INT NOT NULL,
                    {UserAttributeCollectionEntry.index} INT UNSIGNED NOT NULL,
                    {UserAttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {UserAttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({UserAttributeCollectionEntry.attribute_id})
                        REFERENCES {TaskAttribute}({TaskAttribute.id})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {UserAttributeCollectionEntry.attribute_id},
                        {UserAttributeCollectionEntry.norm_slot}
                    ),
                    UNIQUE (
                        {UserAttributeCollectionEntry.attribute_id},
                        {UserAttributeCollectionEntry.index}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeCollectionEntryAlias} (
                    {UserAttributeCollectionEntryAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeCollectionEntryAlias.attribute_id} INT NOT NULL,
                    {UserAttributeCollectionEntryAlias.attribute_collection_entry_id} INT NOT NULL,
                    {UserAttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {UserAttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({UserAttributeCollectionEntryAlias.attribute_collection_entry_id})
                        REFERENCES {UserAttributeCollectionEntry}({UserAttributeCollectionEntry.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeCollectionEntryAlias.attribute_id})
                        REFERENCES {UserAttribute}({UserAttribute.id})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {UserAttributeCollectionEntryAlias.attribute_id},
                        {UserAttributeCollectionEntryAlias.norm_alias}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {Task} (
                    {Task.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {Task.list_id} INT NOT NULL,
                    {Task.norm_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                    {Task.slot_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                    FOREIGN KEY ({Task.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({Task.list_id}, {Task.norm_name})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAlias} (
                    {TaskAlias.id} INT AUTO_INCREMENT PRIMARY KEY,
                    {TaskAlias.task_id} INT NOT NULL,
                    {TaskAlias.list_id} INT NOT NULL,
                    {TaskAlias.norm_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                    {TaskAlias.slot_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                    FOREIGN KEY ({TaskAlias.task_id})
                        REFERENCES {Task}({Task.id})
                        ON DELETE CASCADE,

                    FOREIGN KEY ({TaskAlias.list_id})
                        REFERENCES {List}({List.id})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAlias.list_id}, {TaskAlias.norm_alias})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeTaskValue} (
                    {TaskAttributeTaskValue.task_id} INT NOT NULL,
                    {TaskAttributeTaskValue.attribute_id} INT NOT NULL,
                    {TaskAttributeTaskValue.index} TINYINT UNSIGNED NOT NULL,
                    {TaskAttributeTaskValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    PRIMARY KEY (
                        {TaskAttributeTaskValue.task_id}, 
                        {TaskAttributeTaskValue.attribute_id},
                        {TaskAttributeTaskValue.index}
                    ),
                    
                    FOREIGN KEY ({TaskAttributeTaskValue.task_id})
                        REFERENCES {Task}({Task.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskAttributeTaskValue.attribute_id})
                        REFERENCES {TaskAttribute}({TaskAttribute.id})
                        ON DELETE CASCADE
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeTaskValue} (
                    {UserAttributeTaskValue.user_id} BIGINT UNSIGNED NOT NULL,
                    {UserAttributeTaskValue.task_id} INT NOT NULL,
                    {UserAttributeTaskValue.attribute_id} INT NOT NULL,
                    {UserAttributeTaskValue.index} TINYINT UNSIGNED NOT NULL,
                    {UserAttributeTaskValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    PRIMARY KEY (
                        {UserAttributeTaskValue.user_id},
                        {UserAttributeTaskValue.task_id}, 
                        {UserAttributeTaskValue.attribute_id},
                        {UserAttributeTaskValue.index}
                    ),

                    FOREIGN KEY ({UserAttributeTaskValue.user_id})
                        REFERENCES {JumpediaUser}({JumpediaUser.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeTaskValue.task_id})
                        REFERENCES {Task}({Task.id})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeTaskValue.attribute_id})
                        REFERENCES {UserAttribute}({UserAttribute.id})
                        ON DELETE CASCADE
                )
            """
            )
        except Exception as e:
            try:
                c.raw_execute(
                    f"""
                    DROP DATABASE `{j.connector.database_name}`
                """
                )
            finally:
                raise e

        print("Jumpedia database successfully created!")
