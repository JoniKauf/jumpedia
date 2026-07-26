from dataclasses import dataclass


@dataclass()
class DslError(Exception):
    """Base class of all DSL errors."""
