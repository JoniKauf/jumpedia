from datetime import datetime, timezone
import re
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Optional as Opt
from database import queries
from discordtools import autocompletes, messagetools as msgt
from people import ranks, users
from trickjump import trickjump as tj, attributes as attrs
from discordtools import feedbackerrors as fbe

_PROOF_PATTERN = re.compile(r'^https?://[^\s.]+\.[^\s]+$')
_PROOF_LIMIT = attrs.MAX_LINK_LENGTH

def _validate_proof(proof: Opt[str]) -> Opt[str]:
    if proof is not None:
        proof = proof.strip()

        if len(proof) > _PROOF_LIMIT:
            raise fbe.TooLongLink(proof, _PROOF_LIMIT)
        if not re.match(_PROOF_PATTERN, proof):
            raise fbe.NotAValidLink(proof)
        
        proof = proof or None


class Tj(cmds.GroupCog, group_name="tj"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @acmds.autocomplete(jump_name=autocompletes.best_match_paged(
        tj.Trickjump.get_all_names()
    ))
    async def info(self, ia: dc.Interaction, jump_name: str):
        await ia.response.send_message(tj.Trickjump.get_by_name(jump_name).as_info())

    @acmds.command()
    @acmds.autocomplete(jump_name=autocompletes.best_match_paged(
        tj.Trickjump.get_all_names()
    ))
    async def give(self, ia: dc.Interaction, jump_name: str, proof: Opt[str] = None, user: Opt[str] = None):
        tj_data = tj.Trickjump.get_raw(jump_name)

        ia_user, other_user = users.User.get_if_permitted(
            ia, 
            user or ia.user, 
            ranks.USER_RANKS.MODERATOR, 
            ranks.SERVER_RANKS.MEMBER
        )

        _validate_proof(proof)   

        with queries.connected() as (conn, cursor):
            cursor.execute("""
                SELECT *
                FROM user_trickjump
                WHERE trickjump_id = ? and user_id = ?
                LIMIT 1
            """, (tj_id := tj_data['id'], other_user.id))

            result = cursor.fetchone()

            if result is not None:
                raise fbe.JumpAlreadyObtained(other_user.name)

            cursor.execute("""
                INSERT INTO user_trickjump 
                (trickjump_id, user_id, proof, given_at)
                VALUES
                (?, ?, ?, ?)
            """, (tj_id, other_user.id, proof, datetime.now(timezone.utc)))

            conn.commit()

        await msgt.success(
            ia,
            "Jump Successfully Given",
            " ".join((
                "You successfully gave",
                "yourself" if ia_user == other_user else f"the user `{other_user}`",
                f"the trickjump `{tj_data['name']}` with",
                "no proof yet!" if not proof else "the specified proof!"
            )),
            True
        )

    proof_group = acmds.Group(name="proof", description="Tj Proof Group")

    @proof_group.command(name="give")

    @acmds.autocomplete(jump_name=autocompletes.best_match_paged(
        tj.Trickjump.get_all_names()
    ))
    async def proof_give(self, ia: dc.Interaction, jump_name: str, ):
        pass
        
    list_group = acmds.Group(name="list", description="Tj List Group")
    
    @list_group.command()
    async def all(self, ia: dc.Interaction, filter: Opt[str], sort: Opt[str]):
        await msgt.success(ia, "Work In Progress", "Coming soon...")

    @list_group.command()
    async def completed(self, ia: dc.Interaction, user: Opt[int], filter: Opt[str], sort: Opt[str]):
        await msgt.success(ia, "Work In Progress", "Coming soon...")

    @list_group.command()
    async def missing(self, ia: dc.Interaction, user: Opt[int], filter: Opt[str], sort: Opt[str]):
        await msgt.success(ia, "Work In Progress", "Coming soon...")


async def setup(bot: cmds.Bot):
    await bot.add_cog(Tj(bot))