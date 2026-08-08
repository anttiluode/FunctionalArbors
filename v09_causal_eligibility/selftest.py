#!/usr/bin/env python3
from __future__ import annotations
import os, sys
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
else:
    from .eligibility_arbor import V09Config, CausalEligibilityArbor


def main():
    m=CausalEligibilityArbor(V09Config(size=31,seed=3,bootstrap_mass=70,bootstrap_max=280,probe_steps=120))
    boot=m.bootstrap(); print('bootstrap',boot); assert boot['ok'] and m.mass()==70
    m.mature=True
    vals=[]
    for a in m.bond_fields(True): vals.extend(np.unique(a).tolist())
    vals=sorted(set(round(float(x),7) for x in vals)); print('K values',vals); assert len(vals)==2

    m.prepare_development(); mass0=m.mass()
    # Force at least one ordinary one-cell structural extension through the real v0.7 primitive.
    made=False
    for p in m._start_candidates():
        tip={'pos':p,'prev':None,'age':0,'stall':0,'alive':True,'trail':[],'origin':p}
        ev=m.extend_tip(tip,'coherent')
        if ev.get('event') in ('extend','reconnect'):
            made=True; q=tuple(ev['to']); print('event',ev,'birth',m.birth_tick[q]); assert m.birth_tick[q]==m.dev_tick; break
    assert made
    et=m.event_tag(0); assert et.sum()>=1
    sh=m.shuffled_event_tag(et); print('event/shuffle mass',et.sum(),sh.sum()); assert sh.sum()==et.sum(); assert np.sum((et>0)&(sh>0))==0

    # Signed timing semantics: A-only and B-only event cells must receive opposite signs.
    pa=set(m.path(0) or []); pb=set(m.path(1) or []); ao=list(pa-pb); bo=list(pb-pa)
    fake=np.zeros_like(m.support)
    if ao: fake[ao[0]]=1
    if bo: fake[bo[0]]=1
    pos,neg,err=m.timing_tags(fake,20,0)
    print('timing error',err,'pos',pos.sum(),'neg',neg.sum())
    if ao and bo: assert pos[ao[0]]>0 and neg[bo[0]]>0

    # Frozen v0.8 graph-retrograde carrier: first arrival = graph distance exactly.
    tag=(m.body>0).astype(np.float32); tag[m.soma]=0
    m.support.fill(.20); before=m.support.copy(); m.launch_tagged_retrograde(.8,tag,'latency')
    dist=m.graph_distance_from_soma(); first=np.full(m.body.shape,-1,int)
    for t in range(1,int(dist.max())+3):
        prev=m.support.copy(); m.transport_credit_tick('retrograde'); delta=np.abs(m.support-prev)
        hit=(delta>1e-10)&(first<0); first[hit]=t
    mask=(m.body>0)&(dist>0)&(first>0)
    corr=float(np.corrcoef(dist[mask],first[mask])[0,1]); slope=float(np.polyfit(dist[mask],first[mask],1)[0])
    print('retro latency corr',corr,'slope',slope); assert corr>0.999999 and abs(slope-1)<1e-9

    # Any temporary mass debt must still be repayable by the inherited independent retraction process.
    m.material_target=mass0; ok=m.settle_mass(); print('settled',ok,'mass',m.mass()); assert ok and m.mass()==mass0 and m.both_connected()
    print('SELFTEST PASS')

if __name__=='__main__': main()
