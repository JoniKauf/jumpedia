from abc import ABC

from sqlalchemy.orm import Session


class BaseRepository(ABC):
    def __init__(self, session: Session) -> None:
        if type(self) is BaseRepository:
            raise RuntimeError()

        self.session = session
