#!/usr/bin/env python3
from __future__ import annotations
import os,sys,math
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v07_persistent_ephaptic.persistent_arbor import V07Config,PersistentEphapticArbor
else:
    from .persistent_arbor import V07Config,PersistentEphapticArbor

def main():
    c=V07Config(size=31,seed=2,bootstrap_mass=70,bootstrap_max=280,developmental_drive_steps=58)
    m=PersistentEphapticArbor(c);b=m.bootstrap();assert b['ok'];m.prepare_development()
    print('Functional Arbor v0.7 selftest')
    print('[1] bootstrap / fixed-speed binary body')
    ks=m.bond_fields(True);vals=sorted(set(np.concatenate([x.ravel() for x in ks]).tolist()))
    assert len(vals)==2 and abs(vals[0]-c.k_mature_bath)<1e-8 and abs(vals[1]-c.k_arbor)<1e-6
    print(f"  ok mass={m.mass()} tree={m.is_tree()} L={m.path_length(0)}/{m.path_length(1)} K={vals}")

    print('[2] grounded quasi-static solver')
    s=np.zeros((c.size,c.size),np.complex128);s[c.size//2,c.size//2-2]=1;s[c.size//2,c.size//2+2]=-1
    v=m.solve_extracellular(s);assert np.max(np.abs(v))>1e-5
    assert np.max(np.abs(v[[0,-1],:]))<1e-12 and np.max(np.abs(v[:,[0,-1]]))<1e-12
    print(f"  ok max|Ve|={np.max(np.abs(v)):.4e}, grounded boundary=0")

    print('[3] matched-power phase controls')
    m.drive_sequence(20,'coherent',58);p0=np.asarray(m.field_power[-20:]);chem0=m.chem.copy()
    # Re-run from an identical copy so intracellular activity is identical.
    q=PersistentEphapticArbor(V07Config(**c.as_dict()));q.body=m.body.copy();q.morph=m.morph.copy();q.prepare_development();q.drive_sequence(20,'phase_reverse',58)
    assert np.allclose(p0,np.asarray(q.field_power[-20:]),rtol=1e-5,atol=1e-10)
    assert np.allclose(chem0,q.chem,rtol=1e-5,atol=1e-5)
    print(f"  ok coherent/reversed mean |E|^2 matched at {p0.mean():.4e}; chemistry matched")

    print('[4] persistent one-cell growth, separate retraction')
    # Seed eligibility broadly so a tip can initiate; one structural tick may extend one cell only.
    m.E[m.body>0]=1.;mass0=m.mass();ev=m.structural_tick('coherent');assert m.mass() in (mass0,mass0+1)
    # If extension incurred debt, the independent retraction in the same tick pays at most one cell.
    n_ext=sum(e.get('event') in ('extend','reconnect') for e in ev if isinstance(e,dict))
    assert n_ext<=1
    for _ in range(8):
        m.E[m.body>0]=1.;m.structural_tick('coherent')
    assert m.both_connected();assert m.settle_mass();assert m.mass()==mass0
    print(f"  ok extensions={m.extensions} reconnections={m.reconnections} retractions={m.retractions}; mass={m.mass()}")
    print('SELFTEST PASS')
if __name__=='__main__':main()
