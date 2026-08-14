from discord import app_commands


def create_edit_group() -> app_commands.Group:
    return app_commands.Group(name="edit", description="...")
