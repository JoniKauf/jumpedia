import discord as dc
from discord.ext import commands as cmds
from discord import app_commands as acmds

from discordtools import autocompletes
from trickjump import attributes as attrs

class Attr(cmds.GroupCog, group_name="attr"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    bundle_group = acmds.Group(name="bundle", description="info missing")

    BUNDLE_ATTR_CHOICES = [
        acmds.Choice(name=name, value=name)
        for name, cls
        in attrs.ATTR_ITEMS if issubclass(cls, attrs.AttrStrBundle)
    ]
    
    @bundle_group.command(name="add_item")
    @acmds.autocomplete(attr=autocompletes.best_match_paged(["hi",
    "apple", "giraffe", "thunder", "bicycle", "pancake", "volcano", "comet", "umbrella",
    "galaxy", "rainbow", "elephant", "cactus", "spaceship", "lantern", "notebook",
    "crocodile", "mountain", "chocolate", "sunset", "telescope", "waterfall", "cinnamon",
    "helicopter", "aquarium", "keyboard", "unicorn", "hamster", "diamond", "skateboard",
    "pizza", "dolphin", "treasure", "balloon", "tornado", "magnolia", "penguin", "octopus",
    "sandwich", "carousel", "firefly", "honeycomb", "mushroom", "starlight", "peppermint",
    "glacier", "marigold", "horizon", "sapphire", "butterfly", "jellyfish", "labyrinth",
    "kangaroo", "porcupine", "whisper", "spaghetti", "compass", "lemonade", "cathedral",
    "nightingale", "tambourine", "sunflower", "staircase", "iceberg", "lavender", "blueberry",
    "locomotive", "acorn", "masquerade", "hammock", "fern", "tangerine", "dragonfly", "topaz",
    "mosaic", "parchment", "nebula", "constellation", "lighthouse", "seahorse", "mermaid",
    "caravan", "meadow", "high", "firework", "zephyr", "windmill", "treetop", "honeybee", "silhouette",
    "ziggurat"
], per_page_limit=5))
    async def add_item(self, ia: dc.Interaction, attr: str):
        await ia.response.send_message(attr)

    @bundle_group.command(name="testing")
    async def testing(self, ia: dc.Interaction, aaaaa: str):
        await ia.response.send_message(aaaaa)
    
    
async def setup(bot: cmds.Bot):
    await bot.add_cog(Attr(bot))