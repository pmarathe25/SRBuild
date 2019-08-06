from sbuildr.project.target import ProjectTarget
from sbuildr.project.project import Project
from sbuildr.logger import G_LOGGER
from sbuildr.misc import paths, utils
import sbuildr.logger as logger

from typing import List, Tuple
import argparse
import sys

# Set up a special parser just to intercept -v/-vv. This will not intercept -h, so we duplicate the options
# in the cli() parser.
verbosity_parser = argparse.ArgumentParser(add_help=False)
verbosity_parser.add_argument("-v", "--verbose", action="store_true")
verbosity_parser.add_argument("-vv", "--very-verbose", action="store_true")

args, _ = verbosity_parser.parse_known_args()
if args.very_verbose:
    G_LOGGER.verbosity = logger.Verbosity.VERBOSE
elif args.verbose:
    G_LOGGER.verbosity = logger.Verbosity.DEBUG

# Sets up the the command-line interface for the given project/generator combination.
# When no profile(s) are specified, default_profile will be used.
def cli(project: Project, default_profiles=["debug", "release"]):
    """
    Adds the SBuildr command-line interface to the Python script invoking this function. For detailed usage information, you can run the Python code invoking this function with ``--help``.

    :param project: The project that the CLI will interface with.
    :param default_profiles: Names of default profiles. These are the profiles the `build`, `run`, and `clean` targets will use when none are explicitly specified via the command-line. Note that `tests` will run tests for all profiles by default.
    """
    def all_targets() -> List[ProjectTarget]:
        return list(project.libraries.values()) + list(project.executables.values())

    # Given target names, returns the corresponding targets.
    def select_targets(args) -> List[ProjectTarget]:
        targets = []
        for tgt_name in args.targets:
            if tgt_name not in project:
                G_LOGGER.critical(f"Could not find target: {tgt_name} in project.\n\tAvailable libraries:\n\t\t{list(project.libraries.keys())}\n\tAvailable executables:\n\t\t{list(project.executables.keys())}")
            if tgt_name in project.libraries:
                G_LOGGER.verbose(f"Found library for target: {tgt_name}")
                targets.append(project.libraries[tgt_name])
            if tgt_name in project.executables:
                G_LOGGER.verbose(f"Found executable for target: {tgt_name}")
                targets.append(project.executables[tgt_name])
            if tgt_name in project.executables and tgt_name in project.libraries:
                G_LOGGER.warning(f"Target: {tgt_name} refers to both an executable and a library. Selecting both.")
        return targets

    # Given argparse's args struct, parses out profile flags, and returns a list of profile names included.
    def select_profile_names(args) -> List[str]:
        return [prof_name for prof_name in project.profiles.keys() if getattr(args, prof_name)]


    def help(args):
        targets = select_targets(args) or all_targets()
        G_LOGGER.info(f"\n{utils.wrap_str(' Targets ')}")
        for target in targets:
            G_LOGGER.info(f"Target: {target}{'(internal)' if target.internal else ''}. Available Profiles:")
            for prof, node in target.items():
                G_LOGGER.info(f"\tProfile: {prof}. Path: {node.path}.")
        G_LOGGER.info(f"\n{utils.wrap_str(' Public Interface ')}")
        G_LOGGER.info(f"Headers: {project.public_headers}")


    def configure(args):
        project.configure()


    def build(args) -> Tuple[List[ProjectTarget], List[str]]:
        targets = select_targets(args) or all_targets()
        prof_names = select_profile_names(args) or default_profiles
        project.build(targets, prof_names)


    def run(args):
        targets = select_targets(args) or all_targets()
        prof_names = select_profile_names(args) or default_profiles
        project.run(targets, prof_names)


    def tests(args):
        def select_test_targets(args) -> List[ProjectTarget]:
            targets = []
            for test_name in args.targets:
                if test_name not in project.tests:
                    G_LOGGER.critical(f"Could not find test: {test_name} in project.\n\tAvailable tests:\n\t\t{list(project.tests.keys())}")
                targets.append(project.tests[test_name])
            return targets

        tests = select_test_targets(args)
        prof_names = select_profile_names(args)
        project.run_tests(tests, prof_names)

    def get_install_targets(args):
        headers = [tgt for tgt in args.targets if tgt not in project] or list(project.public_headers)
        args.targets = [tgt for tgt in args.targets if tgt in project]
        targets = [tgt for tgt in (select_targets(args) or all_targets()) if not tgt.internal]
        G_LOGGER.verbose(f"Selected public targets: {targets}")
        prof_names = select_profile_names(args) or ["release"]
        G_LOGGER.verbose(f"Targets: {targets} for profiles: {prof_names}")
        G_LOGGER.verbose(f"Headers: {headers}")
        return targets, prof_names, headers

    # TODO: Add -f flag and --upgrade behavior should be to remove older versions.
    def install(args):
        targets, prof_names, headers = get_install_targets(args)
        project.install(targets, prof_names, headers, args.headers, args.libraries, args.executables, dry_run=not args.force)


    def uninstall(args):
        targets, prof_names, headers = get_install_targets(args)
        project.uninstall(targets, prof_names, headers, args.headers, args.libraries, args.executables, dry_run=not args.force)


    # TODO: Add -f/--force option without which it will not clean.
    def clean(args):
        # By default, cleans all targets for the default profile.
        prof_names = select_profile_names(args) or default_profiles
        project.clean(prof_names, nuke=args.nuke)


    parser = argparse.ArgumentParser(description="Builds this project", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose", help="Enable verbose logging output", action="store_true")
    parser.add_argument("-vv", "--very-verbose", help="Enable very verbose logging output", action="store_true")

    def _add_profile_args(parser_like, verb: str):
        for prof_name in project.profiles.keys():
            parser_like.add_argument(f"--{prof_name}", help=f"{verb} targets for the {prof_name} profile", action="store_true")

    # By setting defaults, each subparser automatically invokes a function to execute it's actions.
    subparsers = parser.add_subparsers()

    # List
    help_parser = subparsers.add_parser("help", help="Display information about available targets and public headers", description="Display information about the targets and public headers in this project")
    help_parser.add_argument("targets", nargs='*', help="Targets to display. By default, displays help information for all targets.", default=[])
    help_parser.set_defaults(func=help)

    # Configure
    configure_parser = subparsers.add_parser("configure", help="Generate build configuration files", description="Generate a build configuration file for the project")
    configure_parser.set_defaults(func=configure)

    # Build
    build_parser = subparsers.add_parser("build", help="Build project targets", description="Build one or more project targets")
    build_parser.add_argument("targets", nargs='*', help="Targets to build. By default, builds all targets for the default profiles.", default=[])
    _add_profile_args(build_parser, "Build")
    build_parser.set_defaults(func=build)

    # Run
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.add_argument("target", help="Target corresponding to an executable")
    run_profile_group = run_parser.add_mutually_exclusive_group()
    _add_profile_args(run_profile_group, "Run")
    run_parser.set_defaults(func=run)

    # Test
    tests_parser = subparsers.add_parser("tests", help="Run project tests", description="Run one or more project tests")
    tests_parser.add_argument("targets", nargs='*', help="Targets to test. By default, tests all targets for all profiles.", default=[])
    _add_profile_args(tests_parser, "Test")
    tests_parser.set_defaults(func=tests)

    def _add_installation_dir_args(parser_like):
        parser_like.add_argument("-I", "--headers", help="Installation directory for headers", default=paths.default_header_install_path())
        parser_like.add_argument("-L", "--libraries", help="Installation directory for libraries", default=paths.default_library_install_path())
        parser_like.add_argument("-X", "--executables", help="Installation directory for executables", default=paths.default_executable_install_path())

    # Install
    install_parser = subparsers.add_parser("install", help="Install project targets", description="Install one or more project targets. Uses only the release profile by default.")
    install_parser.add_argument("targets", nargs='*', help="Targets to install. By default, installs all targets and headers specified.", default=[])
    install_parser.add_argument("-f", "--force", help="Copies targets. Without this flag, install will only do a dry-run", action="store_true")
    _add_installation_dir_args(install_parser)
    _add_profile_args(install_parser, "Install")
    install_parser.set_defaults(func=install)

    # Uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall project targets", description="Uninstall one or more project targets. Uses only the release profile by default.")
    uninstall_parser.add_argument("-f", "--force", help="Remove targets. Without this flag, uninstall will only do a dry-run", action="store_true")
    uninstall_parser.add_argument("targets", nargs='*', help="Targets to uninstall. By default, uninstalls all targets and headers specified.", default=[])
    _add_installation_dir_args(uninstall_parser)
    _add_profile_args(uninstall_parser, "Uninstall")
    uninstall_parser.set_defaults(func=uninstall)

    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets. By default, cleans all targets for the default profiles.")
    clean_parser.add_argument("--nuke", help="The nuclear option. Removes the entire build directory, including all targets for all profiles, meaning that the project must be reconfigured before subsequent builds.", action="store_true")
    _add_profile_args(clean_parser, "Clean")
    clean_parser.set_defaults(func=clean)

    # Display help if no arguments are provided.
    if len(sys.argv) < 2:
        parser.print_help()

    args, unknown = parser.parse_known_args()
    # If there are unknown arguments, make the parser display an error.
    # Done this way because a parser option provided after a subparser will
    # result in an unknown arg that isn't really unknown.
    if unknown:
        parser.parse_args(unknown)
    # Dispatch
    if hasattr(args, "func"):
        args.func(args)
