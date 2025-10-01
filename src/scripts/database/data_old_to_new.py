import json
import re
from typing import Any
from database import queries

IN = "data/jump_data.json"

KINGDOMS = [
    "Mushroom Kingdom",
    "Beanbean Kingdom",
    "Sarasaland",
    "Dark Land",
    "Vanilla Kingdom",
    "Sky Kingdom",
    "Koopa Kingdom",
    "Yoshi's Island",
    "Subcon",
    "Rogueport",
    "Glitzville",
    "Pi'illo Island",
    "Vibe Island",
    "Bowsers Kingdom",
    "Cascade Kingdom",
    "Sand Kingdom",
    "Lake Kingdom",
    "Wooded Kingdom",
    "Lost Kingdom",
    "Metro Kingdom",
    "Snow Kingdom",
    "Seaside Kingdom",
    "Luncheon Kingdom",
    "Ruined Kingdom",
    "Bowser's Kingdom",
    "Moon Kingdom",
    "Odyssey",
]
DIFFICULTIES = [
    "0/10",
    "0.5/10",
    "1/10",
    "1.5/10",
    "2/10",
    "2.5/10",
    "3/10",
    "3.5/10",
    "4/10",
    "4.5/10",
    "5/10",
    "5.5/10",
    "6/10",
    "6.5/10",
    "7/10",
    "7.5/10",
    "8/10",
    "8.5/10",
    "9/10",
    "9.5/10",
    "10/10",
    "Low Elite",
    "Mid Elite",
    "High Elite",
    "Insanity Elite",
    "God Tier",
    "Hell Tier",
    "Unproven",
]
SERVERS = ["SMO Trickjumping Server", "Database"]
PEOPLE_ATTRS: tuple[str, ...] = ("finder", "taser", "prover")

with open(IN) as f:
    data: dict[str, dict[str, Any]] = json.load(f)


def insert_people():
    people: set[str] = set()

    for tj_data in data.values():
        for attr in PEOPLE_ATTRS:
            people.update(tj_data.get(attr, []))

    PATTERN = re.compile(r"[A-Z]")

    best_person: dict[str, tuple[str, int]] = {}
    for person in people:
        uppercase_amt = len(re.findall(PATTERN, person))

        if uppercase_amt > best_person.get(person.casefold().strip(), ("", -1))[1]:
            best_person[person.casefold().strip()] = person, uppercase_amt

    connector.execute("DELETE FROM person")
    connector.execute("ALTER TABLE person AUTO_INCREMENT = 1")
    connector.execute(
        """
        INSERT INTO
            person
            (name)
        VALUES 
        """
        + ", ".join(f"(?)" for _ in best_person),
        tuple(sorted((person[0] for person in best_person.values()), key=str.casefold)),
    )


with queries.CONNECTOR as connector:
    insert_people()

    # for tj_name, tj_data in data.items():
    #     connector.execute(f"""
    #         INSERT INTO
    #             trickjump
    #             (name, difficulty_id, server_id)
    #         VALUES
    #             (?, ?, ?)
    #         """,
    #         (
    #             tj_data["name"],
    #             DIFFICULTIES.index(tj_data["difficulty"]),
    #             SERVERS.index(tj_data["server"])
    #         )
    #     )
    #     connector.execute(f"""
    #         INSERT INTO
    #             trickjump_contributor
    #             (trickjump_id, person_id)
    #         """)

    connector.connection.commit()
