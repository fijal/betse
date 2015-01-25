#!/usr/bin/env python3
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

"""
A toolbox of workhorse functions and routines used in the main simulation. This is the matrix version, which
implements the simulation in terms of Numpy arrays.

"""
# FIXME implement stability safety threshhold parameter checks and loss-of-stability detection + error message
# FIXME think about testing python loop (with numba jit) versus numpy matrix versions regarding speed...
# FIXME what if only some ions are desired instead of all 7 ???
# FIXME instead of saving lots of fields from Simulator, save the whole object + cells + p
# FIXME would be nice to have a time estimate for the simulation

import numpy as np
import os, os.path
import pickle
import copy
from random import shuffle
import warnings
from numba import jit


class Simulator(object):


    def __init__(self):

        self.fileHandling()

    def fileHandling(self):

        """
        Initializes file saving and loading directory as the betse cach.
        For now, automatically assigns file names, but later, will allow
        user-specified file names.

        """

        # Make the BETSE-specific cache directory if not found.
        betse_cache_dir = os.path.expanduser("~/.betse/cache")
        os.makedirs(betse_cache_dir, exist_ok=True)

        # Pickle initial data files into cache directory:
        self.cellConc_init = os.path.join(betse_cache_dir, 'cellConc_init.pickle')
        self.envConc_init = os.path.join(betse_cache_dir, 'envConc_init.pickle')
        self.cellGeom_init = os.path.join(betse_cache_dir, 'cellgeom_init.pickle')
        self.params_init = os.path.join(betse_cache_dir, 'params_init.pickle')

        # Pickle simulation data files into cache directory:
        self.cellConc_sim = os.path.join(betse_cache_dir, 'cellConc_sim.pickle')
        self.envConc_sim = os.path.join(betse_cache_dir, 'envConc_sim.pickle')
        self.cellGeom_sim = os.path.join(betse_cache_dir, 'cellgeom_sim.pickle')
        self.params_sim = os.path.join(betse_cache_dir, 'params_sim.pickle')

        self.cellConc_attimes = os.path.join(betse_cache_dir, 'cellConc_attimes.pickle')
        self.cellVm_attimes = os.path.join(betse_cache_dir, 'cellVm_attimes.pickle')
        self.storedtimes = os.path.join(betse_cache_dir, 'storedtimes.pickle')

    def baseInit(self,cells,p):
        """
        Creates a host of initialized data matrices for the main simulation,
        including intracellular and environmental concentrations, voltages, and specific
        diffusion constants.

        """

        # whether to use the unique volume and surface area of cells or a single average value:
        if p.true_volume == None or p.true_volume==0:

            self.volcelli = np.mean(cells.cell_vol,axis=0)
            self.sacelli = np.mean(cells.cell_sa,axis=0)

            self.volcell = np.zeros(len(cells.cell_i))
            self.volcell[:]=self.volcelli

            self.sacell = np.zeros(len(cells.cell_i))
            self.sacell[:]=self.sacelli

        elif p.true_volume == 1:

            self.volcell = cells.cell_vol
            self.sacell = cells.cell_sa

        # Initialize cellular concentrations of ions:
        cNa_cells = np.zeros(len(cells.cell_i))
        cNa_cells[:]=p.cNa_cell

        cK_cells = np.zeros(len(cells.cell_i))
        cK_cells[:]=p.cK_cell

        cCl_cells = np.zeros(len(cells.cell_i))
        cCl_cells[:]=p.cCl_cell

        cCa_cells = np.zeros(len(cells.cell_i))
        cCa_cells[:]=p.cCa_cell

        cH_cells = np.zeros(len(cells.cell_i))
        cH_cells[:]=p.cH_cell

        cP_cells = np.zeros(len(cells.cell_i))
        cP_cells[:]=p.cP_cell

        cM_cells = np.zeros(len(cells.cell_i))
        cM_cells[:]=p.cM_cell

        # Initialize environmental ion concentrations:
        cNa_env = np.zeros(len(cells.cell_i))
        cNa_env[:]=p.cNa_env

        cK_env = np.zeros(len(cells.cell_i))
        cK_env[:]=p.cK_env

        cCl_env = np.zeros(len(cells.cell_i))
        cCl_env[:]=p.cCl_env

        cCa_env = np.zeros(len(cells.cell_i))
        cCa_env[:]=p.cCa_env

        cH_env = np.zeros(len(cells.cell_i))
        cH_env[:]=p.cH_env

        cP_env = np.zeros(len(cells.cell_i))
        cP_env[:]=p.cP_env

        cM_env = np.zeros(len(cells.cell_i))
        cM_env[:]=p.cM_env

        # Initialize membrane diffusion co-efficients:
        DmNa = np.zeros(len(cells.cell_i))
        DmNa[:] = p.Dm_Na

        DmK = np.zeros(len(cells.cell_i))
        DmK[:] = p.Dm_K

        DmCl = np.zeros(len(cells.cell_i))
        DmCl[:] = p.Dm_Cl

        DmCa = np.zeros(len(cells.cell_i))
        DmCa[:] = p.Dm_Ca

        DmH = np.zeros(len(cells.cell_i))
        DmH[:] = p.Dm_H

        DmP = np.zeros(len(cells.cell_i))
        DmP[:] = p.Dm_P

        DmM = np.zeros(len(cells.cell_i))
        DmM[:] = p.Dm_M

        # Initialize membrane thickness:
        self.tm = np.zeros(len(cells.cell_i))
        self.tm[:] = p.tm

        # Initialize environmental volume:
        self.envV = np.zeros(len(cells.cell_i))
        self.envV[:] = p.vol_env

        # Create vectors holding a range of ion-matched data
        self.cc_cells = [cNa_cells,cK_cells,cCl_cells,cCa_cells,cH_cells,cP_cells,cM_cells]  # cell concentrations
        self.cc_env = [cNa_env,cK_env,cCl_env,cCa_env,cH_env,cP_env,cM_env]   # environmental concentrations
        self.zs = [p.z_Na, p.z_K, p.z_Cl, p.z_Ca, p.z_H, p.z_P, p.z_M]   # matched ion valence state
        self.Dm_cells = [DmNa, DmK, DmCl,DmCa,DmH,DmP,DmM]              # matched membrane diffusion constants

        self.iNa=0     # indices to each ion for use in above arrays
        self.iK = 1
        self.iCl=2
        self.iCa = 3
        self.iH = 4
        self.iP = 5
        self.iM = 6

        self.movingIons = [self.iNa,self.iK,self.iCl,self.iCa,self.iH,self.iM]

        self.ionlabel = {self.iNa:'Sodium',self.iK:'Potassium',self.iCl:'Chloride',self.iCa:'Calcium',self.iH:'Proton',
            self.iP:'Protein',self.iM:'Charge Balance Anion'}

        # gap junction specific arrays:
        self.gjopen = np.ones(len(cells.gj_i))   # holds gap junction open fraction for each gj

        self.gjl = np.zeros(len(cells.gj_i))    # gj length for each gj
        self.gjl[:] = p.gjl

        self.gjsa = np.zeros(len(cells.gj_i))        # gj x-sec surface area for each gj
        self.gjsa[:] = p.gjsa

        # initialization of data-arrays holding time-related information
        self.cc_time = []  # data array holding the concentrations at time points
        self.vm_time = []  # data array holding voltage at time points
        self.time = []     # time values of the simulation

        flx = np.zeros(len(cells.gj_i))
        self.fluxes_gj = [flx,flx,flx,flx,flx,flx,flx]   # stores gj fluxes for each ion
        self.gjopen_time = []   # stores gj open fraction at each time
        self.fgj_time = []      # stores the gj fluxes for each ion at each time
        self.Igj =[]            # current for each gj
        self.Igj_time = []      # current for each gj at each time

    def runInit(self,cells,p):
        """
        Runs an initialization simulation from the existing data state of the Simulation object,
        and saves the resulting data (including the cell world geometry) to files that can be read later.

        Parameters:
        -----------
        cells               An instance of the World class. This is required because simulation data is specific
                            to the cell world data so it needs the reference to save.
        timesteps           The number of timesteps over which the simulation is run. Note the size of the time
                            interval is specified as dt in the parameters module.

        """


        tt = np.linspace(0,p.init_tsteps*p.dt,p.init_tsteps)
        # report
        print('Your sim initialization is running for', int((p.init_tsteps*p.dt)/60),'minutes of in-world time.')


        for t in tt:   # run through the loop

            # get the net, unbalanced charge in each cell:
            q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)

            # calculate the voltage in the cell (which is also Vmem as environment is zero):
            vm = get_volt(q_cells,self.sacell,p)

            # run the Na-K-ATPase pump:   # FIXME there may be other pumps!
            self.cc_cells[self.iNa],self.cc_env[self.iNa],self.cc_cells[self.iK],self.cc_env[self.iK], fNa_NaK, fK_NaK =\
                pumpNaKATP(self.cc_cells[self.iNa],self.cc_env[self.iNa],self.cc_cells[self.iK],self.cc_env[self.iK],
                    self.volcell,self.envV,vm,p)

             # recalculate the net, unbalanced charge and voltage in each cell:
            q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)
            vm = get_volt(q_cells,self.sacell,p)

            # electro-diffuse all ions (except for proteins, which don't move!) across the cell membrane:
            shuffle(self.movingIons)  # shuffle the ion indices so it's not the same order every time step

            for i in self.movingIons:

                self.cc_env[i],self.cc_cells[i],fNa = \
                    electrofuse(self.cc_env[i],self.cc_cells[i],self.Dm_cells[i],self.tm,self.sacell,
                        self.envV,self.volcell,self.zs[i],vm,p)

                # recalculate the net, unbalanced charge and voltage in each cell:
                q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)
                vm = get_volt(q_cells,self.sacell,p)

            self.vm_check = vm

        # Save core data to initialization to file
        with open(self.cellConc_init, 'wb') as f:
            pickle.dump(self.cc_cells, f)
        with open(self.envConc_init, 'wb') as f:
            pickle.dump(self.cc_env, f)
        with open(self.cellGeom_init, 'wb') as f:
            pickle.dump(cells, f)
        with open(self.params_init, 'wb') as f:
            pickle.dump(p, f)

    def loadInit(self):
        # Initialize geometry from file
        with open(self.cellGeom_init, 'rb') as f:
            cells = pickle.load(f)

        with open(self.params_init, 'rb') as f:
            self.params = pickle.load(f)

        self.baseInit(cells,self.params)

        # Initialize from a file
        with open(self.cellConc_init, 'rb') as f:
            self.cc_cells = pickle.load(f)

        with open(self.envConc_init, 'rb') as f:
            self.cc_env = pickle.load(f)

        q_cells = get_charge(self.cc_cells,self.zs,self.volcell,self.params)
        vm = get_volt(q_cells,self.sacell,self.params)
        self.vm_check = vm

        params = self.params

        return cells, params

    def runSim(self,cells,p):
        """
        Drives the actual time-loop iterations for the simulation.
        """
        # create a time-steps vector:
        tt = np.linspace(0,p.sim_tsteps*p.dt,p.sim_tsteps)

        i = 0 # resample the time vector to save data at specific times:
        tsamples =[]
        resample = p.t_resample
        while i < len(tt)-resample:
            i = i + resample
            tsamples.append(tt[i])
        tsamples = set(tsamples)

        # report
        print('Your simulation is running from',0,'to',p.sim_tsteps*p.dt,'seconds, in-world time.')
        # FIXME would be nice to have a time estimate for the simulation

        for t in tt:   # run through the loop

            # get the net, unbalanced charge in each cell:
            q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)

            # calculate the voltage in the cell (which is also Vmem as environment is zero):
            vm = get_volt(q_cells,self.sacell,p)

            # run the Na-K-ATPase pump:  # FIXME would be nice to track ATP use
            self.cc_cells[self.iNa],self.cc_env[self.iNa],self.cc_cells[self.iK],self.cc_env[self.iK], fNa_NaK, fK_NaK =\
                pumpNaKATP(self.cc_cells[self.iNa],self.cc_env[self.iNa],self.cc_cells[self.iK],self.cc_env[self.iK],
                    self.volcell,self.envV,vm,p)

             # recalculate the net, unbalanced charge and voltage in each cell:
            q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)
            vm = get_volt(q_cells,self.sacell,p)

            # electro-diffuse all ions (except for proteins, which don't move!) across the cell membrane:

            shuffle(cells.gj_i)
            shuffle(self.movingIons)

            for i in self.movingIons:

                self.cc_env[i],self.cc_cells[i],fNa = \
                    electrofuse(self.cc_env[i],self.cc_cells[i],self.Dm_cells[i],self.tm,self.sacell,
                        self.envV,self.volcell,self.zs[i],vm,p)

                 # recalculate the net, unbalanced charge and voltage in each cell:
                q_cells = get_charge(self.cc_cells,self.zs,self.volcell,p)
                vm = get_volt(q_cells,self.sacell,p)

                vmA,vmB = vm[cells.gap_jun_i][:,0], vm[cells.gap_jun_i][:,1]
                vgj = vmB - vmA

                self.gjopen = (1.0 - step(abs(vgj),p.gj_vthresh,p.gj_vgrad))

                _,_,fgj = electrofuse(self.cc_cells[i][cells.gap_jun_i][:,0],self.cc_cells[i][cells.gap_jun_i][:,1],
                    self.gjopen*p.Do_Na,self.gjl,self.gjsa,self.volcell[cells.gap_jun_i][:,0],
                    self.volcell[cells.gap_jun_i][:,1],self.zs[i],vgj,p)


                for igj in cells.gj_i:
                    cellAi,cellBi = cells.gap_jun_i[igj]
                    flux = fgj[igj]
                    volA, volB = self.volcell[cellAi],self.volcell[cellBi]
                    self.cc_cells[i][cellAi] = self.cc_cells[i][cellAi] - flux*p.dt/volA
                    self.cc_cells[i][cellBi] = self.cc_cells[i][cellBi] + flux*p.dt/volB

                self.fluxes_gj[i] = fgj

            if t in tsamples:
                # add the new concentration and voltage data to the time-storage matrices:
                concs = copy.deepcopy(self.cc_cells)
                flxs = copy.deepcopy(self.fluxes_gj)
                self.cc_time.append(concs)
                self.vm_time.append(vm)
                self.time.append(t)
                self.fgj_time.append(flxs)
                self.gjopen_time.append(self.gjopen)

        # Save core data of simulation to file   # FIXME just save the whole sim object + cells + p!
        with open(self.cellConc_sim, 'wb') as f:
            pickle.dump(self.cc_cells, f)
        with open(self.envConc_sim, 'wb') as f:
            pickle.dump(self.cc_env, f)
        with open(self.cellGeom_sim, 'wb') as f:
            pickle.dump(cells, f)
        with open(self.params_sim, 'wb') as f:
            pickle.dump(p, f)

        # save time-dependent data
        with open(self.cellConc_attimes, 'wb') as f:
            pickle.dump(self.cc_time, f)
        with open(self.cellVm_attimes, 'wb') as f:
            pickle.dump(self.vm_time, f)
        with open(self.storedtimes, 'wb') as f:
            pickle.dump(self.time, f)

    def loadSim(self):
        # Initialize geometry from file
        with open(self.cellGeom_sim, 'rb') as f:
            cells = pickle.load(f)

        with open(self.params_sim, 'rb') as f:
            self.params = pickle.load(f)

        self.baseInit(cells,self.params)

        # Initialize from a file
        with open(self.cellConc_sim, 'rb') as f:
            self.cc_cells = pickle.load(f)

        with open(self.envConc_sim, 'rb') as f:
            self.cc_env = pickle.load(f)

        with open(self.cellConc_attimes, 'rb') as f:
            self.cc_time = pickle.load(f)

        with open(self.cellVm_attimes, 'rb') as f:
            self.vm_time = pickle.load(f)

        with open(self.storedtimes, 'rb') as f:
            self.time = pickle.load(f)

        q_cells = get_charge(self.cc_cells,self.zs,self.volcell,self.params)
        vm = get_volt(q_cells,self.sacell,self.params)
        self.vm_check = vm

        params = self.params

        return cells,params


def diffuse(cA,cB,Dc,d,sa,vola,volb,p):
    """
    Returns updated concentrations for diffusion between two
    connected volumes.

    Parameters
    ----------
    cA          Initial concentration of c in region A [mol/m3]
    cB          Initial concentration of c in region B [mol/m3]
    Dc          Diffusion constant of c  [m2/s]
    d           Distance between region A and region B [m]
    sa          Surface area separating region A and B [m2]
    vola        volume of region A [m3]
    volb        volume of region B [m3]
    dt          time step   [s]
    method      EULER or RK4 for Euler and Runge-Kutta 4
                integration methods, respectively.

    Returns
    --------
    cA2         Updated concentration of cA in region A [mol/m3]
    cB2         Updated concentration of cB in region B [mol/m3]
    flux        Chemical flux magnitude between region A and B [mol/s]

    """

    assert vola>0
    assert volb>0
    assert d >0

    #volab = (vola + volb)/2
    #qualityfactor = (Dc/d)*(sa/volab)*p.dt   # quality factor should be <1.0 for stable simulations

    flux = -sa*Dc*(cB - cA)/d

    if p.method == 0:

        dmol = sa*p.dt*Dc*(cB - cA)/d

        cA2 = cA + dmol/vola
        cB2 = cB - dmol/volb

        cA2 = check_c(cA2)
        cB2 = check_c(cB2)

    elif p.method == 1:

        k1 = sa*Dc*(cB - cA)/d

        k2 = sa*Dc*(cB - (cA + (1/2)*k1*p.dt))/d

        k3 = sa*Dc*(cB - (cA + (1/2)*k2*p.dt))/d

        k4 = sa*Dc*(cB - (cA + k3*p.dt))/d

        dmol = (p.dt/6)*(k1 + 2*k2 + 2*k3 + k4)

        cA2 = cA + dmol/vola
        cB2 = cB - dmol/volb

        cA2 = check_c(cA2)
        cB2 = check_c(cB2)

    return cA2, cB2, flux

def electrofuse(cA,cB,Dc,d,sa,vola,volb,zc,Vba,p):
    """
    Returns updated concentrations for electro-diffusion between two
    connected volumes. Note for cell work, 'b' is 'inside', 'a' is outside, with
    a positive flux moving from a to b. The voltage is defined as
    Vb - Va (Vba), which is equivalent to Vmem.

    This function defaults to regular diffusion if Vba == 0.0

    This function takes numpy matrix values as input. All inputs must be matrices of
    the same shape.

    Parameters
    ----------
    cA          Initial concentration of c in region A [mol/m3] (out)
    cB          Initial concentration of c in region B [mol/m3] (in)
    Dc          Diffusion constant of c  [m2/s]
    d           Distance between region A and region B [m]
    sa          Surface area separating region A and B [m2]
    vola        volume of region A [m3]
    volb        volume of region B [m3]
    zc          valence of ionic species c
    Vba         voltage between B and A as Vb - Va  [V]
    dt          time step   [s]
    method      EULER or RK4 for Euler and Runge-Kutta 4
                integration methods, respectively. 'RK4_AB' is an
                alternative implementation of RK4.

    Returns
    --------
    cA2         Updated concentration of cA in region A [mol/m3]
    cB2         Updated concentration of cB in region B [mol/m3]
    flux        Chemical flux magnitude between region A and B [mol/s]

    """

    alpha = (zc*Vba*p.F)/(p.R*p.T)

    #volab = (vola + volb)/2
    #qualityfactor = abs((Dc/d)*(sa/volab)*p.dt*alpha)   # quality factor should be <1.0 for stable simulations

    deno = 1 - np.exp(-alpha)   # calculate the denominator for the electrodiffusion equation,..

    izero = (deno==0).nonzero()     # get the indices of the zero and non-zero elements of the denominator
    inzero = (deno!=0).nonzero()

    # initialize data matrices to the same shape as input data
    dmol = np.zeros(deno.shape)
    cA2 = np.zeros(deno.shape)
    cB2 = np.zeros(deno.shape)
    flux = np.zeros(deno.shape)
    k1 = np.zeros(deno.shape)
    k2 = np.zeros(deno.shape)
    k3 = np.zeros(deno.shape)
    k4 = np.zeros(deno.shape)

    if len(deno[izero]):   # if there's anything in the izero array:
         # calculate the flux for those elements [mol/s]:
        flux[izero] = -sa[izero]*Dc[izero]*(cB[izero] - cA[izero])/d[izero]


        if p.method == 0:

            #dmol[izero] = sa[izero]*p.dt*Dc[izero]*(cB[izero] - cA[izero])/d[izero]
            dmol[izero] = -p.dt*flux[izero]

            cA2[izero] = cA[izero] + dmol[izero]/vola[izero]
            cB2[izero] = cB[izero] - dmol[izero]/volb[izero]

            #cA2[izero] = check_c(cA2[izero])
            #cB2[izero] = check_c(cB2[izero])

        elif p.method == 1:

            k1[izero] = -flux[izero]

            k2[izero] = sa[izero]*Dc[izero]*(cB[izero] - (cA[izero] + (1/2)*k1[izero]*p.dt))/d[izero]

            k3[izero] = sa[izero]*Dc[izero]*(cB[izero] - (cA[izero] + (1/2)*k2[izero]*p.dt))/d[izero]

            k4[izero] = sa[izero]*Dc[izero]*(cB[izero] - (cA[izero] + k3[izero]*p.dt))/d[izero]

            dmol[izero] = (p.dt/6)*(k1 + 2*k2 + 2*k3 + k4)

            cA2[izero] = cA[izero] + dmol[izero]/vola[izero]
            cB2[izero] = cB[izero] - dmol[izero]/volb[izero]

            #cA2[izero] = check_c(cA2[izero])
            #cB2[izero] = check_c(cB2[izero])

    if len(deno[inzero]):   # if there's any indices in the inzero array:

        # calculate the flux for those elements:
        flux[inzero] = -((sa[inzero]*Dc[inzero]*alpha[inzero])/d[inzero])*\
                       ((cB[inzero] - cA[inzero]*np.exp(-alpha[inzero]))/deno[inzero])


        if p.method == 0:

            dmol[inzero] = -flux[inzero]*p.dt

            cA2[inzero] = cA[inzero] + dmol[inzero]/vola[inzero]
            cB2[inzero] = cB[inzero] - dmol[inzero]/volb[inzero]

            #cA2[inzero] = check_c(cA2[inzero])
            #cB2[inzero] = check_c(cB2[inzero])

        elif p.method == 1:

            k1[inzero] = -flux[inzero]

            k2[inzero] = ((sa[inzero]*Dc[inzero]*alpha[inzero])/d[inzero])*\
                         (cB[inzero] - (cA[inzero] + (1/2)*k1[inzero]*p.dt)*np.exp(-alpha[inzero]))/deno[inzero]

            k3[inzero] = ((sa[inzero]*Dc[inzero]*alpha[inzero])/d[inzero])*\
                         (cB[inzero] - (cA[inzero] + (1/2)*k2[inzero]*p.dt)*np.exp(-alpha[inzero]))/deno[inzero]

            k4[inzero] = ((sa[inzero]*Dc[inzero]*alpha[inzero])/d[inzero])*\
                         (cB[inzero] - (cA[inzero] + k3[inzero]*p.dt)*np.exp(-alpha[inzero]))/deno[inzero]

            dmol[inzero] = (p.dt/6)*(k1[inzero] + 2*k2[inzero] + 2*k3[inzero] + k4[inzero])

            cA2[inzero] = cA[inzero] + dmol[inzero]/vola[inzero]
            cB2[inzero] = cB[inzero] - dmol[inzero]/volb[inzero]

            #cA2[inzero] = check_c(cA2[inzero])
            #cB2[inzero] = check_c(cB2[inzero])


    return cA2, cB2, flux

def pumpNaKATP(cNai,cNao,cKi,cKo,voli,volo,Vm,p):

    """
    Parameters
    ----------
    cNai            Concentration of Na+ inside the cell
    cNao            Concentration of Na+ outside the cell
    cKi             Concentration of K+ inside the cell
    cKo             Concentration of K+ outside the cell
    voli            Volume of the cell [m3]
    volo            Volume outside the cell [m3]
    Vm              Voltage across cell membrane [V]
    sa              Surface area of membrane
    method          EULER or RK4 solver

    Returns
    -------
    cNai2           Updated Na+ inside cell
    cNao2           Updated Na+ outside cell
    cKi2            Updated K+ inside cell
    cKo2            Updated K+ outside cell
    f_Na            Na+ flux (into cell +)
    f_K             K+ flux (into cell +)
    """

    delG_Na = p.R*p.T*np.log(cNao/cNai) - p.F*Vm
    delG_K = p.R*p.T*np.log(cKi/cKo) + p.F*Vm
    delG_NaKATP = p.deltaGATP - (3*delG_Na + 2*delG_K)
    delG = (delG_NaKATP/1000)

    alpha = p.alpha_NaK*step(delG,p.halfmax_NaK,p.slope_NaK)

    f_Na  = -alpha*cNai*cKo      #flux as [mol/s]
    f_K = -(2/3)*f_Na          # flux as [mol/s]

    if p.method == 0:

        dmol = -alpha*cNai*cKo*p.dt

        cNai2 = cNai + dmol/voli
        cNao2 = cNao - dmol/volo

        cKi2 = cKi - (2/3)*dmol/voli
        cKo2 = cKo + (2/3)*dmol/volo

        #cNai2 = check_c(cNai2)
       # cNao2 = check_c(cNao2)
        #cKi2 = check_c(cKi2)
        #cKo2 = check_c(cKo2)

    elif p.method == 1:

        k1 = alpha*cNai*cKo

        k2 = alpha*(cNai+(1/2)*k1*p.dt)*cKo

        k3 = alpha*(cNai+(1/2)*k2*p.dt)*cKo

        k4 = alpha*(cNai+ k3*p.dt)*cKo

        dmol = (p.dt/6)*(k1 + 2*k2 + 2*k3 + k4)

        cNai2 = cNai - dmol/voli
        cNao2 = cNao + dmol/volo

        cKi2 = cKi + (2/3)*dmol/voli
        cKo2 = cKo - (2/3)*dmol/volo

       # cNai2 = check_c(cNai2)
       # cNao2 = check_c(cNao2)
       # cKi2 = check_c(cKi2)
       # cKo2 = check_c(cKo2)

    return cNai2,cNao2,cKi2,cKo2, f_Na, f_K

def get_volt(q,sa,p):

    """
    Calculates the voltage for a net charge on a capacitor.

    Parameters
    ----------
    q           Net electrical charge [C]
    sa          Surface area [m2]

    Returns
    -------
    V               Voltage on the capacitive space holding charge
    """

    cap = sa*p.cm
    V = (1/cap)*q
    return V

def get_charge(concentrations,zs,vol,p):

    q = 0

    for conc,z in zip(concentrations,zs):
        q = q+ conc*z

    netcharge = p.F*q*vol

    return netcharge

def check_c(cA):
    """
    Does a quick check on two values (concentrations)
    and sets one to zero if it is below zero.

    """
    if isinstance(cA,np.float64):  # if we just have a singular value
        if cA < 0.0:
            cA2 = 0.0

    elif isinstance(cA,np.ndarray): # if we have matrix data
        isubzeros = (cA<0).nonzero()
        if isubzeros:  # if there's anything in the isubzeros matrix...
            cA[isubzeros] = 0.0

    return cA


def sigmoid(x,g,y_sat):
    """
    A sigmoidal function (logistic curve) allowing user
    to specify a saturation level (y_sat) and growth rate (g).

    Parameters
    ----------
    x            Input values, may be numpy array or float
    g            Growth rate
    y_sat        Level at which growth saturates

    Returns
    --------
    y            Numpy array or float of values

    """
    y = (y_sat*np.exp(g*x))/(y_sat + (np.exp(g*x)-1))
    return y

def hill(x,K,n):

    """
    The Hill equation (log-transformed sigmoid). Function ranges
    from y = 0 to +1.

    Parameters
    ----------
    x            Input values, may be numpy array or float. Note all x>0 !
    K            Value of x at which curve is 1/2 maximum (y=0.5)
    n            Hill co-efficient n<1 negative cooperativity, n>1 positive.

    Returns
    --------
    y            Numpy array or float of values

    """
    assert x.all() > 0

    y = x**n/((K**n)+(x**n))

    return y

def step(t,t_on,t_change):
    """
    A step function (bounded by 0 and 1) based on a logistic curve
    and allowing user to specify time for step to come on (t_on) and time for
    change from zero to one to happen.

    Parameters
    ----------
    t            Input values, may be numpy array or float
    t_on         Time step turns on
    t_change     Time for change from 0 to 1 (off to on)

    Returns
    --------
    y            Numpy array or float of values

    """
    g = (1/t_change)*10
    y = 1/(1 + (np.exp(-g*(t-t_on))))
    return y

def pulse(t,t_on,t_off,t_change):
    """
    A pulse function (bounded by 0 and 1) based on logistic curves
    and allowing user to specify time for step to come on (t_on) and time for
    change from zero to one to happen, and time for step to come off (t_change).

    Parameters
    ----------
    t            Input values, may be numpy array or float
    t_on         Time step turns on
    t_off        Time step turns off
    t_change     Time for change from 0 to 1 (off to on)

    Returns
    --------
    y            Numpy array or float of values

    """
    g = (1/t_change)*10
    y1 = 1/(1 + (np.exp(-g*(t-t_on))))
    y2 = 1/(1 + (np.exp(-g*(t-t_off))))
    y = y1 - y2
    return y



