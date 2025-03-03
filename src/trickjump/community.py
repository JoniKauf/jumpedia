import discord as dc

from typing import Iterable, Self


class Catalog:
    def __init__(self):
        ...
        
class Community:
    _ALL: list['Community'] = []
    _LOOKUP: list['']

    def __init__(self, id: int, name: str, guilds: Iterable[int], catalogues: Iterable[Catalog]):
        self._name = name
        self._guilds = frozenset(guilds)
        self._catalogues = frozenset(catalogues)

    @classmethod
    def create(cls, initial_guild: dc.Interaction, name: str) -> Self:
        return cls()
    
    @property
    def name(self) -> str:
        return self._name

