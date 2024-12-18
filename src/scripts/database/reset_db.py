import json
import re
from utils import devtools
from database import queries
from utils.better_inbuilts import BetterSet

SERVERS = ["SMO Trickjumping Server", "Database"]
DIFFICULTIES = ["0/10", "0.5/10", "1/10", "1.5/10", "2/10", "2.5/10", "3/10", "3.5/10", "4/10", "4.5/10", "5/10", "5.5/10", "6/10", "6.5/10", "7/10", "7.5/10", "8/10", "8.5/10", "9/10", "9.5/10", "10/10", "Low Elite", "Mid Elite", "High Elite", "Insanity Elite", "God Tier", "Hell Tier", "Unproven"]

class Counter:
    def __init__(self, start: int = 0, step: int = 1):
        self.n = self.start = start
        self.step = step

    def next(self) -> int:
        ret = self.n
        self.n += self.step
        return ret
    
    def __call__(self) -> int:
        return self.next()

    def reset(self) -> None:
        self.n = self.start


devtools.time_left(seconds=5, feedback=lambda sec: f"You have {sec:.1f} seconds left to cancel!")

input("WARNING: This will clear the entire database. ARE YOU SURE?")
input("Are you like sure, sure???")

with queries.connected() as (connection, cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    cursor.execute("SHOW TABLES")
    tables: list[dict[str, str]] = cursor.fetchall()

    for table_data in tables:
        table_name = tuple(table_data.values())[0]
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

    devtools.noob_log("All tables deleted")

    # A table should only be suffixed with "_junction" if the table is
    # only made of the ids to junction. Any further functionality gets 
    # its own name anyway. This way we avoid having multiple tables
    # with the same name if we follow a convention.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            sort_value INT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_alias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alias VARCHAR(100) UNIQUE NOT NULL,
            location_id INT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_outer_junction (
            location_id INT NOT NULL,
            outer_id INT NOT NULL,
            PRIMARY KEY (location_id, outer_id),
            FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
            FOREIGN KEY (outer_id) REFERENCES location (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_tag (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tag VARCHAR(32) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_tag_junction (
            location_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (location_id, tag_id),
            FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
            FOREIGN KEY (tag_id) REFERENCES location_tag (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tier (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(16) UNIQUE NOT NULL,
            sort_value INT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tier_alias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alias VARCHAR(16) UNIQUE NOT NULL,
            tier_id INT NOT NULL,
            FOREIGN KEY (tier_id) REFERENCES tier (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS difficulty (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(16) UNIQUE NOT NULL,
            sort_value INT UNIQUE NOT NULL,
            missing BOOL NOT NULL DEFAULT TRUE,
            tier_id INT NOT NULL,
            FOREIGN KEY (tier_id) REFERENCES tier (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS difficulty_alias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            difficulty_id INT NOT NULL,
            alias VARCHAR(16) UNIQUE NOT NULL,
            FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS type (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(32) UNIQUE,
            sort_value INT UNIQUE NOT NULL,
            description VARCHAR(512)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS type_alias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alias VARCHAR(100) UNIQUE NOT NULL,
            type_id INT NOT NULL,
            FOREIGN KEY (type_id) REFERENCES type (id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(32) UNIQUE NOT NULL,
            sort_value INT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_alias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alias VARCHAR(100) UNIQUE NOT NULL,
            server_id INT NOT NULL,  
            FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE CASCADE
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS link (
            id INT AUTO_INCREMENT PRIMARY KEY,
            link VARCHAR(512) UNIQUE NOT NULL,
            author INT NULL,
            FOREIGN KEY (author) REFERENCES person (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            text VARCHAR(1024) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tag (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tag VARCHAR(32) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thumbnail (
            id INT AUTO_INCREMENT PRIMARY KEY,
            link VARCHAR(512) UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            text VARCHAR(2048) UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(64) UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `rank` (
            power INT PRIMARY KEY,
            name VARCHAR(16) COLLATE utf8mb4_general1400_as_ci
        )
    """)

    # A user is an actual Jumpedia user while a
    # person could be any finder, taser, prover ...
    # A person must exist for a user to be defined
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id BIGINT PRIMARY KEY,
            custom_name VARCHAR(64) NOT NULL,
            person_id INT NOT NULL,
            rank_power INT NOT NULL DEFAULT 0,
            FOREIGN KEY (person_id) REFERENCES person (id),
            FOREIGN KEY (rank_power) REFERENCES `rank` (power)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(80) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci,
            difficulty_id INT NOT NULL,
            found_at DATETIME NULL,
            tased_at DATETIME NULL,
            proven_at DATETIME NULL,
            server_id INT NOT NULL,
            info_id INT NULL,
            thumbnail_id INT NULL,
            FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE RESTRICT,
            FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE RESTRICT,
            FOREIGN KEY (info_id) REFERENCES info (id) ON DELETE RESTRICT,
            FOREIGN KEY (thumbnail_id) REFERENCES thumbnail (id) ON DELETE SET NULL
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


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_contributor (
            trickjump_id INT NOT NULL,
            person_id INT NOT NULL,
            contribution BIT(3),
            PRIMARY KEY (trickjump_id, person_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_location_junction (
            trickjump_id INT NOT NULL,
            location_id INT NOT NULL,
            PRIMARY KEY (trickjump_id, location_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_type_junction (
            trickjump_id INT NOT NULL,
            type_id INT NOT NULL,
            PRIMARY KEY (trickjump_id, type_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (type_id) REFERENCES type (id) ON DELETE RESTRICT
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_tag_junction (
            trickjump_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (trickjump_id, tag_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_link_junction (
            trickjump_id INT NOT NULL,
            link_id INT NOT NULL,
            PRIMARY KEY (trickjump_id, link_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (link_id) REFERENCES link (id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trickjump_info_junction (
            trickjump_id INT NOT NULL,
            info_id INT NOT NULL,
            PRIMARY KEY (trickjump_id, info_id),
            FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
            FOREIGN KEY (info_id) REFERENCES info (id) ON DELETE RESTRICT
        )
    """)

    devtools.noob_log("All new tables created")

    cursor.execute(f"""
        INSERT INTO tier (name, sort_value) VALUES
        ('Practice Tier', ?),
        ('Beginner', ?),
        ('Intermediate', ?),
        ('Advanced', ?),
        ('Expert', ?),
        ('Master', ?),
        ('Low Elite', ?),
        ('Mid Elite', ?),
        ('High Elite', ?),
        ('Insanity Elite', ?),
        ('God Tier', ?),
        ('Hell Tier', ?),
        ('Unproven', ?)
    """, tuple(i for i in range(13)))

    cursor.execute("""
        INSERT INTO tier_alias (alias, tier_id) VALUES
        ('Practice', (SELECT id FROM tier WHERE name = 'Practice Tier')),
        ('Beginner', (SELECT id FROM tier WHERE name = 'Beginner')),
        ('Intermediate', (SELECT id FROM tier WHERE name = 'Intermediate')),
        ('Advanced', (SELECT id FROM tier WHERE name = 'Advanced')),
        ('Expert', (SELECT id FROM tier WHERE name = 'Expert')),
        ('Master', (SELECT id FROM tier WHERE name = 'Master')),
        ('Low', (SELECT id FROM tier WHERE name = 'Low Elite')),
        ('Mid', (SELECT id FROM tier WHERE name = 'Mid Elite')),
        ('High', (SELECT id FROM tier WHERE name = 'High Elite')),
        ('Insanity', (SELECT id FROM tier WHERE name = 'Insanity Elite')),
        ('God', (SELECT id FROM tier WHERE name = 'God Tier')),
        ('Hell', (SELECT id FROM tier WHERE name = 'Hell Tier'))
    """)

    cursor.execute(f"""
        INSERT INTO difficulty (name, sort_value, tier_id) VALUES
        ('0/10', ?, (SELECT id FROM tier WHERE name = 'Practice Tier')),
        ('0.5/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('1/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('1.5/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('2/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('2.5/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('3/10', ?, (SELECT id FROM tier WHERE name = 'Beginner')),
        ('3.5/10', ?, (SELECT id FROM tier WHERE name = 'Intermediate')),
        ('4/10', ?, (SELECT id FROM tier WHERE name = 'Intermediate')),
        ('4.5/10', ?, (SELECT id FROM tier WHERE name = 'Intermediate')),
        ('5/10', ?, (SELECT id FROM tier WHERE name = 'Intermediate')),
        ('5.5/10', ?, (SELECT id FROM tier WHERE name = 'Advanced')),
        ('6/10', ?, (SELECT id FROM tier WHERE name = 'Advanced')),
        ('6.5/10', ?, (SELECT id FROM tier WHERE name = 'Advanced')),
        ('7/10', ?, (SELECT id FROM tier WHERE name = 'Expert')),
        ('7.5/10', ?, (SELECT id FROM tier WHERE name = 'Expert')),
        ('8/10', ?, (SELECT id FROM tier WHERE name = 'Expert')),
        ('8.5/10', ?, (SELECT id FROM tier WHERE name = 'Master')),
        ('9/10', ?, (SELECT id FROM tier WHERE name = 'Master')),
        ('9.5/10', ?, (SELECT id FROM tier WHERE name = 'Master')),
        ('10/10', ?, (SELECT id FROM tier WHERE name = 'Master')),
        ('Low Elite', ?, (SELECT id FROM tier WHERE name = 'Low Elite')),
        ('Mid Elite', ?, (SELECT id FROM tier WHERE name = 'Mid Elite')),
        ('High Elite', ?, (SELECT id FROM tier WHERE name = 'High Elite')),
        ('Insanity Elite', ?, (SELECT id FROM tier WHERE name = 'Insanity Elite')),
        ('God Tier', ?, (SELECT id FROM tier WHERE name = 'God Tier')),
        ('Hell Tier', ?, (SELECT id FROM tier WHERE name = 'Hell Tier')),
        ('Unproven', ?, (SELECT id FROM tier WHERE name = 'Unproven'))
    """, tuple(i for i in range(28)))

    cursor.execute("""
        INSERT INTO difficulty_alias (alias, difficulty_id) VALUES
        ('0', (SELECT id FROM difficulty WHERE name = '0/10')),
        ('.5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        (',5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        ('0.5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        ('0,5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        ('.5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        (',5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        ('0,5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
        ('1', (SELECT id FROM difficulty WHERE name = '1/10')),
        ('1.5', (SELECT id FROM difficulty WHERE name = '1.5/10')),
        ('1,5', (SELECT id FROM difficulty WHERE name = '1.5/10')),
        ('1,5/10', (SELECT id FROM difficulty WHERE name = '1.5/10')),
        ('2', (SELECT id FROM difficulty WHERE name = '2/10')),
        ('2.5', (SELECT id FROM difficulty WHERE name = '2.5/10')),
        ('2,5', (SELECT id FROM difficulty WHERE name = '2.5/10')),
        ('2,5/10', (SELECT id FROM difficulty WHERE name = '2.5/10')),
        ('3', (SELECT id FROM difficulty WHERE name = '3/10')),
        ('3.5', (SELECT id FROM difficulty WHERE name = '3.5/10')),
        ('3,5', (SELECT id FROM difficulty WHERE name = '3.5/10')),
        ('3,5/10', (SELECT id FROM difficulty WHERE name = '3.5/10')),
        ('4', (SELECT id FROM difficulty WHERE name = '4/10')),
        ('4.5', (SELECT id FROM difficulty WHERE name = '4.5/10')),
        ('4,5', (SELECT id FROM difficulty WHERE name = '4.5/10')),
        ('4,5/10', (SELECT id FROM difficulty WHERE name = '4.5/10')),
        ('5', (SELECT id FROM difficulty WHERE name = '5/10')),
        ('5.5', (SELECT id FROM difficulty WHERE name = '5.5/10')),
        ('5,5', (SELECT id FROM difficulty WHERE name = '5.5/10')),
        ('5,5/10', (SELECT id FROM difficulty WHERE name = '5.5/10')),
        ('6', (SELECT id FROM difficulty WHERE name = '6/10')),
        ('6.5', (SELECT id FROM difficulty WHERE name = '6.5/10')),
        ('6,5', (SELECT id FROM difficulty WHERE name = '6.5/10')),
        ('6,5/10', (SELECT id FROM difficulty WHERE name = '6.5/10')),
        ('7', (SELECT id FROM difficulty WHERE name = '7/10')),
        ('7.5', (SELECT id FROM difficulty WHERE name = '7.5/10')),
        ('7,5', (SELECT id FROM difficulty WHERE name = '7.5/10')),
        ('7,5/10', (SELECT id FROM difficulty WHERE name = '7.5/10')),
        ('8', (SELECT id FROM difficulty WHERE name = '8/10')),
        ('8.5', (SELECT id FROM difficulty WHERE name = '8.5/10')),
        ('8,5', (SELECT id FROM difficulty WHERE name = '8.5/10')),
        ('8,5/10', (SELECT id FROM difficulty WHERE name = '8.5/10')),
        ('9', (SELECT id FROM difficulty WHERE name = '9/10')),
        ('9.5', (SELECT id FROM difficulty WHERE name = '9.5/10')),
        ('9,5', (SELECT id FROM difficulty WHERE name = '9.5/10')),
        ('9,5/10', (SELECT id FROM difficulty WHERE name = '9.5/10')),
        ('10', (SELECT id FROM difficulty WHERE name = '10/10')),
        ('Low', (SELECT id FROM difficulty WHERE name = 'Low Elite')),
        ('Mid', (SELECT id FROM difficulty WHERE name = 'Mid Elite')),
        ('High', (SELECT id FROM difficulty WHERE name = 'High Elite')),
        ('Insanity', (SELECT id FROM difficulty WHERE name = 'Insanity Elite')),
        ('God', (SELECT id FROM difficulty WHERE name = 'God Tier')),
        ('Hell', (SELECT id FROM difficulty WHERE name = 'Hell Tier'))
    """)

    devtools.noob_log("All difficulty & tier 'contants' inserted")

    cursor.execute("""
        INSERT INTO location (name, sort_value) VALUES
        ('Cap Kingdom', ?),
        ('Cascade Kingdom', ?),
        ('Sand Kingdom', ?),
        ('Lake Kingdom', ?),
        ('Wooded Kingdom', ?),
        ('Cloud Kingdom', ?),
        ('Lost Kingdom', ?),
        ('Metro Kingdom', ?),
        ('Snow Kingdom', ?),
        ('Seaside Kingdom', ?),
        ('Luncheon Kingdom', ?),
        ('Ruined Kingdom', ?),
        ('Bowser''s Kingdom', ?),
        ('Moon Kingdom', ?),
        ('Mushroom Kingdom', ?),
        ('Dark side', ?),
        ('Darker side', ?),
        ('Odyssey', ?)
    """, tuple(i for i in range(18)))

    cursor.execute("""
        INSERT INTO location_alias (alias, location_id) VALUES
        ('Mushroom', (SELECT id FROM location WHERE name = 'Mushroom Kingdom')),
        ('Cap', (SELECT id FROM location WHERE name = 'Cap Kingdom')),
        ('Cascade', (SELECT id FROM location WHERE name = 'Cascade Kingdom')),
        ('Sand', (SELECT id FROM location WHERE name = 'Sand Kingdom')),
        ('Lake', (SELECT id FROM location WHERE name = 'Lake Kingdom')),
        ('Wooded', (SELECT id FROM location WHERE name = 'Wooded Kingdom')),
        ('Cloud', (SELECT id FROM location WHERE name = 'Cloud Kingdom')),
        ('Lost', (SELECT id FROM location WHERE name = 'Lost Kingdom')),
        ('Metro', (SELECT id FROM location WHERE name = 'Metro Kingdom')),
        ('Snow', (SELECT id FROM location WHERE name = 'Snow Kingdom')),
        ('Seaside', (SELECT id FROM location WHERE name = 'Seaside Kingdom')),
        ('Luncheon', (SELECT id FROM location WHERE name = 'Luncheon Kingdom')),
        ('Ruined', (SELECT id FROM location WHERE name = 'Ruined Kingdom')),
        ('Bowser', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ('Bowsers', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ('Bowser''s', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ('Bowser Kingdom', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ('Bowsers Kingdom', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ('Moon', (SELECT id FROM location WHERE name = 'Moon Kingdom')),
        ('Dark', (SELECT id FROM location WHERE name = 'Dark side')),
        ('Darker', (SELECT id FROM location WHERE name = 'Darker side'))
    """)
    
    cursor.execute("""
        INSERT INTO location_outer_junction (location_id, outer_id) VALUES
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Mushroom Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Cap Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Cascade Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Sand Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Lake Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Wooded Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Cloud Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Lost Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Metro Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Snow Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Seaside Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Luncheon Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Ruined Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Moon Kingdom')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Dark Side')),
        ((SELECT id FROM location WHERE name = 'Odyssey'), (SELECT id FROM location WHERE name = 'Darker Side'))
    """)

    devtools.noob_log("All location 'contants' inserted")

    cursor.execute(f"""
        INSERT INTO server (name, sort_value) VALUES 
        ('SMO Trickjumping server', ?),
        ('Database', ?)
    """, tuple(i for i in range(2)))

    cursor.execute("""
        INSERT INTO server_alias (alias, server_id) VALUES
        ('Main', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('Main Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('Main Trickjump Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('Main Trickjumping Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('SMO Trickjump', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('SMO Trickjump Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('SMO Trickjumping', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('Trickjump Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('Trickjumping Server', (SELECT id FROM server WHERE name = 'SMO Trickjumping Server')),
        ('DB', (SELECT id FROM server WHERE name = 'Database')),
        ('Database Server', (SELECT id FROM server WHERE name = 'Database')),
        ('SMO Database', (SELECT id FROM server WHERE name = 'Database')),
        ('SMO Trickjumping Database', (SELECT id FROM server WHERE name = 'Database')),
        ('Trickjump Database', (SELECT id FROM server WHERE name = 'Database')),
        ('Trickjumping Database', (SELECT id FROM server WHERE name = 'Database')),
        ('Trickjump db', (SELECT id FROM server WHERE name = 'Database')),
        ('Trickjumping db', (SELECT id FROM server WHERE name = 'Database'))
    """)

    devtools.noob_log("All server 'contants' inserted")

    cursor.execute("""
        INSERT INTO `rank` (power, name) VALUES
        (0, 'User'),
        (1, 'Helper'),
        (2, 'Moderator'),
        (3, 'Administrator'),
        (4, 'Owner')
    """)

    devtools.noob_log("All 'constant' values inserted")

    cursor.execute("""
        SET FOREIGN_KEY_CHECKS = 1
    """)


    # Get all jump data

    with open("scripts/database/data/jump_data.json") as f:
        all_jump_data: dict[str, dict[str, str | list[str]]] = json.load(f)


    # Insert all people

    with open("scripts/database/data/all_people_filtered.json") as f:
        simple_all_people_mapping: dict[str, str] = json.load(f)

    all_contributor_lines_unfiltered: set[str] = set()

    CONTRIBUTOR_KEYS = ("finder", "taser", "prover")
    for jump_data in all_jump_data.values():
        for contributor_line in CONTRIBUTOR_KEYS:
            if contributor_line in jump_data:
                all_contributor_lines_unfiltered |= set(person.strip() for person in jump_data[contributor_line])

    all_people_mapping: dict[str, str] = {}
    all_lines_mapping: dict[str, list[str]] = {}

    for contributor_line in all_contributor_lines_unfiltered:
        actual_people: list[str] = re.split(r", | & | and | - ", contributor_line)

        for line in actual_people:
            person_fixed = simple_all_people_mapping[line]
            all_people_mapping[line] = person_fixed
            all_lines_mapping.setdefault(contributor_line, []).append(person_fixed)

    cursor.execute(f"""
        INSERT INTO person (name) VALUES
        {",\n".join(f"('{person.replace("'", "''")}')" for person in set(all_people_mapping.values()))}
    """)

    devtools.noob_log("All people inserted")
    
    # Insert contributors of trickjumps
    all_trickjumps_with_ftp: list[tuple[str, str, int]] = []

    for jump_data in all_jump_data.values():
        people_ftp_points: dict[str, int] = {}

        for i, contributor_key in enumerate(CONTRIBUTOR_KEYS):
            points_for_this: int = 2**i
            people_flattened: set[str] = set()

            for line in jump_data.get(contributor_key, ()):
                people_flattened |= set(all_lines_mapping[line])

            for person in people_flattened:
                if person not in people_ftp_points:
                    people_ftp_points[person] = 0
                people_ftp_points[person] += points_for_this
        
        for person, points in people_ftp_points.items():
            all_trickjumps_with_ftp.append((jump_data['name'], person, points))
    
    cursor.execute(f"""
        INSERT INTO trickjump_contributor (trickjump_id, person_id, contribution) VALUES
        {",\n".join(f"((SELECT id FROM trickjump WHERE name = ?), (SELECT id FROM person WHERE name = ?), {elem[2]})" for elem in all_trickjumps_with_ftp)}
    """, [elem for tup in all_trickjumps_with_ftp for elem in tup[:2]])

    devtools.noob_log("All trickjump contributors inserted")

    jump_to_info: dict[str, str] = {}
    for jump_name, jump_data in all_jump_data.items():
        jump_infos: list[str] = jump_data.get('extra', [])
        if jump_infos:
            jump_to_info[jump_name] = "\n".join(jump_infos)

    all_infos_unique = tuple(set(jump_to_info.values()))
    cursor.execute(f"""
        INSERT IGNORE INTO info (text) VALUES
        {",\n".join("(?)" for _ in all_infos_unique)}
    """, all_infos_unique)

    devtools.noob_log("All infos inserted")


    # Insert trickjump data

    cursor.execute(f"""
        INSERT INTO trickjump (name, difficulty_id, server_id, extra_id) VALUES
        {",\n".join("(?, (SELECT name FROM difficulty WHERE name = ?), ?, (SELECT text FROM info WHERE text = ?))" for _ in range(len(all_jump_data)))};
    """, [(jump_data['name'], jump_data['diff'], SERVERS.index(jump_data['server']) + 1, "\n".join(line) if line != [None] # for line in jump_data.get('extra', [None])) for jump_data in all_jump_data.values()])

    connection.commit()

devtools.noob_log("All changes committed")