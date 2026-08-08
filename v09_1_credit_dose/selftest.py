#!/usr/bin/env python3
from __future__ import annotations
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
from v09_1_credit_dose.sweep import run_dose

class A:
    lag=20; probe_steps=120; ticks=9; eval_interval=3; drive_steps=32; reward_gain=4.0; base_retro_gain=.48

cfg=V09Config(size=31,seed=3,bootstrap_mass=70,bootstrap_max=280,morph_disorder=.28,
              probe_steps=A.probe_steps,development_ticks=A.ticks,eval_interval=A.eval_interval,
              developmental_drive_steps=A.drive_steps,developmental_lag=A.lag,
              cone_steer_beta=1.85,max_tips=6,reward_gain=A.reward_gain,retrograde_credit_gain=A.base_retro_gain)
base=CausalEligibilityArbor(cfg); boot=base.bootstrap(); assert boot['ok'] and boot['mass']==70
r0=run_dose(base,0.0,A,3); r1=run_dose(base,1.0,A,3); r4=run_dose(base,4.0,A,3)
assert abs(r0['retrograde_gain']) < 1e-12
assert abs(r1['retrograde_gain']-.48) < 1e-12
assert abs(r4['retrograde_gain']-1.92) < 1e-12
assert r0['receipt']['credit_mass'] == 0.0
assert r1['receipt']['tag_mass'] == r4['receipt']['tag_mass'], (r1['receipt']['tag_mass'],r4['receipt']['tag_mass'])
assert r0['receipt']['final_mass']==70 and r1['receipt']['final_mass']==70 and r4['receipt']['final_mass']==70
print('bootstrap',boot)
print('gains',r0['retrograde_gain'],r1['retrograde_gain'],r4['retrograde_gain'])
print('credit masses',r0['receipt']['credit_mass'],r1['receipt']['credit_mass'],r4['receipt']['credit_mass'])
print('tag mass 1x/4x',r1['receipt']['tag_mass'],r4['receipt']['tag_mass'])
print('SELFTEST PASS')
