import functools
import itertools
import json
import re

import mariadb
from utils import devtools
from database import queries


from collections import defaultdict
from typing import Any, Hashable, Iterable, Sequence
import trickjump.attributes as attrs
from trickjump.trickjump import Trickjump

@functools.cache
def remap_nested_collection[KT: Hashable, VT](key: KT, data: Iterable[dict[KT, VT]]) -> dict[KT, dict[KT, VT]]:
    result = defaultdict(dict)
    
    for elem in data:
        key_val = elem[key]
        
        for k, v in elem.items():
            result[k][key_val] = v
            
    return result

# Constants 

SERVERS = ["SMO Trickjumping Server", "Database"]
DIFFICULTIES = ["0/10", "0.5/10", "1/10", "1.5/10", "2/10", "2.5/10", "3/10", "3.5/10", "4/10", "4.5/10", "5/10", "5.5/10", "6/10", "6.5/10", "7/10", "7.5/10", "8/10", "8.5/10", "9/10", "9.5/10", "10/10", "Low Elite", "Mid Elite", "High Elite", "Insanity Elite", "God Tier", "Hell Tier", "Unproven"]

with open("scripts/database/data/jump_data.json") as f:
    # tj_name -> attr -> list[values]
    ALL_JUMP_DATA: dict[str, dict[str, Any]] = json.load(f)

with open("scripts/database/data/all_people_filtered.json", encoding='utf-8') as f:
    ALL_PEOPLE_ALIAS_TO_NAME: dict[str, str] = json.load(f)

# attr -> tj_name -> list[values]
ALL_ATTR_DATA: dict[str, dict[str, list[str]]] = remap_nested_collection("name", ALL_JUMP_DATA.values())

# attr -> list[tuple[tj_name, attr_value]]
ALL_ATTR_FLATTENED: dict[str, list[tuple[str, str]]] = {}

for attr, data in ALL_ATTR_DATA.items():
    attr_list = ALL_ATTR_FLATTENED[attr] = []

    for tj_name, values in data.items():
        for v in values:
            attr_list.append((tj_name, v))


CONTRIBUTOR_KEYS = ("finder", "taser", "prover")
AND_PATTERN = re.compile(r", | & | and | - ")

@functools.cache
def ftp_line_to_people(line: str) -> list[str]:
    parts: list[str] = re.split(AND_PATTERN, line)
    return [ALL_PEOPLE_ALIAS_TO_NAME[part] for part in parts]

def join_text(s: str, amount: int, delim: str = ",\n"):
    return delim.join(s for _ in range(amount))


#devtools.time_left(seconds=5, feedback=lambda sec: f"You have {sec:.1f} seconds left to cancel!")

input("WARNING: This will clear the entire database. ARE YOU SURE?")
input("Are you like sure, sure???")

with queries.connected('Jumpedia') as (connection, cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    cursor.execute("SHOW TABLES")
    tables: list[dict[str, str]] = cursor.fetchall()

    for table_data in tables:
        table_name = tuple(table_data.values())[0]
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

    devtools.noob_log("All tables deleted")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(64) UNIQUE NOT NULL
        )
    """)

    # A user is an actual Jumpedia user while a
    # person could be any finder, taser, prover ...
    # A person must exist for a user to be defined
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id BIGINT PRIMARY KEY,
            name VARCHAR(64) NOT NULL,
            rank_power INT NOT NULL DEFAULT 0,
            person_id INT,
            FOREIGN KEY (person_id) REFERENCES person (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(80) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci,
            location JSON NOT NULL,
            difficulty INT NOT NULL,
            type JSON,
            server INT NOT NULL,
            finder JSON,
            taser JSON,
            prover JSON,
            found_at DATETIME,
            tased_at DATETIME,
            proven_at DATETIME,
            link JSON NOT NULL,
            info VARCHAR(2048),
            tag JSON,
            thumbnail VARCHAR(512)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_trickjump (
            trickjump_id INT NOT NULL,
            user_id BIGINT NOT NULL,
            proof VARCHAR(512),
            given_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (trickjump_id, user_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
        )
    """)

    devtools.noob_log("All new tables created")

    ATTR_INFO = Trickjump.field_value_type_info()
    all_jump_data_fixed: list[list[Any]] = []
    for tj_name, tj_data in ALL_JUMP_DATA.items():
        values: list[Any] = []
        
        for cls, is_multi in ATTR_INFO.items():
            attr = get_attr = cls.NAME

            if attr == 'difficulty':
                get_attr = 'diff'
            elif attr == 'info':
                get_attr = 'extra'
            elif attr == 'link':
                get_attr = 'links'

            v = tj_data.get(get_attr, None)

            if attr == 'info' and v is not None:
                v = '\n'.join(v)
            elif attr in ('location',):
                v = [attrs.name_to_cls(attr).get(elem).id for elem in v]  # type: ignore
            elif attr in ('difficulty', 'server'):
                v = attrs.name_to_cls(attr).get(v).id  # type: ignore

            if is_multi and attr != 'info':
                v = json.dumps(v)

            values.append(v)
        
        all_jump_data_fixed.append(values)
    
    query = f"""
        INSERT INTO trickjump 
        ({', '.join(cls.NAME for cls in ATTR_INFO.keys())})
        VALUES
        {join_text(f"({', '.join("?" for _ in ATTR_INFO)})", len(ALL_JUMP_DATA))}
    """

    devtools.noob_log("Trickjump insert query made")
    
    cursor.execute(query, tuple(elem for lst in all_jump_data_fixed for elem in lst))

    devtools.noob_log("All data inserted")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    connection.commit()

devtools.noob_log("All changes committed")