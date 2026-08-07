#!/usr/bin/env python3
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v04_geometry_only.cable_arbor import CableArbor,CableConfig
print('Functional Arbor v0.4 controlled cable selftest')
a=CableArbor(CableConfig(seed=1))
print('  mass',a.initial_mass,'K bond values',a.cfg.k_bath,a.cfg.k_arbor)
assert a.length_diff()==0
base=a.delays();print('  straight delays',base)
for x in (9,14,18):
    assert a.add_detour(0,x=x,side=-1)
print('  after 3 A detours dL',a.length_diff(),'delay',a.delays())
assert a.length_diff()==6
assert a.delays()['edge50']>base['edge50']
assert int(a.body.sum())==a.initial_mass
print('SELFTEST PASS')
