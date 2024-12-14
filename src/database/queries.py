import functools
from typing import Any

import mariadb.cursors
from . import mariadb_extensions as mdbe
from database import secret
import mariadb

@functools.lru_cache(maxsize=1)
def __get_connection_data() -> dict[str, Any]:
    return secret.listen()['DB_CONNECTION_INFO']

def connection() -> mariadb.Connection:
    return mariadb.connect(**__get_connection_data())
    
class Tables:
    LOCATION = "location"
    LOCATION_ALIAS = "location_alias"
    LOCATION_OUTER_JUNCTION = "location_outer_junction"
    LOCATION_TAG = "location_tag"
    LOCATION_TAG_JUNCTION = "location_tag_junction"
    TIER = "tier"
    TIER_ALIAS = "tier_alias"
    DIFFICULTY = "difficulty"
    DIFFICULTY_ALIAS = "difficulty_alias"
    TYPE = "type"
    PERSON = "person"
    SERVER = "server"
    SERVER_ALIAS = "server_alias"
    LINK = "link"
    INFO = "info"
    TAG = "tag"
    THUMBNAIL = "thumbnail"
    RANK = "rank"
    USER = "user"
    TRICKJUMP = "trickjump"
    USER_TRICKJUMP = "user_trickjump"
    TRICKJUMP_CONTRIBUTOR = "trickjump_contributor"
    TRICKJUMP_LOCATION_JUNCTION = "trickjump_location_junction"
    TRICKJUMP_TYPE_JUNCTION = "trickjump_type_junction"
    TRICKJUMP_EXTRA_JUNCTION = "trickjump_extra_junction"
    TRICKJUMP_TAG_JUNCTION = "trickjump_tag_junction"
    TRICKJUMP_LINK_JUNCTION = "trickjump_link_junction"
    TRICKJUMP_INFO_JUNCTION = "trickjump_info_junction"



def get_all_trickjumps() -> Any:
    with CONNECTOR as conn:
        cursor = conn.execute("""
            SELECT
                name, location
        """)