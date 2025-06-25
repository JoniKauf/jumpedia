



from dataclasses import dataclass
from typing import ClassVar

from ranks.abstract_rank import AbstractRank

@dataclass(frozen=True)
class JumpediaRank(AbstractRank):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['JumpediaRank']
    LOWEST: ClassVar['JumpediaRank']
    HIGHEST: ClassVar['JumpediaRank']

    @classmethod
    def _init(cls) -> None:
        super()._init()
        
        cls.NONE = JumpediaRank(0, "None")
        cls.META_ADMIN = JumpediaRank(100, "Meta Administrator")
        cls.JONIKAUF = JumpediaRank(10 ** 6, "JoniKauf")

        cls.LOWEST = cls.NONE
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


JumpediaRank._init()