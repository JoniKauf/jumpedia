import re
import typing as t

from utils import orm

from .. import BaseStructure
from utils.rank import CommunityRank, JumpediaRank

type UserIdentifierT = int | str | JumpediaUser | CommunityUser


if t.TYPE_CHECKING:
    from ..community import Community
    from ..jumpedia import Jumpedia, db
    from ..list import List


class JumpediaUser(BaseStructure):
    jumpedia: Jumpedia
    user_name: str
    jumpedia_rank: JumpediaRank

    @property
    def name(self) -> str:
        return self.user_name

    @property
    def connector(self) -> orm.Connector:
        return self.jumpedia.connector


class CommunityUser(BaseStructure):
    jumpedia_user: JumpediaUser
    community: Community
    community_rank: CommunityRank
    selected_list_id: int | None

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

        return self.community._list_row_to_obj(row)

    def set_selected_list(self, id: int | None) -> None:
        with self.connector.cursor() as c:
            c.execute(
                db.CommunityUser.update(
                    db.CommunityUser.selected_list_id.set(id)
                ).where(
                    (db.CommunityUser.community_id, orm.Operator.EQ, self.community.id),
                    (db.CommunityUser.id, orm.Operator.EQ, self.id),
                )
            )