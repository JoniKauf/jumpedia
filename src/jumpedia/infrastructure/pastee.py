import enum
import itertools
import os
import time
import typing as t
from collections import deque

import dotenv
import requests

from jumpedia.infrastructure.env import ENV
from jumpedia.infrastructure.utils import text


def create_pastee(
    files: dict[str, str],
    /,
    description: str | None = None,
) -> str:
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": ENV["PASTEE_TOKEN"],
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

    response = requests.post(
        "https://api.pastee.dev/v1/pastes",
        json=payload,
        headers=headers,
    )

    if response.status_code == 201:
        return response.json()["link"]

    raise ConnectionError()


def create_pastee_with_retries(
    files: dict[str, str],
    /,
    description: str | None = None,
    *,
    tries: int = 5,
    between: float = 0.2,
) -> str:
    if tries < 1:
        raise ValueError("'tries' less than 1")

    if between < 0:
        raise ValueError("'between' less than 0")

    err: ConnectionError | None = None

    for i in range(1, tries + 1):
        try:
            return create_pastee(files, description=description)
        except ConnectionError as e:
            time.sleep(between * i)
            err = e
            continue

    assert err is not None

    raise err


def table_to_pastee_strings(
    headers: t.Sequence[str],
    body_rows: t.Iterable[t.Iterable[t.Sequence[str]]],
    *,
    max_body_total_length_per_link: int = 1_500_000,
) -> list[str]:
    if len(headers) <= 0:
        raise ValueError("'headers' less than 1")

    col_count = len(headers)
    max_len_per_col = [len(h) for h in headers]
    final_rows: list[list[str]] = []

    MULTIPLE_ENTRIES_DIVIDOR: str = "   "

    for row in body_rows:
        final_row: list[str] = []

        it = iter(row)

        for i in range(col_count):
            cell = next(it, "")

            s = MULTIPLE_ENTRIES_DIVIDOR.join(cell)

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

    body = "\n".join(
        SPLIT.join(
            row[i].ljust(max_len_per_col[i]) if i < col_count - 1 else row[i]
            for i in range(col_count)
        )
        for row in final_rows
    )

    bodies = text.split_into_chunks_prefer_seperator(
        body, "\n", max_body_total_length_per_link
    )

    for i, body in enumerate(bodies):
        bodies[i] = f"{headers_str}\n{body}"

    return bodies
