import enum
from string.templatelib import Template
import typing as t
from dataclasses import dataclass
import string

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.entities.user import UserEntity

type MentionableT = CommunityEntity | ListEntity | AttributeEntity | TaskEntity | UserEntity | MemberEntity

@dataclass(frozen=True, slots=True)
class MentionableCases:
    singular: str
    plural: str
    singular_possessive: str
    plural_possessive: str

    def case_from_bools(self, plural: bool, possessive: bool) -> str:
        match plural, possessive:
            case False, False:
                return self.singular
            case True, False:
                return self.plural
            case False, True:
                return self.singular_possessive
            case True, True:
                return self.plural_possessive
            case _:
                t.assert_never((plural, possessive))

    @classmethod
    def from_singular_regular(cls, singular: str) -> t.Self:
        return cls(
            singular,
            singular + "s",
            singular + "'s",
            singular + "s'"
        )

def get_cases(mentionable_type: type[MentionableT]) -> MentionableCases:
    if issubclass(mentionable_type, UserEntity):
        return MentionableCases.from_singular_regular("user")

    if issubclass(mentionable_type, MemberEntity):
        return MentionableCases.from_singular_regular("community member")
    
    if issubclass(mentionable_type, CommunityEntity):
        return MentionableCases(
            "community",
            "communities",
            "community's",
            "communities'"
        )
    if issubclass(mentionable_type, ListEntity):
        return MentionableCases.from_singular_regular("list")

    if issubclass(mentionable_type, AttributeEntity):
        return MentionableCases.from_singular_regular("attribute")

    if issubclass(mentionable_type, TaskEntity):
        return MentionableCases.from_singular_regular("task")

    t.assert_never(mentionable_type)

def get_identifier(mentionable: MentionableT) -> str:
    match mentionable:
        case _:
            return str(mentionable.name)

def _shorten(s: str, max: int = 32, ellipsis: str = "...") -> str:
    if len(ellipsis) > max:
        raise ValueError()
    
    if len(s) <= max:
        return s

    return s[:max - len(ellipsis)] + ellipsis

@dataclass(frozen=True, kw_only=True, slots=True)
class F:
    """Class to be used inside interpolations of templates (t-strings) to format
    objects nicely and consistently for actual user display.

    Use its classmethods to generate instances of itself inside of interpolations of
    templates (t-strings).
    """

    _s: str
    
    @classmethod
    def mention(cls, mentionable: MentionableT, *, shorten: bool = True) -> t.Self:
        type_s = get_cases(type(mentionable)).singular
        inst_s = get_identifier(mentionable)
        
        if shorten:
            inst_s = _shorten(inst_s)

        s = f"{type_s} ``{inst_s}``"

        return cls(_s=s)
    
    @classmethod
    def type_name(cls, mentionable_type: type[MentionableT], *, header: bool, plural: bool = False, possessive: bool = False) -> t.Self:
        s = get_cases(mentionable_type).case_from_bools(plural, possessive)

        if header:
            s = string.capwords(s)
        
        return cls(_s=s)
    
    @classmethod
    def raw(cls, value: str) -> t.Self:
        return cls(_s=value)