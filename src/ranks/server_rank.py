import typing as t
from dataclasses import dataclass

from .base_rank import BaseRank


@dataclass(frozen=True)
class ServerRank(BaseRank):
    _init_done: t.ClassVar[bool] = False

    DEFAULT: t.ClassVar["ServerRank"]
    LOWEST: t.ClassVar["ServerRank"]
    HIGHEST: t.ClassVar["ServerRank"]

    @classmethod
    def _init(cls):
        cls.SERVER_MEMBER = ServerRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = ServerRank(10, "Server Administrator")
        cls.SERVER_OWNER = ServerRank(20, "Server Owner")

        cls.LOWEST = cls.SERVER_MEMBER
        cls.HIGHEST = cls.SERVER_OWNER
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


ServerRank._init()
