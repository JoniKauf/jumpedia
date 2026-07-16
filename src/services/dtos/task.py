from dataclasses import dataclass

from domain.types.task import TaskID


@dataclass(frozen=True, slots=True)
class PreparedDeleteTask:
    task_id: TaskID
