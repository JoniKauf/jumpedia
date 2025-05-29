import discord as dc

def get_user_name(user: dc.User | dc.Member) -> str:
    return user.global_name or user.name