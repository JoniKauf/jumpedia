import annotationlib
import enum
import os
import typing as t
from pathlib import Path

import dotenv

from jumpedia.domain.errors.internal import ProgrammingError

lazy from _typeshed import AnnotationForm

PROJECT_ROOT = Path(__file__).resolve().parents[3]
dotenv.load_dotenv(PROJECT_ROOT / ".env")


type EnvironmentT = t.Literal["production", "development"]


class EnvLayout(t.TypedDict, total=True):
    DATABASE_URL: str
    DISCORD_TOKEN: str
    PASTES_PATH: str
    PASTES_LINK: str
    PASTEE_TOKEN: t.NotRequired[str]
    ENVIRONMENT: t.NotRequired[EnvironmentT]


def _get_or_throw_env_variable_if_req(name: str, annot: AnnotationForm) -> str | None:
    v = os.getenv(name)

    if v is None:
        if (t.get_origin(annot) or annot) is t.NotRequired:
            return None

        raise ProgrammingError(f"Env variable {name!r} could not be found!")

    return v


ENV: t.Final[EnvLayout] = {
    name: v
    for name, annot in annotationlib.get_annotations(EnvLayout).items()
    if (v := _get_or_throw_env_variable_if_req(name, annot))
}  # type: ignore


def development() -> bool:
    return ENV.get("ENVIRONMENT") == "development"
