from string.templatelib import Template

from domain.enums.rank import AnyRankT
import typing as t


# --- Base ---
class DomainError(Exception):
    def __init__(self) -> None:
        if type(self) in (DomainError, JumpediaHandledError):
            raise RuntimeError("Instance of base exception class created")
        
        super().__init__()

class JumpediaHandledError(DomainError):
    """This error is handled."""

# --- Invalid String ---
class EmptyString(JumpediaHandledError):
    pass

class DoubleBacktick(JumpediaHandledError):
    pass

# --- Context ---
class NotInServer(JumpediaHandledError):
    pass

class NotInCommunity(JumpediaHandledError):
    pass

# --- Permission ---
class NotAllowed(JumpediaHandledError):
    def __init__(self, rank: AnyRankT, required: AnyRankT) -> None:
        self.rank = rank
        self.required = required


class NotFound(DomainError):
    def __init__(self, type: type) -> None:
        self.type = type