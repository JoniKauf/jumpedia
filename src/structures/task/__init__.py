import typing as t
from dataclasses import field

from src.utils import orm, text

from .. import BaseStructure, errors
from ..attribute.slot_str import SlotStr
from ..jumpedia import db

if t.TYPE_CHECKING:
    from ..list import List


class Task(BaseStructure):
    list: List
    id: int
    slot_name: SlotStr
    norm_name: text.NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity

    @property
    def name(self) -> str:
        return self.slot_name

    @property
    def connector(self) -> orm.Connector:
        return self.list.connector

    def get_real_aliases(self) -> frozenset[text.RealStr]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.TaskAlias.select(db.TaskAlias.slot_alias).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                    (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
                )
            )

        return frozenset(row.slot_alias for row in rows)

    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        with self.connector.cursor() as c:
            rows = c.fetch_all(
                db.TaskAlias.select(db.TaskAlias.norm_alias).where(
                    (db.TaskAlias.list_id, orm.Operator.EQ, self.list.id),
                    (db.TaskAlias.task_id, orm.Operator.EQ, self.id),
                )
            )

        return frozenset(row.norm_alias for row in rows)
