import platform
import runpy
import sys

import discord as dc
from discord.ext import commands
import pickle
import logging

def main():
    if sys.version_info < (3, 14):
        raise RuntimeError('Developed for Python 3.14 or higher')
    
    if platform.python_implementation() != 'CPython':
        raise RuntimeError('Developed for CPython, other Python implementation may not be compatible!')
    
    pickle.DEFAULT_PROTOCOL = 5
    
    logging.basicConfig(
        level=logging.INFO,  # or DEBUG, WARNING, etc.
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    from structures import jumpedia
    
    BOT = commands.Bot(command_prefix=" ", intents=dc.Intents.default(), help_command=None)
    runpy.run_module('running', init_globals={'BOT': BOT})
    

if __name__ == '__main__':
    main()