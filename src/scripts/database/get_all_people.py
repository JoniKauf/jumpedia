import json


with open("scripts/database/data/all_people_goober.txt", encoding="utf-8") as f:
    lines: list[str] = [line for line in f.read().split("\n")]

result: dict[str, str] = {}

for line in lines:
    parts = line.partition(" -> ")

    if not all(parts[:2]):
        raise ValueError

    old, _, new = parts
    old = old.strip()
    new = new.strip()

    if not new:
        new = old

    result[old] = new

with open("scripts/database/data/all_people_filtered.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4)
