from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DslError(Exception):
    """Base class of all DSL errors."""
