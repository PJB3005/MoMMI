from typing import Dict, Any

class MModule(object):
    def __init__(self, name: str) -> None:
        from .handler import MHandler

        self.name: str = name
        self.handlers: Dict[str, MHandler] = {}
        self.loaded: bool = False
        # The actual module
        self.module: Any = None
