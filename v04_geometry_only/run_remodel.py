#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, os, sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v04_geometry_only.binary_arbor import BinaryConfig,BinaryGeometryArbor
from v04_geometry_only.task import GeometryDelayTask, route_delays
from v04_geometry_only.anatomy import metrics


def pflip(d):
    d=np.asarray(d,float);n=len(d);obs=abs(d.mean())
    return float(np.mean([abs(np.mean(d*np.array(s)))>=obs-1e-12 for s in itertools.product((-1.,1.),repeat=n)])) if n else float('nan')

class RemodelTrainer:
    def __init__(self,task,mode='reward',seed=0,rate=.06,swaps=2):
        self.t=task;self.mode=mode;self.rng=np.random.default_rng(seed+444);self.rate=rate;self.swaps=swaps
        self.mu={True:None,False:None};self.var={True:1.,False:1.}
    def trial(self,target):
        score,_=self.t.run(target);mu=self.mu[target]
        if mu is None:z=0.;self.mu[target]=score;self.var[target]=max(score*score*.02,1e-18)
        else:
            z=(score-mu)/(math.sqrt(self.var[target])+1e-12);old=mu
            self.mu[target]=(1-self.rate)*mu+self.rate*score;self.var[target]=(1-self.rate)*self.var[target]+self.rate*(score-old)**2
        z=float(np.clip(z,-2.5,2.5));s=1 if target else -1
        if self.mode=='shuffle':r=float(self.rng.choice([-1,1]))*abs(z)
        elif self.mode=='anti':r=-s*z
        else:r=s*z
        self.t.model.remodel_event(r,self.swaps);return score,r
    def train(self,pairs,epochs):
        for e in range(epochs):
            order=(True,False) if e%2==0 else (False,True)
            for _ in range(pairs):
                for q in order:self.trial(q)

def bootstrap(m,t,events=110,cells=2):
    old=m.condition;m.condition='local'
    # exact A/B dose.  Each single pulse writes binary frontier with no global credit.
    for e in range(events):
        which=e%2
        t.single_trace(which)
        m.grow_event(0.0);m.growth_events+=1
    m.condition=old

def one(seed,mode,a):
    c=BinaryConfig(size=a.size,seed=seed,patch_radius_frac=a.patch_radius,cells_per_event=a.cells,
        morph_disorder=a.disorder,credit_strength=a.credit_strength,eligibility_decay=a.eligibility_decay,
        mature_bath_k=a.mature_bath,mature_arbor_k=a.arbor_k,dev_bath_k=a.dev_bath,dev_arbor_k=a.arbor_k,
        growth_eta=a.growth_eta)
    m=BinaryGeometryArbor(c,mode);t=GeometryDelayTask(m,a.lag,a.pulse,a.trial_len)
    bootstrap(m,t,a.bootstrap,a.cells)
    before_mass=m.mass(); pre=route_delays(t); preA,preB=metrics(m,0),metrics(m,1)
    RemodelTrainer(t,mode,seed,swaps=a.swaps).train(a.pairs,a.epochs)
    assert abs(m.mass()-before_mass)<1e-9
    m.mature=True;post=route_delays(t);A,B=metrics(m,0),metrics(m,1)
    return dict(seed=seed,mode=mode,mass=m.mass(),pre=pre,post=post,
        connected=(A['connected'],B['connected']),connected_fraction=m.connected_fraction(),
        A={k:v for k,v in A.items() if not k.endswith('path')},B={k:v for k,v in B.items() if not k.endswith('path')},
        preA={k:v for k,v in preA.items() if not k.endswith('path')},preB={k:v for k,v in preB.items() if not k.endswith('path')},
        paths={'A':A['path'],'B':B['path']},Bmap=m.B.astype(np.uint8).tolist())

def main():
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=31);p.add_argument('--seeds',type=int,default=4)
    p.add_argument('--lag',type=int,default=10);p.add_argument('--pulse',type=int,default=6);p.add_argument('--trial-len',type=int,default=300,dest='trial_len')
    p.add_argument('--bootstrap',type=int,default=110);p.add_argument('--cells',type=int,default=2);p.add_argument('--swaps',type=int,default=2)
    p.add_argument('--pairs',type=int,default=16);p.add_argument('--epochs',type=int,default=3);p.add_argument('--patch-radius',type=float,default=.29,dest='patch_radius')
    p.add_argument('--disorder',type=float,default=.18);p.add_argument('--credit-strength',type=float,default=6.0,dest='credit_strength');p.add_argument('--eligibility-decay',type=float,default=.995,dest='eligibility_decay')
    p.add_argument('--growth-eta',type=float,default=1.6,dest='growth_eta');p.add_argument('--dev-bath',type=float,default=.20,dest='dev_bath');p.add_argument('--mature-bath',type=float,default=.018,dest='mature_bath');p.add_argument('--arbor-k',type=float,default=1.25,dest='arbor_k')
    p.add_argument('--arms',default='reward,shuffle');p.add_argument('--out',default='remodel_out');a=p.parse_args()
    allr={};print(f'v0.4 geometry remodel lag={a.lag} seeds={a.seeds} bootstrap={a.bootstrap} swaps={a.swaps}')
    for mode in a.arms.split(','):
        rows=[]
        for s in range(a.seeds):
            r=one(s,mode,a);rows.append(r);A,B=r['A'],r['B'];dl=A['length']-B['length'] if A['connected'] and B['connected'] else float('nan')
            print(f" {mode:7s} s{s} mass {r['mass']:.0f} conn {r['connected']} e50 {r['post']['diff']['edge50']:+4d} c25 {r['post']['diff']['common25']:+4d} dL {dl:+.2f}")
        allr[mode]=rows
    summary={}
    if 'reward' in allr and 'shuffle' in allr:
        for key,fun in {
          'edge50':lambda r:r['post']['diff']['edge50'],
          'common25':lambda r:r['post']['diff']['common25'],
          'length':lambda r:r['A']['length']-r['B']['length'] if r['A']['connected'] and r['B']['connected'] else np.nan}.items():
            d=np.asarray([fun(r) for r in allr['reward']])-np.asarray([fun(r) for r in allr['shuffle']]);d=d[np.isfinite(d)]
            summary[key]=dict(n=len(d),mean=float(d.mean()) if len(d) else np.nan,sd=float(d.std(ddof=1)) if len(d)>1 else 0,p=pflip(d) if len(d) else np.nan,values=d.tolist())
            print(f" paired {key:8s} n={len(d)} {summary[key]['mean']:+.3f} +- {summary[key]['sd']:.3f} p={summary[key]['p']:.5f}")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'remodel_results.json').write_text(json.dumps({'args':vars(a),'summary':summary,'rows':allr},indent=2))
if __name__=='__main__':main()
