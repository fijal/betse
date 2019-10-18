#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Low-level custom :mod:`setuptools`-specific :class:`ScriptWriter` monkey patch.
'''

# ....................{ IMPORTS                           }....................
from betse.lib.setuptools.command import supcommand
from betse.util.io import stderrs
from betse.util.type.cls import classes
from betse.util.type.types import (
    type_check, CallableTypes, ClassType, SetType, StrOrNoneTypes)
from distutils.errors import DistutilsClassError
from pkg_resources import Distribution
from setuptools.command.develop import VersionlessRequirement
from setuptools.command.easy_install import ScriptWriter

# ....................{ GLOBALS                           }....................
_PACKAGE_NAMES = None
'''
Unordered set of the fully-qualified names of all top-level Python
packages whose entry points are to be monkey-patched.

Our monkey-patched implementation of the :meth:`ScriptWriter.get_args` class
method defers to the original implementation of that method for all packages
to be installed *except* these packages. For both safety and sanity, entry
points for *all* other packages remain unaffected.
'''


_SCRIPTWRITER_GET_ARGS_OLD = None
'''
Original (i.e., pre-monkey-patched) implementation of the
:meth:`ScriptWriter.get_args` class method, which our monkey-patch
implementation conditionally calls as needed.
'''

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

# ....................{ INITIALIZERS                      }....................
@type_check
def init(
    package_names: SetType,
    scriptwriter_get_args_old: CallableTypes,
) -> None:
    '''
    Initialize this submodule.

    Specifically, this function monkey patches the
    :class:`setuptools.command.easy_install.ScriptWriter` class for improved
    usability of the script wrapper dynamically generated by this class (e.g.,
    ``/usr/bin/betse`` for BETSE on Linux), particularly for editable
    installations via either:

    * This application's POSIX-specific ``symlink`` subcommand.
    * The builtin ``develop`` subcommand bundled with :mod:`setuptools`.

    The default :class:`ScriptWriter` implementation writes scripts attempting
    to import :mod:`setuptools`-installed package resources for installed
    packages. Since no such resources are installed for editable installations,
    these scripts *always* fail and hence are suitable only for use in
    user-specific venvs.

    This submodule amends this deficiency, albeit at a minor cost of ignoring
    the package resources provided by Python packages installed in the standard
    way. Although alternatives exist, this is the most robust means of
    preserving backward compatibility with older :mod:`setuptools` versions.

    Parameters
    ----------
    package_names : SetType
        Unordered set of the fully-qualified names of all top-level Python
        packages whose entry points are to be monkey-patched. Entry points for
        *all* other packages remain unaffected, for both safety and sanity.
    scriptwriter_get_args_old : CallableTypes
        Original (i.e., pre-monkey-patched) implementation of the
        :meth:`ScriptWriter.get_args` class method.
    '''

    # Globals to be defined below.
    global _PACKAGE_NAMES, _SCRIPTWRITER_GET_ARGS_OLD

    # print(
    #     'Monkey-patching class method '
    #     'setuptools.command.easy_install.ScriptWriter.get_args()...')

    # If this install of setuptools does *NOT* define a "ScriptWriter" class
    # defining the subsequently monkey-patched class method, this install is
    # either broken *OR* of an unsupported version. In either case, raise an
    # exception.
    if not hasattr(ScriptWriter, 'get_args'):
        raise DistutilsClassError(
            'Class method '
            'setuptools.command.easy_install.ScriptWriter.get_args() not '
            'found. The current version of setuptools is either broken '
            '(unlikely) or unsupported (likely).'
        )

    # Preserve all passed package names.
    _PACKAGE_NAMES = package_names

    # Preserve the existing implementation of this class method, which our
    # monkey-patch implementation conditionally calls as needed.
    _SCRIPTWRITER_GET_ARGS_OLD = scriptwriter_get_args_old

    # Monkey-patch this class method.
    ScriptWriter.get_args = _scriptwriter_get_args_patched

# ....................{ PATCHES                           }....................
# Functions monkey-patching existing methods of the "ScriptWriter" class above
# and hence defined to have the same method signatures. The "cls" parameter
# implicitly passed to such methods by the @classmethod decorator is guaranteed
# to be the "ScriptWriter" class.

@classmethod
@type_check
def _scriptwriter_get_args_patched(
    cls: ClassType,
    distribution: (Distribution, VersionlessRequirement),
    script_shebang: StrOrNoneTypes = None,
):
    '''
    Monkey-patched :meth:`ScriptWriter.get_args` class method, iteratively
    yielding :meth:`ScriptWriter.write_script` argument tuples for the passed
    distribution's **entry points** (i.e., platform-specific executables
    running this distribution).

    Parameters
    ----------
    cls : ClassType
        The :class:`ScriptWriter` class.
    distribution : (Distribution, VersionlessRequirement)
        Object collecting metadata on the **distribution** (i.e.,
        :mod:`setuptools`-installed Python project) to create these entry
        points for. If the end user invoked the :mod:`setuptools` subcommand:

        * ``develop``, then this object is an instance of the
          :mod:`setuptools`-specific :class:`VersionlessRequirement` class.
          Confusingly, note that this class effectively wraps the underlying
          :mod:`pkg_resources`-specific :class:`Distribution` class as a
          transparent class proxy. Why, :mod:`setuptools:`. Why.
        * ``install``, then this object is an instance of the
          :mod:`pkg_resources`-specific :class:`Distribution` class.
          Confusingly, note that this class has no relationship whatsoever to
          the identically named :class:`distutils.dist.Distribution` and
          :class:`setuptools.dist.Distribution` classes.
    script_shebang : StrOrNoneTypes
        Platform-specific shebang line with which to prefix the contents of all
        entry points installed by this method. Defaults to ``None``.
    '''

    # If this class method is called by a class that is neither "ScriptWriter"
    # nor a subclass thereof, raise an exception.
    classes.die_unless_subclass(subclass=cls, superclass=ScriptWriter)

    # If this distribution does *NOT* correspond to a package whose entry
    # points are to be monkey-patched by this method, then the current call to
    # this method is attempting to install an external dependency of this
    # application rather than this application itself. In this case...
    if distribution.project_name not in _PACKAGE_NAMES:
        # print(
        #     'Distribution "{}" unrecognized; '
        #     'defaulting to unpatched installation logic.'.format(
        #         distribution.project_name))

        # Defer to the original implementation of this method.
        yield from _SCRIPTWRITER_GET_ARGS_OLD(distribution, script_shebang)
        return

    # Print this monkey-patch.
    print(
        'Installing monkey-patched entry points '
        'for distribution "{}"...'.format(distribution.project_name))

    # Default this shebang line if unpassed.
    if script_shebang is None:
        script_shebang = cls.get_header()

    # For each entry point of this distribution...
    for script_basename, script_type, entry_point in (
        supcommand.iter_package_distribution_entry_points(distribution)):
        # If this entry point provides the name of the main function in this
        # entry module to be called, define script code calling this function.
        if len(entry_point.attrs):
            script_entry_func_code = _SCRIPT_ENTRY_FUNC_SUBTEMPLATE.format(
                entry_func=entry_point.attrs[0])
        # Else, default this script code to the empty string.
        else:
            script_entry_func_code = ''

            # Print a non-fatal warning, as the resulting script may *NOT*
            # necessarily be runnable or freezable as expected.
            stderrs.output_warning(
                'Entry module "{}" entry function undefined.'.format(
                entry_point.module_name))

        # Script contents, formatted according to this template.
        script_code = _SCRIPT_TEMPLATE.format(
            # Script code calling this entry module's main function.
            entry_func_code=script_entry_func_code,

            # Fully-qualified name of this entry module's root parent package.
            entry_package_root=entry_point.module_name.split('.')[0],

            # Fully-qualified name of this entry module.
            entry_module=entry_point.module_name,
        )

        # Yield a tuple containing this metadata to the caller.
        for script_tuple in cls._get_script_args(
            script_type, script_basename, script_shebang, script_code):
            yield script_tuple
