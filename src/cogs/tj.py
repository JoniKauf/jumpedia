from datetime import datetime, timezone
import re
import textwrap
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from database import queries
from discordtools import autocompletes, messagetools as msgt
from discordtools import feedbackerrors as fbe

_PROOF_PATTERN = re.compile(r'^https?://[^\s.]+\.[^\s]+$')
_PROOF_LIMIT = 256

def _validate_proof(proof: str | None) -> None | str:
    if proof is not None:
        proof = proof.strip()

        if len(proof) > _PROOF_LIMIT:
            raise fbe.TooLongLink(proof, _PROOF_LIMIT)
        if not re.match(_PROOF_PATTERN, proof):
            raise fbe.NotAValidLink(proof)
        
        proof = proof or None

    return proof

class Tj(cmds.GroupCog, group_name="tj"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot



async def setup(bot: cmds.Bot):
    await bot.add_cog(Tj(bot))