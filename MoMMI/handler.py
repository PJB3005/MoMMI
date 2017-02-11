from typing import TYPE_CHECKING

class MHandler(object):
    """
    Handlers are ways for modules to define stuff for use by other modules.
    For example: commands are handlers!

    Handlers can be queried for a channel and such.
    """

    if TYPE_CHECKING:
        from .master import MoMMI

    def __init__(self, name: str, module: str):
        self.name: str = name
        self.module: str = module

    def register(self, master: "MoMMI"):
        master.register_handler(self)
