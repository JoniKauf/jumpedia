import typing as t

lazy from jumpedia.domain.typing.common import ID

TaskID = t.NewType("TaskID", ID)
TaskAliasID = t.NewType("TaskAliasID", ID)
