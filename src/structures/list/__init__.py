


from typing import NotRequired, TypedDict


class UserCollectionNodeT(TypedDict, total=True):
    value: str
    aliases: list[str]
    sort_value: int
    nodes: NotRequired[list['UserCollectionNodeT']]
    
type UserCollectionNodesT = list[UserCollectionNodeT]