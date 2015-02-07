#!/usr/bin/env python3
# Copyright 2014-2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

# FIXME this module will load parameters from a yaml file!
# FIXME put *all* constants and options in here, including plotting colormaps, etc...

# Lodish H, Berk A, Zipursky SL, et al. Molecular Cell Biology. 4th edition. New York: W. H. Freeman;
# 2000. Section 15.4, Intracellular Ion Environment and Membrane Electric Potential.
# Available from: http://www.ncbi.nlm.nih.gov/books/NBK21627/

import numpy as np
import math

# define the basic class that holds variables
class Parameters(object):
    """
    For now, a very simple object that stores simulation constants.

    """
    def __init__(self):

        self.dt = 5e-5    # Simulation step-size [s] recommended range 1e-2 to 1e-3 for regular sims; 1e-6 for neural
        self.init_end = 20*60      # world time to end the initialization simulation time [s]
        self.sim_end = 0.2         # world time to end the simulation
        self.resamp = 1e-3         # time to resample in world time

        self.init_tsteps = self.init_end/self.dt # Number of timesteps for an initialization from scratch (range 50000 to 100000)
        self.sim_tsteps = self.sim_end/self.dt    # Number of timesteps for the simulation
        self.t_resample = self.resamp/self.dt         # resample the time vector every x steps
        self.method = 0            # Solution method. For 'Euler' = 0, for 'RK4' = 1.

        # File saving
        self.cache_path = "~/.betse/cache/basicInit"  # world, inits, and sims are saved and read to/from this directory.

        self.profile = 'scratch' #ion profile to be used: 'basic' (3 ions), 'mammalian' (7 ions), 'invertebrate' (7 ions)

        # basic constants
        self.F = 96485 # Faraday constant [J/V*mol]
        self.R = 8.314  # Gas constant [J/K*mol]
        self.T = 310   # Temperature [K]

        # geometric constants and factors
        self.wsx = 100e-6  # the x-dimension of the world space [m] recommended range 50 to 1000 um
        self.wsy = 100e-6  # the y-dimension of the world space [m] recommended range 50 to 1000 um
        self.rc = 5e-6  # radius of single cell
        self.d_cell = self.rc * 2  # diameter of single cell
        self.nx = int(self.wsx / self.d_cell)  # number of lattice sites in world x index
        self.ny = int(self.wsy / self.d_cell)  # number of lattice sites in world y index
        self.ac = 1e-6  # cell-cell separation for drawing
        self.nl = 0.8  # noise level for the lattice
        self.wsx = self.wsx + 5 * self.nl * self.d_cell  # readjust the world size for noise
        self.wsy = self.wsy + 5 * self.nl * self.d_cell
        self.vol_env = 1        # volume of the environmental space [m3]
        self.search_d =1.5     # distance to search for nearest neighbours (relative to cell diameter dc) min 1.0 max 5.0
        self.scale_cell = 0.9          # the amount to scale cell membranes in from ecm edges (only affects drawing)
        self.cell_sides = 4      # minimum number of membrane domains per cell (must be >2)
        self.scale_alpha = 1.0   # the amount to scale (1/d_cell) when calculating the concave hull (boundary search)
        self.cell_height = 5.0e-6  # the height of a cell in the z-direction (for volume and surface area calculations)
        self.cell_space = 26.0e-9  # the true cell-cell spacing (width of extracellular space)
        self.cm = 0.010            # patch capacitance of cell membrane up to 0.022 [F/m2]
        self.tm = 7.5e-9           # thickness of cell membrane [m]
        self.um = 1e6    # multiplication factor to convert m to um

        # gap junction constants
        self.gjl = 2*self.tm + self.cell_space     # gap junction length
        self.gjsa = math.pi*((3.0e-9)**2)          # total gap junction surface area as fraction of cell surface area
        self.gj_vthresh = 50e-3              # voltage threshhold gj closing [V]
        self.gj_vgrad  = 20e-3               # the range over which gj goes from open to shut at threshold [V]
        self.Dgj = 1e-10                    # gap junction diffusion coefficient [m2/s]

        # pump parameters
        self.deltaGATP = 50e3    # free energy released in ATP hydrolysis [J/mol]
        self.alpha_NaK = 5.0e-17 # rate constant sodium-potassium ATPase [m3/mols]  range 1.0e-9 to 1.0e-10 for dt =1e-2
        self.halfmax_NaK = 12   # the free energy level at which pump activity is halved [kJ]
        self.slope_NaK = 24  # the energy window width of the NaK-ATPase pump [kJ]
        self.alpha_Ca = 1.0e-17 # pump rate for calcium ATPase [m3/mols]
        self.halfmax_Ca = 12
        self.slope_Ca = 24

        # Scheduled Interventions

        # cell to effect:
        self.target_cell = 10


        #self.ion_options specifications list is [time on, time off, rate of change, Dmem multiplier]
        self.ion_options = {'Na_mem':0,'K_mem':0,'Cl_mem':0,'Ca_mem':0,'H_mem':0,'K_env':0}

        # self.vg_options specifications list is [Dmem multiplier, gain, v_on, v_off, v_inactivate]
        #
        self.vg_options = {'Na_vg':[1000,0.5,-55e-3,40e-3,-68e-3],'K_vg':[100,0.5,10e-3,-70e-3,-60e-3],'Ca_vg':0,'K_cag':0}

        # default diffusion constants
        self.Dm_Na = 1.0e-18     # membrane diffusion constant sodium [m2/s]
        self.Dm_K = 1e-18      # membrane diffusion constant potassium [m2/s]
        self.Dm_Cl = 1.0e-18     # membrane diffusion constant chloride [m2/s]
        self.Dm_Ca = 5.0e-20     # membrane diffusion constant calcium [m2/s]
        self.Dm_H = 1.0e-18      # membrane diffusion constant hydrogen [m2/s]
        self.Dm_M = 1.0e-18     # membrane diffusion constant anchor ion [m2/s]
        self.Dm_P = 0.0        # membrane diffusion constant proteins [m2/s]

        self.Do_Na = 1.33e-9      # free diffusion constant sodium [m2/s]
        self.Do_K = 1.96e-9      # free diffusion constant potassium [m2/s]
        self.Do_Cl = 2.03e-9     # free diffusion constant chloride [m2/s]
        self.Do_Ca = 1.0e-9     # free diffusion constant calcium [m2/s]
        self.Do_H = 2.5e-9      # free diffusion constant hydrogen [m2/s]
        self.Do_M = 1.0e-9     # free diffusion constant mystery anchor ion [m2/s]
        self.Do_P = 5.0e-10      # free diffusion constant protein [m2/s]

        # charge states of ions
        self.z_Na = 1
        self.z_K = 1
        self.z_Cl = -1
        self.z_Ca = 2
        self.z_H = 1
        self.z_P = -1
        self.z_M = -1

        if self.profile == 'scratch':

            self.cNa_env = 145.0
            self.cK_env = 5.0
            self.cCa_env = 1.0
            self.cP_env = 9.0

            zs = [self.z_Na, self.z_K, self.z_Ca, self.z_P]

            conc_env = [self.cNa_env,self.cK_env, self.cCa_env, self.cP_env]
            self.cM_env, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1


            # if self.z_M_env == -1:
            #     self.cMn_env = self.cM_env
            #     self.cMp_env = 0
            #
            # if self.z_M_env == 1:
            #     self.cMp_env = self.cM_env
            #     self.cMn_env = 0

            self.cNa_cell = 5.4
            self.cK_cell = 140.44
            self.cCa_cell = 1.69
            self.cP_cell = 138.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCa_cell, self.cP_cell]

            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            # if self.z_M_cell == -1:
            #     self.cMn_cell = self.cM_cell
            #     self.cMp_cell = 0
            #
            # if self.z_M_cell == 1:
            #     self.cMp_cell = self.cM_cell
            #     self.cMn_cell = 0

            self.ions_dict = {'Na':1,'K':1,'Cl':0,'Ca':1,'H':0,'P':1,'M':1}



        if self.profile == 'basic':

            self.cNa_env = 145.0
            self.cK_env = 5.0

            zs = [self.z_Na, self.z_K]

            conc_env = [self.cNa_env,self.cK_env]
            self.cM_env, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 17.0
            self.cK_cell = 131.0

            conc_cell = [self.cNa_cell,self.cK_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.ions_dict = {'Na':1,'K':1,'Cl':0,'Ca':0,'H':0,'P':0,'M':1}

        # default environmental and initial values mammalian cells and plasma
        if self.profile == 'mammalian':

            self.cNa_env = 145.0
            self.cK_env = 5.0
            self.cCl_env = 105.0
            self.cCa_env = 1.0
            self.cH_env = 4.0e-8
            self.cP_env = 9.0

            zs = [self.z_Na, self.z_K, self.z_Cl, self.z_Ca, self.z_H, self.z_P]

            conc_env = [self.cNa_env,self.cK_env, self.cCl_env, self.cCa_env, self.cH_env, self.cP_env]
            self.cM_env, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 17.0
            self.cK_cell = 131.0
            self.cCl_cell = 6.0
            self.cCa_cell = 1.0e-6
            self.cH_cell = 6.3e-8
            self.cP_cell = 138.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCl_cell, self.cCa_cell, self.cH_cell, self.cP_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.ions_dict = {'Na':1,'K':1,'Cl':1,'Ca':1,'H':1,'P':1,'M':1}

         # default environmental and initial values invertebrate cells and plasma
        if self.profile == 'invertebrate':
            self.cNa_env = 440.0
            self.cK_env = 20.0
            self.cCl_env = 460.0
            self.cCa_env = 10.0
            self.cH_env = 4.0e-8
            self.cP_env = 7.0

            zs = [self.z_Na, self.z_K, self.z_Cl, self.z_Ca, self.z_H, self.z_P]

            conc_env = [self.cNa_env,self.cK_env, self.cCl_env, self.cCa_env, self.cH_env, self.cP_env]
            self.cM_env, self.z_M_env = bal_charge(conc_env,zs)

            assert self.z_M_env == -1

            self.cNa_cell = 50.0
            self.cK_cell = 400.0
            self.cCl_cell = 75.0
            self.cCa_cell = 3.0e-4
            self.cH_cell = 6.3e-8
            self.cP_cell = 350.0

            conc_cell = [self.cNa_cell,self.cK_cell, self.cCl_cell, self.cCa_cell, self.cH_cell, self.cP_cell]
            self.cM_cell, self.z_M_cell = bal_charge(conc_cell,zs)

            assert self.z_M_cell == -1

            self.ions_dict = {'Na':1,'K':1,'Cl':1,'Ca':1,'H':1,'P':1,'M':1}




def bal_charge(concentrations,zs):

    q = 0

    for conc,z in zip(concentrations,zs):
        q = q+ conc*z

        to_zero = -q
        bal_conc = abs(to_zero)
        valance = np.sign(to_zero)

        assert bal_conc >= 0

    return bal_conc,valance


params = Parameters()
