from __future__ import annotations
import math
import numpy as np

class CoincidenceTask:
    """Two-pulse order task for a *wave-like* FunctionalArbor.

    TARGET:     A at t=0, B at t=lag
    DISTRACTOR: B at t=0, A at t=lag

    Each patch receives exactly the same pulse in both classes.  Carrier phase is
    reset at each pulse.  The training readout is soma peak energy; the mechanism
    is judged independently from single-pulse transfer functions after growth.
    """
    def __init__(self, model, lag=18, pulse=6, trial_len=None, amp=None, omega=None):
        if model.cfg.n_patches != 2:
            raise ValueError("CoincidenceTask requires Config(n_patches=2)")
        self.model=model; self.lag=int(lag); self.pulse=int(pulse)
        self.amp=float(model.cfg.source_amp if amp is None else amp)
        self.omega=float(model.cfg.carrier_omega if omega is None else omega)
        self.trial_len=int(trial_len or max(180, self.lag+170))

    def _pulse(self, which, q):
        if q < 0 or q >= self.pulse: return 0.0
        # Smooth finite packet.  The phase resets for each visit.
        env=math.sin(math.pi*(q+1)/(self.pulse+1))**2
        return self.amp*env*self.model.patches[which]*np.exp(1j*self.omega*q)

    def source(self,t,target=True):
        first,second=(0,1) if target else (1,0)
        return self._pulse(first,t)+self._pulse(second,t-self.lag)

    def run(self,target=True,learn=False,reward=0.0,record=False):
        m=self.model; m.reset_fast(); trace=[]
        m.E.fill(0)
        for t in range(self.trial_len):
            trace.append(m._advance(self.source(t,target)))
        a=np.asarray(trace,float)
        # Peak is deliberately only the TRAINING meter.  Delay is audited from
        # independent single-pulse traces in route_delays().
        score=float(a.max())
        if learn:
            m.grow_event(reward); m.growth_events += 1
        if record: return score,a
        return score

    def single_trace(self,which,steps=None):
        m=self.model; m.reset_fast(); m.E.fill(0)
        steps=int(steps or self.trial_len)
        trace=[]
        for t in range(steps):
            trace.append(m._advance(self._pulse(which,t)))
        return np.asarray(trace,float)


def first_fraction(trace,frac):
    trace=np.asarray(trace,float); mx=float(trace.max()) if trace.size else 0.0
    if mx<=0:return -1
    ix=np.flatnonzero(trace>=frac*mx)
    return int(ix[0]) if ix.size else -1


def xcorr_delay(trace, pulse=6):
    """Lag of the soma envelope against a compact source envelope.

    This is not sacred; it is a second estimator.  A delay claim is accepted only
    when edge and correlation estimators move with the same sign.
    """
    y=np.sqrt(np.maximum(np.asarray(trace,float),0.0))
    src=np.zeros_like(y)
    n=min(int(pulse),len(src))
    for q in range(n): src[q]=math.sin(math.pi*(q+1)/(n+1))**2
    y=y-y.mean(); src=src-src.mean()
    c=np.correlate(y,src,mode='full')
    lags=np.arange(-len(src)+1,len(y))
    return int(lags[int(np.argmax(c))])


def _first_absolute(trace,thr):
    ix=np.flatnonzero(np.asarray(trace,float)>=thr)
    return int(ix[0]) if ix.size else -1

def route_delays(task):
    ta=task.single_trace(0); tb=task.single_trace(1)
    out={}
    for name,tr in [('A',ta),('B',tb)]:
        out[name]={
            'peak':int(np.argmax(tr)),
            'edge10':first_fraction(tr,.10),
            'edge25':first_fraction(tr,.25),
            'edge50':first_fraction(tr,.50),
            'peak_value':float(tr.max()),
        }
    out['diff']={k:out['A'][k]-out['B'][k] for k in ('peak','edge10','edge25','edge50')}
    # Common-threshold fronts: both routes cross the SAME absolute level, set
    # from the weaker route.  This prevents a stronger route from moving its own
    # fractional threshold merely by changing amplitude.
    weak=min(float(ta.max()),float(tb.max()))
    for frac in (.05,.10,.25,.50):
        key=f'common{int(frac*100):02d}'
        thr=frac*weak
        a=_first_absolute(ta,thr); b=_first_absolute(tb,thr)
        out['A'][key]=a;out['B'][key]=b;out['diff'][key]=a-b if a>=0 and b>=0 else 9999
    return out



class RewardTrainer:
    """Three-factor credit with a per-class running baseline.

    Fixed material budget is supplied by FunctionalArbor.grow_event(), so zero-mean
    reward cannot make the organism fail to grow; reward only redistributes where
    the next material is placed.
    """
    def __init__(self,task,mode='reward',rate=.06,seed=0):
        if mode not in ('reward','shuffle','local','blind','open_loop','anti'):
            raise ValueError(mode)
        self.task=task; self.mode=mode; self.rate=float(rate)
        self.rng=np.random.default_rng(seed+173)
        self.mu={True:None,False:None}; self.var={True:1.0,False:1.0}

    def trial(self,target):
        t=self.task; m=t.model
        score=t.run(target,learn=False)
        mu=self.mu[target]
        if mu is None:
            z=0.0; self.mu[target]=score; self.var[target]=max(score*score*.02,1e-18)
        else:
            z=(score-mu)/(math.sqrt(self.var[target])+1e-12)
            old=mu; self.mu[target]=(1-self.rate)*mu+self.rate*score
            self.var[target]=(1-self.rate)*self.var[target]+self.rate*(score-old)**2
        z=float(np.clip(z,-2.5,2.5)); sign=1.0 if target else -1.0
        if self.mode=='shuffle': reward=float(self.rng.choice([-1.0,1.0]))*abs(z)
        elif self.mode=='local': reward=0.0
        elif self.mode=='blind': reward=0.0
        elif self.mode=='open_loop': reward=sign*z
        elif self.mode=='anti': reward=-sign*z
        else: reward=sign*z
        m.grow_event(reward); m.growth_events+=1
        return score,reward

    def train(self,pairs=20,epochs=2):
        rows=[]
        for e in range(int(epochs)):
            # alternate pair order each epoch so a class cannot own the terminal state
            order=(True,False) if e%2==0 else (False,True)
            for _ in range(int(pairs)):
                for target in order: rows.append((target,*self.trial(target)))
        return rows
