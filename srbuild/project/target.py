from srbuild.graph.node import LinkedNode
from typing import NewType, Dict

# A Dict[str, LinkedNode] that maps profile names to the LinkedNodes for a target
class ProjectTarget(dict):
    def __init__(self, name, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.name = name
        self.is_lib = False
        self.install_dir = None

    def __str__(self):
        return f"{self.name} {'(lib)' if self.is_lib else '(exe)'}"
