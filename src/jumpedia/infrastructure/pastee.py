import asyncio
import datetime as dt
import enum
import itertools
import logging
import os
import time
import typing as t
from collections import deque

import dotenv
import requests

from jumpedia.infrastructure.env import ENV
from jumpedia.infrastructure.utils import text

logger = logging.getLogger(__name__)


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


SOFT_PASTEE_LIMIT: t.Final[int] = 2_800_000


async def create_pastees_with_retries_from_rows_async(
    headers: t.Iterable[str],
    rows: t.Iterable[t.Iterable[str]],
) -> tuple[str, ...]:
    logger.info("Creating tables...")
    tables = text.table_data_to_str(
        headers,
        rows,
        SOFT_PASTEE_LIMIT,
    )
    logger.info("Sending tables...")

    return tuple(
        await asyncio.gather(
            *(
                asyncio.to_thread(create_pastee_with_retries, {f"#{i}": s})
                for i, s in enumerate(
                    tables,
                    start=1,
                )
            )
        )
    )
