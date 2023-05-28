from mcdreforged.api.utils.serializer import Serializable

from datetime import timedelta

class Config(Serializable):
    minutes: float = 10
    min_permission: int = 2

    cache_file: str = "./kick.json"