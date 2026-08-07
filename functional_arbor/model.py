from __future__ import annotations
import math
import numpy as np
from .config import Config
from .operators import div_k_grad, grad, max_filter, smooth

CONDITIONS=('blind','local','credit','anti_credit','open_loop')

class FunctionalArbor:
    '''A continuous morphogenetic arbor with three-factor structural plasticity.

    Fast state: complex wave psi.
    Slow state: scalar deposited structure M.
    Eligibility: local recent phase-current use E.
    Global teaching signal: soma energy improvement at event boundaries.

    Growth occurs only on the exposed interface and every event receives the same
    material budget. Credit can steer WHERE material is deposited, not how much.
    '''
    def __init__(self,cfg:Config|None=None,condition='credit'):
        self.cfg=cfg or Config()
        if condition not in CONDITIONS: raise ValueError(condition)
        self.condition=condition
        self.rng=np.random.default_rng(self.cfg.seed)
        self._geom(); self.reset()

    def _geom(self):
        c=self.cfg; n=c.size
        y,x=np.mgrid[0:n,0:n].astype(np.float32); cc=(n-1)/2
        self.y,self.x,self.cc=y,x,cc
        rr=np.sqrt((x-cc)**2+(y-cc)**2); self.rr=rr
        self.root=np.exp(-(rr**2)/(2*c.root_sigma**2)).astype(np.float32); self.root/=self.root.sum()+1e-12
        self.patches=[]
        r=n*c.patch_radius_frac
        for k in range(c.n_patches):
            a=2*np.pi*k/c.n_patches
            px=cc+r*np.cos(a); py=cc+r*np.sin(a)
            m=np.exp(-((x-px)**2+(y-py)**2)/(2*c.patch_sigma**2)).astype(np.float32)
            m/=m.max()+1e-12; self.patches.append(m)
        self.patches=np.stack(self.patches)
        d=np.minimum.reduce([x,y,(n-1)-x,(n-1)-y])
        self.window=np.clip(d/max(c.edge_margin,1),0,1); self.window=self.window*self.window*(3-2*self.window)
        self.outer=np.zeros((n,n),np.float32); self.outer[:2]=1;self.outer[-2:]=1;self.outer[:,:2]=1;self.outer[:,-2:]=1

    def reset(self):
        c=self.cfg; n=c.size
        self.psi=np.zeros((n,n),np.complex64); self.vel=np.zeros((n,n),np.complex64)
        self.M=(1/(1+np.exp(np.clip((self.rr-c.root_radius)*3,-60,60)))).astype(np.float32)*self.window
        noise=smooth(self.rng.normal(size=(n,n)).astype(np.float32),2)
        noise=(noise-noise.mean())/(noise.std()+1e-8)
        self.substrate=np.clip(np.exp(c.substrate_noise*noise),0.55,1.8).astype(np.float32)
        self.E=np.zeros((n,n),np.float32); self.credit_map=np.zeros_like(self.E)
        self.opportunity=self.outer.copy(); self.front=np.zeros_like(self.E)
        self.baseline=np.full(c.n_patches,np.nan,np.float64)
        self.t=0; self.growth_events=0; self.mature=False
        self.K_override=None  # mechanistic counterfactual probes only

    def clone_slow_state(self):
        return {'M':self.M.copy(),'substrate':self.substrate.copy(),'baseline':self.baseline.copy(),'credit_map':self.credit_map.copy()}
    def load_slow_state(self,s):
        self.M=np.array(s['M'],copy=True);self.substrate=np.array(s['substrate'],copy=True)
        self.baseline=np.array(s.get('baseline',self.baseline),copy=True);self.credit_map=np.array(s.get('credit_map',self.credit_map),copy=True)
    def reset_fast(self):
        self.psi.fill(0);self.vel.fill(0);self.E.fill(0);self.t=0

    def conductivity(self,mature=None):
        c=self.cfg
        if self.K_override is not None:
            return np.asarray(self.K_override,np.float32)
        if self.condition=='open_loop':
            return np.full_like(self.M,c.dev_base_k)*self.substrate
        if mature is None: mature=self.mature
        if mature:
            base,gain=c.mature_base_k,c.mature_structure_k
        else:
            total=max(c.train_cycles*c.n_patches,1); a=np.clip(self.growth_events/total,0,1); a=a*a*(3-2*a)
            base=(1-a)*c.dev_base_k+a*c.dev_final_base_k
            gain=(1-a)*c.dev_structure_k+a*c.dev_final_structure_k
        return (base+gain*np.power(self.M,c.structure_power))*self.substrate

    def _advance(self,source):
        c=self.cfg; k=self.conductivity()
        # Damped complex wave. The carrier phase lives in psi; K(M) controls local
        # propagation speed. This is intentionally second-order so a pulse actually
        # travels down a mature arbor instead of diffusing through a bath forever.
        lap=div_k_grad(k,self.psi)
        self.vel += c.dt*(c.diffusion*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel
        self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2); self.psi*=self.window; self.vel*=self.window
        gx,gy=grad(self.psi); jx=np.imag(np.conj(self.psi)*k*gx);jy=np.imag(np.conj(self.psi)*k*gy)
        j=np.sqrt(jx*jx+jy*jy).astype(np.float32)
        scale=np.quantile(j,0.98)+1e-9; use=np.clip(j/scale,0,1)
        self.E=c.eligibility_decay*self.E+(1-c.eligibility_decay)*use
        self.t+=1
        return float(np.sum((np.abs(self.psi)**2)*self.root))

    def visit(self,patch,learn=True):
        c=self.cfg; energies=[]
        for q in range(c.dwell):
            if q<c.pulse_frames:
                # carrier phase RESET each visit: patch identity is not tied to carrier epoch
                src=c.source_amp*self.patches[patch]*np.exp(1j*c.carrier_omega*q)
            else: src=0.0
            energies.append(self._advance(src))
        soma=float(np.mean(energies[-max(4,c.dwell//3):]))
        b=self.baseline[patch]
        if not np.isfinite(b): reward=0.0; self.baseline[patch]=soma
        else:
            reward=np.tanh(c.reward_gain*(soma-b)/(abs(b)+1e-9)); self.baseline[patch]=0.85*b+0.15*soma
        if learn:
            self.grow_event(reward); self.growth_events+=1
        return soma,float(reward)

    def _solve_opportunity(self):
        c=self.cfg;p=self.opportunity
        sink=np.clip(1-self.M,0,1)**4
        for _ in range(c.opportunity_iters):
            nb=0.25*(np.roll(p,1,0)+np.roll(p,-1,0)+np.roll(p,1,1)+np.roll(p,-1,1))
            p=(1-c.opportunity_relax)*p+c.opportunity_relax*nb; p*=sink; p=np.maximum(p,self.outer)
        self.opportunity=np.clip(p,0,1)

    def _growth_weights(self,reward):
        c=self.cfg; self._solve_opportunity()
        solid=(self.M>=c.solid_threshold).astype(np.float32)
        boundary=np.clip(max_filter(solid,1)-solid,0,1)*self.window
        ux,uy=grad(self.opportunity);pressure=np.sqrt(ux*ux+uy*uy)
        vals=pressure[boundary>0]
        sc=np.quantile(vals,0.92)+1e-9 if vals.size else pressure.max()+1e-9
        pressure=np.clip(pressure/sc,0,1)
        base=boundary*np.power(pressure+c.growth_pressure_floor,c.growth_eta)*self.substrate
        if self.condition in ('local','credit','anti_credit'):
            e=np.power(np.clip(self.E,0,1),c.eligibility_power)
            base*=0.18+c.eligibility_gain*e
        if self.condition in ('credit','anti_credit'):
            r=float(np.clip(reward,-c.reward_clip,c.reward_clip));
            if self.condition=='anti_credit': r=-r
            # positive soma improvement reinforces recently used frontier; negative de-emphasizes it
            gate=np.exp(np.clip(c.credit_strength*r*self.E,-3,3))
            base*=gate
        return base.astype(np.float32)

    def grow_event(self,reward=0.0):
        c=self.cfg;w=self._growth_weights(reward)
        if w.sum()<=1e-12:
            solid=(self.M>=c.solid_threshold).astype(np.float32);boundary=np.clip(max_filter(solid,1)-solid,0,1)*self.window;w=boundary*self.substrate
        budget=c.material_budget_per_event; actual=np.zeros_like(self.M); remain=budget; active=(w>0).astype(np.float32)
        for _ in range(10):
            room=np.clip(1-self.M-actual,0,1); a=active*(room>1e-8); cur=w*a
            if cur.sum()<=1e-12: cur=a
            if cur.sum()<=1e-12 or remain<=1e-8: break
            add=np.minimum(remain*cur/(cur.sum()+1e-12),room); actual+=add;remain-=float(add.sum())
        self.M=np.clip(self.M+actual,0,1)*self.window;self.front=actual
        if reward>0:self.credit_map+=reward*actual
        return float(actual.sum())

    def train(self,reverse=False,cycles=None):
        cycles=cycles or self.cfg.train_cycles
        order=[0,3,2,1] if reverse else [0,1,2,3]
        rows=[]
        for cy in range(cycles):
            for p in order:
                e,r=self.visit(p,True); rows.append((cy,p,e,r,float(self.M.sum())))
        return rows

    def mature_arbor(self): self.mature=True

    def probe_sequence(self,reverse=False,cycles=None):
        cycles=cycles or self.cfg.probe_cycles; order=[0,3,2,1] if reverse else [0,1,2,3]
        self.mature=True; self.reset_fast(); use=np.zeros_like(self.M); vals=[]
        # settle with no source in mature medium
        for _ in range(self.cfg.settle_frames): self._advance(0.0)
        for _ in range(cycles):
            for p in order:
                vals.append(self.visit(p,learn=False)[0]); use+=self.E
        return {'root_energy':float(np.mean(vals)),'patch_energy':np.array(vals).reshape(cycles,-1).mean(0),'use_map':use/(len(vals)+1e-9)}

    def bath_probe(self,reverse=False):
        old=self.M.copy();self.M=(1/(1+np.exp((self.rr-self.cfg.root_radius)*3))).astype(np.float32)*self.window
        out=self.probe_sequence(reverse);self.M=old;return out

    def _ball_mask(self,cy,cx,r): return ((self.x-cx)**2+(self.y-cy)**2<=r*r)&(self.M>0.03)

    def lesion_from_usage(self,usage):
        c=self.cfg; total=float(self.M.sum()); target=c.lesion_fraction_of_mass*total
        rrn=self.rr/(c.patch_radius_frac*c.size+1e-9); cand=np.argwhere((self.M>0.15)&(rrn>c.lesion_inner_frac)&(rrn<c.lesion_outer_frac))
        if not len(cand): return np.zeros_like(self.M,dtype=bool),0.0
        scores=usage[cand[:,0],cand[:,1]]; top=cand[np.argsort(scores)[::-1][:max(1,min(80,len(cand)))]]
        best=None;key=(1e9,1e9)
        for cy,cx in top:
            for rad in np.linspace(1.5,5.0,8):
                m=self._ball_mask(cy,cx,rad);rm=float(self.M[m].sum());err=abs(rm-target)/(target+1e-9);u=float(usage[m].mean()) if m.any() else 0
                k=(err,-u)
                if k<key:key=k;best=m
        removed=float(self.M[best].sum());self.M[best]=0;return best,removed

    def low_use_matched_lesion(self,usage,removed_target,forbidden=None):
        c=self.cfg; rrn=self.rr/(c.patch_radius_frac*c.size+1e-9); cand=np.argwhere((self.M>0.15)&(rrn>c.lesion_inner_frac)&(rrn<c.lesion_outer_frac))
        best=None;key=(1e9,1e9)
        for cy,cx in cand[::max(1,len(cand)//180)]:
            for rad in np.linspace(1.5,5.0,8):
                m=self._ball_mask(cy,cx,rad)
                if forbidden is not None and np.any(m&forbidden): continue
                rm=float(self.M[m].sum());err=abs(rm-removed_target)/(removed_target+1e-9);u=float(usage[m].mean()) if m.any() else 1e9
                k=(err,u)
                if k<key:key=k;best=m
        if best is None:return np.zeros_like(self.M,dtype=bool),0.0
        removed=float(self.M[best].sum());self.M[best]=0;return best,removed
