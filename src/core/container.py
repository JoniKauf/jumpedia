from sqlalchemy.orm import Session
from service.community import CommunityService
from service.list import ListService
from service.user import UserService
from service.task import TaskService

class ServiceContainer:
    def __init__(self, session: Session):
        self.community = CommunityService(session)
        self.list = ListService(session)
        self.user = UserService(session)
        self.task = TaskService(session)