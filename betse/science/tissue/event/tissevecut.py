#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
High-level classes aggregating all parameters pertaining to simulation events.
'''

# ....................{ IMPORTS                            }....................
from betse.exceptions import BetseMethodUnimplementedException
from betse.science.config.event.eventabc import SimEventSpikeABC
from betse.util.io.log import logs
from betse.util.type.types import (
    type_check, NoneType, NumericTypes, SequenceTypes)

# ....................{ SUBCLASSES                         }....................
class SimEventCut(SimEventSpikeABC):
    '''
    **Cutting event** (i.e., event removing a region of the current cluster at
    some time step during the simulation phase).

    Attributes
    ----------
    profile_names : list
        List of the names of all applicable cut profiles, each describing a
        subset of the cell population to be removed.
    '''

    # ..................{ PUBLIC                             }..................
    @type_check
    def __init__(
        self,
        profile_names: SequenceTypes,
        time: NumericTypes,
    ) -> None:

        # Initialize our superclass.
        super().__init__(time)

        # Classify all passed parameters.
        self.profile_names = profile_names


    #FIXME: Refactor the handler.removeCells() function into this method. Before
    #we do so, note that this will require refactoring this method's signature
    #everywhere to resemble:
    #    def fire(
    #        self,
    #        sim: 'Simulation',
    #        cells: 'Cells',
    #        p: 'Parameters',
    #        t: NumericTypes,
    #    ) -> None:
    @type_check
    def fire(self, sim: 'betse.science.sim.Simulator', t: NumericTypes) -> None:
        raise BetseMethodUnimplementedException()

# ....................{ MAKERS                             }....................
@type_check
def make(p: 'betse.science.parameters.Parameters') -> (SimEventCut, NoneType):
    '''
    Create and return a new :class:`SimEventCut` instance if enabled by the
    passed simulation configuration *or* ``None`` otherwise.

    Parameters
    ----------
    p : Parameters
        Current simulation configuration.

    Returns
    ----------
    SimEventCut, NoneType
        Either:
        * If enabled by the passed simulation configuration, a new
          :class:`SimEventCut` instance.
        * Else, ``None``.
    '''

    # Object to be returned, defaulting to nothing.
    action = None

    ce = p._conf['cutting event']

    # If this event is enabled, create an instance of this class.
    if bool(ce['event happens']):
        #FIXME: Terrible check. Rather than simply test the emptiness of the
        #"profiles" list, actually iterate through the "profile_names" parameter
        #in the SimEventCut.__init__() method and ensure that each listed
        #profile name actually exists in the "profiles" list. Hence, this entire
        #check should be shifted there. After doing so, this entire function
        #should ideally be removed. It's terrible. I hate these make()-style
        #factory functions, which only obfuscate the codebase.

        # If profiles are enabled, parse this event.
        if p.is_tissue_profiles:
            action = SimEventCut(
                # Time step at which to cut. For simplicity, this is coerced
                # to be the start of the simulation.
                time=0.0,
                profile_names=ce['apply to'],
            )
        # Else, log a non-fatal warning.
        else:
            logs.log_warning(
                'Ignoring cutting event, as cut profiles are disabled.')

    return action