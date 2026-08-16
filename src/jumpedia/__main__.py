import logging
import platform
import subprocess
import sys
import textwrap

from jumpedia.infrastructure import env


def _setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not env.development():
        logging.disable(logging.INFO)

    return logging.getLogger(__name__)


def main() -> None:
    if sys.version_info < (3, 15):
        raise RuntimeError("Developed for Python 3.15 or higher")

    if platform.python_implementation() != "CPython":
        raise Warning(
            "Developed for CPython, other Python implementation may not be compatible!"
        )

    print(textwrap.dedent("""
        Before starting, please consider the following infos first!
                          
        1. Jumpedia is currently only desgined to run in one process at a time. 
           It has no internal locks and relies on that commands do not happen at the
           same time. If multiple processes were to run at the same time, it COULD lead
           to corruption due to dirty database reads and writes.
    """))

    logger = _setup_logging()

    import jumpedia.db.session
    from jumpedia.infrastructure.dc import JumpediaBot
    from jumpedia.infrastructure.env import ENV

    logger.info("Formatting Code...")
    subprocess.run(["isort", "."])
    subprocess.run(["black", "."])

    logger.info("Initializing Database...")
    jumpedia.db.session.init_db()

    if _yes_no("Run old_to_new script?", False):
        from jumpedia._scripts.old_to_new import __main__ as old_to_new

        old_to_new.main()
        return

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
    main()
