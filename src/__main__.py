import os
import platform
import runpy
import subprocess
import sys
import textwrap
from pathlib import Path


def __main() -> None:

    if sys.version_info < (3, 15):
        raise RuntimeError("Developed for Python 3.15 or higher")

    if platform.python_implementation() != "CPython":
        raise Warning(
            "Developed for CPython, other Python implementation may not be compatible!"
        )

    input(textwrap.dedent("""
        Before starting, please consider the following infos first!
                          
        1. Jumpedia is currently only desgined to run in one process at a time. 
           It has no internal locks and relies on that commands do not happen at the
           same time. If multiple processes were to run at the same time, it COULD lead
           to corruption due to dirty database reads and writes.
    """))

    if _yes_no("Format Code?"):
        subprocess.run(["isort", "."])
        subprocess.run(["black", "."])

    # --- Make CWD be "src/" --- #
    src_dir = Path(__file__).resolve().parent

    os.chdir(src_dir)
    sys.path.insert(0, str(src_dir))

    from infrastructure.dc import JumpediaBot
    from infrastructure.env import ENV

    bot = JumpediaBot()
    bot.run(ENV["DISCORD_TOKEN"])


def _yes_no(question: str) -> bool:
    answer: str = ""

    while len(answer) != 1 or answer not in "yn":
        answer = input(f"{question} [Y/N]\n> ").lower()
        print("\n\n")

    return answer == "y"


if __name__ == "__main__":
    __main()
