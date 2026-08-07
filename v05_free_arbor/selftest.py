#!/usr/bin/env python3
from __future__ import annotations
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v05_free_arbor.free_arbor import FreeConfig,FreeBinaryArbor
from v05_free_arbor.task import DelayTask

print('Functional Arbor v0.5 selftest')
m=FreeBinaryArbor(FreeConfig(seed=2,bootstrap_mass=70,bootstrap_max=220))
b=m.bootstrap();print(' bootstrap',b)
assert b['ok'] and m.is_tree() and m.both_connected()
assert m.edge_count()==m.mass()-1
mass=m.mass();m.mature=True;t=DelayTask(m,10)
pre=t.delays();LA0,LB0=m.path_length(0),m.path_length(1)
print(' pre delay',pre,'paths',LA0,LB0)
# A real pulse supplies eligibility; the generic free-body surgery must discover a
# local detour without being handed a pre-drawn cable or target detour location.
t.single(0,accumulate=True,steps=m.cfg.train_trace_steps)
snap=m.snapshot();prop=m.propose_detour(0)
print(' proposal',prop)
assert prop is not None
assert m.mass()==mass and m.is_tree() and m.both_connected()
post=t.delays();LA1,LB1=m.path_length(0),m.path_length(1)
print(' post delay',post,'paths',LA1,LB1)
assert prop['onA'] and not prop['onB']
assert LA1-LA0==2 and LB1==LB0
assert post['edge50']-pre['edge50']>=7
# Structural move only: every occupied bond remains exactly the same K.
kr,kl,kd,ku=m.bond_fields(True);vals=set()
for a in (kr,kl,kd,ku):vals.update(round(float(x),7) for x in set(a.ravel()))
print(' bond K values',sorted(vals));assert vals.issubset({round(m.cfg.k_arbor,7),round(m.cfg.k_mature_bath,7)})
m.restore(snap);assert m.mass()==mass and m.is_tree()
print('SELFTEST PASS')
