

from dataclasses import dataclass
from typing import ClassVar

from structures.abstract_structure import AbstractStructure
from structures.jumpedia.jumpedia import Jumpedia
from structures.ranks.meta_rank import MetaRank


@dataclass(frozen=True, kw_only=True)
class MetaUser(AbstractStructure):
    MAX_NAME_LENGTH: ClassVar[int] = 32

    jumpedia: Jumpedia
    id: int
    meta_rank: MetaRank
    name: str

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)

    @property
    def parent(self) -> Jumpedia:
        return self.jumpedia
