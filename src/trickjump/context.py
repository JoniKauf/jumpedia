from typing import Self
import discord as dc

from trickjump.community import Community

class Context():
    def __init__(self, community: Community) -> None:
        self.community = community


    @classmethod
    def from_interaction(cls, ia: dc.Interaction) -> Self:
        ...