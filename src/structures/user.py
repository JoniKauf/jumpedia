import re
import typing as t

from utils import orm
from utils.rank import CommunityRank, JumpediaRank

from . import BaseStructure, db, errors

type UserIdentifierT = int | str | JumpediaUser | CommunityUser


if t.TYPE_CHECKING:
    from .community import Community
    from .jumpedia import Jumpedia
    from .list import List


class JumpediaUser(BaseStructure):
    jumpedia: Jumpedia
    user_name: str
    jumpedia_rank: JumpediaRank

    @property
    def name(self) -> str:
        return self.user_name


class CommunityUser(BaseStructure):
    jumpedia_user: JumpediaUser
    community: Community
    community_rank: CommunityRank
    selected_list_id: int | None

    @property
    def name(self) -> str:
        return self.jumpedia_user.name

    def get_selected_list(self, c: orm.Cursor, /) -> List | None:
        if self.selected_list_id is None:
            return None

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
            execute_data = c.execute(
                db.CommunityUser.update(
                    db.CommunityUser.selected_list_id.set(id)
                ).where(
                    (db.CommunityUser.community_id, orm.Operator.EQ, self.community.id),
                    (db.CommunityUser.id, orm.Operator.EQ, self.id),
                ),
                get_affected_row_count=True,
            )

            assert execute_data.affected_row_count <= 1

            if execute_data.affected_row_count < 1:
                raise errors.StructureNotFoundError(CommunityUser)
