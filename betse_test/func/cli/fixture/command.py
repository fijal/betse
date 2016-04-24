#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
External command fixtures.

These fixtures automate testing of the current versions of BETSE's externally
runnable CLI and GUI commands (e.g., `betse`, `betse-qt4`) in subprocesses of
the current test process, regardless of whether these commands have been
editably installed (i.e., as synchronized symlinks rather than desynchronized
copies) into the current Python environment or not.
'''

# ....................{ IMPORTS                            }....................
from pytest import fixture

# ....................{ FIXTURES ~ low-level               }....................
#FIXME: Run "python3 -m betse.cli.__main__". Questions include:
#
#* How do we get the absolute path of the currently running Python interpreter,
#  for use in rerunning this exact same interpreter?

# Command execution is
@fixture(scope='function')
def betse_command(tmpdir_factory, request) -> 'py.path.local':
    '''
    Context manager-driven fixture creating and returning the absolute path of a
    temporary simulation configuration file specific to the parent fixture, with
    contents identical to that of the default simulation configuration.

    On completion of this test session, the parent directory of this file will
    be recursively deleted.

    This private fixture is intended to be used _only_ by public fixtures
    creating and returning the absolute paths of temporary simulation
    configuration files specific to those fixtures. To isolate each such file to
    its corresponding fixture, each filename returned by this fixture resides in
    a subdirectory of the session-wide temporary directory with basename the
    name of the parent fixture excluding suffixing `_sim_config_filename`.

    For example, when called by the public parent fixture
    `default_sim_config_filename()`, this fixture returns the filename
    `{tmpdir}/default/sim_config.yaml` (e.g.,
    `/tmp/pytest-0/default/sim_config.yaml`), where `{tmpdir}` is the absolute
    path of the session-wide temporary directory (e.g., `/tmp/pytest-0/`).

    Parameters
    ----------
    tmpdir_factory : ???
        Builtin session-scoped fixture whose `mktemp()` method returns a
        `py.path.local` instance encapsulating a new temporary subdirectory.
    request : FixtureRequest
        Builtin fixture parameter describing the parent fixture or test of this
        fixture (and similar contextual metadata).

    Returns
    ----------
    py.path.local
        Absolute path of a temporary simulation configuration file specific to
        the parent fixture as a `py.path.local` instance, defining an
        object-oriented superset of the non-object-oriented `os.path` module.

    See Also
    ----------
    http://pytest.org/latest/tmpdir.html#the-tmpdir-factory-fixture
        Official `tmpdir_factory` fixture parameter documentation.
    https://pytest.org/latest/builtin.html#_pytest.python.FixtureRequest
        Official `request` fixture parameter documentation.
    '''

    # This module's importation imports dependencies and is hence delayed.
    from betse_test_func.context.context import SimTestContext

    #FIXME: Ah ha! While there's no direct means of finding this name, there is
    #a sneaky alternative: search the "request.fixturenames" list for the set of
    #all fixture names suffixed by "_sim_config_file". This set should contain
    #exactly one element. If it doesn't, raise an exception! Done.

    # Prefix of the name of the parent fixture preceding "_sim_config_file".
    # sim_config_type = request.fixturename

    # Absolute path of the parent directory of this configuration file,
    # specific to the parent fixture.
    sim_config_dirname = tmpdir_factory.mktemp(sim_config_type)

    #FIXME: Return an instance of "SimTestConfig" instead.

    # Absolute path of this configuration file.
    sim_config_filename = sim_config_dirname.join('sim_config.yaml')

    #FIXME: Implement me!

    # Create this file with the default configuration.
    # create_config_file_default(sim_config_filename)

    # Return this path. Since this path's parent directory resides in the
    # session-wide temporary directory, py.test guaranteeably recursively
    # deletes this path's parent directory on session completion *WITHOUT* any
    # explicit intervention (e.g., via finalizers) on our part. Isn't that nice?
    return sim_config_filename
