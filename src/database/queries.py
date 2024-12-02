from database import mariadb_extensions as mdbe
import secret
from trickjump.catalog import Catalog

CONNECTOR = mdbe.MariaDBConnector(secret.listen())


class Tables:
    LOCATION = "location"
    LOCATION_ALIAS = "location_alias"
    LOCATION_PARENT = "location_parent"
    TIER = "tier"
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


def get_all_trickjumps() -> Catalog:
    with CONNECTOR as conn:
        cursor = conn.execute("""
            SELECT
                name, location
        """)