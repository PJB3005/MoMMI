from .config import get_config

def isowner(user):
    return user.id == get_config("owner.id", "nope")
    