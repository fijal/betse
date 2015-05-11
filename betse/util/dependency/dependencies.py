#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

'''
High-level **dependency** (i.e., both mandatory and optional Python packages
imported at runtime) facilities.

This module provides functions intended to be called by high-level interface
modules (e.g., `betse.cli.cli`) *before* attempting to import such dependencies.
'''

#FIXME: Refactor as follows:
#
#* Create a new subpackage "betse.util.dependency".
#* Split this module into two modules:
#  * "betse.util.dependency.dependencies", providing the exception handling
#    function.
#  * "betse.util.dependency.matplotlib", providing the matplotlib-specific
#    functions.
#
#Hence, this module survives, albeit in *EXTREMELY* limited form. That's fine,
#for now. (Better minimal than overkill, we should think.)

#FIXME: It'd be great to raise human-readable exceptions on the specified
#backends *NOT* being available. This is certainly feasible, as the
#following stackoverflow answer demonstrates -- if somewhat involved:
#    https://stackoverflow.com/questions/5091993/list-of-all-available-matplotlib-backends
#That said, we really want to do this *ANYWAY* to print such list when running
#"betse info". So, let's just get this done, please.

# ....................{ IMPORTS                            }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable exceptions on missing mandatory dependencies,
# the top-level of this module may import *ONLY* from packages guaranteed to
# exist at installation time (e.g., stock Python packages).
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from betse import metadata
from betse.util.dependency import matplotlibs
from betse.util.python import modules
from collections import OrderedDict

# ....................{ GETTERS                            }....................
def get_metadata() -> OrderedDict:
    '''
    Get an ordered dictionary synopsizing all currently installed dependencies.
    '''
    # Imports deferred to their point of use, as documented above.
    import matplotlib, numpy, scipy

    # Get such dictionary.
    return OrderedDict((
        ('matplotlib version', matplotlib.__version__),
        ('numpy version', numpy.__version__),
        ('scipy version', scipy.__version__),
    ))

# ....................{ INITIALIZERS                       }....................
def init() -> None:
    '''
    Initialize all mandatory runtime dependencies of `betse`.

    Specifically (in order):

    * Raise an exception unless all such dependencies are currently satisfiable.
    * Reconfigure `matplotlib` with sane defaults specific to the current
      system.
    '''
    # Ensure that all mandatory dependencies exist *BEFORE* subsequent logic
    # (possibly) importing such dependencies.
    die_unless_satisfiable()

    # Configure such dependencies.
    matplotlibs.config.init()

# ....................{ EXCEPTIONS                         }....................
def die_unless_satisfiable() -> None:
    '''
    Raise an exception unless mandatory runtime dependencies of `betse` are
    **satisfiable** (i.e., importable and of a satisfactory version).

    Equivalently, an exception is raised if at least one such dependency is
    unsatisfied.

    Specifically, this function unconditionally validates the existence of all
    such dependencies. For such dependencies with `setuptools`-specific metadata
    (e.g., `.egg-info/`-suffixed subdirectories of the `site-packages/`
    directory for the active Python 3 interpreter, typically created by
    `setuptools` at install time), this function additionally validates the
    versions of such dependencies to satisfy `betse` requirements.
    '''
    # Template for exception messages raised on missing dependencies.
    exception_template = 'Mandatory dependency "{}" not found.'

    # If the setuptools-specific "pkg_resources" dependency is missing, fail
    # *BEFORE* attempting to import such dependency below.
    modules.die_unless(
        module_name = 'pkg_resources',
        exception_message = exception_template.format('pkg_resources')
    )

    # Import such dependency and all required classes in such dependency.
    from pkg_resources import (Environment, VersionConflict, WorkingSet)
    import pkg_resources

    # Set of all betse-specific dependencies in a manner usable below.
    requirements = pkg_resources.parse_requirements(
        metadata.DEPENDENCIES_RUNTIME)

    # Set of all setuptools-installed Python packages available under the active
    # Python 3 interpreter.
    working_set = WorkingSet()

    # Helper for finding the former in the latter.
    environment = Environment(working_set.entries)

    # Validate each such dependency.
    for requirement_required in requirements:
        # Name of the top-level importable module provided by such project.
        module_name = requirement_required.project_name

        # If such dependency is missing, fail.
        if not modules.is_module(module_name):
            # If such dependency is "setuptools", reduce such dependency to
            # merely "pkg_resources" and try again. "pkg_resources" is a single
            # module installed with (but inexplicably outside of the package
            # tree of) setuptools. BETSE requires setuptools and hence
            # "pkg_resources" at install time but *ONLY* the latter at runtime.
            if module_name == 'setuptools':
                module_name = 'pkg_resources'

            # Try again.
            modules.die_unless(
                module_name, exception_template.format(
                    str(requirement_required)))

        # Else, such dependency exists.
        #
        # Best match for such dependency under the active Python 3 interpreter
        # if any or None otherwise.
        requirement_provided = environment.best_match(
            requirement_required, working_set)

        # If a match was found with version conflicting with that required,
        # fail.
        if requirement_provided is not None and\
           requirement_provided not in requirement_required:
               raise VersionConflict(
                   'Mandatory dependency {} required but only {} found.'.format(
                       requirement_required, requirement_provided))

# --------------------( WASTELANDS                         )--------------------
    # If the current operating system is Apple OS X, prefer the "CocoaAgg"
    # backend to the "MacOSX" backend. The former leverages the cross-platform
    # C++ library AGG (Anti-grain Geometry) and hence tends to be better
    # supported; the latter does not.
        #FUXME: Extract into a new packages.is_package_PyObjC() function.
        # If PyObjC is installed, enable the "CocoaAgg" backend, which
        # internally requires such dependency.
        #if modules.is_module('PyObjCTools'):
#           loggers.log_warning(
#               'Optional dependency "PyObjC" not found. '
#               'Falling back from matplotlib backend "CocoaAgg" to "MacOSX".'
#           )
#           matplotlib.use('macosx')

        #FUXME: Alternately, perhaps we want to redirect
            # exception_template.format(metadata.DEPENDENCY_SETUPTOOLS)
    # List of setuptools requirements strings signifying all safely testable
    # mandatory dependencies. Sadly, the following mandatory dependencies are
    # *NOT* safely testable:
    #
    # * PySide. Under numerous Linux distributions, PySide is installed with
    #   cmake rather than setuptools
    # 'pyside >= 1.2.0',

#FUXME: Implement setuptools-based version checking as well, for dependencies
#providing setuptools-specific egg metadata. stackoverflow offered the following
#useful example code:
#
#    from pkg_resources import (WorkingSet, DistributionNotFound)
#    working_set = WorkingSet()
#
#    # Printing all installed modules
#    print tuple(working_set)
#
#    # Detecting if module is installed
#    try:
#        dep = working_set.require('paramiko>=1.0')
#    except DistributionNotFound:
#        pass
#
#Given that, consider the following approach:
#
#    import metadata
#    import pkg_resources
#    from pkg_resources import (
#        DistributionNotFound, Environment, VersionConflict, WorkingSet)
#    working_set = WorkingSet()
#    environment = Environment(working_set.entries)
#    requirements = pkg_resources.parse_requirements(
#        metadata.REQUIREMENTS)
#    for requirement in requirements:
#        if not importlib.find_loader(requirement.project_name):
#            raise DistributionNotFound(
#                "Mandatory dependency {} not found.".format(requirement))
#            )
#
#        requirement_distribution = environment.best_match(
#            requirement, working_set)
#
#        # Oops, the "best" so far conflicts with a dependency.
#        if requirement_distribution and\
#           requirement_distribution not in requirements:
#               raise VersionConflict(
#                   "Mandatory dependency {} found but {} required.".format(
#                       requirement_distribution, requirement))
#
#The above *SHOULD* work, but assumes use of a new
#"metadata.install_requirements" module dict. Not terribly arduous, of course;
#merely shift such dict from its current use in "setup.py".

        # if not importlib.find_loader(requirement.project_name):
        #     raise DistributionNotFound(
        #         'Mandatory dependency {} not found.'.format(requirement))
    # for module_name in {
    #     'scipy'
    # }:
    # For each such dependency, this function also attempts to validate such
    # dependency's version. Specifically, if such dependency both exists *and*,
    # an exception is raised if

    # Caveats
    # ----------
    # Dependency versions are *not* validated. This is subject to change