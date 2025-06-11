



from dataclasses import dataclass
from typing import ClassVar

from ranks.abstract_rank import AbstractRank

@dataclass(frozen=True)
class MetaRank(AbstractRank):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['MetaRank']
    LOWEST: ClassVar['MetaRank']
    HIGHEST: ClassVar['MetaRank']

    @classmethod
    def _init(cls) -> None:
        super()._init()
        
        cls.NONE = MetaRank(0, "None")
        cls.META_ADMIN = MetaRank(100, "Meta Administrator")
        cls.JONIKAUF = MetaRank(10 ** 6, "JoniKauf")

        cls.LOWEST = cls.NONE
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


MetaRank._init()