import types
import typing as t

from utils.orm import *

if t.TYPE_CHECKING:
    from .attribute.slot_str import SlotStr
    from .jumpedia import Jumpedia
else:
    SlotStr = RealStr


class Community(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
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

    @column(str)
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

    @column(str)
    def norm_name(self):
        pass

    @column(str)
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


class Attribute(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def type_id(self):
        pass

    @column(str)
    def norm_name(self):
        pass

    @column(str)
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

    @column(int, types.NoneType)
    def kind(self):
        pass


class AttributeAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def attribute_type_id(self):
        pass

    @column(str)
    def norm_alias(self):
        pass

    @column(str)
    def real_alias(self):
        pass


class AttributeCollectionEntry(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(int)
    def index(self):
        pass

    @column(str)
    def norm_slot(self):
        pass

    @column(SlotStr)
    def slot_slot(self):
        pass


class AttributeCollectionEntryAlias(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def attribute_collection_entry_id(self):
        pass

    @column(int)
    def attribute_id(self):
        pass

    @column(str)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


class Task(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(str)
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

    @column(str)
    def norm_alias(self):
        pass

    @column(SlotStr)
    def slot_alias(self):
        pass


class TaskAttributeValue(Model, table_name=SNAKE):
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


class CommunityUserTask(Model, table_name=SNAKE):
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


class CommunityUserTaskAttributeValue(Model, table_name=SNAKE):
    @column(int)
    def id(self):
        pass

    @column(int)
    def community_user_task_id(self):
        pass

    @column(int)
    def list_id(self):
        pass

    @column(int)
    def community_user_id(self):
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


def create_database(
    j: Jumpedia, database_name: str, meta_c: Cursor, get_c: t.Callable[[], Cursor]
) -> None:
    import time

    meta_c.raw_execute("SHOW SCHEMAS")

    rows = meta_c.raw_fetchall()

    for row in rows:
        if database_name.lower() in map(str.lower, row.values()):
            print("Database exists!")
            return

    print("Jumpedia database does NOT exist, creating new in 5 seconds!")

    time.sleep(5)

    meta_c.raw_execute(
        f"""
        CREATE DATABASE {database_name}
        CHARACTER SET utf8mb4 
        COLLATE utf8mb4_bin
    """
    )

    meta_c.commit()
    meta_c._mariadb_cursor.close()
    meta_c._mariadb_connection.close()

    del meta_c

    from structures import attribute
    from structures.attribute.slot_str import SLOT_TYPES
    from structures.list import Kind

    c = get_c()

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
            CREATE TABLE {Attribute} (
                {Attribute.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {Attribute.list_id} INT UNSIGNED NOT NULL,
                {Attribute.type_id} TINYINT UNSIGNED NOT NULL,
                {Attribute.kind} TINYINT UNSIGNED,
                {Attribute.norm_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {Attribute.real_name} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {Attribute.slot_type} TINYINT UNSIGNED NOT NULL,
                {Attribute.position} TINYINT UNSIGNED NOT NULL,
                {Attribute.min_slots} TINYINT UNSIGNED NOT NULL,
                {Attribute.max_slots} TINYINT UNSIGNED NOT NULL,

                FOREIGN KEY ({Attribute.list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({Attribute.list_id.unqualified}, {Attribute.kind.unqualified}),
                UNIQUE ({Attribute.list_id.unqualified}, {Attribute.norm_name.unqualified}),
                UNIQUE ({Attribute.list_id.unqualified}, {Attribute.position.unqualified}),

                CHECK ({Attribute.type_id.unqualified} < {len(attribute.ALL_ATTRIBUTE_TYPES)}),
                CHECK ({Attribute.kind.unqualified} IS NULL OR {Attribute.kind.unqualified} <= {max(Kind._value2member_map_)}),
                CHECK ({Attribute.slot_type.unqualified} < {len(SLOT_TYPES)})
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {AttributeAlias} (
                {AttributeAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {AttributeAlias.attribute_id} INT UNSIGNED NOT NULL,
                {AttributeAlias.list_id} INT UNSIGNED NOT NULL,
                {AttributeAlias.attribute_type_id} TINYINT UNSIGNED NOT NULL,
                {AttributeAlias.norm_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,
                {AttributeAlias.real_alias} VARCHAR({j.limits.attribute_syn_length_max}) NOT NULL,

                FOREIGN KEY ({AttributeAlias.attribute_id.unqualified})
                    REFERENCES {Attribute}({Attribute.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({AttributeAlias.list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({AttributeAlias.list_id.unqualified}, {AttributeAlias.norm_alias.unqualified}),

                CHECK ({AttributeAlias.attribute_type_id.unqualified} < {len(attribute.ALL_ATTRIBUTE_TYPES)})
            )
        """
        )

        from .attribute import slot_str

        c.raw_execute(
            f"""
            CREATE TABLE {AttributeCollectionEntry} (
                {AttributeCollectionEntry.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {AttributeCollectionEntry.attribute_id} INT UNSIGNED NOT NULL,
                {AttributeCollectionEntry.index} TINYINT UNSIGNED NOT NULL,
                {AttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                {AttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({AttributeCollectionEntry.attribute_id.unqualified})
                    REFERENCES {Attribute}({Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {AttributeCollectionEntry.attribute_id.unqualified},
                    {AttributeCollectionEntry.norm_slot.unqualified}
                ),
                UNIQUE (
                    {AttributeCollectionEntry.attribute_id.unqualified},
                    {AttributeCollectionEntry.index.unqualified}
                )
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {AttributeCollectionEntryAlias} (
                {AttributeCollectionEntryAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {AttributeCollectionEntryAlias.attribute_id} INT UNSIGNED NOT NULL,
                {AttributeCollectionEntryAlias.attribute_collection_entry_id} INT UNSIGNED NOT NULL,
                {AttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                {AttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({AttributeCollectionEntryAlias.attribute_collection_entry_id.unqualified})
                    REFERENCES {AttributeCollectionEntry}({AttributeCollectionEntry.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({AttributeCollectionEntryAlias.attribute_id.unqualified})
                    REFERENCES {Attribute}({Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {AttributeCollectionEntryAlias.attribute_id.unqualified},
                    {AttributeCollectionEntryAlias.norm_alias.unqualified}
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
            CREATE TABLE {TaskAttributeValue} (
                {TaskAttributeValue.list_id} INT UNSIGNED NOT NULL,
                {TaskAttributeValue.task_id} INT UNSIGNED NOT NULL,
                {TaskAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                {TaskAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                {TaskAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                PRIMARY KEY (
                    {TaskAttributeValue.list_id.unqualified},
                    {TaskAttributeValue.task_id.unqualified}, 
                    {TaskAttributeValue.attribute_id.unqualified},
                    {TaskAttributeValue.index.unqualified}
                ),
                
                FOREIGN KEY ({TaskAttributeValue.list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({TaskAttributeValue.task_id.unqualified})
                    REFERENCES {Task}({Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({TaskAttributeValue.attribute_id.unqualified})
                    REFERENCES {Attribute}({Attribute.id.unqualified})
                    ON DELETE CASCADE
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {CommunityUserTask} (
                {CommunityUserTask.id} BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {CommunityUserTask.list_id} INT UNSIGNED NOT NULL,
                {CommunityUserTask.community_user_id} INT UNSIGNED NOT NULL,
                {CommunityUserTask.task_id} INT UNSIGNED NOT NULL,

                FOREIGN KEY ({CommunityUserTask.list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTask.task_id.unqualified})
                    REFERENCES {Task}({Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTask.community_user_id.unqualified})
                    REFERENCES {CommunityUser}({CommunityUser.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {CommunityUserTask.list_id.unqualified}, 
                    {CommunityUserTask.task_id.unqualified},
                    {CommunityUserTask.community_user_id.unqualified}
                )
            )
            """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {CommunityUserTaskAttributeValue} (
                {CommunityUserTaskAttributeValue.id} BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {CommunityUserTaskAttributeValue.list_id} INT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.community_user_id} INT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.community_user_task_id} BIGINT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.task_id} INT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                {CommunityUserTaskAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({CommunityUserTaskAttributeValue.community_user_task_id.unqualified})
                    REFERENCES {CommunityUserTask}({CommunityUserTask.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTaskAttributeValue.list_id.unqualified})
                    REFERENCES {List}({List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTaskAttributeValue.task_id.unqualified})
                    REFERENCES {Task}({Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTaskAttributeValue.community_user_id.unqualified})
                    REFERENCES {CommunityUser}({CommunityUser.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({CommunityUserTaskAttributeValue.attribute_id.unqualified})
                    REFERENCES {Attribute}({Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {CommunityUserTaskAttributeValue.community_user_task_id.unqualified},
                    {CommunityUserTaskAttributeValue.attribute_id.unqualified},
                    {CommunityUserTaskAttributeValue.index.unqualified}
                ),
                UNIQUE (
                    {CommunityUserTaskAttributeValue.list_id.unqualified},
                    {CommunityUserTaskAttributeValue.community_user_id.unqualified}, 
                    {CommunityUserTaskAttributeValue.task_id.unqualified},
                    {CommunityUserTaskAttributeValue.attribute_id.unqualified},
                    {CommunityUserTaskAttributeValue.index.unqualified}
                )
            )
        """
        )
    except Exception as e:
        try:
            c.raw_execute(f"""
                DROP DATABASE {database_name}
            """)
        except Exception as e2:
            raise e2

        raise e
    else:
        print("Jumpedia database successfully created!")

    c.commit()
    c._mariadb_cursor.close()