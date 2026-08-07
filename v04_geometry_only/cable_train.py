#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, math, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v04_geometry_only.cable_arbor import CableArbor,CableConfig


def pair_peak(a:CableArbor,lag:int,target:bool,steps:int=180):
    a.reset_fast(); tr=[]
    first,second=(0,1) if target else (1,0)
    for t in range(steps):
        s1=a.pulse_source(first,t);s2=a.pulse_source(second,t-lag)
        if isinstance(s1,float):src=s2
        elif isinstance(s2,float):src=s1
        else:src=s1+s2
        tr.append(a._advance(src))
    return float(max(tr))


def contrast(a,lag,steps=180):
    tg=pair_peak(a,lag,True,steps);ds=pair_peak(a,lag,False,steps)
    return float((tg-ds)/(tg+ds+1e-12)),tg,ds


def exact_signflip_p(d):
    d=np.asarray(d,float);n=len(d)
    if n==0:return float('nan')
    obs=abs(float(d.mean()))
    if n<=16:
        vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)]
    else:
        rng=np.random.default_rng(0);vals=[abs(float(np.mean(d*rng.choice([-1.,1.],size=n)))) for _ in range(30000)]
    return float(np.mean(np.asarray(vals)>=obs-1e-12))


def train_one(seed,mode,lag,steps_train=40,trace_steps=100,probe_steps=140):
    a=CableArbor(CableConfig(seed=seed,size=31,reserve_cells=20))
    current,_,_=contrast(a,lag,probe_steps)
    history=[]
    accepted=0
    rng=np.random.default_rng(seed+5021)
    for step in range(int(steps_train)):
        which=int(rng.integers(2))
        # The pulse creates the local eligibility field.  The proposed mutation
        # is constrained to that route and weighted by its recent activity.
        a.trace(which,trace_steps)
        snap=a.snapshot(); before=current
        prop=a.propose_mutation(which)
        if prop is None:
            history.append((step,which,'none',before,before,False,a.length_diff()))
            continue
        new,_,_=contrast(a,lag,probe_steps)
        delta=new-before
        if mode=='reward': signal=delta
        elif mode=='shuffle': signal=(1 if rng.random()<.5 else -1)*delta
        elif mode=='anti': signal=-delta
        elif mode=='blind': signal=(1 if rng.random()<.5 else -1)  # random walk, no soma credit
        else: raise ValueError(mode)
        keep=signal>1e-7
        if keep:
            current=new;accepted+=1
        else:
            a.restore(snap);current=before
        history.append((step,which,prop[1],before,new,keep,a.length_diff()))
    d=a.delays(probe_steps); final,tg,ds=contrast(a,lag,probe_steps)
    return {
        'seed':seed,'mode':mode,'lag':lag,'contrast':final,'target_peak':tg,'distractor_peak':ds,
        'delay':d,'length_A':a.path_length(0),'length_B':a.path_length(1),'length_diff':a.length_diff(),
        'detours_A':len(a.detours[0]),'detours_B':len(a.detours[1]),'mass':int(a.body.sum()),
        'accepted':accepted,'history':history,'body':a.body.tolist()
    }


def ms(v):
    x=np.asarray(v,float);return float(x.mean()),float(x.std(ddof=1) if len(x)>1 else 0.)


def run(lag,seeds,steps_train,arms,out,probe_steps=180):
    allr={}
    print(f'Functional Arbor v0.4 controlled geometry learner lag={lag} seeds={seeds} mutations={steps_train}')
    for mode in arms:
        rows=[]
        for seed in range(seeds):
            r=train_one(seed,mode,lag,steps_train,probe_steps=probe_steps);rows.append(r)
            print(f" {mode:7s} s{seed}: dL {r['length_diff']:+3d} edge50 {r['delay']['edge50']:+3d} c25 {r['delay']['common25']:+3d} contrast {r['contrast']:+.4f} detours {r['detours_A']}/{r['detours_B']} acc {r['accepted']}")
        allr[mode]=rows
    summary={}
    for mode,rows in allr.items():
        summary[mode]={}
        for key,fun in {
            'length_diff':lambda r:r['length_diff'],
            'edge50':lambda r:r['delay']['edge50'],
            'common25':lambda r:r['delay']['common25'],
            'contrast':lambda r:r['contrast'],
        }.items():
            summary[mode][key+'_mean'],summary[mode][key+'_sd']=ms([fun(r) for r in rows])
    if 'reward' in allr and 'shuffle' in allr:
        pair={}
        for key,fun in {
            'length_diff':lambda r:r['length_diff'],
            'edge50':lambda r:r['delay']['edge50'],
            'common25':lambda r:r['delay']['common25'],
            'contrast':lambda r:r['contrast'],
        }.items():
            d=np.asarray([fun(r) for r in allr['reward']],float)-np.asarray([fun(r) for r in allr['shuffle']],float)
            pair[key]={'mean':float(d.mean()),'sd':float(d.std(ddof=1) if len(d)>1 else 0.),'p':exact_signflip_p(d),'values':d.tolist()}
        summary['paired_reward_shuffle']=pair
    payload={'lag':lag,'seeds':seeds,'steps_train':steps_train,'summary':summary,'rows':allr}
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/f'cable_lag{lag}.json').write_text(json.dumps(payload,indent=2))
    print('\nsummary')
    for m in arms:
        s=summary[m];print(f" {m:7s}: dL {s['length_diff_mean']:+.2f} edge50 {s['edge50_mean']:+.2f} contrast {s['contrast_mean']:+.4f}")
    if 'paired_reward_shuffle' in summary:
        print(' paired reward-shuffle')
        for k,v in summary['paired_reward_shuffle'].items():print(f"  {k:10s} {v['mean']:+.3f} +- {v['sd']:.3f} p={v['p']:.5f}")
    return payload


def main():
    p=argparse.ArgumentParser();p.add_argument('--lag',type=int,default=10);p.add_argument('--seeds',type=int,default=8)
    p.add_argument('--mutations',type=int,default=12);p.add_argument('--arms',default='reward,shuffle,anti');p.add_argument('--out',default='cable_out')
    p.add_argument('--probe-steps',type=int,default=140,dest='probe_steps');a=p.parse_args()
    run(a.lag,a.seeds,a.mutations,[x.strip() for x in a.arms.split(',') if x.strip()],a.out,a.probe_steps)
if __name__=='__main__':main()
