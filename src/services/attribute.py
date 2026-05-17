from discord import Interaction

from db.models import List
from domain.value_objects.string import StrStore
from interfaces.decorators.context import CommandContext
from repositories.attribute import AttributeRepository
from repositories.list import ListRepository
from repositories.community import CommunityRepository
from sqlalchemy.orm import Session
from domain import errors
from services.dto.list import ListInfoDTO


class ListService:
    def __init__(self, session: Session) -> None:
        self.attribute_repo = AttributeRepository(session)
