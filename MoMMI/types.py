from typing import Union


class SnowflakeID(int):
    """
    Represents a Discord Snowflake ID.
    """
    pass


MIdentifier = Union[SnowflakeID, str]
