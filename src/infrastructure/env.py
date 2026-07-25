import annotationlib
import os
import typing as t

import dotenv

dotenv.load_dotenv(r"..\.env")


class EnvLayout(t.TypedDict, total=True):
    DATABASE_URL: str
    DISCORD_TOKEN: str
    PASTEE_TOKEN: str


def _get_or_throw_env(name: str) -> str:
    v = os.getenv(name)

    if v is None:
        raise RuntimeError(f"Env variable {name!r} could not be found!")

    return v


ENV: t.Final[EnvLayout] = {
    name: _get_or_throw_env(name) for name in annotationlib.get_annotations(EnvLayout)
}  # type: ignore
