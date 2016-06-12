#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
BETSE-specific monkey patching of `setuptools`'s `ScriptWriter` class.

Such patching improves the usability of this class with respect to editable
installations packages (e.g., via BETSE's *nix-specific `symlink` subcommand or
setuptools' general-purpose `develop` subcommand). The default `ScriptWriter`
implementation writes scripts attempting to import the `setuptools`-installed
package resources for these packages. Since no such resources are installed for
editable installations, these scripts _always_ fail and hence are suitable
_only_ for use in user-specific venvs.

Such patching corrects this deficiency, albeit at a minor cost of ignoring the
package resources provided by Python packages installed in the customary way.
While there exist alternatives, this appears to be the most robust means of
maintaining backward compatibility with older `setuptools` versions.
'''

# ....................{ IMPORTS                            }....................
from distutils.errors import DistutilsClassError
from pkg_resources import Distribution
from betse_setup import util
from setuptools.command import easy_install
from setuptools.command.easy_install import ScriptWriter, WindowsScriptWriter

# ....................{ CONSTANTS                          }....................
SCRIPT_TEMPLATE = '''
# This script is auto-generated by the "build_scripts" setuptools subcommand
# monkey-patched by the BETSE-specific "betse_setup.build" submodule.
#
# Welcome to the theatre of the absurd.

import importlib, sys

def is_module_root(module_name: str) -> bool:
    """
    `True` only if the Python module with the passed fully-qualified name is a
    **top-level module** (i.e., module whose name contains no `.` delimiters)
    importable under the active Python interpreter.

    If this is _not_ a top-level module, an exception is raised. If this top-
    level module is _not_ importable via the standard `importlib.find_loader()`
    mechanism (e.g., the OS X-specific `PyObjCTools` package), this module may
    be imported by this function as an unwanted side effect.
    """
    assert isinstance(module_name, str), (
        '"{{}}" not a string.'.format(module_name))

    # If this is *NOT* a top-level module, raise an exception.
    if '.' in module_name:
        raise ImportError('Module "{{}}" not a top-level module.'.format(
            module_name))

    # See betse.util.py.modules.is_module() for implementation details.
    try:
        return importlib.find_loader(module_name) is not None
    except ValueError:
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

# If this script is run directly, do so.
if __name__ == '__main__':
    # If the root parent package of this entry module is unimportable, raise a
    # human-readable exception. For inscrutable reasons, testing for whether
    # this entry module itself is importable is highly non-trivial under Python
    # 3.3 but *NOT* Python >= 3.4. While requiring Python >= 3.4 above would
    # obviate this, such version requirements are best asserted in the main
    # application codebase. Instead, we defer to the next best test.
    if not is_module_root('{entry_package_root}'):
        raise ImportError(
            'Package "{entry_package_root}" unimportable. Consider running either:\\n'
            '\\tsudo python3 setup.py install\\n'
            '\\tsudo python3 setup.py symlink')

    # Import the entry module.
    import {entry_module} as entry_module

    # For debugging purposes, print the absolute path of this module.
    #print('{entry_module}: ' + entry_module.__file__)
    {entry_func_code}
# Else, this script is imported by another module rather than run directly. In
# this erroneous case, noop by printing a non-fatal warning and then returning.
# While this script should *NEVER* be imported, edge cases do happen.
else:
    print('WARNING: Entry point imported rather than run.', file=sys.stderr)
'''
'''
Script template to be formatted by `ScriptWriterSimple.get_script_args()`.
'''

SCRIPT_ENTRY_FUNC_SUBTEMPLATE = '''
    # If this module requires an entry function to be run, call this function.
    # For POSIX compliance, propagate the value returned by this function
    # (ideally a single-byte integer) back to the calling process as this
    # script's exit status.
    sys.exit(entry_module.{entry_func}())
'''
'''
Script subtemplate to be formatted by `ScriptWriterSimple.get_script_args()`
for entry points requiring an entry function to be called.

This excludes entry points for which merely importing the desired entry module
suffices to implicitly run that entry point -- typically, entry modules with
basename `__main__`.
'''

# ....................{ COMMANDS                           }....................
def add_setup_commands(metadata: dict, setup_options: dict) -> None:
    '''
    Add commands building distribution entry points to the passed dictionary of
    `setuptools` options.
    '''
    assert isinstance(setup_options, dict), (
        '"{}" not a dictionary.'.format(setup_options))

    # If neither of the class functions monkey-patched below exist, setuptools
    # is either broken or an unsupported newer version. In either case, an
    # exception is raised.
    if (not hasattr(ScriptWriter, 'get_args') and
        not hasattr(ScriptWriter, 'get_script_args')):
        raise DistutilsClassError(
            'Class "setuptools.command.easy_install.ScriptWriter" '
            'methods get_args() and get_script_args() not found. '
            'The current version of setuptools is either broken '
            '(unlikely) or unsupported (likely).'
        )

    # Monkey-patch the following class methods:
    #
    # * ScriptWriter.get_args(), defined by recent versions of setuptools.
    # * ScriptWriter.get_script_args(), defined by obsolete versions of
    #   setuptools.
    #
    # For convenience, our implementation of the latter is implemented in terms
    # of the former. Hence, the former is *ALWAYS* monkey-patched.
    ScriptWriter.get_args = _patched_get_args

    # If the ScriptWriter.get_script_args() class method exists, monkey-patch
    # both that *AND* the setuptools.command.easy_install.get_script_args()
    # alias referring to that method as well.
    if hasattr(ScriptWriter, 'get_script_args'):
        ScriptWriter.get_script_args = _patched_get_script_args
        easy_install.get_script_args = ScriptWriter.get_script_args

        # If the ScriptWriter.get_script_header() class method does *NOT*
        # exist, monkey-patch that method as well.
        if not hasattr(ScriptWriter, 'get_script_header'):
            ScriptWriter.get_script_header = _patched_get_script_header

# ....................{ PATCHES                            }....................
# Functions monkey-patching existing methods of the "ScriptWriter" class above
# and hence defined to have the same method signatures. The "cls" parameter
# implicitly passed to such methods by the @classmethod decorator is guaranteed
# to be the "ScriptWriter" class.

@classmethod
def _patched_get_args(
    cls: type,
    distribution: Distribution,
    script_shebang: str = None
):
    '''
    Yield `write_script()` argument tuples for the passed distribution's **entry
    points** (i.e., platform-specific executables running this distribution).

    This function monkey-patches the `ScriptWriter.get_args()` class function.
    '''
    # Default this shebang line if unpassed.
    if script_shebang is None:
        script_shebang = cls.get_header()

    assert isinstance(cls, type), '"{}" not a class.'.format(cls)
    assert isinstance(script_shebang, str), (
        '"{}" not a string.'.format(script_shebang))
    #print('In BETSE ScriptWriter.get_args()!')

    # For each entry point of this distribution...
    for script_basename, script_type, entry_point in (
        util.package_distribution_entry_points(distribution)):
        # If this entry point provides the name of the main function in this
        # entry module to be called, define script code calling this function.
        if len(entry_point.attrs):
            script_entry_func_code = SCRIPT_ENTRY_FUNC_SUBTEMPLATE.format(
                entry_func=entry_point.attrs[0])
        # Else, default this script code to the empty string.
        else:
            script_entry_func_code = ''

            # Print a non-fatal warning, as the resulting script may *NOT*
            # necessarily be runnable or freezable as expected.
            util.output_warning(
                'Entry module "{}" entry function undefined.'.format(
                entry_point.module_name))

        # Script contents, formatted according to such template.
        script_code = SCRIPT_TEMPLATE.format(
            # Script code calling this entry module's main function.
            entry_func_code=script_entry_func_code,

            # Fully-qualified name of this entry module's root parent package.
            entry_package_root=entry_point.module_name.split('.')[0],

            # Fully-qualified name of this entry module.
            entry_module=entry_point.module_name,
        )

        # Yield a tuple containing this metadata to the caller. Note that the
        # _get_script_args() method called here is *NOT* the
        # _patched_get_script_args() method defined below. Confusing, but true.
        for script_tuple in cls._get_script_args(
            script_type, script_basename, script_shebang, script_code):
            yield script_tuple


@classmethod
def _patched_get_script_args(
    cls: type,
    distribution: Distribution,
    executable = None,
    is_windows_vanilla: bool = False
):
    '''
    Yield `write_script()` argument tuples for the passed distribution's **entry
    points** (i.e., platform-specific executables running this distribution).

    This function monkey-patches the deprecated
    `ScriptWriter.get_script_args()` class function.
    '''
    assert isinstance(cls, type), '"{}" not a class.'.format(cls)
    # print('In BETSE ScriptWriter.get_script_args()!')

    # Platform-specific entry point writer.
    #
    # If the newer ScriptWriter.best() class function exists, obtain this
    # writer by calling this function.
    script_writer = None
    if hasattr(ScriptWriter, 'best'):
        script_writer = (
            WindowsScriptWriter if is_windows_vanilla else ScriptWriter).best()
    # Else, obtain this writer by calling the older ScriptWriter.get_writer()
    # class function.
    else:
        script_writer = cls.get_writer(is_windows_vanilla)

    # Shebang line prefixing the contents of this script.
    script_shebang = cls.get_script_header('', executable, is_windows_vanilla)

    # Defer to the newer get_args() method. Note that this is the
    # _patched_get_args() method defined above.
    return script_writer.get_args(distribution, script_shebang)


@classmethod
def _patched_get_script_header(cls: type, *args, **kwargs):
    '''
    Defer to the deprecated
    `setuptools.command.easy_install.get_script_header()` function under older
    versions of setuptools.
    '''

    from setuptools.command.easy_install import get_script_header
    return get_script_header(*args, **kwargs)
