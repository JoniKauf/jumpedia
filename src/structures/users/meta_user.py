

from dataclasses import dataclass
from typing import ClassVar

from ranks.meta_rank import MetaRank
from structures.base_structure import BaseStructure
from structures.jumpedia.jumpedia import Jumpedia


@dataclass(frozen=True, kw_only=True)
class MetaUser(BaseStructure):
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
