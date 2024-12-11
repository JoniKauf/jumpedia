import json
from typing import Any

IN = "data/jump_data.json"
OUT = "data/all_people_unfiltered.txt"
PEOPLE_ATTRS: tuple[str, ...] = ("finder", "taser", "prover")

with open(IN) as f:
    data: dict[str, dict[str, Any]] = json.load(f)


people: set[str] = set()

for tj_name, tj_data in data.items():
    for attr in PEOPLE_ATTRS:
        people.update(tj_data.get(attr, []))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(
        "\n".join(f"{person} -> " for person in sorted(people, key=str.casefold))
    )