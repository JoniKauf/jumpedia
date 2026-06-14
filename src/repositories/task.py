from sqlalchemy import func, select

from db.models import List, Task
from domain.types.community import CommunityID
from domain.types.list import ListID
from .base import BaseRepository


class TaskRepository(BaseRepository):
    def create(self, list_id: int, norm_name: str, slot_name: str) -> Task:
        obj = Task(
            list_id=list_id,
            norm_name=norm_name,
            slot_name=slot_name,
        )

        self.session.add(obj)
        self.session.flush()

        return obj

    def get_by_id(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def count_by_list(self, list_id: ListID) -> int:
        stmt = select(func.count()).select_from(Task).where(Task.list_id == list_id)
        return self.session.scalar(stmt) or 0

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .join(List, List.list_id == Task.list_id)
            .where(List.community_id == community_id)
        )

        return self.session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> dict[CommunityID, int]:
        stmt = (
            select(
                List.community_id,
                func.count(),
            )
            .join(Task, Task.list_id == List.list_id)
            .group_by(List.community_id)
        )

        return {
            CommunityID(community_id): count
            for community_id, count in self.session.execute(stmt)
        }

    def count_grouped_by_list_id(
        self,
        community_id: CommunityID,
    ) -> dict[ListID, int]:
        stmt = (
            select(
                Task.list_id,
                func.count(),
            )
            .join(List, List.list_id == Task.list_id)
            .where(List.community_id == community_id)
            .group_by(Task.list_id)
        )

        return {ListID(list_id): count for list_id, count in self.session.execute(stmt)}
