import enum
import typing as t

from domain.entities.attribute import AttributeEntity
from domain.entities.base import BaseEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.entities.user import UserEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.concept import Concept
from domain.enums.rank import AnyRankT, CommunityRank, MetaRank, ServerRank
from domain.typing.entity import NamedEntityT
from interfaces.dsls.core.lex import Token, TokenType
from interfaces.message.formattable import FormattableT

type MentionableT = AnyRankT | AttributeKind | AttributeSlotType | AttributeType | NamedEntityT | Token | TokenType


def get_name_of_mentionable(mentionable: MentionableT) -> str:
    match mentionable:
        case TokenType() as token_type:
            match token_type:
                case TokenType.NONE:
                    return "End"
                case TokenType.STRING:
                    return "String"
                case TokenType.IDENT:
                    return "Identifier"
                case TokenType.LPAREN:
                    return "Symbol: Left Parenthesis ('(')"
                case TokenType.RPAREN:
                    return "Symbol: Right Parenthesis (')')"
                case TokenType.LT:
                    return "Symbol: Lower Than Operator ('<')"
                case TokenType.LTE:
                    return "Symbol: Lower Than Or Equal Operator ('<=')"
                case TokenType.GT:
                    return "Symbol: Greater Than Operator ('>')"
                case TokenType.GTE:
                    return "Symbol: Greater Than Or Equal Operator ('>=')"
                case TokenType.PLUS:
                    return "Symbol: Plus ('+')"
                case TokenType.MINUS:
                    return "Symbol: Minus ('-')"
                case TokenType.COLON:
                    return "Symbol: Colon (':')"
                case TokenType.COMMA:
                    return "Symbol: Comma (',')"
                case TokenType.IF:
                    return "Keyword: If ('if')"
                case TokenType.ELSE:
                    return "Keyword: Else ('else')"
                case TokenType.IS:
                    return "Keyword: Is ('is')"
                case TokenType.NOT:
                    return "Keyword: Not ('not')"
                case TokenType.OR:
                    return "Keyword: Or ('or')"
                case TokenType.AND:
                    return "Keyword: And ('and')"
                case _:
                    t.assert_never(token_type)

        case enum.Enum() as rank:
            return rank.name.title()

        case BaseEntity() as entity:
            return str(entity.name)

        case Token() as token:
            return token.value

        case _:
            t.assert_never(mentionable)


def mentionable_to_formattable(mentionable: MentionableT) -> FormattableT:
    match mentionable:
        case AttributeEntity():
            return Concept.ATTRIBUTE
        case AttributeKind():
            return Concept.ATTRIBUTE_KIND
        case AttributeSlotType():
            return Concept.ATTRIBUTE_SLOT_TYPE
        case AttributeType():
            return Concept.ATTRIBUTE_TYPE
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
        case Token():
            return Concept.TOKEN
        case TokenType():
            return Concept.TOKEN_TYPE
        case UserEntity():
            return Concept.USER
        case _:
            t.assert_never(mentionable)
