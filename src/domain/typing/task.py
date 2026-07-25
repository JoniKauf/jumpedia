import typing as t

lazy from domain.typing.common import ID

TaskID = t.NewType("TaskID", ID)
TaskAliasID = t.NewType("TaskAliasID", ID)
