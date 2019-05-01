from srbuild.graph.node import Node, CompiledNode, LinkedNode
from srbuild.tools.flags import BuildFlags
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER

from typing import List, Union, Dict
import os

# Inserts suffix into path, just before the extension
def _file_suffix(path: str, suffix: str, ext: str = None) -> str:
    split = os.path.splitext(os.path.basename(path))
    basename = split[0]
    ext = ext or split[1]
    suffixed = f"{basename}.{suffix}" + (ext if ext else "")
    G_LOGGER.verbose(f"_file_suffix received path: {path}, split into {split}. Using suffix: {suffix}, generated final name: {suffixed}")
    return suffixed

# Each profile has a Graph for linked/compiled targets. The source tree (i.e. FileManager) is shared.
# Profiles can have default properties that are applied to each target within.
# TODO: Add compiler/linker as a property of Profile.
class Profile(object):
    def __init__(self, flags: BuildFlags, build_dir: str):
        self.flags = flags
        self.build_dir = build_dir
        self.graph = Graph()

    # libs can contain either Nodes from this graph, or paths to libraries, or names of libraries
    # This cannot be called with a target_config that has not been
    def target(self, basename, source_nodes, flags, libs: List[Union[Node, str]], compiler, include_dirs, linker, lib_dirs) -> LinkedNode:
        # Per-target flags always overwrite profile flags.
        flags = self.flags + flags

        # First, add or retrieve object nodes for each source.
        object_nodes = []
        for source_node in source_nodes:
            # Only the include dirs provided by the user are part of the hash. When the automatically deduced
            # include_dirs change, it means the file is stale, so name collisions don't matter (i.e. OK to overwrite.)
            # TODO: Maybe push signature generation into Generator.
            obj_sig = compiler.signature(source_node.path, include_dirs, flags)
            obj_path = os.path.join(self.build_dir, _file_suffix(source_node.path, obj_sig, ".o"))
            # User defined includes are always prepended the ones deduced for SourceNodes.
            obj_node = CompiledNode(obj_path, source_node, compiler, include_dirs, flags)
            object_nodes.append(self.graph.add(obj_node))

        # For any libraries that are Nodes, add as inputs to the final LinkedNode.
        # For any libraries that are names, pass them along to the linker as-is.
        lib_nodes: List[Node] = [lib for lib in libs if isinstance(lib, Node)]
        # Next, convert all libs to paths or names.
        libs: List[str] = [lib if not isinstance(lib, Node) else lib.path for lib in libs]
        # Finally, add the actual linked node
        input_paths = [node.path for node in object_nodes]
        linked_sig = linker.signature(input_paths, libs, lib_dirs, flags)
        linked_path = os.path.join(self.build_dir, _file_suffix(basename, linked_sig))
        linked_node = LinkedNode(linked_path, object_nodes + lib_nodes, linker, libs, lib_dirs, flags, name=basename)
        return self.graph.add(linked_node)
