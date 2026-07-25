from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.enums.rank import ServerRank
from domain.errors.business import InCommunity
from domain.value_objects.community import CommunityNameStr

lazy from repositories.community import CommunityRepository
lazy from repositories.server import ServerRepository
lazy from services.community import CommunityAccessService
lazy from services.contexts.interacting_user import InteractingUserContext
lazy from services.internal.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class ServerService:
    _ctx: InteractingUserContext

    _community_repository: CommunityRepository
    _server_repository: ServerRepository

    _community_access_service: CommunityAccessService
    _permission_service: PermissionService

    def link(self, community_name: CommunityNameStr) -> CommunityEntity:
        self._permission_service.ensure_server_rank(
            required_server_rank=ServerRank.ADMINISTRATOR
        )

        community = self._community_repository.get_by_server_id(self._ctx.server_id)

        if community is not None:
            raise InCommunity(community)

        community = self._community_access_service.get_by_name_or_raise(community_name)

        self._server_repository.link(community, self._ctx.server_id)

        return community

    def unlink(self) -> CommunityEntity:
        self._permission_service.ensure_server_rank(
            required_server_rank=ServerRank.ADMINISTRATOR
        )

        community = self._community_access_service.get_current_or_raise()

        self._server_repository.unlink(self._ctx.server_id)

        return community
