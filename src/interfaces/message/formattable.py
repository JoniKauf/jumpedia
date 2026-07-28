import typing as t
from dataclasses import dataclass

from domain.enums.concept import Concept

type FormattableT = Concept


@dataclass(frozen=True, slots=True)
class FormattableForms:
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
        return cls(singular, singular + "s", singular + "'s", singular + "s'")

    @classmethod
    def from_singular_ending_in_y_regular(cls, singular: str) -> t.Self:
        return cls(
            singular, singular[:-1] + "ies", singular + "'s", singular[:-1] + "ies'"
        )

    @classmethod
    def from_formattable(cls, formattable: FormattableT) -> FormattableForms:
        match formattable:
            case Concept.ATTRIBUTE:
                return cls.from_singular_regular("attribute")
            case Concept.ATTRIBUTE_KIND:
                return cls.from_singular_regular("attribute kind")
            case Concept.ATTRIBUTE_SLOT_TYPE:
                return cls.from_singular_regular("attribute slot type")
            case Concept.ATTRIBUTE_TYPE:
                return cls.from_singular_regular("attribute type")
            case Concept.COLLECTION:
                return cls.from_singular_regular("collection")
            case Concept.COLLECTION_ENTRY:
                return cls.from_singular_ending_in_y_regular("collection entry")
            case Concept.COMMUNITY:
                return cls.from_singular_ending_in_y_regular("community")
            case Concept.COMMUNITY_RANK:
                return cls.from_singular_regular("community rank")
            case Concept.FIELD:
                return cls.from_singular_regular("field")
            case Concept.FIELD_MAPPING:
                return cls.from_singular_regular("field mapping")
            case Concept.FIELD_SLOT:
                return cls.from_singular_regular("field slot")
            case Concept.MEMBER:
                return cls.from_singular_regular("member")
            case Concept.META_RANK:
                return cls.from_singular_regular("meta rank")
            case Concept.LIST:
                return cls.from_singular_regular("list")
            case Concept.TASK:
                return cls.from_singular_regular("task")
            case Concept.SERVER:
                return cls.from_singular_regular("server")
            case Concept.SERVER_RANK:
                return cls.from_singular_regular("server rank")
            case Concept.TOKEN:
                return cls.from_singular_regular("token")
            case Concept.TOKEN_TYPE:
                return cls.from_singular_regular("token type")
            case Concept.USER:
                return cls.from_singular_regular("user")
            case _:
                t.assert_never(formattable)
