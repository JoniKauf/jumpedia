


from dataclasses import dataclass, field
from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._discord.user import UserAdapter
from adapters._users.jumpedia_user import JumpediaUserAdapter
from adapters.interaction import InteractionAdapter
from errors.feedback import feedbacks
from ranks.jumpedia_rank import JumpediaRank
from structures import community
from structures.community import Community
from structures.jumpedia import Jumpedia

def _require_server_with_community(community: Community | None) -> Community:
    if community is None:
        raise feedbacks.temp("Server isnt connected ot community")
    
    return community

def _require_community_with_name(name: str, jumpedia: Jumpedia) -> Community:
    community = jumpedia.get_community_by_name(name)

    if community is None:
        raise feedbacks.temp(f"Community with the name `{name}` could not be found!")
    
    return community


def _valnitize_community_name(name: str) -> str:
    from utils import text

    return text.raw_to_real_and_validate(
        name, 
        community.MIN_NAME_LENGTH, 
        community.MAX_NAME_LENGTH
    )



@dataclass(frozen=True)
class JumpediaAdapter(BaseAdapter):
    _jumpedia: Jumpedia = field(init=False, default=Jumpedia())
    
    interaction: InteractionAdapter

    # --- Community ---

    def get_communities(self) -> list[CommunityAdapter]:
        return [
            CommunityAdapter(c, self) 
            for c in
            self._jumpedia.get_communities()
        ]
    
    def get_community(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            _require_community_with_name(_valnitize_community_name(name), self._jumpedia),
            self
        )
    
    def get_current_community(self) -> CommunityAdapter:
        return self.get_community(_require_server_with_community(
            self._jumpedia.get_community_by_server_id(self.interaction.current_server.id)
        ).name)
    
    def create_community(self, name: str, initial_list_name: str | None) -> CommunityAdapter:
        jumpedia_user = self.get_or_create_current_jumpedia_user()._jumpedia_user
        
        community = CommunityAdapter(self._jumpedia.create_community(
            jumpedia_user=jumpedia_user,
            server_id=self.interaction.current_server.id,
            real_name=_valnitize_community_name(name)
        ), self)

        if initial_list_name is not None:
            list = community.create_list(initial_list_name)
            community.set_default_selected_list(list.name)

        return community
    
    def delete_community(self, name: str) -> None:
        community = _require_community_with_name(_valnitize_community_name(name), self._jumpedia)

        if not self._jumpedia.delete_community(community):
            raise feedbacks.temp("The community was just deleted!")
        
    def delete_current_community(self) -> None:
        self._jumpedia.delete_community(self.get_current_community()._community)
    
    def add_community_to_current_server(self, name: str) -> None:
        self._jumpedia.add_community_to_server(
            self.get_community(name)._community.id, 
            self.interaction.current_server.id
        )

    def remove_community_from_current_server(self) -> None:
        self._jumpedia.remove_community_from_server(self.interaction.current_server._server.id)



    # --- Jumpedia User ---

    def get_or_create_jumpedia_user(self, user: UserAdapter, override_jumpedia_rank: JumpediaRank | None = None) -> JumpediaUserAdapter:
        jumpedia_user = self._jumpedia.create_or_get_jumpedia_user(
            user.id,
            user.name,
            override_jumpedia_rank or JumpediaRank.DEFAULT,
            True,
            override_jumpedia_rank is not None
        )

        return JumpediaUserAdapter(jumpedia_user, self)
    
    def get_or_create_current_jumpedia_user(self, override_jumpedia_rank: JumpediaRank | None = None) -> JumpediaUserAdapter:
        return self.get_or_create_jumpedia_user(self.interaction.current_user, override_jumpedia_rank)

        