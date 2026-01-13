import functools
import discord as dc
from discord import app_commands as acmds
from discord.ext import commands as cmds
from types import CoroutineType
import typing as t

from adapters.interaction import InteractionAdapter