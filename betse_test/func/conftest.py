#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright 2014-2019 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

# ....................{ IMPORTS ~ fixture                 }....................
'''
Global functional test configuration for BETSE's command-line interface (CLI).

``py.test`` implicitly imports all functionality defined by this module into
all CLI-specific functional test modules. Since this functionality now includes
all publicly declared functional fixtures in this ``fixture`` subpackage, these
tests may reference these fixtures without explicit imports.
'''

# ....................{ IMPORTS ~ fixture                 }....................
from betse_test.func.fixture.clier import betse_cli
