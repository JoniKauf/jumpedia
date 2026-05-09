from sqlalchemy.orm import Session

class BaseRepository:
    def __init__(self, session: Session) -> None:
        if type(self) is BaseRepository:
            raise RuntimeError()
        
        self.session = session
