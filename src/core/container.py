from sqlalchemy.orm import Session
from services.community import CommunityService
from services.list import ListService
from services.user import UserService
from services.task import TaskService

class ServiceContainer:
    def __init__(self, session: Session):
        self.community = CommunityService(session)
        self.list = ListService(session)
        self.user = UserService(session)
        self.task = TaskService(session)