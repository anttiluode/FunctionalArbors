from __future__ import annotations
import numpy as np
from .free_arbor import FreeBinaryArbor


def first_fraction(x,frac):
    x=np.asarray(x,float);m=float(x.max()) if x.size else 0
    if m<=0:return -1
    q=np.flatnonzero(x>=frac*m);return int(q[0]) if q.size else -1

def first_abs(x,thr):
    q=np.flatnonzero(np.asarray(x,float)>=thr);return int(q[0]) if q.size else -1


class DelayTask:
    def __init__(self,model:FreeBinaryArbor,lag=10,steps=None):
        self.m=model;self.lag=int(lag);self.steps=int(steps or model.cfg.probe_steps)

    def pair_trace(self,target=True,accumulate=False):
        m=self.m;m.reset_fast(clear_E=False);first,second=(0,1) if target else (1,0);tr=[]
        for t in range(self.steps):
            a=m.pulse_source(first,t,False);b=m.pulse_source(second,t-self.lag,False)
            if isinstance(a,float):src=b
            elif isinstance(b,float):src=a
            else:src=a+b
            tr.append(m.advance(src,accumulate=accumulate,mature=True))
        return np.asarray(tr,float)

    def contrast(self):
        tg=self.pair_trace(True,False);ds=self.pair_trace(False,False)
        a=float(tg.max());b=float(ds.max())
        return float((a-b)/(a+b+1e-12)),a,b

    def single(self,which,accumulate=False,steps=None):
        m=self.m;m.reset_fast(clear_E=accumulate);out=[];n=int(steps or self.steps)
        for t in range(n):out.append(m.advance(m.pulse_source(which,t,False),accumulate=accumulate,mature=True))
        return np.asarray(out,float)

    def delays(self):
        A=self.single(0,False);B=self.single(1,False);weak=min(float(A.max()),float(B.max()))
        out={}
        for f in (.25,.50):out[f'edge{int(100*f)}']=first_fraction(A,f)-first_fraction(B,f)
        for f in (.10,.25):out[f'common{int(100*f)}']=first_abs(A,f*weak)-first_abs(B,f*weak)
        out['peak']=int(np.argmax(A))-int(np.argmax(B));out['A_peak']=float(A.max());out['B_peak']=float(B.max())
        return out
