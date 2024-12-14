from typing import get_args


class Test():
    test: list[str]


print(get_args(Test.__annotations__["test"]))