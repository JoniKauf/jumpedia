


from typing import NotRequired, TypedDict


MAX_NAME_LENGTH: int = 64
MAX_ATTRIBUTES: int = 3
MAX_TASKS: int = 1


class UserCollectionNodeT(TypedDict, total=True):
    value: str
    aliases: list[str]
    sort_value: int
    nodes: NotRequired[list['UserCollectionNodeT']]
    
type UserCollectionNodesT = list[UserCollectionNodeT]