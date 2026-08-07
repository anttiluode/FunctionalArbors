from __future__ import annotations
import argparse,itertools,json,os,sys
from pathlib import Path
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v05_free_arbor.free_arbor import FreeConfig,FreeBinaryArbor
    from v05_free_arbor.task import DelayTask
else:
    from .free_arbor import FreeConfig,FreeBinaryArbor
    from .task import DelayTask


def signflip(d):
    d=np.asarray(d,float);n=len(d);obs=abs(float(d.mean()))
    if n==0:return float('nan')
    if n<=16: vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)]
    else:
        r=np.random.default_rng(0);vals=[abs(float(np.mean(d*r.choice([-1.,1.],n)))) for _ in range(30000)]
    return float(np.mean(np.asarray(vals)>=obs-1e-12))


def train_from_bootstrap(base:FreeBinaryArbor,mode,lag,mutations,seed):
    m=base.copy();m.mature=True;t=DelayTask(m,lag)
    pre_score,_,_=t.contrast();pre_delay=t.delays();pre_stats=m.branch_stats();mass0=m.mass();score=pre_score
    rng=np.random.default_rng(seed+7919);accepted=0;hist=[]
    for step in range(int(mutations)):
        which=int(rng.integers(2))
        # A real pulse through the current body supplies local eligibility.
        t.single(which,accumulate=True,steps=m.cfg.train_trace_steps)
        snap=m.snapshot();prop=m.propose_detour(which)
        if prop is None:
            hist.append({'step':step,'which':which,'proposal':None,'keep':False,'score':score});continue
        new,_,_=t.contrast();delta=new-score
        if mode=='reward':signal=delta
        elif mode=='anti':signal=-delta
        elif mode=='shuffle':signal=(1 if rng.random()<.5 else -1)*delta
        elif mode=='blind':signal=(1 if rng.random()<.5 else -1)
        else:raise ValueError(mode)
        keep=signal>1e-7
        if keep:score=new;accepted+=1
        else:m.restore(snap)
        hist.append({'step':step,'which':which,'proposal':prop,'delta':float(delta),'keep':bool(keep),'score':float(score)})
        assert m.mass()==mass0 and m.is_tree() and m.both_connected()
    post=t.delays();stats=m.branch_stats();final,ta,ds=t.contrast()
    return {'mode':mode,'seed':seed,'mass':m.mass(),'accepted':accepted,'pre_contrast':pre_score,'contrast':final,
            'target_peak':ta,'distractor_peak':ds,'pre_delay':pre_delay,'delay':post,'pre_stats':pre_stats,'stats':stats,
            'history':hist,'body':m.body.tolist(),'pathA':m.path(0),'pathB':m.path(1)}


def one_seed(seed,args,arms):
    cfg=FreeConfig(size=args.size,seed=seed,bootstrap_mass=args.bootstrap_mass,bootstrap_max=args.bootstrap_max,
                   morph_disorder=args.disorder,mutations=args.mutations,probe_steps=args.probe_steps)
    base=FreeBinaryArbor(cfg);boot=base.bootstrap()
    if not boot['ok']:return {'seed':seed,'bootstrap':boot,'arms':{}}
    mass=base.mass();rows={}
    for mode in arms:rows[mode]=train_from_bootstrap(base,mode,args.lag,args.mutations,seed)
    for r in rows.values():assert r['mass']==mass
    return {'seed':seed,'bootstrap':boot,'base_body':base.body.tolist(),'arms':rows}


def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--seed-start',type=int,default=0,dest='seed_start');p.add_argument('--lag',type=int,default=10)
    p.add_argument('--size',type=int,default=31);p.add_argument('--mutations',type=int,default=28)
    p.add_argument('--bootstrap-mass',type=int,default=90,dest='bootstrap_mass');p.add_argument('--bootstrap-max',type=int,default=240,dest='bootstrap_max')
    p.add_argument('--probe-steps',type=int,default=180,dest='probe_steps');p.add_argument('--disorder',type=float,default=.28)
    p.add_argument('--arms',default='reward,shuffle,anti');p.add_argument('--out',default='free_out');a=p.parse_args()
    arms=[x.strip() for x in a.arms.split(',') if x.strip()];allrows=[]
    print(f'Functional Arbor v0.5 free-tree geometry learner lag={a.lag} seeds={a.seeds} mutations={a.mutations}')
    for s in range(a.seed_start,a.seed_start+a.seeds):
        z=one_seed(s,a,arms);allrows.append(z);boot=z['bootstrap']
        print(f" seed{s} bootstrap ok={boot['ok']} mass={boot.get('mass')} leaves={boot.get('leaves')} junctions={boot.get('junctions')} L={boot.get('length_A')}/{boot.get('length_B')}")
        for mode,r in z['arms'].items():
            dL=r['stats']['length_A']-r['stats']['length_B'];print(f"   {mode:7s}: dL {dL:+3d} edge50 {r['delay']['edge50']:+4d} c25 {r['delay']['common25']:+4d} contrast {r['contrast']:+.4f} acc {r['accepted']}")
    valid=[z for z in allrows if z['arms']];summary={}
    for mode in arms:
        rr=[z['arms'][mode] for z in valid if mode in z['arms']]
        def val(r,k):
            if k=='length_diff':return r['stats']['length_A']-r['stats']['length_B']
            if k=='delta_length':return (r['stats']['length_A']-r['stats']['length_B'])-(r['pre_stats']['length_A']-r['pre_stats']['length_B'])
            if k=='contrast':return r['contrast']
            if k=='delta_contrast':return r['contrast']-r['pre_contrast']
            return r['delay'][k]
        summary[mode]={}
        for k in ('length_diff','delta_length','edge50','common25','contrast','delta_contrast'):
            x=np.asarray([val(r,k) for r in rr],float);summary[mode][k]={'mean':float(x.mean()),'sd':float(x.std(ddof=1) if len(x)>1 else 0),'values':x.tolist()}
    if 'reward' in arms and 'shuffle' in arms:
        pair={}
        R=[z['arms']['reward'] for z in valid];S=[z['arms']['shuffle'] for z in valid]
        fun={
          'length_diff':lambda r:r['stats']['length_A']-r['stats']['length_B'],
          'delta_length':lambda r:(r['stats']['length_A']-r['stats']['length_B'])-(r['pre_stats']['length_A']-r['pre_stats']['length_B']),
          'edge50':lambda r:r['delay']['edge50'],'common25':lambda r:r['delay']['common25'],
          'contrast':lambda r:r['contrast'],'delta_contrast':lambda r:r['contrast']-r['pre_contrast']}
        for k,f in fun.items():
            d=np.asarray([f(r)-f(s) for r,s in zip(R,S)],float);pair[k]={'mean':float(d.mean()),'sd':float(d.std(ddof=1) if len(d)>1 else 0),'p':signflip(d),'values':d.tolist()}
        summary['paired_reward_shuffle']=pair
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);payload={'args':vars(a),'summary':summary,'rows':allrows}
    (out/'free_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('\nsummary')
    for mode in arms:
        s=summary[mode];print(f" {mode:7s}: dL {s['length_diff']['mean']:+.2f} edge50 {s['edge50']['mean']:+.2f} contrast {s['contrast']['mean']:+.4f}")
    if 'paired_reward_shuffle' in summary:
        print(' paired reward-shuffle')
        for k,v in summary['paired_reward_shuffle'].items():print(f"  {k:13s} {v['mean']:+.3f} +- {v['sd']:.3f} p={v['p']:.5f}")

if __name__=='__main__':main()
