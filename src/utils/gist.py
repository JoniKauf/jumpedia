import enum
import itertools
import time
import typing as t
from collections import deque

import requests

from . import secret

__TOKEN = secret.listen().PASTEE_TOKEN


def create_pastee(
    files: dict[str, str],
    /,
    description: str | None = None,
) -> str:
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": __TOKEN,
    }

    payload: dict[str, t.Any] = {
        "sections": [
            {
                "name": file_name,
                "contents": content,
            }
            for file_name, content in files.items()
        ]
    }

    if description is not None:
        payload["description"] = description

    RETRIES = 5
    FIRST_SLEEP = 0.2

    for i in range(1, RETRIES + 1):
        response = requests.post(
            "https://api.pastee.dev/v1/pastes",
            json=payload,
            headers=headers,
        )

        if response.status_code == 201:
            return response.json()["link"]

        if i < RETRIES:
            time.sleep(FIRST_SLEEP**i)

    raise Exception(f"Failed to create paste: {response.status_code}\n{response.text}")


def table_to_pastee_strings(
    headers: t.Sequence[str],
    rows: t.Iterable[t.Iterable[str | t.Sequence[str]]],
    *,
    approx_split_limit: int = 1_500_000,
) -> list[str]:
    assert headers

    col_count = len(headers)
    max_len_per_col = [len(h) for h in headers]
    final_rows: list[list[str]] = []

    for row in rows:
        final_row: list[str] = []

        it = iter(row)

        for i in range(col_count):
            cell = next(it, "")

            if isinstance(cell, str):
                s = cell
            else:
                s = "   ".join(cell)

            final_row.append(s)
            max_len_per_col[i] = max(max_len_per_col[i], len(s))

        final_rows.append(final_row)

    SPLIT = " | "
    SPLIT_DIVIDOR = "-+-"

    header_list = [
        (
            headers[i].upper().ljust(max_len_per_col[i])
            if i < col_count - 1
            else headers[i].upper()
        )
        for i in range(col_count)
    ]

    divider_list = ["-" * max_len_per_col[i] for i in range(col_count)]

    headers_str = SPLIT.join(header_list) + "\n" + SPLIT_DIVIDOR.join(divider_list)

    res: list[str] = []
    cur: list[str] = []
    cur_length = 0

    def push():
        nonlocal cur, cur_length
        if cur:
            res.append("\n".join(cur))
            cur = []
            cur_length = 0

    for row in final_rows:
        row_str = SPLIT.join(
            row[i].ljust(max_len_per_col[i]) if i < col_count - 1 else row[i]
            for i in range(col_count)
        )

        needed = len(row_str) + (1 if cur else len(headers_str) + 1)

        if cur_length + needed > approx_split_limit:
            push()

        if not cur:
            cur.append(headers_str)
            cur_length += len(headers_str) + 1  # newline

        cur.append(row_str)
        cur_length += len(row_str) + 1

    push()
    return res
