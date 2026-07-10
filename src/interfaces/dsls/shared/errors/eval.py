from dataclasses import dataclass

from interfaces.dsls.shared.errors.base import DslError


@dataclass(frozen=True, slots=True)
class EvalError(DslError):
    """Base class of all errors that occur in the evaluaton phase."""
