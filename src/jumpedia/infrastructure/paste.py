import hashlib
import json
import urllib.parse
from collections.abc import Iterable
from pathlib import Path

from compression import zstd

from jumpedia.infrastructure.env import ENV

_PATH = Path(ENV["PASTES_PATH"])
_URL = ENV["PASTES_LINK"]


def create_and_get_link(
    headers: Iterable[str],
    rows: Iterable[Iterable[Iterable[str]]],
) -> str:
    data = {
        "headers": list(headers),
        "rows": [[list(values) for values in row] for row in rows],
    }

    encoded = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    file_id = hashlib.sha256(encoded).hexdigest()
    path = _PATH / f"{file_id}.zst"

    path.write_bytes(
        zstd.compress(encoded),
    )

    return urllib.parse.urljoin(
        _URL.rstrip("/") + "/",
        file_id,
    )
