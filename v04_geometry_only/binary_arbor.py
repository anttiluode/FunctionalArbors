from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np

from functional_arbor.operators import div_k_grad, grad, max_filter, smooth


@dataclass
class BinaryConfig:
    size: int = 31
    seed: int = 0
    patch_radius_frac: float = 0.29
    patch_sigma: float = 1.25
    root_sigma: float = 1.20
    root_radius: float = 2.15
    edge_margin: int = 2

    # second-order wave
    dt: float = 0.14
    wave_stiffness: float = 1.0
    damping: float = 0.095
    restoring: float = 0.040
    saturation: float = 0.0015
    source_amp: float = 0.95
    carrier_omega: float = 0.20

    # THE v0.4 restriction.  Every occupied site has the same K.
    dev_bath_k: float = 0.20
    dev_arbor_k: float = 1.25
    mature_bath_k: float = 0.018
    mature_arbor_k: float = 1.25

    # growth
    opportunity_iters: int = 18
    opportunity_relax: float = 0.60
    growth_eta: float = 2.4
    pressure_floor: float = 0.025
    morph_disorder: float = 0.22  # affects growth choice ONLY, never K
    cells_per_event: int = 2
    eligibility_decay: float = 0.993
    eligibility_gain: float = 1.10
    eligibility_power: float = 0.72
    credit_strength: float = 5.0
    reward_clip: float = 2.2

    def as_dict(self):
        return asdict(self)


class BinaryGeometryArbor:
    """A morphogenetic wave medium with a binary structural body.

    B[y,x] is exactly 0 or 1.  Conductivity has only two values: bath and arbor.
    Quenched disorder may influence morphogenesis, but it is forbidden from
    modulating conductivity.  Therefore learned timing cannot be stored as local
    thickness/material-speed variation inside the arbor.
    """
    def __init__(self, cfg: BinaryConfig | None = None, condition: str = 'credit'):
        self.cfg = cfg or BinaryConfig()
        if condition not in ('reward','shuffle','local','blind','anti'):
            raise ValueError(condition)
        self.condition = condition
        self.rng = np.random.default_rng(self.cfg.seed)
        self._geometry()
        self.reset()
        self._stability_guard()

    def _geometry(self):
        c=self.cfg; n=c.size
        y,x=np.mgrid[0:n,0:n].astype(np.float32); cc=(n-1)/2.0
        self.y,self.x,self.cc=y,x,cc
        self.rr=np.sqrt((x-cc)**2+(y-cc)**2)
        root=np.exp(-(self.rr**2)/(2*c.root_sigma**2)).astype(np.float32)
        self.root=root/(root.sum()+1e-12)
        r=n*c.patch_radius_frac
        patches=[]
        # exactly opposite A/B regions
        for ang in (math.pi,0.0):
            px=cc+r*math.cos(ang); py=cc+r*math.sin(ang)
            m=np.exp(-((x-px)**2+(y-py)**2)/(2*c.patch_sigma**2)).astype(np.float32)
            patches.append(m/(m.max()+1e-12))
        self.patches=np.stack(patches)
        d=np.minimum.reduce([x,y,(n-1)-x,(n-1)-y])
        self.window=np.clip(d/max(c.edge_margin,1),0,1)
        self.window=self.window*self.window*(3-2*self.window)
        self.outer=np.zeros((n,n),np.float32)
        self.outer[:2]=1; self.outer[-2:]=1; self.outer[:,:2]=1; self.outer[:,-2:]=1

    def reset(self):
        c=self.cfg; n=c.size
        self.psi=np.zeros((n,n),np.complex64)
        self.vel=np.zeros((n,n),np.complex64)
        self.B=(self.rr <= c.root_radius).astype(np.float32)
        self.B*= (self.window>0).astype(np.float32)
        # disorder is a morphogenetic landscape only
        q=smooth(self.rng.normal(size=(n,n)).astype(np.float32),2)
        q=(q-q.mean())/(q.std()+1e-8)
        self.morph=np.exp(c.morph_disorder*q).astype(np.float32)
        self.E=np.zeros((n,n),np.float32)
        self.front=np.zeros((n,n),np.float32)
        self.opportunity=self.outer.copy()
        self.growth_events=0
        self.mature=False
        self.K_override=None

    def _stability_guard(self):
        # leapfrog-ish explicit update; conservative safety bound based on max K.
        c=self.cfg
        kmax=max(c.dev_arbor_k,c.mature_arbor_k,c.dev_bath_k,c.mature_bath_k)
        dtmax=1.0/math.sqrt(8*c.wave_stiffness*kmax + c.restoring + 1e-12)
        self.dt_max=dtmax
        if c.dt > 0.80*dtmax:
            raise ValueError(f'dt={c.dt:.4f} too large for binary-wave safety bound {dtmax:.4f}')

    @property
    def M(self):
        # Compatibility with v0.3 anatomy tools.  It is strictly binary here.
        return self.B

    def conductivity(self, mature=None):
        if self.K_override is not None:
            return np.asarray(self.K_override,np.float32)
        c=self.cfg
        if mature is None: mature=self.mature
        kb,ka=(c.mature_bath_k,c.mature_arbor_k) if mature else (c.dev_bath_k,c.dev_arbor_k)
        # No substrate factor. No B**p. No thickness. Two numbers only.
        return np.where(self.B>0.5,ka,kb).astype(np.float32)

    def reset_fast(self):
        self.psi.fill(0); self.vel.fill(0); self.E.fill(0)

    def _advance(self, source):
        c=self.cfg; K=self.conductivity()
        lap=div_k_grad(K,self.psi)
        self.vel += c.dt*(c.wave_stiffness*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel
        self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2)
        self.psi*=self.window; self.vel*=self.window
        gx,gy=grad(self.psi)
        jx=np.imag(np.conj(self.psi)*K*gx); jy=np.imag(np.conj(self.psi)*K*gy)
        mag=np.sqrt(jx*jx+jy*jy).astype(np.float32)
        scale=np.quantile(mag,0.985)+1e-9
        use=np.clip(mag/scale,0,1)
        self.E=c.eligibility_decay*self.E+(1-c.eligibility_decay)*use
        return float(np.sum(np.abs(self.psi)**2*self.root))

    def _solve_opportunity(self):
        c=self.cfg; p=self.opportunity
        empty=1-self.B
        for _ in range(c.opportunity_iters):
            nb=.25*(np.roll(p,1,0)+np.roll(p,-1,0)+np.roll(p,1,1)+np.roll(p,-1,1))
            p=(1-c.opportunity_relax)*p+c.opportunity_relax*nb
            p*=empty
            p=np.maximum(p,self.outer)
        self.opportunity=np.clip(p,0,1)

    def growth_weights(self, reward=0.0):
        c=self.cfg; self._solve_opportunity()
        boundary=np.clip(max_filter(self.B,1)-self.B,0,1)*(self.window>0)
        ux,uy=grad(self.opportunity); pressure=np.sqrt(ux*ux+uy*uy)
        vals=pressure[boundary>0]
        scale=np.quantile(vals,.90)+1e-9 if vals.size else pressure.max()+1e-9
        pressure=np.clip(pressure/scale,0,1)
        w=boundary*np.power(pressure+c.pressure_floor,c.growth_eta)*self.morph
        if self.condition not in ('blind',):
            e=np.power(np.clip(self.E,0,1),c.eligibility_power)
            w*=0.12+c.eligibility_gain*e
        if self.condition in ('reward','shuffle','anti'):
            r=float(np.clip(reward,-c.reward_clip,c.reward_clip))
            if self.condition=='anti': r=-r
            w*=np.exp(np.clip(c.credit_strength*r*self.E,-4,4))
        return np.asarray(w,np.float64)

    def grow_event(self,reward=0.0):
        c=self.cfg; w=self.growth_weights(reward)
        cand=np.flatnonzero((w>0).ravel())
        n=min(int(c.cells_per_event),len(cand))
        self.front.fill(0)
        if n<=0: return 0
        p=w.ravel()[cand]; p=p/(p.sum()+1e-30)
        # Weighted without replacement. Fixed cell count => fixed structural mass.
        chosen=self.rng.choice(cand,size=n,replace=False,p=p)
        flat=self.B.ravel(); flat[chosen]=1.0
        self.front.ravel()[chosen]=1.0
        return n

    def mass(self):
        return float(self.B.sum())

    def connected_fraction(self):
        # fraction of arbor belonging to root-connected 8-neighbour component
        seed=np.argwhere((self.root>=.45*self.root.max())&(self.B>0.5))
        if not len(seed): return 0.0
        seen=np.zeros_like(self.B,bool); stack=[tuple(seed[0])]; seen[stack[0]]=True
        h,w=self.B.shape
        while stack:
            y,x=stack.pop()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not (dy or dx): continue
                    yy,xx=y+dy,x+dx
                    if 0<=yy<h and 0<=xx<w and self.B[yy,xx]>0.5 and not seen[yy,xx]:
                        seen[yy,xx]=True; stack.append((yy,xx))
        return float(seen.sum()/(self.B.sum()+1e-12))

    def patch_connected(self, which, level=.35):
        target=self.patches[which]>=level*self.patches[which].max()
        # flood root component, then test overlap with target region
        seed=np.argwhere((self.root>=.40*self.root.max())&(self.B>0.5))
        if not len(seed): return False
        seen=np.zeros_like(self.B,bool); stack=[tuple(seed[0])]; seen[stack[0]]=True
        h,w=self.B.shape
        while stack:
            y,x=stack.pop()
            if target[y,x]: return True
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not(dy or dx):continue
                    yy,xx=y+dy,x+dx
                    if 0<=yy<h and 0<=xx<w and self.B[yy,xx]>0.5 and not seen[yy,xx]:
                        seen[yy,xx]=True; stack.append((yy,xx))
        return False

    def _degree8(self):
        b=self.B
        d=np.zeros_like(b,np.float32)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dy or dx:
                    d += np.roll(np.roll(b,dy,0),dx,1)
        d[0]=0;d[-1]=0;d[:,0]=0;d[:,-1]=0
        return d

    def remodel_event(self, reward=0.0, swaps=1):
        """Mass-conserving structural turnover.

        Positive credit consolidates recently used geometry: add near used frontier,
        withdraw weakly used non-root material. Negative credit does the converse:
        prune recently used material and explore a different frontier.  Conductivity
        is still strictly binary; this operation can only change topology/geometry.
        """
        c=self.cfg; made=0
        protect=(self.rr <= c.root_radius+0.5)
        for _ in range(int(swaps)):
            addw=self.growth_weights(reward)
            cand_add=np.flatnonzero((addw>0).ravel())
            if not len(cand_add):break
            pa=addw.ravel()[cand_add];pa=pa/(pa.sum()+1e-30)
            ai=int(self.rng.choice(cand_add,p=pa))

            deg=self._degree8()
            occ=(self.B>0.5)&(~protect)
            # avoid removing isolated leaves on negative trials: to change a route,
            # bad-credit pruning is allowed to attack used through-path material.
            if reward < 0:
                rw=(0.03+np.clip(self.E,0,1))*(0.25+deg/8.0)
            else:
                rw=(0.03+1.0-np.clip(self.E,0,1))*(0.25+(8.0-deg)/8.0)
            rw*=occ
            cand_rem=np.flatnonzero((rw>0).ravel())
            if not len(cand_rem):break
            pr=rw.ravel()[cand_rem];pr=pr/(pr.sum()+1e-30)
            ri=int(self.rng.choice(cand_rem,p=pr))
            if ri==ai:continue
            self.B.ravel()[ai]=1.0; self.B.ravel()[ri]=0.0
            self.front.fill(0);self.front.ravel()[ai]=1.0;self.front.ravel()[ri]=-1.0
            made+=1
        return made
