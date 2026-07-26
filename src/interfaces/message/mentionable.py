import typing as t

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.entities.user import UserEntity
from domain.enums.attribute import AttributeSlotType
from domain.enums.concept import Concept
from domain.enums.rank import AnyRankT, CommunityRank, MetaRank, ServerRank
from domain.typing.entity import NamedEntityT
from interfaces.message.formattable import FormattableT

type MentionableT = NamedEntityT | AnyRankT | AttributeSlotType


def get_name_of_mentionable(mentionable: MentionableT) -> str:
    match mentionable:
        case (ServerRank() | CommunityRank() | MetaRank()) as rank:
            return rank.name.title()

        case _:
            return str(mentionable.name)


def mentionable_to_formattable(mentionable: MentionableT) -> FormattableT:
    match mentionable:
        case AttributeEntity():
            return Concept.ATTRIBUTE
        case CommunityEntity():
            return Concept.COMMUNITY
        case CommunityRank():
            return Concept.COMMUNITY_RANK
        case ListEntity():
            return Concept.LIST
        case MemberEntity():
            return Concept.MEMBER
        case MetaRank():
            return Concept.META_RANK
        case ServerRank():
            return Concept.SERVER_RANK
        case TaskEntity():
            return Concept.TASK
        case UserEntity():
            return Concept.USER
        case AttributeSlotType():
            return Concept.ATTRIBUTE_SLOT_TYPE
        case _:
            t.assert_never(mentionable)
