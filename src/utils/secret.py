import json
import os
import typing as t
from pathlib import Path

__LOCATION = os.path.join(
    str(Path(__file__).resolve().parent.parent.parent), "secret.json"
)


class SecretContentT(t.NamedTuple):
    DATABASE_URL: str
    DISCORD_TOKEN: str
    GITHUB_GIST_TOKEN: str


def listen() -> SecretContentT:
    with open(os.path.abspath(__LOCATION), encoding="utf-8") as f:
        data: dict[str, t.Any] = json.load(f)

    tup = tuple(data.items())

    # Assert same order
    assert tuple(map(lambda e: e[0], tup)) == SecretContentT._fields

    return SecretContentT(*map(lambda e: e[1], tup))
