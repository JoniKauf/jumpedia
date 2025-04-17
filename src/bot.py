import platform
import runpy
import sys

import discord
from discord.ext import commands
import pickle

pickle.DEFAULT_PROTOCOL = 5

BOT = commands.Bot(intents=discord.Intents.all(), command_prefix=" ", help_command=None)

def main():
    if sys.version_info < (3, 12):
        raise RuntimeError('Developed for Python 3.12 or higher')
    
    if platform.python_implementation() != 'CPython':
        raise RuntimeError('Developed for CPython, other Python implementation may not be compatible!')

    runpy.run_module('running', init_globals={'BOT': BOT})
    

if __name__ == '__main__':
    main()