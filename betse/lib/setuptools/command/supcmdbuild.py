#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level custom :mod:`setuptools`-specific :class:`ScriptWriter` monkey patch.

Motivation
----------
This submodule monkey patches the
:class:`setuptools.command.easy_install.ScriptWriter` class for improved
usability of the script wrapper dynamically generated by this class (e.g.,
``/usr/bin/betse`` for BETSE on Linux), particularly for editable installations
via either:

* This application's POSIX-specific ``symlink`` subcommand.
* The builtin ``develop`` subcommand bundled with :mod:`setuptools`.

The default :class:`ScriptWriter` implementation writes scripts attempting to
import :mod:`setuptools`-installed package resources for installed packages.
Since no such resources are installed for editable installations, these scripts
*always* fail and hence are suitable only for use in user-specific venvs.

This submodule corrects this deficiency, albeit at a minor cost of ignoring the
package resources provided by Python packages installed in the customary way.
While there exist alternatives, this appears to be the most robust means of
maintaining backward compatibility with older :mod:`setuptools` versions.
'''

#FIXME: Implement us up, please.

# ....................{ IMPORTS                           }....................
import sys
from betse.exceptions import BetseTestException
from betse.lib.setuptools.command import supcommand
from setuptools import Command

# ....................{ ADDERS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable exceptions on missing mandatory
# dependencies, the top-level of this module may import *ONLY* from packages
# guaranteed to exist at installation time -- which typically means *ONLY*
# BETSE packages and stock Python packages.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def add_subcommand(setup_options: dict, custom_metadata: dict) -> None:
    '''
    Add the custom ``test`` :mod:`setuptools` subcommand to the passed
    dictionaries of :mod:`setuptools` options and arbirtrary metadata.
    '''

    pass

# ....................{ CONSTANTS                         }....................
_SCRIPT_TEMPLATE = '''
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.
#
# --------------------( SYNOPSIS                          )--------------------
# This script is auto-generated by the "build_scripts" setuptools subcommand
# monkey-patched by the application-specific "betse_setup.build" submodule.
#
# Welcome to the theatre of the absurd.

# ....................[ IMPORTS                           ]....................
import importlib, sys

# ....................[ TESTERS                           ]....................
def is_module_root(module_name: str) -> bool:
    """
    ``True`` only if the Python module with the passed fully-qualified name is
    a **top-level module** (i.e., module whose name contains no ``.``
    delimiters) importable under the active Python interpreter.

    If this is *not* a top-level module, an exception is raised. If this
    top-level module is *not* importable via the standard
    :func:`importlib.find_loader` mechanism (e.g., the OS X-specific
    :mod:`PyObjCTools` package), this module may be imported by this function
    as an unwanted side effect.
    """
    assert isinstance(module_name, str), (
        '"{{}}" not a string.'.format(module_name))

    # If this is *NOT* a top-level module, raise an exception.
    if '.' in module_name:
        raise ImportError(
            'Module "{{}}" not top-level.'.format(module_name))

    # Attempt to...
    #
    # Note that most of the following logic has been copied from the
    # betse.util.py.module.pymodname.is_module() function, excluding
    # explanatory commentary.
    try:
        # If the importlib.util.find_spec() function exists, this *MUST* be
        # Python >= 3.4. In this case, call this function to avoid deprecation
        # warnings induced by calling the comparable (albeit obsolete)
        # importlib.find_loader() function.
        if hasattr(importlib.util, 'find_spec'):
            return importlib.util.find_spec(module_name) is not None
        # Else, this *MUST* be Python <= 3.3. In this case, call the obsolete
        # importlib.find_loader() function.
        else:
            return importlib.find_loader(module_name) is not None
    except ValueError:
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

# ....................[ MAIN                              ]....................
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
            'Package "{entry_package_root}" unimportable. '
            'Consider re-running either:\\n\\n'
            '\\tsudo python3 setup.py install\\n'
            '\\tsudo python3 setup.py develop\\n'
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
Script template to be formatted by the
:meth:`ScriptWriterSimple.get_script_args` method.
'''


_SCRIPT_ENTRY_FUNC_SUBTEMPLATE = '''
    # If this module requires an entry function to be run, call this function.
    # For POSIX compliance, propagate the value returned by this function
    # (ideally a single-byte integer) back to the calling process as this
    # script's exit status.
    sys.exit(entry_module.{entry_func}())
'''
'''
Script subtemplate to be formatted by the
:meth:`ScriptWriterSimple.get_script_args` method for entry points requiring an
entry function to be called.

This excludes entry points for which merely importing the desired entry module
suffices to implicitly run that entry point -- typically, entry modules with
basename ``__main__``.
'''

