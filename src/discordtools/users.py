import discord as dc

def get_user_name(user: dc.User | dc.Member) -> str:
    return user.global_name or user.name

def get_user_id_and_name(user: dc.User | dc.Member) -> tuple[int, str]:
    return (user.id, get_user_name(user))