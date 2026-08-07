#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json,os,sys,time,math
from pathlib import Path
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v07_persistent_ephaptic.persistent_arbor import V07Config,PersistentEphapticArbor
    from v07_persistent_ephaptic.task import DelayTask
else:
    from .persistent_arbor import V07Config,PersistentEphapticArbor
    from .task import DelayTask

ARMS={
 'coherent':('coherent','reward'),
 'phase_scramble':('phase_scramble','reward'),
 'phase_reverse':('phase_reverse','reward'),
 'magnitude_only':('magnitude','reward'),
 'no_field':('none','reward'),
 'shuffle_credit':('coherent','shuffle'),
 'no_credit':('coherent','none'),
}

def signflip(d):
    d=np.asarray(d,float);n=len(d);obs=abs(float(d.mean()))
    if n==0:return float('nan')
    if n<=16:
        vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)]
    else:
        r=np.random.default_rng(0);vals=[abs(float(np.mean(d*r.choice([-1.,1.],n)))) for _ in range(50000)]
    return float(np.mean(np.asarray(vals)>=obs-1e-12))

def run_arm(base,arm,args,seed):
    mode,credit=ARMS[arm];m=base.copy();m.prepare_development();task=DelayTask(m,args.lag)
    pre_c,_,_=task.contrast();pre_d=task.delays();pre_stats=m.branch_stats();score=pre_c
    rng=np.random.default_rng(seed+70707);hist=[]
    for tick in range(args.ticks):
        # Every arm receives identical intracellular A->B dose. Only the extracellular
        # guidance representation changes.
        m.drive_sequence(args.lag,mode,args.drive_steps)
        events=m.structural_tick(mode)
        reward=0.0;raw_delta=0.0
        if (tick+1)%args.eval_interval==0:
            new,_,_=task.contrast();raw_delta=float(new-score)
            if credit=='reward':reward=math.tanh(m.cfg.reward_gain*raw_delta)
            elif credit=='shuffle':reward=(1 if rng.random()<.5 else -1)*math.tanh(m.cfg.reward_gain*raw_delta)
            elif credit=='none':reward=0.0
            m.apply_credit(reward);score=float(new)
        else:
            # Chemistry/activity can hold a new process between delayed task evaluations.
            m.apply_credit(0.0)
        hist.append({'tick':tick,'events':events,'score':float(score),'raw_delta':raw_delta,'reward':float(reward),
                     'mass':m.mass(),'dL':m.path_length(0)-m.path_length(1),'tips':sum(t.get('alive',False) for t in m.tips)})
    m.settle_mass();post_c,ta,ds=task.contrast();post_d=task.delays();stats=m.branch_stats();rec=m.state_receipt()
    return dict(arm=arm,seed=seed,pre_contrast=pre_c,contrast=post_c,target_peak=ta,distractor_peak=ds,
                pre_delay=pre_d,delay=post_d,pre_stats=pre_stats,stats=stats,receipt=rec,history=hist,
                body=m.body.tolist(),chem=m.chem.tolist())

def metric(r,k):
    if k=='length_diff':return r['stats']['length_A']-r['stats']['length_B']
    if k=='delta_length':return metric(r,'length_diff')-(r['pre_stats']['length_A']-r['pre_stats']['length_B'])
    if k=='contrast':return r['contrast']
    if k=='delta_contrast':return r['contrast']-r['pre_contrast']
    if k=='reconnections':return r['receipt']['reconnections']
    if k=='extensions':return r['receipt']['extensions']
    if k=='reconnect_rate':return r['receipt']['reconnections']/max(r['receipt']['extensions'],1)
    if k=='field_power':return r['receipt']['mean_field_power']
    return r['delay'][k]

def one_seed(seed,args,arms):
    cfg=V07Config(size=args.size,seed=seed,bootstrap_mass=args.bootstrap_mass,bootstrap_max=args.bootstrap_max,
                  morph_disorder=args.disorder,probe_steps=args.probe_steps,development_ticks=args.ticks,
                  eval_interval=args.eval_interval,developmental_drive_steps=args.drive_steps,developmental_lag=args.lag,
                  cone_steer_beta=args.steer_beta,max_tips=args.max_tips)
    base=PersistentEphapticArbor(cfg);boot=base.bootstrap()
    if not boot['ok']:return {'seed':seed,'bootstrap':boot,'arms':{}}
    rows={}
    for a in arms:rows[a]=run_arm(base,a,args,seed)
    return {'seed':seed,'bootstrap':boot,'base_body':base.body.tolist(),'arms':rows}

def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--lag',type=int,default=20);p.add_argument('--size',type=int,default=31);p.add_argument('--ticks',type=int,default=36)
    p.add_argument('--eval-interval',type=int,default=3,dest='eval_interval');p.add_argument('--drive-steps',type=int,default=64,dest='drive_steps')
    p.add_argument('--bootstrap-mass',type=int,default=70,dest='bootstrap_mass');p.add_argument('--bootstrap-max',type=int,default=280,dest='bootstrap_max')
    p.add_argument('--probe-steps',type=int,default=210,dest='probe_steps');p.add_argument('--max-tips',type=int,default=6,dest='max_tips')
    p.add_argument('--steer-beta',type=float,default=1.85,dest='steer_beta');p.add_argument('--disorder',type=float,default=.28)
    p.add_argument('--arms',default='coherent,phase_scramble,phase_reverse,magnitude_only,no_field,shuffle_credit,no_credit')
    p.add_argument('--out',default='v07_out');a=p.parse_args();arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    for x in arms:
        if x not in ARMS:raise ValueError(x)
    rows=[];t0=time.time();print(f'Functional Arbor v0.7 persistent ephaptic development lag={a.lag} seeds={a.seeds} ticks={a.ticks}')
    for s in range(a.seed_start,a.seed_start+a.seeds):
        z=one_seed(s,a,arms);rows.append(z);b=z['bootstrap'];print(f" seed{s} boot={b['ok']} mass={b.get('mass')} L={b.get('length_A')}/{b.get('length_B')}")
        for arm,r in z['arms'].items():
            dL=r['stats']['length_A']-r['stats']['length_B'];rr=r['receipt']
            print(f"   {arm:14s} dL {dL:+3d} e50 {r['delay']['edge50']:+4d} C {r['contrast']:+.4f} ext {rr['extensions']:2d} rec {rr['reconnections']:2d} rate {rr['reconnections']/max(rr['extensions'],1):.3f}")
    valid=[z for z in rows if z['arms']];summary={};keys=('length_diff','delta_length','edge50','common25','contrast','delta_contrast','extensions','reconnections','reconnect_rate','field_power')
    for arm in arms:
        rr=[z['arms'][arm] for z in valid];summary[arm]={}
        for k in keys:
            x=np.asarray([metric(r,k) for r in rr],float);summary[arm][k]=dict(mean=float(x.mean()),sd=float(x.std(ddof=1) if len(x)>1 else 0),values=x.tolist())
    if 'coherent' in arms:
        F=[z['arms']['coherent'] for z in valid]
        for arm in arms:
            if arm=='coherent':continue
            O=[z['arms'][arm] for z in valid];pair={}
            for k in ('length_diff','delta_length','edge50','common25','contrast','delta_contrast','reconnect_rate','field_power'):
                d=np.asarray([metric(f,k)-metric(o,k) for f,o in zip(F,O)],float)
                pair[k]=dict(mean=float(d.mean()),sd=float(d.std(ddof=1) if len(d)>1 else 0),p=signflip(d),values=d.tolist())
            summary[f'paired_coherent_minus_{arm}']=pair
        rr=F;dl=np.asarray([metric(r,'delta_length') for r in rr],float);dt=np.asarray([r['delay']['edge50']-r['pre_delay']['edge50'] for r in rr],float)
        if len(rr)>1 and dl.std()>0 and dt.std()>0:corr=float(np.corrcoef(dl,dt)[0,1]);slope,inter=np.polyfit(dl,dt,1)
        else:corr=slope=inter=float('nan')
        summary['coherent_geometry_timing']=dict(corr=corr,slope=float(slope),intercept=float(inter),delta_length=dl.tolist(),delta_edge50=dt.tolist())
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);payload={'args':vars(a),'summary':summary,'rows':rows}
    (out/'v07_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('\nsummary')
    for arm in arms:
        s=summary[arm];print(f" {arm:14s} dL {s['length_diff']['mean']:+.2f} e50 {s['edge50']['mean']:+.2f} C {s['contrast']['mean']:+.4f} rec/ext {s['reconnect_rate']['mean']:.3f} power {s['field_power']['mean']:.3e}")
    for arm in ('phase_scramble','phase_reverse','magnitude_only','no_field','shuffle_credit','no_credit'):
        k=f'paired_coherent_minus_{arm}'
        if k in summary:
            q=summary[k];print(f" coh-{arm:14s}: dL {q['length_diff']['mean']:+.2f} p={q['length_diff']['p']:.4f} e50 {q['edge50']['mean']:+.2f} p={q['edge50']['p']:.4f} C {q['contrast']['mean']:+.4f} p={q['contrast']['p']:.4f} recRate {q['reconnect_rate']['mean']:+.3f} p={q['reconnect_rate']['p']:.4f}")
    if 'coherent_geometry_timing' in summary:
        q=summary['coherent_geometry_timing'];print(f" coherent corr(delta path, delta edge50)={q['corr']:.4f}, slope={q['slope']:.3f} frames/edge")
    print(f' elapsed {time.time()-t0:.1f}s; wrote {out}/v07_results.json')
if __name__=='__main__':main()
