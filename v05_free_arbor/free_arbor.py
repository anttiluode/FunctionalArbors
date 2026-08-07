from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import deque
import math
import numpy as np


def shift(a, dy, dx):
    out=np.zeros_like(a); h,w=a.shape
    ys0=max(0,dy); ys1=min(h,h+dy); yd0=max(0,-dy); yd1=min(h,h-dy)
    xs0=max(0,dx); xs1=min(w,w+dx); xd0=max(0,-dx); xd1=min(w,w-dx)
    out[ys0:ys1,xs0:xs1]=a[yd0:yd1,xd0:xd1]
    return out


def n4(y,x,h,w):
    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
        yy,xx=y+dy,x+dx
        if 0<=yy<h and 0<=xx<w:
            yield yy,xx


def smooth4(a, passes=2):
    x=a.astype(np.float32,copy=True)
    for _ in range(passes):
        x=(x+shift(x,1,0)+shift(x,-1,0)+shift(x,0,1)+shift(x,0,-1))/5.0
    return x


@dataclass
class FreeConfig:
    size:int=31
    seed:int=0
    # geometry
    source_x:int=4
    target_radius:float=1.45
    edge_margin:int=2
    # wave -- fixed-speed binary material
    dt:float=.12
    stiffness:float=1.0
    damping:float=.055
    restoring:float=.025
    saturation:float=.0008
    k_arbor:float=2.5
    k_dev_bath:float=.18
    k_mature_bath:float=2e-4
    pulse_frames:int=6
    source_amp:float=1.0
    carrier_omega:float=.16
    # field-grown bootstrap
    opportunity_iters:int=65
    opportunity_relax:float=.70
    growth_eta:float=2.2
    morph_disorder:float=.28
    eligibility_decay:float=.982
    eligibility_gain:float=.85
    bootstrap_mass:int=90
    bootstrap_max:int=240
    dev_trace_steps:int=58
    # remodeling
    train_trace_steps:int=110
    probe_steps:int=180
    mutations:int=28
    def as_dict(self): return asdict(self)


class FreeBinaryArbor:
    """Free field-grown binary arbor with fixed-speed mature material.

    Bootstrap growth is a Laplacian/opportunity interface process constrained only
    to add one 4-neighbour-connected cell at a time.  This keeps the body tree-like
    while allowing stochastic branches.  Remodeling is local and mass-conserving:
    a straight pulse-used segment may be replaced by a 3-cell U detour, paid for by
    pruning two weak terminal leaves elsewhere.  No route-specific K exists.
    """
    def __init__(self,cfg:FreeConfig|None=None):
        self.cfg=cfg or FreeConfig(); c=self.cfg
        if c.size%2==0: raise ValueError('v0.5 uses an odd grid for an exact soma cell')
        self.rng=np.random.default_rng(c.seed); n=c.size; self.cy=self.cx=n//2
        self.soma=(self.cy,self.cx); self.sources=[(self.cy,c.source_x),(self.cy,n-1-c.source_x)]
        y,x=np.mgrid[0:n,0:n]; self.y=y; self.x=x
        self.body=np.zeros((n,n),np.uint8); self.body[self.soma]=1
        self.initial_seed_mass=1
        q=smooth4(self.rng.normal(size=(n,n)).astype(np.float32),2)
        q=(q-q.mean())/(q.std()+1e-8); self.morph=np.exp(c.morph_disorder*q).astype(np.float32)
        self.psi=np.zeros((n,n),np.complex64); self.vel=np.zeros_like(self.psi); self.E=np.zeros((n,n),np.float32)
        self.mature=False; self._check_stability(); self._make_masks()

    def _make_masks(self):
        c=self.cfg;n=c.size
        self.target_masks=[]
        for sy,sx in self.sources:
            self.target_masks.append((((self.y-sy)**2+(self.x-sx)**2)<=c.target_radius**2))
        self.target_masks=np.asarray(self.target_masks)
        self.protect=np.zeros((n,n),bool); self.protect[self.soma]=True
        self.outer=np.zeros((n,n),bool); m=c.edge_margin
        self.outer[m,:]=True;self.outer[-1-m,:]=True;self.outer[:,m]=True;self.outer[:,-1-m]=True
        self.window=np.zeros((n,n),bool); self.window[m:n-m,m:n-m]=True

    def _check_stability(self):
        c=self.cfg; k=max(c.k_arbor,c.k_dev_bath)
        dtmax=1.0/math.sqrt(8*c.stiffness*k+c.restoring+1e-12)
        self.dt_max=dtmax
        if c.dt>.82*dtmax: raise ValueError(f'dt {c.dt} too high; safety bound {dtmax:.4f}')

    def copy(self):
        z=FreeBinaryArbor(FreeConfig(**self.cfg.as_dict()))
        z.body=self.body.copy();z.morph=self.morph.copy();z.mature=self.mature
        return z

    def mass(self): return int(self.body.sum())

    def degree4(self, body=None):
        b=self.body if body is None else body
        return shift(b,1,0)+shift(b,-1,0)+shift(b,0,1)+shift(b,0,-1)

    def edge_count(self, body=None):
        b=(self.body if body is None else body).astype(bool)
        return int(np.sum(b & shift(b,0,-1)) + np.sum(b & shift(b,-1,0)))

    def connected_component(self, body=None):
        b=(self.body if body is None else body).astype(bool); seen=np.zeros_like(b,bool)
        if not b[self.soma]: return seen
        q=deque([self.soma]);seen[self.soma]=True
        while q:
            y,x=q.popleft()
            for yy,xx in n4(y,x,*b.shape):
                if b[yy,xx] and not seen[yy,xx]:seen[yy,xx]=True;q.append((yy,xx))
        return seen

    def is_tree(self, body=None):
        b=(self.body if body is None else body).astype(bool);v=int(b.sum())
        if v==0:return False
        seen=self.connected_component(b)
        return int(seen.sum())==v and self.edge_count(b)==v-1

    def source_terminal(self,which,body=None):
        b=(self.body if body is None else body).astype(bool); pts=np.argwhere(b & self.target_masks[which])
        if not len(pts): return None
        sy,sx=self.sources[which];d=(pts[:,0]-sy)**2+(pts[:,1]-sx)**2
        p=pts[int(np.argmin(d))];return (int(p[0]),int(p[1]))

    def path(self,which,body=None):
        b=(self.body if body is None else body).astype(bool); src=self.source_terminal(which,b)
        if src is None or not b[self.soma]:return None
        q=deque([src]);prev={src:None}
        while q:
            p=q.popleft()
            if p==self.soma:
                out=[]
                while p is not None:out.append(p);p=prev[p]
                return out[::-1]
            for nb in n4(*p,*b.shape):
                if b[nb] and nb not in prev:prev[nb]=p;q.append(nb)
        return None

    def path_length(self,which,body=None):
        p=self.path(which,body);return (len(p)-1 if p is not None else math.inf)

    def both_connected(self,body=None):return all(self.path(k,body) is not None for k in (0,1))

    def branch_stats(self):
        d=self.degree4();b=self.body.astype(bool)
        return {'mass':self.mass(),'leaves':int(np.sum(b&(d==1))),'junctions':int(np.sum(b&(d>=3))),
                'edges':self.edge_count(),'tree':bool(self.is_tree()),'length_A':self.path_length(0),'length_B':self.path_length(1)}

    # ------------------------- wave transport -------------------------
    def bond_fields(self,mature=None):
        b=self.body.astype(bool); c=self.cfg
        if mature is None:mature=self.mature
        kb=c.k_mature_bath if mature else c.k_dev_bath;ka=c.k_arbor
        kr=np.where(b & shift(b,0,-1),ka,kb).astype(np.float32)
        kl=np.where(b & shift(b,0,1),ka,kb).astype(np.float32)
        kd=np.where(b & shift(b,-1,0),ka,kb).astype(np.float32)
        ku=np.where(b & shift(b,1,0),ka,kb).astype(np.float32)
        return kr,kl,kd,ku

    def _lap(self,u,mature=None):
        kr,kl,kd,ku=self.bond_fields(mature)
        return kr*(shift(u,0,-1)-u)+kl*(shift(u,0,1)-u)+kd*(shift(u,-1,0)-u)+ku*(shift(u,1,0)-u)

    def reset_fast(self,clear_E=True):
        self.psi.fill(0);self.vel.fill(0)
        if clear_E:self.E.fill(0)

    def pulse_source(self,which,q,development=False):
        c=self.cfg
        if not(0<=q<c.pulse_frames):return 0.0
        env=math.sin(math.pi*(q+1)/(c.pulse_frames+1))**2
        src=np.zeros_like(self.psi); phase=np.exp(1j*c.carrier_omega*q)
        if development:
            mask=self.target_masks[which].astype(np.float32); mask/=mask.sum()+1e-12
            src += c.source_amp*env*phase*mask
        else:
            p=self.source_terminal(which)
            if p is None:return 0.0
            src[p]=c.source_amp*env*phase
        return src

    def advance(self,source=0.0,accumulate=True,mature=None):
        c=self.cfg;lap=self._lap(self.psi,mature)
        self.vel += c.dt*(c.stiffness*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel; self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2)
        if accumulate:
            amp=np.abs(self.vel).astype(np.float32)*self.body
            vals=amp[amp>0];sc=np.quantile(vals,.95)+1e-9 if vals.size else 1.
            use=np.clip(amp/sc,0,1)
            self.E=c.eligibility_decay*self.E+(1-c.eligibility_decay)*use
        return float(np.abs(self.psi[self.soma])**2)

    def trace(self,which,steps=None,development=False,accumulate=True):
        steps=steps or (self.cfg.dev_trace_steps if development else self.cfg.train_trace_steps)
        self.reset_fast(clear_E=True);out=[]
        for t in range(int(steps)):
            out.append(self.advance(self.pulse_source(which,t,development),accumulate=accumulate,mature=(False if development else True)))
        return np.asarray(out,float)

    # ------------------------- field-grown bootstrap -------------------------
    def _opportunity(self,which=None,outer=False):
        c=self.cfg;n=c.size
        target=self.outer if outer else self.target_masks[int(which)]
        u=np.zeros((n,n),np.float32);u[target]=1.0;u[self.body>0]=0.0
        for _ in range(c.opportunity_iters):
            nb=.25*(shift(u,1,0)+shift(u,-1,0)+shift(u,0,1)+shift(u,0,-1))
            u=(1-c.opportunity_relax)*u+c.opportunity_relax*nb
            u[~self.window]=0;u[self.body>0]=0;u[target]=1
        return u

    def _tree_frontier(self):
        deg=self.degree4();return (self.body==0)&self.window&(deg==1)

    def grow_field_cell(self,which=None,outer=False):
        u=self._opportunity(which,outer);front=self._tree_frontier();cand=np.flatnonzero(front.ravel())
        if not len(cand):return None
        c=self.cfg
        w=(np.power(np.clip(u,0,1)+1e-5,c.growth_eta)*self.morph*(.20+c.eligibility_gain*np.clip(self.E,0,1))).ravel()[cand]
        if not np.isfinite(w).all() or w.sum()<=1e-30:w=np.ones(len(cand),float)
        w=w/w.sum();i=int(self.rng.choice(cand,p=w));self.body.ravel()[i]=1
        assert self.is_tree()
        return np.unravel_index(i,self.body.shape)

    def bootstrap(self):
        c=self.cfg; events=0
        # Alternate sensory fields until both terminals are reached.
        while events<c.bootstrap_max and not self.both_connected():
            which=events%2; self.trace(which,c.dev_trace_steps,development=True,accumulate=True)
            self.grow_field_cell(which,False);events+=1
        if not self.both_connected():return {'ok':False,'events':events,**self.branch_stats()}
        # Protect the actual terminal cells and then grow spare side branches from a
        # continuous outer reservoir.  These branches provide material for later
        # mass-conserving detours; there is no disconnected reserve block.
        for k in (0,1):
            p=self.source_terminal(k); self.protect[p]=True
        j=0
        while self.mass()<c.bootstrap_mass and events<c.bootstrap_max+c.bootstrap_mass:
            which=j%2;self.trace(which,max(28,c.dev_trace_steps//2),development=True,accumulate=True)
            self.grow_field_cell(None,True);events+=1;j+=1
        assert self.is_tree();return {'ok':True,'events':events,**self.branch_stats()}

    # ------------------------- generic local structural remodeling -------------------------
    def _detour_candidates(self):
        b=self.body.astype(bool);d=self.degree4();h,w=b.shape;out=[]
        for y,x in np.argwhere(b&(d==2)&(~self.protect)):
            y=int(y);x=int(x)
            left=(x>0 and b[y,x-1]);right=(x<w-1 and b[y,x+1]);up=(y>0 and b[y-1,x]);down=(y<h-1 and b[y+1,x])
            if left and right:
                for s in (-1,1):
                    yy=y+s
                    if yy<=0 or yy>=h-1:continue
                    cells=[(yy,x-1),(yy,x),(yy,x+1)]
                    if all(self.window[p] and not b[p] for p in cells):
                        # no accidental contacts beyond intended endpoints
                        tmp=b.copy();tmp[y,x]=False
                        for p in cells:tmp[p]=True
                        # Before paying with leaves, the local substitution itself must stay connected.
                        if self.connected_component(tmp).sum()==tmp.sum():out.append(((y,x),cells))
            if up and down:
                for s in (-1,1):
                    xx=x+s
                    if xx<=0 or xx>=w-1:continue
                    cells=[(y-1,xx),(y,xx),(y+1,xx)]
                    if all(self.window[p] and not b[p] for p in cells):
                        tmp=b.copy();tmp[y,x]=False
                        for p in cells:tmp[p]=True
                        if self.connected_component(tmp).sum()==tmp.sum():out.append(((y,x),cells))
        return out

    def _safe_leaves(self,body,exclude=()):
        d=self.degree4(body);ex=set(exclude);pts=[]
        for y,x in np.argwhere((body>0)&(d==1)&(~self.protect)):
            p=(int(y),int(x))
            if p not in ex:pts.append(p)
        return pts

    def propose_detour(self,which):
        """Generic pulse-eligible local detour, not tied to a pre-drawn cable.

        A straight degree-2 segment anywhere in the free tree may be replaced by a
        three-cell U. Two weak terminal leaves elsewhere pay the +2-cell cost.
        Candidate pivots are weighted only by the recent local eligibility field.
        """
        cand=self._detour_candidates()
        if not cand:return None
        w=np.asarray([.015+float(self.E[p]) for p,_ in cand],float);w/=w.sum()
        order=self.rng.choice(len(cand),size=min(len(cand),24),replace=False,p=w)
        old=self.body.copy();oldmass=self.mass(); oldpaths=(self.path(0),self.path(1))
        for idx in np.atleast_1d(order):
            pivot,cells=cand[int(idx)];tmp=old.copy();tmp[pivot]=0
            for p in cells:tmp[p]=1
            leaves=self._safe_leaves(tmp,exclude=cells)
            if len(leaves)<2:continue
            # Pay for the detour with the least-used terminal material. Try several
            # combinations because a leaf removal can expose another leaf.
            leaves=sorted(leaves,key=lambda p:float(self.E[p]))
            paid=[];work=tmp.copy()
            for _ in range(2):
                avail=self._safe_leaves(work,exclude=cells)
                if not avail:break
                q=min(avail,key=lambda p:float(self.E[p]));work[q]=0;paid.append(q)
            if len(paid)!=2:continue
            if int(work.sum())!=oldmass:continue
            if not self.is_tree(work):continue
            if not self.both_connected(work):continue
            # classify whether the pivot belonged to either unique functional path
            onA=oldpaths[0] is not None and pivot in set(oldpaths[0]);onB=oldpaths[1] is not None and pivot in set(oldpaths[1])
            self.body=work
            return {'pivot':pivot,'cells':cells,'pruned':paid,'onA':bool(onA),'onB':bool(onB),'which_trace':int(which)}
        self.body=old;return None

    def snapshot(self):return self.body.copy()
    def restore(self,s):self.body=s.copy()
