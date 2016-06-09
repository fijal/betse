#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Abstract base classes of all channel classes.
'''

# ....................{ IMPORTS                            }....................
from abc import ABCMeta, abstractmethod
import numpy as np
from betse.science import sim_toolbox as stb

# ....................{ BASE                               }....................
class ChannelsABC(object, metaclass=ABCMeta):
    '''
    Abstract base class of all channel classes.

    Attributes
    ----------
    '''

    @abstractmethod
    def init(self, dyna, sim, cells, p):
        '''
        Runs the initialization sequence for a voltage gated ion channel.
        '''
        pass

    @abstractmethod
    def run(self, dyna, sim, cells, p):
        '''
        Runs the voltage gated ion channel.
        '''
        pass

    def update_charge(self, ion_index, delta_Q, targets, sim, cells, p):

        """
        A general helper function to update charge in the cell and environment
        given a flux derived from the Hodgkin-Huxley equivalent circuit model.

        Parameters
        ----------------
        ion_index:  index of an ion in the sim module (i.e. sim.iNa, sim.iK, sim.iCl, etc)
        delta_Q:    Hodgkin-Huxkley flux for the channel state
        targets:    Indices to the cell membrane targets for the channel (e.g. dyna.targets_vgNa)
        sim:        Instance of sim object
        cells:      Instance of cells object
        p:          Instances of params object

        """

        # multiply by the distribution of channels, for the case where electrophoresis/osmosis of channels
        # is simulated. This will simulate an uneven distribution of the channel on the membrane.
        delta_Q = sim.rho_channel*delta_Q

        # update charge in the cell and environment, assuming a trans-membrane flux occurs due to open channel state,
        # which is described by the original Hodgkin Huxley equation.

        # update the fluxes across the membrane to account for charge transfer from HH flux:
        sim.fluxes_mem[ion_index][targets] = delta_Q

        # update the concentrations of Na in cells and environment using HH flux delta_Q:
        # first in cells:
        sim.cc_mems[ion_index][targets] = (
            sim.cc_mems[ion_index][targets] +
            delta_Q * (cells.mem_sa[targets] / cells.mem_vol[targets]) * p.dt)

        if p.sim_ECM is False:

            # transfer charge directly to the environment:
            sim.cc_env[ion_index][targets] = (
                sim.cc_env[ion_index][targets] -
                delta_Q * (cells.mem_sa[targets] / cells.mem_vol[targets]) * p.dt)

            # assume auto-mixing of environmental concs
            sim.cc_env[ion_index][:] = sim.cc_env[ion_index].mean()

        else:

            flux_env = np.zeros(sim.edl)
            flux_env[cells.map_mem2ecm][targets] = -delta_Q

            # save values at the cluster boundary:
            bound_vals = flux_env[cells.ecm_bound_k]

            # set the values of the global environment to zero:
            flux_env[cells.inds_env] = 0

            # finally, ensure that the boundary values are restored:
            flux_env[cells.ecm_bound_k] = bound_vals

            # Now that we have a nice, neat interpolation of flux from cell membranes, multiply by the,
            # true membrane surface area in the square, and divide by the true ecm volume of the env grid square,
            # to get the mol/s change in concentration (divergence):
            delta_env = (flux_env * cells.memSa_per_envSquare) / cells.true_ecm_vol

            # update the concentrations:
            sim.cc_env[ion_index][:] = sim.cc_env[ion_index][:] + delta_env * p.dt

        # update the concentration intra-cellularly:
        sim.cc_mems[ion_index], sim.cc_cells[ion_index], _ = stb.update_intra(sim, cells, sim.cc_mems[ion_index],
            sim.cc_cells[ion_index], sim.D_free[ion_index], sim.zs[ion_index], p)

        # recalculate the net, unbalanced charge and voltage in each cell:
        sim.update_V(cells, p)

    def clip_flux(self, delta_Q, threshold = 1.0e-4):
        """
        Clips flux so that it remains within stable limits of the BETSE model
        for a reasonable time step.

        delta_Q:  Flux
        threshold: Flux is clipped to within +/- threshold

        """

        inds_over = (delta_Q > threshold).nonzero()
        delta_Q[inds_over] = threshold

        inds_under = (delta_Q < -threshold).nonzero()
        delta_Q[inds_under] = -threshold

        return delta_Q

