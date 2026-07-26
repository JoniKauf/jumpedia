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

    # --- Make CWD Be "src/" --- #
    src_dir = Path(__file__).resolve().parent

    os.chdir(src_dir)
    sys.path.insert(0, str(src_dir))

    import db.session
    from infrastructure.dc import JumpediaBot
    from infrastructure.env import ENV

    if _yes_no("Format Code?"):
        subprocess.run(["isort", "."])
        subprocess.run(["black", "."])

    if _yes_no("Try Create Database?"):
        print("Creating database...")
        db.session.init_db()
        print("Database created!")

    bot = JumpediaBot()
    bot.run(ENV["DISCORD_TOKEN"])


def _yes_no(question: str, default: bool = True) -> bool:
    answer: str | None = None
    y, n = "Yn" if default else "yN"

    while answer is None or answer not in ("y", "n", ""):
        answer = input(f"{question} [{y}/{n}]\n> ").lower()
        print("\n\n")

    if not answer:
        return default

    return answer == "y"


if __name__ == "__main__":
    __main()
