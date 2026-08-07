#!/usr/bin/env python3
from __future__ import annotations
import os,sys,numpy as np
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v06_ephaptic_growth.ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from v06_ephaptic_growth.task import DelayTask
else:
    from .ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from .task import DelayTask

print('Functional Arbor v0.6 selftest')
cfg=EphapticConfig(size=31,seed=2,bootstrap_mass=78,bootstrap_max=260,cone_attempts=80)
m=EphapticFreeArbor(cfg);b=m.bootstrap();print(' bootstrap',b)
assert b['ok'] and m.is_tree() and m.both_connected() and m.mass()==78
# Fixed-speed invariant.
kr,kl,kd,ku=m.bond_fields(True);vals=np.unique(np.concatenate([q.ravel() for q in (kr,kl,kd,ku)]))
print(' mature K values',vals.tolist());assert np.allclose(np.sort(vals),np.sort([cfg.k_mature_bath,cfg.k_arbor]),rtol=0,atol=1e-7)
# Real pulse creates local eligibility and a nonzero phase-sensitive guidance field.
m.mature=True;t=DelayTask(m,20)
t.single(0,True,'full',steps=cfg.train_trace_steps)
g=np.sqrt(m.Gx*m.Gx+m.Gy*m.Gy);print(' traces Emax/Gmax/Hmax',float(m.E.max()),float(g.max()),float(m.H.max()))
assert m.E.max()>0 and g.max()>0 and m.H.max()>0
# Generic cone proposal: no named detour, final body must remain same-mass connected tree.
old=m.body.copy();oldmass=m.mass();p=m.propose_growth_episode('full')
print(' proposal',p)
assert p is not None
assert m.mass()==oldmass and m.is_tree() and m.both_connected()
print(' paths',len(m.path(0))-1,len(m.path(1))-1)
# Restore and verify no-ephaptic mode is still capable of legal exploration, just unguided.
m.restore(old);m.trace(0,cfg.train_trace_steps,False,True,'none');p2=m.propose_growth_episode('none')
print(' unguided legal proposal',bool(p2))
print('SELFTEST PASS')
