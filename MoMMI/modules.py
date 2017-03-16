import asyncio
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__)
modules = []


class MModule(object):
    def __init__(self, name: str):
        from .handler import MHandler

        self.name = name  # type: str
        self.handlers = {}  # type: Dict[str, MHandler]
        self.loaded= False  # type: bool
        # The actual module
        self.module = None
