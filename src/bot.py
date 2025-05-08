import platform
import runpy
import sys

from discord.ext import commands
import pickle

def main():
    if sys.version_info < (3, 12):
        raise RuntimeError('Developed for Python 3.12 or higher')
    
    if platform.python_implementation() != 'CPython':
        raise RuntimeError('Developed for CPython, other Python implementation may not be compatible!')

    pickle.DEFAULT_PROTOCOL = 5

    from structures import jumpedia
    
    #BOT = commands.Bot(command_prefix=" ", help_command=None)
    #runpy.run_module('running', init_globals={'BOT': BOT})
    

if __name__ == '__main__':
    main()