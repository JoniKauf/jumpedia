import os
import platform
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable

def clear() -> None:
    os.system("cls" if platform.system() == "Windows" else "clear")


def time_left(
    seconds: float = 8,
    interval: float = 0.1,
    feedback: Callable[[float], str] = str,
    clear_console: bool = True,
):
    start = time.time()
    TIME = difference = seconds

    while (difference := TIME - (time.time() - start)) > 0:
        if clear_console:
            clear()
        print(feedback(difference))
        time.sleep(interval)


@contextmanager
def timed(name: str):
    start = time.time()
    try:
        yield
    finally:
        end = time.time()
        print(f"{end - start:.4f} - {name}")


def noob_log(s: str) -> None:
    print(f"{datetime.now(timezone.utc)}   {s}")
