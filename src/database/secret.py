import json
from typing import Any, TypedDict

__LOCATION = r"C:\Users\JoniKaufYT\Documents\GitHub\JumpediaRework\secret.json"


class SecretContentT(TypedDict):
    DB_CONNECTION_INFO: dict[str, Any]


def listen() -> dict[str, Any]:
    with open(__LOCATION, encoding='utf-8') as f:
        return json.load(f)