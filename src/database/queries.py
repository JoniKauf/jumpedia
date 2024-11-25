from database import mariadb_extensions as mdbe
import secret
from trickjump.catalog import Catalog

_CONNECTOR = mdbe.MariaDBConnector(secret.listen())


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
    with _CONNECTOR as conn:
        cursor = conn.execute("""
            SELECT 
            tj.name AS trickjump_name,
            l.name AS location_name,
            d.name AS difficulty_name,
            t.name AS type_name,
            s.name AS server_name,
            th.link AS thumbnail_link,
            tj.found_at,
            tj.tased_at,
            tj.proven_at
            FROM trickjump tj
            LEFT JOIN location l ON tj.location_id = l.id
            LEFT JOIN difficulty d ON tj.difficulty_id = d.id
            LEFT JOIN type t ON tj.type_id = t.id
            LEFT JOIN server s ON tj.server_id = s.id
            LEFT JOIN thumbnail th ON tj.thumbnail_id = th.id;
        """)