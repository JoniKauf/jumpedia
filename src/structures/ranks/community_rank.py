


from dataclasses import dataclass
from typing import ClassVar

from structures.abstract_structure import AbstractStructure
from structures.ranks.abstract_rank import AbstractRank


@dataclass(frozen=True)
class CommunityRank(AbstractRank):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['CommunityRank']
    LOWEST: ClassVar['CommunityRank']
    HIGHEST: ClassVar['CommunityRank']

    @classmethod
    def _init(cls):
        super()._init()

        cls.USER = CommunityRank(0, "User")
        cls.HELPER = CommunityRank(10, "Helper")
        cls.MODERATOR = CommunityRank(20, "Moderator")
        cls.ADMINISTRATOR = CommunityRank(30, "Administrator")
        cls.OWNER = CommunityRank(40, "Owner")

        cls.LOWEST = cls.USER
        cls.HIGHEST = cls.OWNER
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


CommunityRank._init()