import platform
import runpy
import sys

import discord
from discord.ext import commands

bot = commands.Bot(intents=discord.Intents.all(), command_prefix=" ", help_command=None)

def main():
    if sys.version_info < (3, 12):
        raise RuntimeError('Developed for Python 3.12 or higher')
    
    if platform.python_implementation() != 'CPython':
        raise RuntimeError('Developed for CPython, other Python implementation may not be compatible!')

    import scripts.old_to_new.data_old_to_new
    
    return
    runpy.run_module('meta.integrity')
    runpy.run_module('running')
    

if __name__ == '__main__':
    main()