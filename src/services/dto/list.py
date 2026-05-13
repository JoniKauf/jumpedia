from dataclasses import dataclass
import typing as t

@dataclass(frozen=True)
class ListInfo:
    name: t.Annotated[str, "Name"]
    static_attribute: t.Annotated[tuple[str, ...], "Static Attribute"]
    task_attribute: t.Annotated[tuple[str, ...], "Task Attribute"]
    user_attribute: t.Annotated[tuple[str, ...], "User Attribute"]
    task_count: t.Annotated[int, "Task Count"]
    is_default_selected_list: t.Annotated[bool, "Is Default Selected List"]