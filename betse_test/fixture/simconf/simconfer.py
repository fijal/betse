#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Fixtures and fixture classes creating temporary simulation configurations
isolated to specific tests, which typically modify the contents of these
configurations so as to exercise specific feature sets and edge cases.
'''

# ....................{ IMPORTS                           }....................
from betse_test.fixture.simconf.simconfclser import (
    SimConfTestExternal, SimConfTestInternal)
from pytest import fixture
from py._path.local import LocalPath

# ....................{ FIXTURES                          }....................
# Test-scope fixture creating and returning a new object for each unique test.
@fixture
def betse_sim_conf(betse_temp_dir: LocalPath) -> SimConfTestInternal:
    '''
    Per-test fixture creating a temporary minified simulation configuration
    file and returning an object encapsulating the contents of this file.

    Configuration Modifications (On-disk)
    ----------
    This fixture copies BETSE's default simulation configuration file,
    complete with all external assets (e.g., geometry masks) referenced and
    required by this file, into a temporary directory whose basename is the
    name of the test requesting this fixture excluding the prefixing substring
    ``test_``. When requested by the ``test_cli_sim_default`` test, for
    example, this fixture creates a temporary simulation configuration file
    ``{tmpdir}/cli_sim_default/sim_config.yaml`` for the absolute path
    ``{tmpdir}`` of this test session's root temporary directory (e.g.,
    ``/tmp/pytest-0/cli_sim_default/sim_config.yaml``).

    This directory and hence simulation configuration is safely accessible
    *only* for the duration of the current test. Subsequently run tests and
    fixtures *cannot* safely reuse this configuration.

    Configuration Modifications (In-memory)
    ----------
    This fixture also transforms the in-memory instance of the
    :class:`betse.science.parameters.Parameters` class encapsulating this
    configuration as follows:

    * All configuration options either requiring interactive input *or*
      displaying interactive output are disabled (e.g., plots, animations).
    * The space and time costs associated with simulating this configuration
      are safely minimized in a manner preserving all features.

    Since this fixture does *not* write these changes back to this file, the
    parent fixture or test is expected to do so manually (e.g., by calling the
    :meth:`SimConfTestInternal.config.overwrite` method on the object returned
    by this fixture).

    Parameters
    ----------
    betse_temp_dir : LocalPath
        Object embodying a temporary directory isolated to the current test.

    Returns
    ----------
    SimConfTestInternal
        Test-specific object encapsulating a temporary simulation configuration
        file specific to the current test, including such metadata as:

        * The absolute path of this configuration's on-disk YAML file.
        * This configuration's in-memory dictionary deserialized from this
          file.
    '''

    # Absolute filename of this configuration file in this temporary directory.
    sim_conf_filepath = betse_temp_dir.join('sim_config.yaml')

    # Test-specific object encapsulating this simulation configuration file.
    sim_state = SimConfTestInternal(conf_filepath=sim_conf_filepath)

    # Minimize the space and time costs associated with this configuration.
    sim_state.config.minify()

    # Return this object.
    return sim_state


# Test-scope fixture creating and returning a new object for each unique test.
@fixture
def betse_sim_conf_default(betse_temp_dir: LocalPath) -> SimConfTestInternal:
    '''
    Per-test fixture creating a temporary default simulation configuration file
    and returning an object encapsulating the contents of this file.

    Unlike the minified simulation configuration created by the
    :func:`betse_sim_conf` fixture and leveraged by most tests, the default
    simulation configuration created by this fixture remains unmodified (except
    for unavoidably disabling interactive simulation features, which
    non-interactive testing requires). Tests leveraging this fixture incur a
    significant performance penalty but can expose edge-case issues obscured by
    minification, including computational instability produced by the default
    non-minified time steps.

    Parameters
    ----------
    betse_temp_dir : LocalPath
        Object embodying a temporary directory isolated to the current test.

    Returns
    ----------
    SimConfTestInternal
        Test-specific object embodying a temporary simulation configuration.

    See Also
    ----------
    :func:`betse_sim_conf`
        Further details, ignoring minification performed by this fixture.
    '''

    # Absolute filename of this configuration file in this temporary directory.
    sim_conf_filepath = betse_temp_dir.join('sim_config.yaml')

    # Test-specific object encapsulating this simulation configuration file.
    sim_state = SimConfTestInternal(conf_filepath=sim_conf_filepath)

    # Return this object *WITHOUT* calling sim_state.config.minify().
    return sim_state


#FIXME: Fundamentally refactor this fixture to leverage the existing
#"betse_test/data/v0.5.0/yaml/sim_config.yaml" simulation configuration. To do
#so, we'll need to:
#
#* Generalize the "simconfclser.SimConfTestInternal" subclass to support
#  caller-defined simulation configuration filenames. We have a few possible
#  options here, including:
#  * Generalizing the simconfclser.SimConfTestInternal.__init__() method with a
#    new optional (or perhaps mandatory? ...yes, almost certainly mandatory)
#    "src_conf_filename" parameter. For disambiguity, we'd then also want to
#    rename the existing mandatory "conf_filepath" parameter to
#    "trg_conf_filepath".
#  * Refactoring the currently concrete "simconfclser.SimConfTestInternal"
#    subclass into an abstract subclass and then defining two new concrete
#    subclasses of "simconfclser.SimConfTestInternal":
#    * "SimConfTestInternalDefault", equivalent to the existing
#      "simconfclser.SimConfTestInternal" implementation (i.e., sourcing
#      BETSE's default simulation configuration).
#    * "SimConfTestInternalCompat", sourcing the above compatibility-specific
#      configuration.
#
#While either certainly work, first approach outlined above strikes as the
#more general-purpose and hence useful. After all, given how painful this issue
#has ultimately become, we'd prefer to avoid revisitting it... ever. This needs
#to be done right the first time -- and then never again.
#FIXME: Absolutely. The first approach is the correct approach, largely because
#we only ever instantiate the "SimConfTestInternal" once throughout the entire
#codebase. In synopsis, do this:
#
#* Refactor the "betse.science.config.confio" submodule as detailed there.
#* Generalize the simconfclser.SimConfTestInternal.__init__() method as
#  follows:
#  * Rename the "conf_filepath" parameter to "trg_conf_filepath".
#  * Define a new mandatory "src_conf_filename" parameter.
#* Replace the only call to the SimConfigTestWrapper.make_default() class
#  method with a call to whatever we've refactored "confio" into.
#* Remove the SimConfigTestWrapper.make_default() class method.
#* Refactor this fixture to leverage "SimConfTestInternal" directly, passing
#  the equivalent of
#  "src_conf_filename='betse_test/data/v0.5.0/yaml/sim_config.yaml'".
#* Reduce the conftest.pytest_addoption() hook to a noop.
#* Remove all references to the public
#  "betse_test.conftest.EXPORT_SIM_CONF_DIRNAME" global.
#* Remove the "betse_test.func.sim.test_sim_export.py" submodule.
@fixture
def betse_sim_conf_compat(
    betse_temp_dir: LocalPath) -> SimConfTestExternal:
    '''
    Per-test fixture creating and returning an object encapsulating a temporary
    simulation configuration file (complete with a pickled seed,
    initialization, and simulation) produced by the oldest version of this
    application for which the current version of this application guarantees
    backward compatibility.

    Caveats
    ----------
    Unlike the object returned by the comparable :func:`betse_sim_conf`
    fixture, the object returned by this fixture is *not* safely modifiable by
    the current version of this application. Doing so would invalidate the
    pickled files produced by the older version of this application, which
    would largely defeat the purpose of invoking this fixture.

    Parameters
    ----------
    betse_temp_dir : LocalPath
        Object embodying a temporary directory isolated to the current test.

    Returns
    ----------
    SimConfTestExternal
        Test-specific object encapsulating a temporary simulation configuration
        file specific to the current test, complete with pickled seed,
        initialization, and simulation files produced by the older version of
        this application.
    '''

    # Defer heavyweight imports.
    from betse import metadata
    from betse.util.app.meta import appmetaone
    from betse.util.io.log import logs
    from betse.util.os.shell import shelldir
    from betse.util.path import gits
    from betse.util.path.command import cmdrun
    from betse.util.py import pys

    # Character uniquely padding all banners logged below.
    BANNER_PADDING = '*'

    # Absolute path of the top-level temporary directory isolated to this test.
    betse_temp_dirname = str(betse_temp_dir)

    # ..................{ PHASE                             }..................
    # Log a single-line terminal banner identifying the initial fixture phase.
    logs.log_banner(title='PHASE 1: shallow git clone', padding=BANNER_PADDING)

    # Absolute pathname of this application's Git-based working tree. Since
    # this test suite should only every be run from within a working tree, this
    # retrieval should *ALWAYS* succeed.
    git_worktree_dirname = appmetaone.get_app_meta().git_worktree_dirname

    # Absolute path of a temporary non-existing directory isolated to this test
    # to clone the older version of this application into.
    betse_old_dirpath = betse_temp_dir.join('betse_old')
    betse_old_dirname = str(betse_old_dirpath)

    # Shallowly clone from the tag referring to the older version of this
    # application in this Git working tree into this temporary directory.
    gits.clone_worktree_shallow(
        branch_or_tag_name=metadata.GIT_TAG_OLDEST_BACKWARD_COMPATIBILITY,
        src_dirname=git_worktree_dirname,
        trg_dirname=betse_old_dirname,
    )

    # ..................{ PHASE                             }..................
    # Log a single-line terminal banner identifying the next fixture phase.
    logs.log_banner(title='PHASE 2: sim config export', padding=BANNER_PADDING)

    # Name of the functional test exporting an obsolete simulation
    # configuration from this older version.
    test_cli_sim_export_name = 'test_cli_sim_export'

    # Absolute path of the simulation configuration file exported by this test
    # into a temporary directory isolated to the current test.
    sim_conf_old_filepath = betse_temp_dir.join(
        test_cli_sim_export_name, 'sim_config.yaml')
    sim_conf_old_filename = str(sim_conf_old_filepath)

    # List of one or more shell words unambiguously running the executable
    # specific to the active Python interpreter and machine architecture.
    py_command_line_prefix = pys.get_command_line_prefix()

    # List of shell words comprising the "py.test"-based command exporting this
    # old simulation configuration.
    export_sim_conf_old_command = py_command_line_prefix + [
        'setup.py', 'test',
        '-k', test_cli_sim_export_name,
        '--export-sim-conf-dir', betse_temp_dirname,
    ]

    # Temporary change to the directory containing this "setup.py" script.
    with shelldir.setting_cwd(betse_old_dirname):
        # Export this old simulation configuration with this script.
        cmdrun.run_or_die(command_words=export_sim_conf_old_command)

    # Test-specific object encapsulating this simulation configuration file.
    sim_state = SimConfTestExternal(conf_filename=sim_conf_old_filename)

    # ..................{ PHASE                             }..................
    # Log a single-line terminal banner identifying the final fixture phase.
    logs.log_banner(title='PHASE 3: sim config test', padding=BANNER_PADDING)

    # Return this object.
    return sim_state
