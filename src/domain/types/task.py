import typing as t

from domain.types.common import ID

TaskID = t.NewType("TaskID", ID)
TaskAliasID = t.NewType("TaskAliasID", ID)
