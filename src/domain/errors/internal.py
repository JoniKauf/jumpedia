# --- Internal Errors --- #


from domain.entities.base import BaseEntity


class InternalError(Exception):
    pass


class NotFoundById(InternalError):
    def __init__(self, type: type[BaseEntity]) -> None:
        super().__init__()
        self.type = type
