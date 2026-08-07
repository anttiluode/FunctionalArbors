#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json,math,os,sys,time
from pathlib import Path
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v06_ephaptic_growth.ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from v06_ephaptic_growth.task import DelayTask
else:
    from .ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from .task import DelayTask

ARMS={
 'full':('full','reward'),
 'no_ephaptic':('none','reward'),
 'magnitude_only':('magnitude','reward'),
 'phase_shuffle':('phase_shuffle','reward'),
 'shuffle_credit':('full','shuffle'),
 'no_credit':('full','local'),
}

def signflip(d):
    d=np.asarray(d,float);n=len(d);obs=abs(float(d.mean()))
    if n==0:return float('nan')
    if n<=16:vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)]
    else:
        r=np.random.default_rng(0);vals=[abs(float(np.mean(d*r.choice([-1.,1.],n)))) for _ in range(40000)]
    return float(np.mean(np.asarray(vals)>=obs-1e-12))

def run_arm(base,arm,lag,mutations,seed):
    guide,credit=ARMS[arm];m=base.copy();m.mature=True;t=DelayTask(m,lag)
    pre_score,_,_=t.contrast();pre_delay=t.delays();pre_stats=m.branch_stats();mass0=m.mass();score=pre_score
    rng=np.random.default_rng(seed+19071);accepted=0;legal=0;attempted=0;hist=[]
    for step in range(int(mutations)):
        which=int(rng.integers(2));attempted+=1
        # A real source pulse writes intracellular eligibility plus the requested
        # extracellular guidance ablation.
        t.single(which,True,guide,steps=m.cfg.train_trace_steps)
        snap=m.snapshot();old_stats=m.branch_stats();prop=m.propose_growth_episode(guide)
        if prop is None:
            hist.append({'step':step,'which':which,'proposal':None,'keep':False,'score':score});continue
        legal+=1;new,_,_=t.contrast();delta=float(new-score)
        if credit=='reward':signal=delta
        elif credit=='shuffle':signal=(1 if rng.random()<.5 else -1)*delta
        elif credit=='local':signal=float(prop.get('field_support',0.0))-.55
        else:raise ValueError(credit)
        keep=signal>1e-7
        if keep:score=new;accepted+=1
        else:m.restore(snap)
        ns=m.branch_stats() if keep else old_stats
        hist.append({'step':step,'which':which,'proposal':prop,'delta':delta,'signal':float(signal),'keep':bool(keep),
                     'score':float(score),'dL':int(ns['length_A']-ns['length_B'])})
        assert m.mass()==mass0 and m.is_tree() and m.both_connected()
    post=t.delays();stats=m.branch_stats();final,ta,ds=t.contrast()
    return dict(arm=arm,seed=seed,mass=m.mass(),accepted=accepted,legal=legal,attempted=attempted,
                pre_contrast=pre_score,contrast=final,target_peak=ta,distractor_peak=ds,pre_delay=pre_delay,delay=post,
                pre_stats=pre_stats,stats=stats,history=hist,body=m.body.tolist(),pathA=m.path(0),pathB=m.path(1))

def one_seed(seed,args,arms):
    cfg=EphapticConfig(size=args.size,seed=seed,bootstrap_mass=args.bootstrap_mass,bootstrap_max=args.bootstrap_max,
                       morph_disorder=args.disorder,mutations=args.mutations,probe_steps=args.probe_steps,
                       cone_attempts=args.cone_attempts,cone_max_steps=args.cone_max_steps,steer_beta=args.steer_beta)
    base=EphapticFreeArbor(cfg);boot=base.bootstrap()
    if not boot['ok']:return {'seed':seed,'bootstrap':boot,'arms':{}}
    rows={}
    for a in arms:rows[a]=run_arm(base,a,args.lag,args.mutations,seed)
    return {'seed':seed,'bootstrap':boot,'base_body':base.body.tolist(),'arms':rows}

def metric(r,k):
    if k=='length_diff':return r['stats']['length_A']-r['stats']['length_B']
    if k=='delta_length':return (r['stats']['length_A']-r['stats']['length_B'])-(r['pre_stats']['length_A']-r['pre_stats']['length_B'])
    if k=='contrast':return r['contrast']
    if k=='delta_contrast':return r['contrast']-r['pre_contrast']
    if k=='yield':return r['legal']/max(r['attempted'],1)
    if k=='accept_rate':return r['accepted']/max(r['legal'],1)
    return r['delay'][k]

def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--lag',type=int,default=20);p.add_argument('--size',type=int,default=31);p.add_argument('--mutations',type=int,default=18)
    p.add_argument('--bootstrap-mass',type=int,default=70,dest='bootstrap_mass');p.add_argument('--bootstrap-max',type=int,default=260,dest='bootstrap_max')
    p.add_argument('--probe-steps',type=int,default=210,dest='probe_steps');p.add_argument('--cone-attempts',type=int,default=8,dest='cone_attempts')
    p.add_argument('--cone-max-steps',type=int,default=10,dest='cone_max_steps');p.add_argument('--steer-beta',type=float,default=2.3,dest='steer_beta')
    p.add_argument('--disorder',type=float,default=.28);p.add_argument('--arms',default='full,no_ephaptic,magnitude_only,phase_shuffle,shuffle_credit,no_credit')
    p.add_argument('--out',default='ephaptic_out');a=p.parse_args();arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    for x in arms:
        if x not in ARMS:raise ValueError(x)
    rows=[];t0=time.time();print(f'Functional Arbor v0.6 ephaptic-growth learner lag={a.lag} seeds={a.seeds} mutations={a.mutations}')
    for s in range(a.seed_start,a.seed_start+a.seeds):
        z=one_seed(s,a,arms);rows.append(z);b=z['bootstrap'];print(f" seed{s} boot={b['ok']} mass={b.get('mass')} L={b.get('length_A')}/{b.get('length_B')} leaves={b.get('leaves')}")
        for arm,r in z['arms'].items():
            dL=r['stats']['length_A']-r['stats']['length_B'];print(f"   {arm:14s} dL {dL:+3d} e50 {r['delay']['edge50']:+4d} c25 {r['delay']['common25']:+4d} C {r['contrast']:+.4f} legal {r['legal']:2d} acc {r['accepted']:2d}")
    valid=[z for z in rows if z['arms']];summary={}
    keys=('length_diff','delta_length','edge50','common25','contrast','delta_contrast','yield','accept_rate')
    for arm in arms:
        rr=[z['arms'][arm] for z in valid];summary[arm]={}
        for k in keys:
            x=np.asarray([metric(r,k) for r in rr],float);summary[arm][k]=dict(mean=float(x.mean()),sd=float(x.std(ddof=1) if len(x)>1 else 0),values=x.tolist())
    # Paired comparisons always against full when available.
    if 'full' in arms:
        F=[z['arms']['full'] for z in valid]
        for arm in arms:
            if arm=='full':continue
            O=[z['arms'][arm] for z in valid];pair={}
            for k in ('length_diff','delta_length','edge50','common25','contrast','delta_contrast','yield'):
                d=np.asarray([metric(f,k)-metric(o,k) for f,o in zip(F,O)],float)
                pair[k]=dict(mean=float(d.mean()),sd=float(d.std(ddof=1) if len(d)>1 else 0),p=signflip(d),values=d.tolist())
            summary[f'paired_full_minus_{arm}']=pair
    # Mechanism correlation within full: geometry change vs timing change.
    if 'full' in arms:
        rr=[z['arms']['full'] for z in valid]
        dl=np.asarray([metric(r,'delta_length') for r in rr],float);dt=np.asarray([r['delay']['edge50']-r['pre_delay']['edge50'] for r in rr],float)
        if len(rr)>1 and dl.std()>0 and dt.std()>0:
            corr=float(np.corrcoef(dl,dt)[0,1]);slope,inter=np.polyfit(dl,dt,1)
        else:corr=slope=inter=float('nan')
        summary['full_geometry_timing']=dict(corr=corr,slope=float(slope),intercept=float(inter),delta_length=dl.tolist(),delta_edge50=dt.tolist())
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);payload={'args':vars(a),'summary':summary,'rows':rows}
    (out/'ephaptic_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('\nsummary')
    for arm in arms:
        s=summary[arm];print(f" {arm:14s} dL {s['length_diff']['mean']:+.2f} edge50 {s['edge50']['mean']:+.2f} C {s['contrast']['mean']:+.4f} yield {s['yield']['mean']:.2f}")
    for arm in ('no_ephaptic','magnitude_only','phase_shuffle','shuffle_credit','no_credit'):
        k=f'paired_full_minus_{arm}'
        if k in summary:
            q=summary[k];print(f" full-{arm:14s}: dL {q['length_diff']['mean']:+.2f} p={q['length_diff']['p']:.4f} edge50 {q['edge50']['mean']:+.2f} p={q['edge50']['p']:.4f} C {q['contrast']['mean']:+.4f} p={q['contrast']['p']:.4f}")
    if 'full_geometry_timing' in summary:
        q=summary['full_geometry_timing'];print(f" full corr(delta path, delta edge50)={q['corr']:.4f}, slope={q['slope']:.3f} frames/edge")
    print(f' elapsed {time.time()-t0:.1f}s; wrote {out}/ephaptic_results.json')
if __name__=='__main__':main()
