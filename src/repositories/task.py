from db.models import Task as TaskORM
from .base import BaseRepository


class TaskRepository(BaseRepository):
    def create(self, list_id: int, norm_name: str, slot_name: str) -> TaskORM:
        obj = TaskORM(
            list_id=list_id,
            norm_name=norm_name,
            slot_name=slot_name,
        )
        
        self.session.add(obj)
        self.session.flush()

        return obj

    def get_by_id(self, task_id: int) -> TaskORM | None:
        return self.session.get(TaskORM, task_id)