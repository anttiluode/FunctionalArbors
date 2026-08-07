from __future__ import annotations
import math
import numpy as np


class GeometryDelayTask:
    def __init__(self, model, lag=10, pulse=6, trial_len=260):
        self.model=model; self.lag=int(lag); self.pulse=int(pulse); self.trial_len=int(trial_len)

    def _pulse(self,which,q):
        if q<0 or q>=self.pulse:return 0.0
        c=self.model.cfg
        env=math.sin(math.pi*(q+1)/(self.pulse+1))**2
        return c.source_amp*env*self.model.patches[which]*np.exp(1j*c.carrier_omega*q)

    def source(self,t,target=True):
        first,second=(0,1) if target else (1,0)
        return self._pulse(first,t)+self._pulse(second,t-self.lag)

    def run(self,target=True):
        m=self.model; m.reset_fast(); trace=[]
        for t in range(self.trial_len): trace.append(m._advance(self.source(t,target)))
        return float(np.max(trace)), np.asarray(trace,float)

    def single_trace(self,which):
        m=self.model;m.reset_fast();trace=[]
        for t in range(self.trial_len): trace.append(m._advance(self._pulse(which,t)))
        return np.asarray(trace,float)


def first_fraction(x,frac):
    x=np.asarray(x,float); mx=float(x.max()) if x.size else 0
    if mx<=0:return -1
    q=np.flatnonzero(x>=frac*mx); return int(q[0]) if q.size else -1


def first_abs(x,thr):
    q=np.flatnonzero(np.asarray(x,float)>=thr);return int(q[0]) if q.size else -1


def route_delays(task):
    A=task.single_trace(0);B=task.single_trace(1)
    weak=min(float(A.max()),float(B.max()))
    out={'A':{},'B':{},'diff':{}}
    for name,tr in [('A',A),('B',B)]:
        out[name]['peak']=int(np.argmax(tr));out[name]['peak_value']=float(tr.max())
        for f in (.10,.25,.50):out[name][f'edge{int(f*100):02d}']=first_fraction(tr,f)
        for f in (.10,.25,.50):out[name][f'common{int(f*100):02d}']=first_abs(tr,f*weak)
    for k in ('peak','edge10','edge25','edge50','common10','common25','common50'):
        a,b=out['A'][k],out['B'][k];out['diff'][k]=(a-b if a>=0 and b>=0 else 9999)
    return out


class GeometryTrainer:
    """Same three-factor logic, but the body has only binary fixed-speed material."""
    def __init__(self,task,mode='reward',rate=.06,seed=0):
        self.task=task;self.mode=mode;self.rate=rate;self.rng=np.random.default_rng(seed+991)
        self.mu={True:None,False:None};self.var={True:1.,False:1.}
    def trial(self,target):
        score,_=self.task.run(target)
        mu=self.mu[target]
        if mu is None:
            z=0.;self.mu[target]=score;self.var[target]=max(score*score*.02,1e-18)
        else:
            z=(score-mu)/(math.sqrt(self.var[target])+1e-12);old=mu
            self.mu[target]=(1-self.rate)*mu+self.rate*score
            self.var[target]=(1-self.rate)*self.var[target]+self.rate*(score-old)**2
        z=float(np.clip(z,-2.5,2.5));sign=1 if target else -1
        if self.mode=='shuffle': reward=float(self.rng.choice([-1,1]))*abs(z)
        elif self.mode in ('local','blind'):reward=0.
        elif self.mode=='anti':reward=-sign*z
        else:reward=sign*z
        self.task.model.grow_event(reward);self.task.model.growth_events+=1
        return score,reward
    def train(self,pairs=12,epochs=3):
        rows=[]
        for e in range(epochs):
            order=(True,False) if e%2==0 else (False,True)
            for _ in range(pairs):
                for target in order:rows.append((target,*self.trial(target)))
        return rows
