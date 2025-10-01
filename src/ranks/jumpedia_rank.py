from dataclasses import dataclass
from typing import ClassVar

from ranks.base_rank import BaseRank


@dataclass(frozen=True)
class JumpediaRank(BaseRank):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar["JumpediaRank"]
    LOWEST: ClassVar["JumpediaRank"]
    HIGHEST: ClassVar["JumpediaRank"]

    @classmethod
    def _init(cls) -> None:
        cls.JUMPEDIA_USER = JumpediaRank(0, "None")
        cls.META_ADMIN = JumpediaRank(100, "Meta Administrator")
        cls.JONIKAUF = JumpediaRank(200, "JoniKauf")

        cls.LOWEST = cls.JUMPEDIA_USER
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


JumpediaRank._init()
