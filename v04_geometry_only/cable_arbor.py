from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np


def shift(a,dy,dx):
    out=np.zeros_like(a);h,w=a.shape
    ys0=max(0,dy);ys1=min(h,h+dy);yd0=max(0,-dy);yd1=min(h,h-dy)
    xs0=max(0,dx);xs1=min(w,w+dx);xd0=max(0,-dx);xd1=min(w,w-dx)
    out[ys0:ys1,xs0:xs1]=a[yd0:yd1,xd0:xd1]
    return out


@dataclass
class CableConfig:
    size:int=41
    dt:float=.12
    stiffness:float=1.0
    damping:float=.055
    restoring:float=.025
    saturation:float=.0008
    k_arbor:float=2.5
    k_bath:float=2e-4
    pulse_frames:int=6
    source_amp:float=1.0
    carrier_omega:float=.16
    reserve_cells:int=28
    seed:int=0
    def as_dict(self):return asdict(self)


class CableArbor:
    """Controlled binary-cable geometry experiment.

    Two source-to-soma cables are one-cell-wide binary structures.  Every occupied
    bond has exactly k_arbor; every non-arbor bond has exactly k_bath.  Geometry is
    the only route-specific transport variable.

    Local remodeling moves two cells of material from/to a disconnected reserve
    whenever a plaquette detour is inserted/removed, so total material is constant.
    """
    def __init__(self,cfg:CableConfig|None=None):
        self.cfg=cfg or CableConfig(); self.rng=np.random.default_rng(self.cfg.seed)
        n=self.cfg.size;self.cy=n//2;self.cx=n//2
        self.A=(self.cy,5);self.Bsrc=(self.cy,n-6);self.soma=(self.cy,self.cx)
        self.body=np.zeros((n,n),np.uint8)
        # straight one-cell cables meeting at soma
        self.body[self.cy,5:self.cx+1]=1;self.body[self.cy,self.cx:n-5]=1
        self.base_body=self.body.copy()
        # disconnected reserve material block near top edge; used only for mass accounting
        self.reserve_slots=[]
        for y in range(2,5):
            for x in range(2,n-2):
                if len(self.reserve_slots)>=self.cfg.reserve_cells:break
                self.reserve_slots.append((y,x));self.body[y,x]=1
            if len(self.reserve_slots)>=self.cfg.reserve_cells:break
        self.reserve_free=[]  # slots currently emptied into cable detours
        self.detours={0:[],1:[]}
        self.psi=np.zeros((n,n),np.complex64);self.vel=np.zeros_like(self.psi)
        self.E=np.zeros((n,n),np.float32)
        self.K_override=None
        self.initial_mass=int(self.body.sum())

    def reset_fast(self):self.psi.fill(0);self.vel.fill(0);self.E.fill(0)

    def bond_fields(self):
        b=self.body.astype(bool);ka,kb=self.cfg.k_arbor,self.cfg.k_bath
        # bond is fast only when BOTH endpoint cells belong to arbor material.
        kr=np.where(b & shift(b,0,-1),ka,kb).astype(np.float32)
        kl=np.where(b & shift(b,0,1),ka,kb).astype(np.float32)
        kd=np.where(b & shift(b,-1,0),ka,kb).astype(np.float32)
        ku=np.where(b & shift(b,1,0),ka,kb).astype(np.float32)
        return kr,kl,kd,ku

    def _lap(self,u):
        kr,kl,kd,ku=self.bond_fields()
        return (kr*(shift(u,0,-1)-u)+kl*(shift(u,0,1)-u)+kd*(shift(u,-1,0)-u)+ku*(shift(u,1,0)-u))

    def _advance(self,source):
        c=self.cfg;lap=self._lap(self.psi)
        self.vel += c.dt*(c.stiffness*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel
        self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2)
        # eligibility: local kinetic/current proxy on occupied material only
        amp=np.abs(self.vel).astype(np.float32)*self.body
        sc=np.quantile(amp[amp>0],.95)+1e-9 if np.any(amp>0) else 1.
        use=np.clip(amp/sc,0,1)
        self.E=.985*self.E+.015*use
        return float(np.abs(self.psi[self.soma])**2)

    def pulse_source(self,which,q):
        if not(0<=q<self.cfg.pulse_frames):return 0.0
        env=math.sin(math.pi*(q+1)/(self.cfg.pulse_frames+1))**2
        src=np.zeros_like(self.psi);p=self.A if which==0 else self.Bsrc
        src[p]=self.cfg.source_amp*env*np.exp(1j*self.cfg.carrier_omega*q)
        return src

    def trace(self,which,steps=220):
        self.reset_fast();out=[]
        for t in range(steps):out.append(self._advance(self.pulse_source(which,t)))
        return np.asarray(out,float)

    @staticmethod
    def first_fraction(tr,frac=.25):
        tr=np.asarray(tr,float);mx=float(tr.max())
        if mx<=0:return -1
        q=np.flatnonzero(tr>=frac*mx);return int(q[0]) if q.size else -1

    def delays(self,steps=220):
        a=self.trace(0,steps);b=self.trace(1,steps);weak=min(a.max(),b.max())
        def first_abs(x,thr):
            q=np.flatnonzero(x>=thr);return int(q[0]) if q.size else -1
        return {
            'edge25':self.first_fraction(a,.25)-self.first_fraction(b,.25),
            'edge50':self.first_fraction(a,.50)-self.first_fraction(b,.50),
            'common25':first_abs(a,.25*weak)-first_abs(b,.25*weak),
            'peak':int(np.argmax(a))-int(np.argmax(b)),
            'A_peak':float(a.max()),'B_peak':float(b.max())}

    def path_length(self,which):
        # shortest 4-neighbour occupied path source -> soma
        src=self.A if which==0 else self.Bsrc;goal=self.soma;b=self.body.astype(bool)
        from collections import deque
        q=deque([src]);dist={src:0}
        while q:
            y,x=q.popleft()
            if (y,x)==goal:return dist[(y,x)]
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                p=(y+dy,x+dx)
                if 0<=p[0]<b.shape[0] and 0<=p[1]<b.shape[1] and b[p] and p not in dist:
                    dist[p]=dist[(y,x)]+1;q.append(p)
        return math.inf

    def length_diff(self):return self.path_length(0)-self.path_length(1)

    def _straight_centers(self,which):
        # candidate middle cells still on the central direct row; avoid soma/endpoints and nearby detours
        if which==0: xs=range(self.A[1]+2,self.cx-1)
        else: xs=range(self.cx+2,self.Bsrc[1]-1)
        used={d['center'][1] for d in self.detours[which]}
        out=[]
        for x in xs:
            # keep detours separated so each one contributes its own path length
            if any(abs(x-u) <= 3 for u in used):continue
            if self.body[self.cy,x] and self.body[self.cy,x-1] and self.body[self.cy,x+1]:out.append(x)
        return out

    def _reserve_take(self,n=2):
        live=[p for p in self.reserve_slots if self.body[p]]
        if len(live)<n:return None
        sel=live[:n]
        for p in sel:self.body[p]=0;self.reserve_free.append(p)
        return sel

    def _reserve_return(self,n=2):
        if len(self.reserve_free)<n:return False
        for _ in range(n):self.body[self.reserve_free.pop()]=1
        return True

    def add_detour(self,which,x=None,side=None):
        cand=self._straight_centers(which)
        if not cand:return False
        if x is None:
            # eligibility-weighted centre choice, falling back to random
            w=np.asarray([self.E[self.cy,xx]+.02 for xx in cand],float);w/=w.sum()
            x=int(self.rng.choice(cand,p=w))
        side=int(self.rng.choice([-1,1])) if side is None else int(side)
        y=self.cy+side
        cells=[(y,x-1),(y,x),(y,x+1)]
        if any(self.body[p] for p in cells):return False
        taken=self._reserve_take(2)
        if taken is None:return False
        self.body[self.cy,x]=0
        for p in cells:self.body[p]=1
        self.detours[which].append({'center':(self.cy,x),'side':side,'cells':cells,'reserve':taken})
        assert int(self.body.sum())==self.initial_mass
        return True

    def remove_detour(self,which,index=None):
        if not self.detours[which]:return False
        if index is None:index=int(self.rng.integers(len(self.detours[which])))
        d=self.detours[which].pop(index)
        for p in d['cells']:self.body[p]=0
        self.body[d['center']]=1
        if not self._reserve_return(2):raise RuntimeError('reserve accounting')
        assert int(self.body.sum())==self.initial_mass
        return True

    def snapshot(self):
        return {'body':self.body.copy(),'detours':{0:[dict(x) for x in self.detours[0]],1:[dict(x) for x in self.detours[1]]},'reserve_free':list(self.reserve_free)}

    def restore(self,s):
        self.body=s['body'].copy();self.detours={0:[dict(x) for x in s['detours'][0]],1:[dict(x) for x in s['detours'][1]]};self.reserve_free=list(s['reserve_free'])

    def propose_mutation(self, which=None):
        if which is None: which=int(self.rng.integers(2))
        else: which=int(which)
        # choose add/remove without being told target sign
        can_add=bool(self._straight_centers(which)) and len([p for p in self.reserve_slots if self.body[p]])>=2
        can_remove=bool(self.detours[which])
        if can_add and can_remove:op='add' if self.rng.random()<.55 else 'remove'
        elif can_add:op='add'
        elif can_remove:op='remove'
        else:return None
        ok=self.add_detour(which) if op=='add' else self.remove_detour(which)
        return (which,op) if ok else None
