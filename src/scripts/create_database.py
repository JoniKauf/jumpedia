import typing as t

import mariadb

from _adapters import interaction
from structures import db
from structures.jumpedia import Jumpedia
from utils import orm, secret


def create_database(
    j: Jumpedia,
    conn_data: secret.DatabaseConnectionData,
    get_root_meta_c: t.Callable[[], orm.Cursor],
) -> None:
    import time

    c = get_root_meta_c()
    c.raw_execute("SHOW SCHEMAS")

    rows = c.raw_fetchall()

    for row in rows:
        if conn_data["db"] in row.values():
            print("Database exists!")
            return

    if (
        input("Jumpedia database does NOT exist!\nEnter 'yes' to create new one: ")
        != "yes"
    ):
        print("Aborted")
        exit()
        return

    c.raw_execute(
        f"""
        CREATE DATABASE {conn_data["db"]}
        CHARACTER SET utf8mb4 
        COLLATE utf8mb4_bin
    """
    )

    c.raw_execute(
        f"""
        CREATE USER '{conn_data['user']}'@'%' IDENTIFIED BY '{conn_data['password'].replace("'", "''")}';
        """
    )

    c.raw_execute(
        f"""
        GRANT SELECT, INSERT, UPDATE, DELETE ON `{conn_data['db']}`.* TO '{conn_data['user']}'@'%'
        """
    )

    from structures import attribute
    from structures.attribute.slot_str import SLOT_TYPES
    from structures.list import Kind

    c.raw_execute(f"""USE {conn_data['db']}""")

    try:
        c.raw_execute(
            f"""
            CREATE TABLE {db.Community} (
                {db.Community.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.Community.norm_name} VARCHAR({j.limits['community_name_length_max']}) UNIQUE NOT NULL,
                {db.Community.real_name} VARCHAR({j.limits['community_name_length_max']}) UNIQUE NOT NULL,
                {db.Community.default_selected_list_id} INT UNSIGNED DEFAULT NULL,
                {db.Community.limits} JSON NOT NULL
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.Server} (
                {db.Server.id} BIGINT UNSIGNED PRIMARY KEY,
                {db.Server.community_id} INT UNSIGNED NOT NULL,

                FOREIGN KEY ({db.Server.community_id.unqualified}) 
                    REFERENCES {db.Community}({db.Community.id.unqualified})
                    ON DELETE CASCADE
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.List} (
                {db.List.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.List.community_id} INT UNSIGNED NOT NULL,
                {db.List.norm_name} VARCHAR({j.limits['list_name_length_max']}) NOT NULL,
                {db.List.real_name} VARCHAR({j.limits['list_name_length_max']}) NOT NULL,

                FOREIGN KEY ({db.List.community_id.unqualified})
                    REFERENCES {db.Community}({db.Community.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({db.List.community_id.unqualified}, {db.List.norm_name.unqualified})
            )
        """
        )

        c.raw_execute(
            f"""
            ALTER TABLE {db.Community}
            ADD CONSTRAINT fk_community_default_list
            FOREIGN KEY ({db.Community.default_selected_list_id.unqualified})
                REFERENCES {db.List}({db.List.id.unqualified})
                ON DELETE SET NULL
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.JumpediaUser} (
                {db.JumpediaUser.id} BIGINT UNSIGNED PRIMARY KEY,
                {db.JumpediaUser.norm_name} VARCHAR({32}) NOT NULL,
                {db.JumpediaUser.raw_name} VARCHAR({32}) NOT NULL,
                {db.JumpediaUser.power} INT NOT NULL
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.CommunityUser} (
                {db.CommunityUser.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.CommunityUser.community_id} INT UNSIGNED NOT NULL,
                {db.CommunityUser.jumpedia_user_id} BIGINT UNSIGNED NOT NULL,
                {db.CommunityUser.power} INT NOT NULL,
                {db.CommunityUser.selected_list_id} INT UNSIGNED,

                FOREIGN KEY ({db.CommunityUser.community_id.unqualified})
                    REFERENCES {db.Community}({db.Community.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUser.jumpedia_user_id.unqualified})
                    REFERENCES {db.JumpediaUser}({db.JumpediaUser.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUser.selected_list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE SET NULL
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.Attribute} (
                {db.Attribute.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.Attribute.list_id} INT UNSIGNED NOT NULL,
                {db.Attribute.type_id} TINYINT UNSIGNED NOT NULL,
                {db.Attribute.kind} TINYINT UNSIGNED,
                {db.Attribute.norm_name} VARCHAR({j.limits['attribute_syn_length_max']}) NOT NULL,
                {db.Attribute.real_name} VARCHAR({j.limits['attribute_syn_length_max']}) NOT NULL,
                {db.Attribute.slot_type} TINYINT UNSIGNED NOT NULL,
                {db.Attribute.position} TINYINT UNSIGNED NOT NULL,
                {db.Attribute.min_slot_count} TINYINT UNSIGNED NOT NULL,
                {db.Attribute.max_slot_count} TINYINT UNSIGNED NOT NULL,

                FOREIGN KEY ({db.Attribute.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({db.Attribute.list_id.unqualified}, {db.Attribute.kind.unqualified}),
                UNIQUE ({db.Attribute.list_id.unqualified}, {db.Attribute.norm_name.unqualified}),
                UNIQUE ({db.Attribute.list_id.unqualified}, {db.Attribute.position.unqualified}),

                CHECK ({db.Attribute.type_id.unqualified} < {len(attribute.ALL_ATTRIBUTE_TYPES)}),
                CHECK ({db.Attribute.kind.unqualified} IS NULL OR {db.Attribute.kind.unqualified} <= {max(Kind._value2member_map_)}),
                CHECK ({db.Attribute.slot_type.unqualified} < {len(SLOT_TYPES)})
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.AttributeAlias} (
                {db.AttributeAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.AttributeAlias.attribute_id} INT UNSIGNED NOT NULL,
                {db.AttributeAlias.list_id} INT UNSIGNED NOT NULL,
                {db.AttributeAlias.attribute_type_id} TINYINT UNSIGNED NOT NULL,
                {db.AttributeAlias.norm_alias} VARCHAR({j.limits['attribute_syn_length_max']}) NOT NULL,
                {db.AttributeAlias.real_alias} VARCHAR({j.limits['attribute_syn_length_max']}) NOT NULL,

                FOREIGN KEY ({db.AttributeAlias.attribute_id.unqualified})
                    REFERENCES {db.Attribute}({db.Attribute.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.AttributeAlias.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({db.AttributeAlias.list_id.unqualified}, {db.AttributeAlias.norm_alias.unqualified}),

                CHECK ({db.AttributeAlias.attribute_type_id.unqualified} < {len(attribute.ALL_ATTRIBUTE_TYPES)})
            )
        """
        )

        from structures.attribute import slot_str

        c.raw_execute(
            f"""
            CREATE TABLE {db.AttributeCollectionEntry} (
                {db.AttributeCollectionEntry.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.AttributeCollectionEntry.attribute_id} INT UNSIGNED NOT NULL,
                {db.AttributeCollectionEntry.index} TINYINT UNSIGNED NOT NULL,
                {db.AttributeCollectionEntry.norm_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                {db.AttributeCollectionEntry.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({db.AttributeCollectionEntry.attribute_id.unqualified})
                    REFERENCES {db.Attribute}({db.Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {db.AttributeCollectionEntry.attribute_id.unqualified},
                    {db.AttributeCollectionEntry.norm_slot.unqualified}
                ),
                UNIQUE (
                    {db.AttributeCollectionEntry.attribute_id.unqualified},
                    {db.AttributeCollectionEntry.index.unqualified}
                )
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.AttributeCollectionEntryAlias} (
                {db.AttributeCollectionEntryAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.AttributeCollectionEntryAlias.attribute_id} INT UNSIGNED NOT NULL,
                {db.AttributeCollectionEntryAlias.attribute_collection_entry_id} INT UNSIGNED NOT NULL,
                {db.AttributeCollectionEntryAlias.norm_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,
                {db.AttributeCollectionEntryAlias.slot_alias} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({db.AttributeCollectionEntryAlias.attribute_collection_entry_id.unqualified})
                    REFERENCES {db.AttributeCollectionEntry}({db.AttributeCollectionEntry.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.AttributeCollectionEntryAlias.attribute_id.unqualified})
                    REFERENCES {db.Attribute}({db.Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {db.AttributeCollectionEntryAlias.attribute_id.unqualified},
                    {db.AttributeCollectionEntryAlias.norm_alias.unqualified}
                )
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.Task} (
                {db.Task.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.Task.list_id} INT UNSIGNED NOT NULL,
                {db.Task.norm_name} VARCHAR({j.limits['attribute_task_value_slot_length_max']}) NOT NULL,
                {db.Task.slot_name} VARCHAR({j.limits['attribute_task_value_slot_length_max']}) NOT NULL,

                FOREIGN KEY ({db.Task.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({db.Task.list_id.unqualified}, {db.Task.norm_name.unqualified})
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.TaskAlias} (
                {db.TaskAlias.id} INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.TaskAlias.task_id} INT UNSIGNED NOT NULL,
                {db.TaskAlias.list_id} INT UNSIGNED NOT NULL,
                {db.TaskAlias.norm_alias} VARCHAR({j.limits['attribute_task_value_slot_length_max']}) NOT NULL,
                {db.TaskAlias.slot_alias} VARCHAR({j.limits['attribute_task_value_slot_length_max']}) NOT NULL,

                FOREIGN KEY ({db.TaskAlias.task_id.unqualified})
                    REFERENCES {db.Task}({db.Task.id.unqualified})
                    ON DELETE CASCADE,

                FOREIGN KEY ({db.TaskAlias.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE ({db.TaskAlias.list_id.unqualified}, {db.TaskAlias.norm_alias.unqualified})
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.TaskAttributeValue} (
                {db.TaskAttributeValue.list_id} INT UNSIGNED NOT NULL,
                {db.TaskAttributeValue.task_id} INT UNSIGNED NOT NULL,
                {db.TaskAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                {db.TaskAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                {db.TaskAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                PRIMARY KEY (
                    {db.TaskAttributeValue.list_id.unqualified},
                    {db.TaskAttributeValue.task_id.unqualified}, 
                    {db.TaskAttributeValue.attribute_id.unqualified},
                    {db.TaskAttributeValue.index.unqualified}
                ),
                
                FOREIGN KEY ({db.TaskAttributeValue.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.TaskAttributeValue.task_id.unqualified})
                    REFERENCES {db.Task}({db.Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.TaskAttributeValue.attribute_id.unqualified})
                    REFERENCES {db.Attribute}({db.Attribute.id.unqualified})
                    ON DELETE CASCADE
            )
        """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.CommunityUserTask} (
                {db.CommunityUserTask.id} BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.CommunityUserTask.list_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTask.community_user_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTask.task_id} INT UNSIGNED NOT NULL,

                FOREIGN KEY ({db.CommunityUserTask.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTask.task_id.unqualified})
                    REFERENCES {db.Task}({db.Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTask.community_user_id.unqualified})
                    REFERENCES {db.CommunityUser}({db.CommunityUser.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {db.CommunityUserTask.list_id.unqualified}, 
                    {db.CommunityUserTask.task_id.unqualified},
                    {db.CommunityUserTask.community_user_id.unqualified}
                )
            )
            """
        )

        c.raw_execute(
            f"""
            CREATE TABLE {db.CommunityUserTaskAttributeValue} (
                {db.CommunityUserTaskAttributeValue.id} BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                {db.CommunityUserTaskAttributeValue.list_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.community_user_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.community_user_task_id} BIGINT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.task_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.attribute_id} INT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.index} TINYINT UNSIGNED NOT NULL,
                {db.CommunityUserTaskAttributeValue.slot_slot} VARCHAR({slot_str.STR_MAX_LEN}) NOT NULL,

                FOREIGN KEY ({db.CommunityUserTaskAttributeValue.community_user_task_id.unqualified})
                    REFERENCES {db.CommunityUserTask}({db.CommunityUserTask.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTaskAttributeValue.list_id.unqualified})
                    REFERENCES {db.List}({db.List.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTaskAttributeValue.task_id.unqualified})
                    REFERENCES {db.Task}({db.Task.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTaskAttributeValue.community_user_id.unqualified})
                    REFERENCES {db.CommunityUser}({db.CommunityUser.id.unqualified})
                    ON DELETE CASCADE,
                FOREIGN KEY ({db.CommunityUserTaskAttributeValue.attribute_id.unqualified})
                    REFERENCES {db.Attribute}({db.Attribute.id.unqualified})
                    ON DELETE CASCADE,

                UNIQUE (
                    {db.CommunityUserTaskAttributeValue.community_user_task_id.unqualified},
                    {db.CommunityUserTaskAttributeValue.attribute_id.unqualified},
                    {db.CommunityUserTaskAttributeValue.index.unqualified}
                ),
                UNIQUE (
                    {db.CommunityUserTaskAttributeValue.list_id.unqualified},
                    {db.CommunityUserTaskAttributeValue.community_user_id.unqualified}, 
                    {db.CommunityUserTaskAttributeValue.task_id.unqualified},
                    {db.CommunityUserTaskAttributeValue.attribute_id.unqualified},
                    {db.CommunityUserTaskAttributeValue.index.unqualified}
                )
            )
        """
        )
    except Exception:
        print("Error! Dropping database in 5 seconds...")
        time.sleep(5)

        c.raw_execute(f"DROP DATABASE {conn_data["db"]}")
        c.commit()
        raise

    print("Jumpedia database successfully created!")

    c.commit()
    c._close_connection()


if __name__ == "__main__":
    conn_data = secret.listen().DATABASE_CONNECTION_DATA

    create_database(
        interaction.THE_ONE_PIECE,
        conn_data,
        lambda: orm.Cursor(
            conn := mariadb.connect(
                **conn_data
                | {
                    "db": None,
                    "user": "root",
                    "password": input("Enter mariadb root password: "),
                }
            ),
            conn.cursor(dictionary=True),
        ),
    )
