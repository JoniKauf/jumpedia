import json
import Levenshtein

with open("scripts/database/data/all_people_filtered.json", encoding="utf-8") as f:
    data: dict[str, str] = json.load(f)

unique_dct: dict[str, str] = {}
for v in data.values():
    unique_dct[v.casefold()] = v

unique: set[str] = {v for v in unique_dct}

result: dict[str, set[str]] = {}

for elem1 in unique:
    for elem2 in unique:
        if elem1 == elem2:
            continue

        if elem1 not in result.get(elem2, set()) and Levenshtein.distance(elem1, elem2, score_cutoff=3) <= 3:
            result.setdefault(elem1, set()).add(elem2)

with open("scripts/database/data/all_people_levenshteined.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4, default=lambda obj: list(obj)) 