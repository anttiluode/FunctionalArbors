#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
else:
    from .eligibility_arbor import V09Config, CausalEligibilityArbor


def stats(m, tag):
    pts=[tuple(p) for p in np.argwhere(tag>0)]; d=m.graph_distance_from_soma()
    if not pts:return {'n':0,'mean_distance':None,'mean_age':None}
    ages=[]; ds=[]
    for p in pts:
        bt=int(m.birth_tick[p]); ages.append((m.dev_tick-bt) if bt>=0 else m.cfg.new_cell_grace+6); ds.append(int(d[p]))
    return {'n':len(pts),'mean_distance':float(np.mean(ds)),'mean_age':float(np.mean(ages))}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--seed',type=int,default=4); ap.add_argument('--ticks',type=int,default=18); ap.add_argument('--out',default='tag_instrument.json'); a=ap.parse_args()
    m=CausalEligibilityArbor(V09Config(size=31,seed=a.seed,bootstrap_mass=70,bootstrap_max=280,developmental_drive_steps=32,probe_steps=120))
    boot=m.bootstrap(); assert boot['ok']; m.prepare_development(); last=0; rows=[]
    for tick in range(a.ticks):
        m.drive_sequence(20,'coherent',32); m.structural_tick('coherent'); m.background_support_tick(); m.transport_credit_tick('retrograde')
        if (tick+1)%3==0:
            ev=m.event_tag(last); sh=m.shuffled_event_tag(ev); se=stats(m,ev); ss=stats(m,sh)
            if se['n']:
                assert se['n']==ss['n']; assert np.sum((ev>0)&(sh>0))==0
                rows.append({'tick':tick+1,'event':se,'shuffle':ss,'distance_error':abs(se['mean_distance']-ss['mean_distance']),'age_error':abs(se['mean_age']-ss['mean_age'])})
            last=m.dev_tick
    out={'seed':a.seed,'bootstrap':boot,'windows':rows,'mean_distance_error':float(np.mean([r['distance_error'] for r in rows])) if rows else None,'mean_age_error':float(np.mean([r['age_error'] for r in rows])) if rows else None}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
    assert rows

if __name__=='__main__': main()
