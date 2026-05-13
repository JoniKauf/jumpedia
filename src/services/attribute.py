from discord import Interaction

from db.models import List
from domain.value_objects.strings import StrStore
from repositories.list import ListRepository
from repositories.community import CommunityRepository
from sqlalchemy.orm import Session
from domain import errors
from services.dto.list import ListInfo

from .base import BaseService

class ListService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

        self.attribute_repo = AttributeRepository(session)