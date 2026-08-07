#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json,math,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v04_geometry_only.binary_arbor import BinaryConfig,BinaryGeometryArbor
from v04_geometry_only.task import GeometryDelayTask,GeometryTrainer,route_delays
from v04_geometry_only.anatomy import metrics


def exact_signflip_p(d):
    d=np.asarray(d,float);n=len(d)
    if n==0:return float('nan')
    obs=abs(float(d.mean())); vals=[]
    if n<=16:
        for b in itertools.product((-1.,1.),repeat=n):vals.append(abs(float(np.mean(d*np.asarray(b)))))
    else:
        rng=np.random.default_rng(0)
        for _ in range(30000):vals.append(abs(float(np.mean(d*rng.choice([-1.,1.],size=n)))))
    return float(np.mean(np.asarray(vals)>=obs-1e-12))


def cfg(seed,a):
    return BinaryConfig(size=a.size,seed=seed,patch_radius_frac=a.patch_radius,
        cells_per_event=a.cells, morph_disorder=a.disorder, credit_strength=a.credit_strength,
        eligibility_decay=a.eligibility_decay, eligibility_gain=a.eligibility_gain,
        mature_bath_k=a.mature_bath, mature_arbor_k=a.arbor_k,
        dev_bath_k=a.dev_bath, dev_arbor_k=a.arbor_k)


def one(seed,mode,a):
    m=BinaryGeometryArbor(cfg(seed,a),mode); task=GeometryDelayTask(m,lag=a.lag,pulse=a.pulse,trial_len=a.trial_len)
    pre=route_delays(task)
    tr=GeometryTrainer(task,mode=mode,seed=seed);tr.train(a.pairs,a.epochs)
    mass=m.mass(); connected=(m.patch_connected(0),m.patch_connected(1)); connfrac=m.connected_fraction()
    m.mature=True
    post=route_delays(task)
    A=metrics(m,0);B=metrics(m,1)
    return {'seed':seed,'mode':mode,'mass':mass,'connected':connected,'connected_fraction':connfrac,
            'pre':pre,'post':post,
            'A':{k:v for k,v in A.items() if not k.endswith('path')},'B':{k:v for k,v in B.items() if not k.endswith('path')},
            'paths':{'A':A['path'],'B':B['path'],'A_soft':A['soft_path'],'B_soft':B['soft_path']},
            'Bmap':m.B.astype(np.uint8).tolist()}


def mean_sd(x):
    x=np.asarray(x,float);return float(x.mean()),float(x.std(ddof=1) if len(x)>1 else 0.)


def main():
    p=argparse.ArgumentParser(description='v0.4 binary fixed-speed geometry-only learning assay')
    p.add_argument('--size',type=int,default=31);p.add_argument('--seeds',type=int,default=8);p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--lag',type=int,default=10);p.add_argument('--pulse',type=int,default=6);p.add_argument('--trial-len',type=int,default=280,dest='trial_len')
    p.add_argument('--pairs',type=int,default=14);p.add_argument('--epochs',type=int,default=3);p.add_argument('--cells',type=int,default=2)
    p.add_argument('--patch-radius',type=float,default=.29,dest='patch_radius');p.add_argument('--disorder',type=float,default=.22)
    p.add_argument('--credit-strength',type=float,default=5.0,dest='credit_strength');p.add_argument('--eligibility-decay',type=float,default=.993,dest='eligibility_decay')
    p.add_argument('--eligibility-gain',type=float,default=1.1,dest='eligibility_gain')
    p.add_argument('--dev-bath',type=float,default=.20,dest='dev_bath');p.add_argument('--mature-bath',type=float,default=.018,dest='mature_bath');p.add_argument('--arbor-k',type=float,default=1.25,dest='arbor_k')
    p.add_argument('--arms',default='reward,shuffle');p.add_argument('--out',default='geometry_out')
    a=p.parse_args();arms=[x.strip() for x in a.arms.split(',') if x.strip()];seeds=range(a.seed_start,a.seed_start+a.seeds)
    print(f'Functional Arbor v0.4 binary geometry assay lag={a.lag} N={a.size} seeds={list(seeds)}')
    print(f'  binary K: dev bath/arbor={a.dev_bath}/{a.arbor_k} mature bath/arbor={a.mature_bath}/{a.arbor_k}; cells/event={a.cells}')
    allr={}
    for mode in arms:
        rows=[]
        for s in seeds:
            r=one(s,mode,a);rows.append(r)
            A,B=r['A'],r['B'];post=r['post']['diff'];
            dl=(A['length']-B['length']) if A['connected'] and B['connected'] else float('nan')
            print(f" {mode:7s} s{s}: mass {r['mass']:5.0f} conn {r['connected']} cfrac {r['connected_fraction']:.3f} | "
                  f"e50 {post['edge50']:+4d} c25 {post['common25']:+4d} | dL {dl:+6.2f}")
        allr[mode]=rows
    summary={}
    print('\nsummary')
    for mode,rows in allr.items():
        vals={
            'edge50':[r['post']['diff']['edge50'] for r in rows],
            'common25':[r['post']['diff']['common25'] for r in rows],
            'length_diff':[(r['A']['length']-r['B']['length']) if r['A']['connected'] and r['B']['connected'] else np.nan for r in rows],
            'connect_both':[float(r['connected'][0] and r['connected'][1]) for r in rows],
            'mass':[r['mass'] for r in rows],
        }
        sm={}
        for k,v in vals.items():
            x=np.asarray(v,float);x=x[np.isfinite(x)];sm[k+'_mean'],sm[k+'_sd']=mean_sd(x) if len(x) else (float('nan'),float('nan'))
        summary[mode]=sm
        print(f" {mode:7s}: edge50 {sm['edge50_mean']:+.2f} common25 {sm['common25_mean']:+.2f} dL {sm['length_diff_mean']:+.2f} connect {sm['connect_both_mean']:.2f} mass {sm['mass_mean']:.1f}")
    if 'reward' in allr and 'shuffle' in allr:
        paired={}
        funs={
            'edge50':lambda r:r['post']['diff']['edge50'],
            'common25':lambda r:r['post']['diff']['common25'],
            'length_diff':lambda r:(r['A']['length']-r['B']['length']) if r['A']['connected'] and r['B']['connected'] else np.nan,
        }
        for k,f in funs.items():
            d=np.asarray([f(r) for r in allr['reward']],float)-np.asarray([f(r) for r in allr['shuffle']],float)
            d=d[np.isfinite(d)]
            paired[k]={'n':int(len(d)),'mean':float(d.mean()) if len(d) else float('nan'),'sd':float(d.std(ddof=1)) if len(d)>1 else 0.,'signflip_p':exact_signflip_p(d) if len(d) else float('nan'),'values':d.tolist()}
        summary['paired_reward_shuffle']=paired
        print('\npaired reward-shuffle')
        for k,v in paired.items():print(f" {k:12s} n={v['n']} {v['mean']:+.3f} +- {v['sd']:.3f} p={v['signflip_p']:.5f}")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'geometry_results.json').write_text(json.dumps({'args':vars(a),'summary':summary,'rows':allr},indent=2),encoding='utf-8')
    print('\nVerdict rule: geometry earns the delay claim only if reward moves BOTH physical wavefront delay and connected binary path length in the requested positive A-B direction beyond shuffled credit. Equal mass and two-valued K are construction invariants.')

if __name__=='__main__':main()
