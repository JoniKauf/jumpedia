import subprocess
import sys

import colorama
from colorama import Fore, Style

colorama.init()


def task(name: str) -> None:
    print(f"\n\n\n{Fore.BLUE}Starting task {Style.BRIGHT}{name}{Style.RESET_ALL}:")


def main():
    task("Install Requirements")
    subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"])

    # uv pip compile pyproject.toml --output-file requirements.txt --no-deps

    task("Format Code")
    subprocess.run(["isort", "."])
    subprocess.run(["black", "."])

    subprocess.run([sys.executable, "src", "from_main"])


if __name__ == "__main__":
    main()
