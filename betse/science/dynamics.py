#!/usr/bin/env python3
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

import numpy as np
import os, os.path
import copy
from random import shuffle
from betse.science import filehandling as fh
from betse.science import visualize as viz
from betse.science import toolbox as tb
import matplotlib.pyplot as plt
from betse.exceptions import BetseExceptionSimulation
from betse.util.io import loggers
import time


class Dynamics(object):

    def __init__(self, sim, cells, p):

        if p.sim_ECM == True:
            self.data_length = len(cells.mem_i)

        elif p.sim_ECM == False:
            self.data_length = len(cells.cell_i)

    def globalInit(self,sim,cells,p):

        if p.global_options['K_env'] != 0:

            self.t_on_Kenv = p.global_options['K_env'][0]
            self.t_off_Kenv = p.global_options['K_env'][1]
            self.t_change_Kenv = p.global_options['K_env'][2]
            self.mem_mult_Kenv = p.global_options['K_env'][3]

        if p.global_options['Cl_env'] != 0:

            self.t_on_Clenv = p.global_options['Cl_env'][0]
            self.t_off_Clenv = p.global_options['Cl_env'][1]
            self.t_change_Clenv = p.global_options['Cl_env'][2]
            self.mem_mult_Clenv = p.global_options['Cl_env'][3]

        if p.global_options['Na_env'] != 0:

            self.t_on_Naenv = p.global_options['Na_env'][0]
            self.t_off_Naenv = p.global_options['Na_env'][1]
            self.t_change_Naenv = p.global_options['Na_env'][2]
            self.mem_mult_Naenv = p.global_options['Na_env'][3]

        if p.global_options['T_change'] != 0:

            self.tonT = p.global_options['T_change'][0]
            self.toffT = p.global_options['T_change'][1]
            self.trampT = p.global_options['T_change'][2]
            self.multT = p.global_options['T_change'][3]

        if p.global_options['gj_block'] != 0:

            self.tonGJ = p.global_options['gj_block'][0]
            self.toffGJ = p.global_options['gj_block'][1]
            self.trampGJ = p.global_options['gj_block'][2]

        if p.global_options['NaKATP_block'] != 0:

            self.tonNK = p.global_options['NaKATP_block'][0]
            self.toffNK = p.global_options['NaKATP_block'][1]
            self.trampNK = p.global_options['NaKATP_block'][2]

        if p.global_options['HKATP_block'] != 0:

            self.tonHK = p.global_options['HKATP_block'][0]
            self.toffHK = p.global_options['HKATP_block'][1]
            self.trampHK = p.global_options['HKATP_block'][2]

    def scheduledInit(self,sim,cells,p):

        if p.scheduled_options['Na_mem'] != 0:

            self.t_on_Namem = p.scheduled_options['Na_mem'][0]
            self.t_off_Namem = p.scheduled_options['Na_mem'][1]
            self.t_change_Namem = p.scheduled_options['Na_mem'][2]
            self.mem_mult_Namem = p.scheduled_options['Na_mem'][3]
            self.apply_Namem = p.scheduled_options['Na_mem'][4]

        if p.scheduled_options['K_mem'] != 0:

            self.t_on_Kmem = p.scheduled_options['K_mem'][0]
            self.t_off_Kmem = p.scheduled_options['K_mem'][1]
            self.t_change_Kmem = p.scheduled_options['K_mem'][2]
            self.mem_mult_Kmem = p.scheduled_options['K_mem'][3]
            self.apply_Kmem = p.scheduled_options['K_mem'][4]

        if p.scheduled_options['Cl_mem'] != 0:

            self.t_on_Clmem = p.scheduled_options['Cl_mem'][0]
            self.t_off_Clmem = p.scheduled_options['Cl_mem'][1]
            self.t_change_Clmem = p.scheduled_options['Cl_mem'][2]
            self.mem_mult_Clmem = p.scheduled_options['Cl_mem'][3]
            self.apply_Clmem = p.scheduled_options['Cl_mem'][4]

        if p.scheduled_options['Ca_mem'] != 0:

            self.t_on_Camem = p.scheduled_options['Ca_mem'][0]
            self.t_off_Camem = p.scheduled_options['Ca_mem'][1]
            self.t_change_Camem = p.scheduled_options['Ca_mem'][2]
            self.mem_mult_Camem = p.scheduled_options['Ca_mem'][3]
            self.apply_Camem = p.scheduled_options['Ca_mem'][4]

        if p.scheduled_options['IP3'] != 0:

            self.t_onIP3 = p.scheduled_options['IP3'][0]
            self.t_offIP3 = p.scheduled_options['IP3'][1]
            self.t_changeIP3 = p.scheduled_options['IP3'][2]
            self.rate_IP3 = p.scheduled_options['IP3'][3]
            self.apply_IP3 = p.scheduled_options['IP3'][4]

        if p.scheduled_options['extV'] != 0:

            self.t_on_extV = p.scheduled_options['extV'][0]
            self.t_off_extV = p.scheduled_options['extV'][1]
            self.t_change_extV = p.scheduled_options['extV'][2]
            self.peak_val_extV = p.scheduled_options['extV'][3]
            self.apply_extV = p.scheduled_options['extV'][4]


    def dynamicInit(self,sim,cells,p):

        if p.vg_options['Na_vg'] != 0:

            # Initialization of logic values for voltage gated sodium channel
            self.maxDmNa = p.vg_options['Na_vg'][0]
            self.v_activate_Na = p.vg_options['Na_vg'][1]
            self.v_inactivate_Na = p.vg_options['Na_vg'][2]
            self.v_deactivate_Na = p.vg_options['Na_vg'][3]
            self.t_alive_Na = p.vg_options['Na_vg'][4]
            self.t_dead_Na = p.vg_options['Na_vg'][5]
            self.targets_vgNa = p.vg_options['Na_vg'][6]

            # Initialize matrices defining states of vgNa channels for each cell membrane:
            self.inactivated_Na = np.zeros(self.data_length)
            self.vgNa_state = np.zeros(self.data_length)

            self.vgNa_aliveTimer = np.zeros(self.data_length) # sim time at which vgNa starts to close if activated
            self.vgNa_deadTimer = np.zeros(self.data_length) # sim time at which vgNa reactivates after inactivation

        if p.vg_options['K_vg'] !=0:

            # Initialization of logic values forr voltage gated potassium channel
            self.maxDmK = p.vg_options['K_vg'][0]
            self.v_on_K = p.vg_options['K_vg'][1]
            self.v_off_K = p.vg_options['K_vg'][2]
            self.t_alive_K = p.vg_options['K_vg'][3]
            self.targets_vgK = p.vg_options['K_vg'][4]

            # Initialize matrices defining states of vgK channels for each cell:
            self.active_K = np.zeros(self.data_length)
            self.crossed_activate_K = np.zeros(self.data_length)
            self.crossed_inactivate_K = np.zeros(self.data_length)

            # Initialize other matrices for vgK timing logic: NEW!
            self.vgK_state = np.zeros(self.data_length)   # state can be 0 = off, 1 = open
            self.vgK_OFFtime = np.zeros(self.data_length) # sim time at which vgK starts to close


        if p.vg_options['Ca_vg'] !=0:

            # Initialization of logic values for voltage gated calcium channel
            self.maxDmCa = p.vg_options['Ca_vg'][0]
            self.v_on_Ca = p.vg_options['Ca_vg'][1]
            self.v_off_Ca = p.vg_options['Ca_vg'][2]
            self.ca_upper_ca = p.vg_options['Ca_vg'][3]
            self.ca_lower_ca = p.vg_options['Ca_vg'][4]
            self.targets_vgCa = p.vg_options['Ca_vg'][5]

            # Initialize matrices defining states of vgK channels for each cell membrane:
            self.active_Ca = np.zeros(self.data_length)

            self.vgCa_state = np.zeros(self.data_length)   # state can be 0 = off, 1 = open

        if p.vg_options['K_cag'] != 0:

            self.maxDmKcag = p.vg_options['K_cag'][0]
            self.Kcag_halfmax = p.vg_options['K_cag'][1]
            self.Kcag_n = p.vg_options['K_cag'][2]
            self.targets_cagK = p.vg_options['K_cag'][3]

            # Initialize matrices defining states of cag K channels for each cell membrane:
            self.active_Kcag = np.zeros(self.data_length)


        # calcium dynamics
        if p.Ca_dyn_options['CICR'] != 0:

            self.stateER = np.zeros(len(cells.cell_i))   # state of ER membrane Ca permeability

            self.maxDmCaER = p.Ca_dyn_options['CICR'][0][0]
            self.topCa = p.Ca_dyn_options['CICR'][0][1]
            self.bottomCa =  p.Ca_dyn_options['CICR'][0][2]

            if len(p.Ca_dyn_options['CICR'][1])!=0:

                self.midCaR = p.Ca_dyn_options['CICR'][1][0]
                self.widthCaR = p.Ca_dyn_options['CICR'][1][1]

            if len(p.Ca_dyn_options['CICR'][2])!=0:

                self.KhmIP3 = p.Ca_dyn_options['CICR'][2][0]
                self.n_IP3 = p.Ca_dyn_options['CICR'][2][1]

            self.apply_Ca = p.Ca_dyn_options['CICR'][3]


    def globalDyn(self,sim,cells,p):

        if p.global_options['K_env'] != 0:

            effector_Kenv = tb.pulse(t,self.t_on_Kenv,self.t_off_Kenv,self.t_change_Kenv)

            self.cc_env[self.iK][:] = self.mem_mult_Kenv*effector_Kenv*p.cK_env + p.cK_env

        if p.global_options['Cl_env'] != 0 and p.ions_dict['Cl'] == 1:

            effector_Clenv = tb.pulse(t,self.t_on_Clenv,self.t_off_Clenv,self.t_change_Clenv)

            self.cc_env[self.iCl][:] = self.mem_mult_Clenv*effector_Clenv*p.cCl_env + p.cCl_env

        if p.global_options['Na_env'] != 0:

            effector_Naenv = tb.pulse(t,self.t_on_Naenv,self.t_off_Naenv,self.t_change_Naenv)

            self.cc_env[self.iNa][:] = self.mem_mult_Naenv*effector_Naenv*p.cNa_env + p.cNa_env

        if p.global_options['T_change'] != 0:

            self.T = self.multT*tb.pulse(t,self.tonT,self.toffT,self.trampT)*p.T + p.T

        if p.global_options['gj_block'] != 0:

            self.gj_block = (1.0 - tb.pulse(t,self.tonGJ,self.toffGJ,self.trampGJ))

        if p.global_options['NaKATP_block'] != 0:

            self.NaKATP_block = (1.0 - tb.pulse(t,self.tonNK,self.toffNK,self.trampNK))

        if p.global_options['HKATP_block'] != 0:

            self.HKATP_block = (1.0 - tb.pulse(t,self.tonHK,self.toffHK,self.trampHK))

    def scheduledDyn(self,sim,cells,p):

        if p.scheduled_options['Na_mem'] != 0:

            if p.ions_dict['Na'] == 0 or target_length == 0:
                pass

            else:

                effector_Na = tb.pulse(t,self.t_on_Namem,self.t_off_Namem,self.t_change_Namem)

                self.Dm_scheduled[self.iNa][self.scheduled_target_inds] = self.mem_mult_Namem*effector_Na*p.Dm_Na

        if p.scheduled_options['K_mem'] != 0:

            if p.ions_dict['K'] == 0 or target_length == 0:
                pass

            else:

                effector_K = tb.pulse(t,self.t_on_Kmem,self.t_off_Kmem,self.t_change_Kmem)

                self.Dm_scheduled[self.iK][self.scheduled_target_inds] = self.mem_mult_Kmem*effector_K*p.Dm_K

        if p.scheduled_options['Cl_mem'] != 0:

            if p.ions_dict['Cl'] == 0 or target_length == 0:
                pass

            else:

                effector_Cl = tb.pulse(t,self.t_on_Clmem,self.t_off_Clmem,self.t_change_Clmem)

                self.Dm_scheduled[self.iCl][self.scheduled_target_inds] = self.mem_mult_Clmem*effector_Cl*p.Dm_Cl

        if p.scheduled_options['Ca_mem'] != 0:

            if p.ions_dict['Ca'] == 0 or target_length == 0:
                pass

            else:

                effector_Ca = tb.pulse(t,self.t_on_Camem,self.t_off_Camem,self.t_change_Camem)

                self.Dm_scheduled[self.iCa][self.scheduled_target_inds] = self.mem_mult_Camem*effector_Ca*p.Dm_Ca

        if p.scheduled_options['IP3'] != 0:

            self.cIP3[self.scheduled_target_inds] = self.cIP3[self.scheduled_target_inds] + self.rate_IP3*pulse(t,self.t_onIP3,
                self.t_offIP3,self.t_changeIP3)


    def dynamicDyn(self,sim,cells,p):

        self.dvsign = np.sign(self.dvm)

    def vgSodium(self,sim,cells,p):

        # Logic phase 1: find out which cells have activated their vgNa channels
        truth_vmGTvon_Na = self.vm > self.v_activate_Na  # returns bools of vm that are bigger than threshhold
        #truth_depol_Na = dvsign==1  # returns bools of vm that are bigger than threshhold
        truth_not_inactivated_Na = self.inactivated_Na == 0  # return bools of vm that can activate
        truth_vgNa_Off = self.vgNa_state == 0 # hasn't been turned on yet

        # find the cell indicies that correspond to all statements of logic phase 1:
        inds_activate_Na = (truth_vmGTvon_Na*truth_not_inactivated_Na*truth_vgNa_Off*
                            self.target_cells).nonzero()

        self.vgNa_state[inds_activate_Na] = 1 # open the channel
        self.vgNa_aliveTimer[inds_activate_Na] = t + self.t_alive_Na # set the timers for the total active state
        self.vgNa_deadTimer[inds_activate_Na] = 0  # reset any timers for an inactivated state to zero

        # Logic phase 2: find out which cells have closed their gates due to crossing inactivating voltage:
        truth_vgNa_On = self.vgNa_state == 1  # channel must be on already
        truth_vmGTvoff_Na = self.vm > self.v_inactivate_Na  # bools of cells that have vm greater than shut-off volts

        inds_inactivate_Na = (truth_vgNa_On*truth_vmGTvoff_Na*self.target_cells).nonzero()

        self.vgNa_state[inds_inactivate_Na] = 0    # close the vg sodium channels
        self.inactivated_Na[inds_inactivate_Na] = 1   # switch these so cells do not re-activate
        self.vgNa_aliveTimer[inds_inactivate_Na] = 0            # reset any alive timers to zero
        self.vgNa_deadTimer[inds_inactivate_Na] = t + self.t_dead_Na # set the timer of the inactivated state

         # Logic phase 3: find out if cell activation state has timed out, also rendering inactivated state:

        truth_vgNa_act_timeout = self.vgNa_aliveTimer < t   # find cells that have timed out their vgNa open state
        truth_vgNa_On = self.vgNa_state == 1 # ensure the vgNa is indeed open
        inds_timeout_Na_act = (truth_vgNa_act_timeout*truth_vgNa_On*self.target_cells).nonzero()

        self.vgNa_state[inds_timeout_Na_act] = 0             # set the state to closed
        self.vgNa_aliveTimer[inds_timeout_Na_act] = 0            # reset the timers to zero
        self.inactivated_Na[inds_timeout_Na_act] = 1    # inactivate the channel so it can't reactivate
        self.vgNa_deadTimer[inds_timeout_Na_act] = t + self.t_dead_Na # set the timer of the inactivated state

        # Logic phase 4: find out if inactivation timers have timed out:
        truth_vgNa_inact_timeout = self.vgNa_deadTimer <t  # find cells that have timed out their vgNa inact state
        truth_vgNa_Off = self.vgNa_state == 0 # check to make sure these channels are indeed closed
        inds_timeout_Na_inact = (truth_vgNa_inact_timeout*truth_vgNa_Off*self.target_cells).nonzero()

        self.vgNa_deadTimer[inds_timeout_Na_inact] = 0    # reset the inactivation timer
        self.inactivated_Na[inds_timeout_Na_inact] = 0    # remove inhibition to activation

        # Logic phase 5: find out if cells have passed below threshhold to become deactivated:
        truth_vmLTvreact_Na = self.vm < self.v_deactivate_Na # voltage is lower than the deactivate voltage

        inds_deactivate_Na = (truth_vmLTvreact_Na*self.target_cells).nonzero()

        self.inactivated_Na[inds_deactivate_Na] = 0  # turn any inhibition to activation off
        self.vgNa_state[inds_deactivate_Na] = 0   # shut the Na channel off if it's on
        self.vgNa_aliveTimer[inds_deactivate_Na] = 0       # reset any alive-timers to zero
        self.vgNa_deadTimer[inds_deactivate_Na] = 0   # reset any dead-timers to zero


        # Define ultimate activity of the vgNa channel:

        self.Dm_vg[self.iNa] = self.maxDmNa*self.vgNa_state

    def vgPotassium(self,sim,cells,p):
         # detecting channels to turn on:

        truth_vmGTvon_K = self.vm > self.v_on_K  # bools for cells with vm greater than the on threshold for vgK
        truth_depol_K = self.dvsign == 1  # bools matrix for cells that are depolarizing
        truth_vgK_OFF = self.vgK_state == 0   # bools matrix for cells that are in the off state

        # cells at these indices will become activated in this time step:
        inds_activate_K = (truth_vmGTvon_K*truth_depol_K*truth_vgK_OFF*self.target_cells).nonzero()
        self.vgK_state[inds_activate_K] = 1  # set the state of these channels to "open"
        self.vgK_OFFtime[inds_activate_K] = self.t_alive_K + t  # set the time at which these channels will close

        #  detecting channels to turn off:
        truth_vgK_ON = self.vgK_state == 1  # detect cells that are in their on state
        truth_vgK_timeout = self.vgK_OFFtime < t     # detect the cells that have expired off timers
        inds_deactivate_K = (truth_vgK_ON*truth_vgK_timeout*self.target_cells).nonzero()
        self.vgK_state[inds_deactivate_K] = 0 # turn off the channels to closed
        self.vgK_OFFtime[inds_deactivate_K] = 0

        inds_open_K = (self.vgK_state == 1).nonzero()
        self.active_K[inds_open_K] = 1

        inds_closed_K =(self.vgK_state == 0).nonzero()
        self.active_K[inds_closed_K] = 0

        self.Dm_vg[self.iK] = self.maxDmK*self.active_K

    def vgCalcium(self,sim,cells,p):
         # detect condition to turn vg_Ca channel on:
        truth_vmGTvon_Ca = self.vm > self.v_on_Ca  # bools for cells with vm greater than the on threshold for vgK
        truth_caLTcaOff = self.cc_cells[self.iCa] < self.ca_lower_ca # check that cellular calcium is below inactivating Ca
        truth_depol_Ca = self.dvsign == 1  # bools matrix for cells that are depolarizing
        truth_vgCa_OFF = self.vgCa_state == 0   # bools matrix for cells that are in the off state

        # cells at these indices will become activated in this time step:
        inds_activate_Ca = (truth_vmGTvon_Ca*truth_depol_Ca*truth_caLTcaOff*truth_vgCa_OFF*self.target_cells).nonzero()
        self.vgCa_state[inds_activate_Ca] = 1  # set the state of these channels to "open"

        # detect condition to turn off vg_Ca channel:
        truth_caGTcaOff = self.cc_cells[self.iCa] > self.ca_upper_ca   # check that calcium exceeds maximum
        truth_vgCa_ON = self.vgCa_state == 1 # check that the channel is on
        inds_inactivate_Ca = (truth_caGTcaOff*truth_vgCa_ON*self.target_cells).nonzero()
        self.vgCa_state[inds_inactivate_Ca] = 0

        # additional condition to turn off vg_Ca via depolarizing voltage:
        truth_vmGTvcaOff = self.vm > self.v_off_Ca
        inds_inactivate_Ca_2 = (truth_vmGTvcaOff*self.target_cells*truth_vgCa_ON).nonzero()
        self.vgCa_state[inds_inactivate_Ca_2] = 0


        inds_open_Ca = (self.vgCa_state == 1).nonzero()
        self.active_Ca[inds_open_Ca] = 1

        inds_closed_Ca =(self.vgCa_state == 0).nonzero()
        self.active_Ca[inds_closed_Ca] = 0

        self.Dm_vg[self.iCa] = self.maxDmCa*self.active_Ca


    def cagPotassium(self,sim,cells,p):

        inds_cagK_targets = (self.target_cells).nonzero()

        self.active_Kcag[inds_cagK_targets] = tb.hill(self.cc_cells[self.iCa][inds_cagK_targets],
            self.Kcag_halfmax,self.Kcag_n)

        self.Dm_cag[self.iK] = self.maxDmKcag*self.active_Kcag

        # finally, add together all effects to make change on the cell membrane permeabilities:
        self.Dm_cells = self.Dm_scheduled + self.Dm_vg + self.Dm_cag + self.Dm_base


    def calciumDynamics(self,sim,cells,p):

        if p.Ca_dyn_options['CICR'] != 0:

            dcc_CaER_sign = np.sign(self.dcc_ER[0])

            if len(p.Ca_dyn_options['CICR'][1])==0:
                term_Ca_reg = 1.0

            else:
                term_Ca_reg = (np.exp(-((self.cc_cells[self.iCa]-self.midCaR)**2)/((2*self.widthCaR)**2)))

            if len(p.Ca_dyn_options['CICR'][2]) == 0:
                term_IP3_reg = 1.0

            else:
                term_IP3_reg = tb.hill(self.cIP3,self.KhmIP3,self.n_IP3)

            if p.FMmod == 1:
                span = self.topCa - self.bottomCa
                FMmod = p.ip3FM*span
                topCa = self.topCa - FMmod*term_IP3_reg
            else:
                topCa = self.topCa

            truth_overHighCa = self.cc_er[0] >=  topCa
            truth_increasingCa = dcc_CaER_sign == 1
            truth_alreadyClosed = self.stateER == 0.0
            inds_open_ER = (truth_overHighCa*truth_increasingCa*truth_alreadyClosed).nonzero()

            truth_underBottomCa = self.cc_er[0]< self.bottomCa
            truth_decreasingCa = dcc_CaER_sign == -1
            truth_alreadyOpen = self.stateER == 1.0
            inds_close_ER = (truth_underBottomCa*truth_alreadyOpen).nonzero()

            self.stateER[inds_open_ER] = 1.0
            self.stateER[inds_close_ER] = 0.0

            self.Dm_er_CICR[0] = self.maxDmCaER*self.stateER*term_IP3_reg*term_Ca_reg

            self.Dm_er = self.Dm_er_CICR + self.Dm_er_base

    def tissueDefine(self,sim,cells,p):

        if p.scheduled_targets == 'none':
            self.scheduled_target_inds = []
            self.scheduled_target_mem_inds = []

        elif p.scheduled_targets == 'all':
            self.scheduled_target_inds = cells.cell_i
            self.scheduled_target_mem_inds = cells.mem_i

        elif p.scheduled_targets =='random1':
            shuffle(cells.cell_i)
            trgt2 = cells.cell_i[0]

            self.scheduled_target_inds = [trgt2]

            self.scheduled_target_mems_inds = cells.cell_to_mems[trgt2]
            self.scheduled_target_mems_inds,_,_ = tb.flatten(self.scheduled_target_mems_inds)

        elif p.scheduled_targets == 'random50':
            shuffle(cells.cell_i)
            halflength = int(len(cells.cell_i)/2)
            self.scheduled_target_inds = [cells.cell_i[x] for x in range(0,halflength)]

            trgt3 = self.scheduled_target_inds

            self.scheduled_target_mems_inds = cells.cell_to_mems[trgt3]
            self.scheduled_target_mems_inds,_,_ = tb.flatten(self.scheduled_target_mems_inds)


        elif isinstance(p.scheduled_targets, list):

            self.scheduled_target_inds = p.scheduled_targets

            trgt4 = self.scheduled_target_inds

            self.scheduled_target_mems_inds = cells.cell_to_mems[trgt4]
            self.scheduled_target_mems_inds,_,_ = tb.flatten(self.scheduled_target_mems_inds)


# To call a function "omelet" defined in the current module, any of the following should work:
#     globals()['omelet']()
#
#     getattr(sys.modules[__name__], 'omelet')()
#
#     import dynamics
#     getattr(dynamics, 'omelet')()
#
# To call a function "bomblet" defined in another module "fastido", the following should work:
#     import fastido
#     getattr(fastido, 'bomblet')()