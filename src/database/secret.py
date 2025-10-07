import json
import os
from typing import Any, NamedTuple

__LOCATION = r"secret.json"


class SecretContentT(NamedTuple):
    DB_CONNECTION_INFO: dict[str, Any]
    DISCORD_TOKEN: str
    GITHUB_GIST_TOKEN: str


def listen() -> SecretContentT:
    with open(os.path.abspath(__LOCATION), encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    
    tup = tuple(data.items())
    
    # Assert same order
    assert tuple(map(lambda e: e[0], tup)) == SecretContentT._fields

    return SecretContentT(*map(lambda e: e[1], tup))
