import sbuild.graph.cpp as cpp
import sbuild.tools.compiler as compiler
import unittest
import shutil
import os

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
TEST_PROJECT_ROOT = os.path.join(TESTS_ROOT, "minimal_project")
TEST_PROJECT_BUILD = os.path.join(TEST_PROJECT_ROOT, "build")

class TestCppNodes(unittest.TestCase):
    def setUp(self):
        self.include_dirs = [os.path.join(TEST_PROJECT_ROOT, "include")]
        os.mkdir(TEST_PROJECT_BUILD)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "objs"), exist_ok=True)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "libs"), exist_ok=True)

    def build_utils_node(self):
        utils_header_node = cpp.HeaderNode(path=os.path.join(TEST_PROJECT_ROOT, "include", "utils.hpp"))
        return utils_header_node

    def build_test_node(self, utils_header_node):
        test_header_node = cpp.HeaderNode(path=os.path.join(TEST_PROJECT_ROOT, "test", "test.hpp"), inputs=set([utils_header_node]))
        return test_header_node

    def build_object_graph(self, source_name, utils_header_node):
        header_node = cpp.HeaderNode(path=os.path.join(TEST_PROJECT_ROOT, "include", f"{source_name}.hpp"), inputs=set([utils_header_node]))
        source_path = os.path.join(TEST_PROJECT_ROOT, "src", f"{source_name}.cpp")
        source_node = cpp.SourceNode(path=source_path, inputs=set([header_node]))
        opts = set(["--std=c++17"])
        object_node = cpp.ObjectNode(inputs=set([source_node]), compiler=compiler.clang, opts=opts)
        return object_node

    def test_single_source_node_has_dirs(self):
        utils_header_node = self.build_utils_node()
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "include") in utils_header_node.dirs)

    def test_nested_source_node_has_dirs(self):
        utils_header_node = self.build_utils_node()
        # This header should include the
        test_header_node = self.build_test_node(utils_header_node)
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "include") in test_header_node.dirs)
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "test") in test_header_node.dirs)

    def test_factorial_object_node_compiles(self):
        # Nested header dependency.
        utils_header_node = self.build_utils_node()
        # Direct header dependency and source file.
        factorial_object_node = self.build_object_graph("factorial", utils_header_node)
        # Object node.
        self.assertTrue("factorial" in factorial_object_node.path)
        self.assertTrue(os.path.splitext(factorial_object_node.path)[1] == ".o")
        factorial_object_node.build()
        self.assertTrue(os.path.exists(factorial_object_node.path))

    def tearDown(self):
        shutil.rmtree(TEST_PROJECT_BUILD)
