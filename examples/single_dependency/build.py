#!/usr/bin/env python3
import sbuildr
import sbuildr.dependencies.builders as builders
import sbuildr.dependencies.fetchers as fetchers

import pathlib
import os

cppstdlib = sbuildr.Library("stdc++")
project = sbuildr.Project()

# Assumes that minimal_project is located in ~/Python/SBuildr/examples/minimal_project
minimal_project_path = os.path.abspath(os.path.join(pathlib.Path.home(), "Python", "SBuildr", "examples", "minimal_project"))
minimal_project = sbuildr.dependencies.Dependency(fetchers.CopyFetcher(minimal_project_path), builders.SBuildrBuilder())

# Add targets for this project
project.interfaces(["dep.hpp"])
libdep = project.library("dep", sources=["dep.cpp"], libs=[cppstdlib, minimal_project.library("math")])
project.test("test", sources=["test.cpp"], libs=[cppstdlib, libdep])
project.test("selfContainedTest", sources=["selfContainedTest.cpp"])

project.export()
