import re
import typing as t

from utils import orm

from .. import BaseStructure
from .rank import CommunityRank, JumpediaRank

type UserIdentifierT = int | str | JumpediaUser | CommunityUser


if t.TYPE_CHECKING:
    from ..community import Community
    from ..jumpedia import Jumpedia, db
    from ..list import List

MAX_NAME_LENGTH: t.Final[int] = 32

MIN_ID: t.Final[int] = 0
MAX_ID: t.Final[int] = 2**64 - 1  # Snowflake is Unsigned Long int

ID_BOUNDS = (MIN_ID, MAX_ID)

MIN_ID_STR_LENGTH: t.Final[int] = min(len(str(n)) for n in ID_BOUNDS)
MAX_ID_STR_LENGTH: t.Final[int] = max(len(str(n)) for n in ID_BOUNDS)

_BOUNDS_REGEX_INSERT: str = (
    "{" + f"{MIN_ID_STR_LENGTH},{MAX_ID_STR_LENGTH}" + "}"
)  # {n,m}
_USER_MENTION_PATTERN: re.Pattern = re.compile(rf"^<@!?(\d{_BOUNDS_REGEX_INSERT})>$")


def extract_id_from_int(user_id: int) -> int:
    if not user_id < 0:
        raise ValueError(user_id)

    return user_id


def extract_id_from_str(user_id: str) -> int:
    if user_id.isdigit():
        return extract_id_from_int(int(user_id))

    if match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        return int(match.group(1) or match.group(2))

    raise ValueError(user_id)


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, int):
        return extract_id_from_int(identifier)

    if isinstance(identifier, str):
        return extract_id_from_str(identifier)

    if isinstance(identifier, JumpediaUser):
        return identifier.id

    if isinstance(identifier, CommunityUser):
        return identifier.jumpedia_user.id

    t.assert_never(identifier)


class JumpediaUser(BaseStructure):
    jumpedia: Jumpedia
    id: int
    user_name: str
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.jumpedia.identity)

    @property
    def name(self) -> str:
        return self.user_name

    @property
    def connector(self) -> orm.Connector:
        return self.jumpedia.connector


class CommunityUser(BaseStructure):
    jumpedia_user: JumpediaUser
    community: Community
    id: int
    community_rank: CommunityRank
    selected_list_id: int | None

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.community.identity)

    @property
    def name(self) -> str:
        return self.jumpedia_user.name

    @property
    def connector(self) -> orm.Connector:
        return self.jumpedia_user.connector

    def get_selected_list(self) -> List | None:
        if self.selected_list_id is None:
            return None

        with self.connector.cursor() as c:
            row = c.fetch_one(
                db.List.select("*").where(
                    (db.List.community_id, orm.Operator.EQ, self.community.id),
                    (db.List.id, orm.Operator.EQ, self.selected_list_id),
                )
            )

        if row is None:
            return None

        return (
            self.community._list_row_to_obj(row)
            or self.community.get_default_selected_list()
        )
