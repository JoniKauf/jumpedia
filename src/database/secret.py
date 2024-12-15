import json
import os
from typing import Any, TypedDict

__LOCATION = r"..\secret.json"


class SecretContentT(TypedDict):
    DB_CONNECTION_INFO: dict[str, Any]
    DISCORD_TOKEN: str


def listen() -> SecretContentT:
    with open(os.path.abspath(__LOCATION), encoding='utf-8') as f:
        return json.load(f)