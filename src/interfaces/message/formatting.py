from string.templatelib import Template
import typing as t

from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors import AnyRankT

def shorten(s: str, max_len: int, more: str = "...") -> str:
    if len(s) <= max_len:
        return s
    
    if max_len <= len(more):
        return more
    
    return s[:max_len - len(more)] + "..."


def human_join(
    objects: t.Sequence[t.Any], final_delimiter: str, delimiter: str = ", "
) -> str:
    objects_str = tuple(map(str, objects))

    if len(objects) <= 1:
        return delimiter.join(objects_str)

    return f"{delimiter.join(objects_str[:-1])}{final_delimiter}{objects[-1]}"

def mention(
    obj: AnyRankT
) -> Template:
    match obj:
        case MetaRank() | ServerRank() | CommunityRank():
            return Template(f"{str(type(obj)).replace("Rank", " Rank")} ``{obj.name.replace('_', ' ').title()}``")
        
        case _:
            t.assert_never(obj)