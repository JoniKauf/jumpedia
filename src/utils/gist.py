import enum
import typing as t
from collections import deque

import requests

from . import secret

__TOKEN = secret.listen().GITHUB_GIST_TOKEN
API_URL: str = "https://api.github.com/gists"


class _FileContentT(t.TypedDict):
    content: str


def create_gist(
    files: dict[str, str],
    /,
    description: str | None = None,
    public: bool = False,
) -> str:

    headers: dict[str, str] = {
        "Authorization": f"token {__TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    payload: dict[str, t.Any] = {"public": public}

    if description is not None:
        payload["description"] = description

    payload["files"] = {
        file_name: {"content": content} for file_name, content in files.items()
    }

    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 201:
        gist_url: str = response.json().get("html_url")
        return gist_url
    else:
        raise Exception(
            f"Failed to create gist: {response.status_code}\n{response.text}"
        )


_ESCAPE_TABLE: t.Final[dict[t.Any, str]] = str.maketrans(
    {char: rf"\{char}" for char in r"$&\`*_~#+-.!|()[]{}<>"}
)
_DELIM: t.Final[str] = "|"
_DIV: t.Final[str] = ":---"


def _escape_cell(c: str | t.Sequence[str], /) -> str:
    if isinstance(c, str):
        c = (c,)

    if not c:
        return ""

    if "`" in c:
        return "<br/>".join(f"<code>{s.translate(_ESCAPE_TABLE)}</code>" for s in c)

    return "<br/>".join(f"`{s}`".replace("|", r"\|") for s in c)


class RowToStrMode(enum.Enum):
    HEADER = enum.auto()
    DIVIDER = enum.auto()
    BODY = enum.auto()


def _row_to_str(
    row: t.Iterable[str | t.Sequence[str]],
    mode: RowToStrMode = RowToStrMode.BODY,
    # pos: int = 0,
) -> str:
    if mode is not RowToStrMode.DIVIDER:
        # {_DELIM}**{pos}**
        return f"{_DELIM}{_DELIM.join(map(_escape_cell, row))}"

    if mode is RowToStrMode.DIVIDER:
        # {_DELIM}{_DIV}
        return f"{_DELIM}{_DELIM.join(map('<br/>'.join, row))}"

    t.assert_never(mode)


def table_to_gist_strings(
    rows: t.Iterable[t.Iterable[str | t.Sequence[str]]],
    headers: t.Sequence[str] | None = None,
    *,
    soft_split_limit: int = 1_000_000,
) -> list[str]:
    result: list[str] = []

    curr_rows: deque[str] = deque()
    char_count: int = 0

    headers_str_rev: tuple[str, str] | tuple[()] = ()

    if headers is not None:
        headers_str_rev = (
            _row_to_str(((_DIV,) for _ in range(len(headers))), RowToStrMode.DIVIDER),
            _row_to_str(((h,) for h in headers), RowToStrMode.HEADER),
        )

    del headers

    for row in rows:
        row_str = _row_to_str(row)

        del row

        char_count += len(row_str)

        curr_rows.append(row_str)

        if char_count >= soft_split_limit:
            curr_rows.extendleft(headers_str_rev)
            result.append("\n".join(curr_rows))

            curr_rows.clear()
            char_count = 0

    if curr_rows:
        curr_rows.extendleft(headers_str_rev)
        result.append("\n".join(curr_rows))

    return result
