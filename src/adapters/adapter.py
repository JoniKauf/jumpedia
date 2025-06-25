

from dataclasses import dataclass
from typing import Final
import typing
from adapters.base_adapter import BaseAdapter
from adapters.jumpedia_adapter import JumpediaAdapter

import discord as dc

from structures.jumpedia import Jumpedia
from utils import functools2, required

INTERACTION: Final[str] = '_interaction'
STRUCTURE: Final[str] = '_structure'

hints = typing.get_type_hints(BaseAdapter)

if INTERACTION not in hints or STRUCTURE not in hints:
    raise AssertionError()


@dataclass(frozen=True)
class EntryAdapter(BaseAdapter[None]):
    def __init__(self, interaction: dc.Interaction):
        object.__setattr__(self, INTERACTION, interaction)
        object.__setattr__(self, STRUCTURE, None)
    
    @functools2.optimized_no_arg_method_cache
    def get_jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(self._interaction, Jumpedia())
    
    @functools2.optimized_no_arg_method_cache
    def get_server(self) -> dc.Guild:
        return required.server_not_none(self._interaction.guild)