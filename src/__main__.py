import platform
import sys
import textwrap

# from scripts import one_to_two


def __main() -> None:
    # if not sys.argv or "from_main" not in sys.argv:
    # raise RuntimeError("Please start by running main.py!")

    # --- Set global defaults ---
    # import logging

    # logging.basicConfig(
    #     level=logging.INFO,  # or DEBUG, WARNING, etc.
    #     format="%(asctime)s - %(levelname)s - %(message)s",
    # )

    if sys.version_info < (3, 15):
        raise RuntimeError("Developed for Python 3.15 or higher")

    if platform.python_implementation() != "CPython":
        raise Warning(
            "Developed for CPython, other Python implementation may not be compatible!"
        )

    input(textwrap.dedent("""
        Before starting, please consider the following infos first!
                          
        1. Jumpedia is currently only desgined to run in one process at a time. 
           It has no internal locks and relies on that commands do not happen at the same time.
           If multiple processes were to run at the same time, it COULD lead to corruption do to 
           dirty database reads and writes.
    """))
    
    # one_to_two.main()
    import _dc.run


if __name__ == "__main__":
    __main()
