from dataclasses import dataclass

from discord import Interaction

from db.models import List
from domain.value_objects.string import StrStore
from interfaces.decorators.context import CommandContext
from repositories.attribute import AttributeRepository
from repositories.list import ListRepository
from repositories.community import CommunityRepository
from sqlalchemy.orm import Session
from domain import errors
from services.dtos.list import ListInfoDTO


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    repo: AttributeRepository