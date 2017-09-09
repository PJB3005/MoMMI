from MoMMI.master import MoMMI

class MHandler(object):
    """
    Handlers are ways for modules to define stuff for use by other modules.
    For example: commands are handlers!

    Handlers can be queried for a channel and such.
    """

    def __init__(self, name: str, module: str) -> None:
        self.name: str = name
        self.module: str = module

    def register(self, master: MoMMI) -> None:
        master.register_handler(self)
