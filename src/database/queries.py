from typing import Any
from . import mariadb_extensions as mdbe
from database import secret


CONNECTOR = mdbe.MariaDBConnector(secret.listen()['DB_CONNECTION_INFO'])


class Tables:
    LOCATION = "location"
    LOCATION_ALIAS = "location_alias"
    LOCATION_PARENT = "location_parent"
    LOCATION_TAG = "location_tag"
    LOCATION_TAGS = "location_tags"
    TIER = "tier"
    TIER_ALIAS = "tier_alias"
    DIFFICULTY = "difficulty"
    DIFFICULTY_ALIAS = "difficulty_alias"
    TYPE = "type"
    PERSON = "person"
    SERVER = "server"
    SERVER_ALIAS = "server_alias"
    LINK = "link"
    EXTRA = "extra"
    TAG = "tag"
    THUMBNAIL = "thumbnail"
    RANK = "rank"
    USER = "user"
    TRICKJUMP = "trickjump"
    USER_TRICKJUMP = "user_trickjump"
    TRICKJUMP_FINDER = "trickjump_finder"
    TRICKJUMP_TASER = "trickjump_taser"
    TRICKJUMP_PROVER = "trickjump_prover"
    TRICKJUMP_EXTRA = "trickjump_extra"
    TRICKJUMP_TAG = "trickjump_tag"
    TRICKJUMP_LINK = "trickjump_link"


def get_all_trickjumps() -> Any:
    with CONNECTOR as conn:
        cursor = conn.execute("""
            SELECT
                name, location
        """)