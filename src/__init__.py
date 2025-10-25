def __main() -> None:
    # --- Set global defaults ---
    import sys

    sys.dont_write_bytecode = True

    import logging

    logging.basicConfig(
        level=logging.INFO,  # or DEBUG, WARNING, etc.
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # --- Check Python Implementation ---
    import platform

    if sys.version_info < (3, 14):
        raise RuntimeError("Developed for Python 3.14 or higher")

    if platform.python_implementation() != "CPython":
        raise RuntimeError(
            "Developed for CPython, other Python implementation may not be compatible!"
        )

    # --- Import/Run modules to preload and test functionality ---
    import src.discord_
    from src.structures import jumpedia


if __name__ == "__main__":
    __main()
