import types
import typing as t

from utils.orm import *
from utils.text import NormStr, RealStr

if t.TYPE_CHECKING:
    from .attribute.slot_str import SlotStr
    from .jumpedia import Jumpedia
else:
    SlotStr = RealStr


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

    @column(str)
    def limits(self):
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
    def id(self):
        pass

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

    @column(int)
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


class TaskTaskAttributeValue(Model, table_name=SNAKE):
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


class ListTaskCommunityUser(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def community_user_id(self):
        pass


class TaskUserAttributeValue(Model, table_name=SNAKE):
    @column(int)
    def list_task_community_user_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def task_id(self):
        pass

    @column(int)
    def community_user_id(self):
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
type AnyTaskAttributeValueTable = TaskTaskAttributeValue | TaskUserAttributeValue


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


class AbstractTaskAttributeValueTable(
    TaskTaskAttributeValue, TaskUserAttributeValue, table_name=""
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
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_bin
        """
        )

    with j.connector.cursor() as c:
        try:
            c.raw_execute(
                f"""
                CREATE TABLE {Community} (
                    {Community.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {Community.norm_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                    {Community.real_name} VARCHAR({j.limits.community_name_length_max}) UNIQUE NOT NULL,
                    {Community.default_selected_list_id} INT UNSIGNED DEFAULT NULL,
                    {Community.limits} JSON NOT NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {Server} (
                    {Server.id} BIGINT UNSIGNED PRIMARY KEY,
                    {Server.community_id} INT UNSIGNED NOT NULL,

                    FOREIGN KEY ({Server.community_id.unqualified}) 
                        REFERENCES {Community}({Community.id.unqualified})
                        ON DELETE CASCADE
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {List} (
                    {List.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {List.community_id} INT UNSIGNED NOT NULL,
                    {List.norm_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,
                    {List.real_name} VARCHAR({j.limits.list_name_length_max}) NOT NULL,

                    FOREIGN KEY ({List.community_id.unqualified})
                        REFERENCES {Community}({Community.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({List.community_id.unqualified}, {List.norm_name.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                ALTER TABLE {Community}
                ADD CONSTRAINT fk_community_default_list
                FOREIGN KEY ({Community.default_selected_list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE SET NULL
            """
            )

            from . import user

            c.raw_execute(
                f"""
                CREATE TABLE {JumpediaUser} (
                    {JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                    {JumpediaUser.norm_name} VARCHAR({32}) NOT NULL,
                    {JumpediaUser.raw_name} VARCHAR({32}) NOT NULL,
                    {JumpediaUser.power} INT NOT NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {CommunityUser} (
                    {CommunityUser.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {CommunityUser.community_id} INT UNSIGNED NOT NULL,
                    {CommunityUser.jumpedia_user_id} BIGINT UNSIGNED NOT NULL,
                    {CommunityUser.power} INT NOT NULL,
                    {CommunityUser.selected_list_id} INT UNSIGNED,

                    FOREIGN KEY ({CommunityUser.community_id.unqualified})
                        REFERENCES {Community}({Community.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({CommunityUser.jumpedia_user_id.unqualified})
                        REFERENCES {JumpediaUser}({JumpediaUser.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({CommunityUser.selected_list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE SET NULL
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {StaticAttribute} (
                    {StaticAttribute.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {StaticAttribute.list_id} INT UNSIGNED NOT NULL,
                    {StaticAttribute.kind} TINYINT NOT NULL,
                    {StaticAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttribute.slot_type} TINYINT UNSIGNED NOT NULL,
                    {StaticAttribute.position} TINYINT UNSIGNED NOT NULL,
                    {StaticAttribute.min_slots} TINYINT UNSIGNED NOT NULL,
                    {StaticAttribute.max_slots} TINYINT UNSIGNED NOT NULL,

                    FOREIGN KEY ({StaticAttribute.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({StaticAttribute.list_id.unqualified}, {StaticAttribute.kind.unqualified}),
                    UNIQUE ({StaticAttribute.list_id.unqualified}, {StaticAttribute.norm_name.unqualified}),
                    UNIQUE ({StaticAttribute.list_id.unqualified}, {StaticAttribute.position.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {StaticAttributeAlias} (
                    {StaticAttributeAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {StaticAttributeAlias.attribute_id} INT UNSIGNED NOT NULL,
                    {StaticAttributeAlias.list_id} INT UNSIGNED NOT NULL,
                    {StaticAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {StaticAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({StaticAttributeAlias.attribute_id.unqualified})
                        REFERENCES {StaticAttribute}({StaticAttribute.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({StaticAttributeAlias.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({StaticAttributeAlias.list_id.unqualified}, {StaticAttributeAlias.norm_alias.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttribute} (
                    {TaskAttribute.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttribute.list_id} INT UNSIGNED NOT NULL,
                    {TaskAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttribute.slot_type} TINYINT UNSIGNED NOT NULL,
                    {TaskAttribute.position} TINYINT UNSIGNED NOT NULL,
                    {TaskAttribute.min_slots} TINYINT UNSIGNED NOT NULL,
                    {TaskAttribute.max_slots} TINYINT UNSIGNED NOT NULL,

                    FOREIGN KEY ({TaskAttribute.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAttribute.list_id.unqualified}, {TaskAttribute.norm_name.unqualified}),
                    UNIQUE ({TaskAttribute.list_id.unqualified}, {TaskAttribute.position.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeAlias} (
                    {TaskAttributeAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeAlias.attribute_id} INT UNSIGNED NOT NULL,
                    {TaskAttributeAlias.list_id} INT UNSIGNED NOT NULL,
                    {TaskAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {TaskAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeAlias.attribute_id.unqualified})
                        REFERENCES {TaskAttribute}({TaskAttribute.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskAttributeAlias.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAttributeAlias.list_id.unqualified}, {TaskAttributeAlias.norm_alias.unqualified})
                )
            """
            )

            from .attribute import slot_str

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeCollectionEntry} (
                    {TaskAttributeCollectionEntry.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeCollectionEntry.attribute_id} INT UNSIGNED NOT NULL,
                    {TaskAttributeCollectionEntry.index} INT UNSIGNED NOT NULL,
                    {TaskAttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {TaskAttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeCollectionEntry.attribute_id.unqualified})
                        REFERENCES {TaskAttribute}({TaskAttribute.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {TaskAttributeCollectionEntry.attribute_id.unqualified},
                        {TaskAttributeCollectionEntry.norm_slot.unqualified}
                    ),
                    UNIQUE (
                        {TaskAttributeCollectionEntry.attribute_id.unqualified},
                        {TaskAttributeCollectionEntry.index.unqualified}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAttributeCollectionEntryAlias} (
                    {TaskAttributeCollectionEntryAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {TaskAttributeCollectionEntryAlias.attribute_id} INT UNSIGNED NOT NULL,
                    {TaskAttributeCollectionEntryAlias.attribute_collection_entry_id} INT UNSIGNED NOT NULL,
                    {TaskAttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {TaskAttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({TaskAttributeCollectionEntryAlias.attribute_collection_entry_id.unqualified})
                        REFERENCES {TaskAttributeCollectionEntry}({TaskAttributeCollectionEntry.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskAttributeCollectionEntryAlias.attribute_id.unqualified})
                        REFERENCES {TaskAttribute}({TaskAttribute.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {TaskAttributeCollectionEntryAlias.attribute_id.unqualified},
                        {TaskAttributeCollectionEntryAlias.norm_alias.unqualified}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttribute} (
                    {UserAttribute.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {UserAttribute.list_id} INT UNSIGNED NOT NULL,
                    {UserAttribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttribute.slot_type} TINYINT UNSIGNED NOT NULL,
                    {UserAttribute.position} TINYINT UNSIGNED NOT NULL,
                    {UserAttribute.min_slots} TINYINT UNSIGNED NOT NULL,
                    {UserAttribute.max_slots} TINYINT UNSIGNED NOT NULL,

                    FOREIGN KEY ({UserAttribute.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({UserAttribute.list_id.unqualified}, {UserAttribute.norm_name.unqualified}),
                    UNIQUE ({UserAttribute.list_id.unqualified}, {UserAttribute.position.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeAlias} (
                    {UserAttributeAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeAlias.attribute_id} INT UNSIGNED NOT NULL,
                    {UserAttributeAlias.list_id} INT UNSIGNED NOT NULL,
                    {UserAttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                    {UserAttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                    FOREIGN KEY ({UserAttributeAlias.attribute_id.unqualified})
                        REFERENCES {UserAttribute}({UserAttribute.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeAlias.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({UserAttributeAlias.list_id.unqualified}, {UserAttributeAlias.norm_alias.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeCollectionEntry} (
                    {UserAttributeCollectionEntry.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeCollectionEntry.attribute_id} INT UNSIGNED NOT NULL,
                    {UserAttributeCollectionEntry.index} INT UNSIGNED NOT NULL,
                    {UserAttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {UserAttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({UserAttributeCollectionEntry.attribute_id.unqualified})
                        REFERENCES {UserAttribute}({UserAttribute.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {UserAttributeCollectionEntry.attribute_id.unqualified},
                        {UserAttributeCollectionEntry.norm_slot.unqualified}
                    ),
                    UNIQUE (
                        {UserAttributeCollectionEntry.attribute_id.unqualified},
                        {UserAttributeCollectionEntry.index.unqualified}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {UserAttributeCollectionEntryAlias} (
                    {UserAttributeCollectionEntryAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {UserAttributeCollectionEntryAlias.attribute_id} INT UNSIGNED NOT NULL,
                    {UserAttributeCollectionEntryAlias.attribute_collection_entry_id} INT UNSIGNED NOT NULL,
                    {UserAttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                    {UserAttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    FOREIGN KEY ({UserAttributeCollectionEntryAlias.attribute_collection_entry_id.unqualified})
                        REFERENCES {UserAttributeCollectionEntry}({UserAttributeCollectionEntry.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({UserAttributeCollectionEntryAlias.attribute_id.unqualified})
                        REFERENCES {UserAttribute}({UserAttribute.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {UserAttributeCollectionEntryAlias.attribute_id.unqualified},
                        {UserAttributeCollectionEntryAlias.norm_alias.unqualified}
                    )
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {Task} (
                    {Task.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {Task.list_id} INT UNSIGNED NOT NULL,
                    {Task.norm_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                    {Task.slot_name} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                    FOREIGN KEY ({Task.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({Task.list_id.unqualified}, {Task.norm_name.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskAlias} (
                    {TaskAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {TaskAlias.task_id} INT UNSIGNED NOT NULL,
                    {TaskAlias.list_id} INT UNSIGNED NOT NULL,
                    {TaskAlias.norm_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,
                    {TaskAlias.slot_alias} VARCHAR({j.limits.attribute_task_value_slot_length_max}) NOT NULL,

                    FOREIGN KEY ({TaskAlias.task_id.unqualified})
                        REFERENCES {Task}({Task.id.unqualified})
                        ON DELETE CASCADE,

                    FOREIGN KEY ({TaskAlias.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE ({TaskAlias.list_id.unqualified}, {TaskAlias.norm_alias.unqualified})
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskTaskAttributeValue} (
                    {TaskTaskAttributeValue.list_id} INT UNSIGNED NOT NULL,
                    {TaskTaskAttributeValue.task_id} INT UNSIGNED NOT NULL,
                    {TaskTaskAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                    {TaskTaskAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                    {TaskTaskAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    PRIMARY KEY (
                        {TaskTaskAttributeValue.list_id.unqualified},
                        {TaskTaskAttributeValue.task_id.unqualified}, 
                        {TaskTaskAttributeValue.attribute_id.unqualified},
                        {TaskTaskAttributeValue.index.unqualified}
                    ),
                    
                    FOREIGN KEY ({TaskTaskAttributeValue.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskTaskAttributeValue.task_id.unqualified})
                        REFERENCES {Task}({Task.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskTaskAttributeValue.attribute_id.unqualified})
                        REFERENCES {TaskAttribute}({TaskAttribute.id.unqualified})
                        ON DELETE CASCADE
                )
            """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {ListTaskCommunityUser} (
                    {ListTaskCommunityUser.id} BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    {ListTaskCommunityUser.list_id} INT UNSIGNED NOT NULL,
                    {ListTaskCommunityUser.task_id} INT UNSIGNED NOT NULL,
                    {ListTaskCommunityUser.community_user_id} INT UNSIGNED NOT NULL,

                    FOREIGN KEY ({ListTaskCommunityUser.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({ListTaskCommunityUser.task_id.unqualified})
                        REFERENCES {Task}({Task.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({ListTaskCommunityUser.community_user_id.unqualified})
                        REFERENCES {CommunityUser}({CommunityUser.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {ListTaskCommunityUser.list_id.unqualified}, 
                        {ListTaskCommunityUser.task_id.unqualified},
                        {ListTaskCommunityUser.community_user_id.unqualified}
                    )
                )
                """
            )

            c.raw_execute(
                f"""
                CREATE TABLE {TaskUserAttributeValue} (
                    {TaskUserAttributeValue.list_task_community_user_id} BIGINT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.list_id} INT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.task_id} INT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.community_user_id} INT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                    {TaskUserAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                    PRIMARY KEY (
                        {TaskUserAttributeValue.list_id.unqualified},
                        {TaskUserAttributeValue.task_id.unqualified},
                        {TaskUserAttributeValue.community_user_id.unqualified}, 
                        {TaskUserAttributeValue.attribute_id.unqualified},
                        {TaskUserAttributeValue.index.unqualified}
                    ),

                    FOREIGN KEY ({TaskUserAttributeValue.list_task_community_user_id.unqualified})
                        REFERENCES {ListTaskCommunityUser}({ListTaskCommunityUser.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskUserAttributeValue.list_id.unqualified})
                        REFERENCES {List}({List.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskUserAttributeValue.task_id.unqualified})
                        REFERENCES {Task}({Task.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskUserAttributeValue.community_user_id.unqualified})
                        REFERENCES {CommunityUser}({CommunityUser.id.unqualified})
                        ON DELETE CASCADE,
                    FOREIGN KEY ({TaskUserAttributeValue.attribute_id.unqualified})
                        REFERENCES {UserAttribute}({UserAttribute.id.unqualified})
                        ON DELETE CASCADE,

                    UNIQUE (
                        {TaskUserAttributeValue.list_task_community_user_id.unqualified},
                        {TaskUserAttributeValue.attribute_id.unqualified},
                        {TaskUserAttributeValue.index.unqualified}
                    )
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
            except Exception as e2:
                raise e2

            raise e
        else:
            print("Jumpedia database successfully created!")
