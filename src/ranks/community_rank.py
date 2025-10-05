import typing as t
from dataclasses import dataclass

from .base_rank import BaseRank


@dataclass(frozen=True)
class CommunityRank(BaseRank):
    _init_done: t.ClassVar[bool] = False

    DEFAULT: t.ClassVar["CommunityRank"]
    LOWEST: t.ClassVar["CommunityRank"]
    HIGHEST: t.ClassVar["CommunityRank"]

    @classmethod
    def _init(cls):
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
