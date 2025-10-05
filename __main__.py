
def __main():
    import sys
    import platform

    # --- Check Python Implementation ---
    if sys.version_info < (3, 14):
        raise RuntimeError("Developed for Python 3.14 or higher")

    if platform.python_implementation() != "CPython":
        raise RuntimeError(
            "Developed for CPython, other Python implementation may not be compatible!"
        )
    
    import subprocess

    subprocess.run(['py -m isort .'])
    subprocess.run(['py -m black .'])

    from beartype.claw import beartype_package

    beartype_package("src")

    
    


if __name__ == "__main__":
    __main()
