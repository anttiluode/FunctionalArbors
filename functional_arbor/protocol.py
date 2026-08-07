from __future__ import annotations
import numpy as np
from .model import FunctionalArbor


def train_probe(cfg,condition='credit',reverse=False):
    m=FunctionalArbor(cfg,condition); hist=m.train(reverse); slow=m.clone_slow_state()
    q=FunctionalArbor(cfg,condition);q.load_slow_state(slow); pf=q.probe_sequence(False)
    q2=FunctionalArbor(cfg,condition);q2.load_slow_state(slow); pr=q2.probe_sequence(True)
    pref=(pf['root_energy']-pr['root_energy'])/(pf['root_energy']+pr['root_energy']+1e-15)
    return {'model':m,'slow':slow,'history':hist,'fwd':pf,'rev':pr,'preference':float(pref),'signed_preference':float((-1 if reverse else 1)*pref)}


def functional_assay(cfg,condition='credit',reverse=False):
    r=train_probe(cfg,condition,reverse); state=r['slow']
    intact=FunctionalArbor(cfg,condition);intact.load_slow_state(state); p=intact.probe_sequence(reverse); usage=p['use_map']; E0=p['root_energy']
    bath=FunctionalArbor(cfg,condition);bath.substrate=state['substrate'].copy(); Eb=bath.probe_sequence(reverse)['root_energy']
    les=FunctionalArbor(cfg,condition);les.load_slow_state(state); mask,rm=les.lesion_from_usage(usage); El=les.probe_sequence(reverse)['root_energy']
    low=FunctionalArbor(cfg,condition);low.load_slow_state(state); lmask,lrm=low.low_use_matched_lesion(usage,rm,forbidden=mask); Er=low.probe_sequence(reverse)['root_energy']
    return {'train':r,'intact':E0,'bath':Eb,'lesion':El,'lowuse':Er,
            'gain':(E0-Eb)/(E0+1e-15),'target_drop':(E0-El)/(E0+1e-15),'lowuse_drop':(E0-Er)/(E0+1e-15),
            'M':state['M'],'usage':usage,'lesion_mask':mask,'lowuse_mask':lmask,'removed':rm,'low_removed':lrm}

def regrowth_assay(cfg,condition='credit',reverse=False):
    base=functional_assay(cfg,condition,reverse)
    # Recreate the trained state, apply the same high-use lesion, then reopen development.
    state=base['train']['slow']; reg=FunctionalArbor(cfg,condition);reg.load_slow_state(state)
    reg.mature_arbor(); mask,_=reg.lesion_from_usage(base['usage']); les_state=reg.clone_slow_state()
    before=reg.probe_sequence(reverse)['root_energy']
    # Reopen the developmental bath; preserve learned per-patch baselines as the teaching reference.
    reg.mature=False; reg.reset_fast(); order=[0,3,2,1] if reverse else [0,1,2,3]
    for _ in range(cfg.regrow_cycles):
        for p in order: reg.visit(p,learn=True)
    after=reg.probe_sequence(reverse)['root_energy']
    intact=base['intact']
    recovery=(after-before)/(intact-before+1e-15)
    return {'intact':intact,'before':before,'after':after,'recovery':float(recovery),'M':reg.M,'mask':mask}
