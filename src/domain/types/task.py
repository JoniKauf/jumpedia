import typing as t

from domain.types.id import ID

TaskID = t.NewType("TaskID", ID)
TaskAliasID = t.NewType("TaskAliasID", ID)
