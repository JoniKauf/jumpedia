import platform
import sys

from scripts import one_to_two


def __main() -> None:
    if not sys.argv or "from_main" not in sys.argv:
        raise RuntimeError("Please start by running main.py!")

    # --- Set global defaults ---
    # import logging

    # logging.basicConfig(
    #     level=logging.INFO,  # or DEBUG, WARNING, etc.
    #     format="%(asctime)s - %(levelname)s - %(message)s",
    # )

    if sys.version_info < (3, 14):
        raise RuntimeError("Developed for Python 3.14 or higher")

    if platform.python_implementation() != "CPython":
        raise RuntimeError(
            "Developed for CPython, other Python implementation may not be compatible!"
        )

    # one_to_two.main()
    import discord_.run


if __name__ == "__main__":
    __main()
