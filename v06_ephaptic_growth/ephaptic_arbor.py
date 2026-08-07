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
    x=a.copy()
    for _ in range(passes):
        x=.50*x+.125*(shift(x,1,0)+shift(x,-1,0)+shift(x,0,1)+shift(x,0,-1))
    return x


@dataclass
class EphapticConfig:
    size:int=31
    seed:int=0
    source_x:int=4
    target_radius:float=1.45
    edge_margin:int=2

    # fixed-speed binary wave medium
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
    bootstrap_mass:int=70
    bootstrap_max:int=260
    dev_trace_steps:int=58

    # local activity / ephaptic guidance
    eligibility_decay:float=.982
    ephaptic_decay:float=.965
    ephaptic_smooth:int=5
    steer_beta:float=2.3
    magnitude_gain:float=2.0
    start_power:float=1.2

    # generic growth-cone episode
    train_trace_steps:int=125
    cone_min_steps:int=2
    cone_max_steps:int=10
    cone_attempts:int=8
    probe_steps:int=210
    mutations:int=18

    def as_dict(self): return asdict(self)


class EphapticFreeArbor:
    """Binary field-grown arbor with no named detour topology primitive.

    The mature body has only two bond conductivities. Structural proposals are
    episodes made from ordinary local operations:

      branch initiation -> one-cell tip extensions -> accidental reconnection
      -> connectivity-safe pruning elsewhere.

    A phase-sensitive extracellular-field proxy biases the growth-cone walk.
    Soma credit is applied only after a complete legal episode; the structural
    operator itself does not inspect A/B identity or desired delay.
    """
    def __init__(self,cfg:EphapticConfig|None=None):
        self.cfg=cfg or EphapticConfig(); c=self.cfg
        if c.size%2==0: raise ValueError('v0.6 uses odd N for an exact soma cell')
        self.rng=np.random.default_rng(c.seed); self.guide_rng=np.random.default_rng(c.seed+88173)
        n=c.size; self.cy=self.cx=n//2; self.soma=(self.cy,self.cx)
        self.sources=[(self.cy,c.source_x),(self.cy,n-1-c.source_x)]
        y,x=np.mgrid[0:n,0:n]; self.y=y;self.x=x
        self.body=np.zeros((n,n),np.uint8);self.body[self.soma]=1
        q=smooth4(self.rng.normal(size=(n,n)).astype(np.float32),2)
        q=(q-q.mean())/(q.std()+1e-8);self.morph=np.exp(c.morph_disorder*q).astype(np.float32)
        self.psi=np.zeros((n,n),np.complex64);self.vel=np.zeros_like(self.psi)
        self.E=np.zeros((n,n),np.float32)
        self.Gx=np.zeros((n,n),np.float32);self.Gy=np.zeros((n,n),np.float32);self.H=np.zeros((n,n),np.float32)
        self.mature=False;self._make_masks();self._check_stability()

    def _make_masks(self):
        c=self.cfg;n=c.size;self.target_masks=[]
        for sy,sx in self.sources:
            self.target_masks.append((((self.y-sy)**2+(self.x-sx)**2)<=c.target_radius**2))
        self.target_masks=np.asarray(self.target_masks)
        self.protect=np.zeros((n,n),bool);self.protect[self.soma]=True
        m=c.edge_margin;self.window=np.zeros((n,n),bool);self.window[m:n-m,m:n-m]=True
        self.outer=np.zeros((n,n),bool);self.outer[m,:]=True;self.outer[-1-m,:]=True;self.outer[:,m]=True;self.outer[:,-1-m]=True

    def _check_stability(self):
        c=self.cfg;k=max(c.k_arbor,c.k_dev_bath)
        dtmax=1.0/math.sqrt(8*c.stiffness*k+c.restoring+1e-12);self.dt_max=dtmax
        if c.dt>.82*dtmax:raise ValueError(f'dt {c.dt} too high; safety bound {dtmax:.4f}')

    def copy(self):
        z=EphapticFreeArbor(EphapticConfig(**self.cfg.as_dict()))
        z.body=self.body.copy();z.morph=self.morph.copy();z.mature=self.mature
        return z

    def mass(self):return int(self.body.sum())
    def degree4(self,body=None):
        b=self.body if body is None else body
        return shift(b,1,0)+shift(b,-1,0)+shift(b,0,1)+shift(b,0,-1)
    def edge_count(self,body=None):
        b=(self.body if body is None else body).astype(bool)
        return int(np.sum(b&shift(b,0,-1))+np.sum(b&shift(b,-1,0)))

    def connected_component(self,body=None):
        b=(self.body if body is None else body).astype(bool);seen=np.zeros_like(b,bool)
        if not b[self.soma]:return seen
        q=deque([self.soma]);seen[self.soma]=True
        while q:
            p=q.popleft()
            for nb in n4(*p,*b.shape):
                if b[nb] and not seen[nb]:seen[nb]=True;q.append(nb)
        return seen

    def is_tree(self,body=None):
        b=(self.body if body is None else body).astype(bool);v=int(b.sum())
        if v==0:return False
        return int(self.connected_component(b).sum())==v and self.edge_count(b)==v-1

    def source_terminal(self,which,body=None):
        b=(self.body if body is None else body).astype(bool);pts=np.argwhere(b&self.target_masks[which])
        if not len(pts):return None
        sy,sx=self.sources[which];d=(pts[:,0]-sy)**2+(pts[:,1]-sx)**2;p=pts[int(np.argmin(d))]
        return int(p[0]),int(p[1])

    def path(self,which,body=None):
        b=(self.body if body is None else body).astype(bool);src=self.source_terminal(which,b)
        if src is None:return None
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
        p=self.path(which,body);return len(p)-1 if p is not None else math.inf
    def both_connected(self,body=None):return all(self.path(k,body) is not None for k in (0,1))
    def branch_stats(self):
        d=self.degree4();b=self.body.astype(bool)
        return dict(mass=self.mass(),leaves=int(np.sum(b&(d==1))),junctions=int(np.sum(b&(d>=3))),edges=self.edge_count(),
                    tree=bool(self.is_tree()),length_A=self.path_length(0),length_B=self.path_length(1))

    # ---------------- wave and extracellular-field proxy ----------------
    def bond_fields(self,mature=None):
        b=self.body.astype(bool);c=self.cfg
        if mature is None:mature=self.mature
        kb=c.k_mature_bath if mature else c.k_dev_bath;ka=c.k_arbor
        return (np.where(b&shift(b,0,-1),ka,kb).astype(np.float32),
                np.where(b&shift(b,0,1),ka,kb).astype(np.float32),
                np.where(b&shift(b,-1,0),ka,kb).astype(np.float32),
                np.where(b&shift(b,1,0),ka,kb).astype(np.float32))
    def _lap(self,u,mature=None):
        kr,kl,kd,ku=self.bond_fields(mature)
        return kr*(shift(u,0,-1)-u)+kl*(shift(u,0,1)-u)+kd*(shift(u,-1,0)-u)+ku*(shift(u,1,0)-u)
    def reset_fast(self,clear_traces=True):
        self.psi.fill(0);self.vel.fill(0)
        if clear_traces:
            self.E.fill(0);self.Gx.fill(0);self.Gy.fill(0);self.H.fill(0)
    def pulse_source(self,which,q,development=False):
        c=self.cfg
        if not(0<=q<c.pulse_frames):return 0.0
        env=math.sin(math.pi*(q+1)/(c.pulse_frames+1))**2;phase=np.exp(1j*c.carrier_omega*q);src=np.zeros_like(self.psi)
        if development:
            mask=self.target_masks[which].astype(np.float32);mask/=mask.sum()+1e-12;src+=c.source_amp*env*phase*mask
        else:
            p=self.source_terminal(which)
            if p is None:return 0.0
            src[p]=c.source_amp*env*phase
        return src

    def _accumulate_traces(self,guidance_mode='full'):
        c=self.cfg
        # Intracellular use trace: local velocity on occupied material.
        amp=np.abs(self.vel).astype(np.float32)*self.body
        vals=amp[amp>0];sc=np.quantile(vals,.95)+1e-9 if vals.size else 1.
        use=np.clip(amp/sc,0,1);self.E=c.eligibility_decay*self.E+(1-c.eligibility_decay)*use

        if guidance_mode=='none':return
        # Toy extracellular potential: spatially blurred analytic membrane-current proxy.
        # It is intentionally a computational proxy, not a biophysical volume-conductor solver.
        ve=smooth4(self.vel*self.body,c.ephaptic_smooth)
        ex=-.5*(shift(ve,0,-1)-shift(ve,0,1));ey=-.5*(shift(ve,-1,0)-shift(ve,1,0))
        mag=np.sqrt(np.abs(ex)**2+np.abs(ey)**2).astype(np.float32)
        msc=np.quantile(mag,.98)+1e-9;mag=np.clip(mag/msc,0,1)
        ref=self.psi[self.soma]
        if abs(ref)>1e-8:
            ref=ref/(abs(ref)+1e-12)
            if guidance_mode=='phase_shuffle':ref=ref*np.exp(1j*self.guide_rng.uniform(-math.pi,math.pi))
            gx=np.real(ex*np.conj(ref)).astype(np.float32);gy=np.real(ey*np.conj(ref)).astype(np.float32)
            gscale=np.quantile(np.sqrt(gx*gx+gy*gy),.98)+1e-9;gx/=gscale;gy/=gscale
            if guidance_mode=='magnitude':gx.fill(0);gy.fill(0)
            a=c.ephaptic_decay;self.Gx=a*self.Gx+(1-a)*gx;self.Gy=a*self.Gy+(1-a)*gy
        a=c.ephaptic_decay;self.H=a*self.H+(1-a)*mag

    def advance(self,source=0.0,accumulate=True,mature=None,guidance_mode='full'):
        c=self.cfg;lap=self._lap(self.psi,mature)
        self.vel += c.dt*(c.stiffness*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel;self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2)
        if accumulate:self._accumulate_traces(guidance_mode)
        return float(np.abs(self.psi[self.soma])**2)

    def trace(self,which,steps=None,development=False,accumulate=True,guidance_mode='full'):
        steps=steps or (self.cfg.dev_trace_steps if development else self.cfg.train_trace_steps)
        self.reset_fast(clear_traces=True);out=[]
        for t in range(int(steps)):
            out.append(self.advance(self.pulse_source(which,t,development),accumulate=accumulate,
                                    mature=(False if development else True),guidance_mode=guidance_mode))
        return np.asarray(out,float)

    # ---------------- field-grown bootstrap ----------------
    def _opportunity(self,which=None,outer=False):
        c=self.cfg;n=c.size;target=self.outer if outer else self.target_masks[int(which)]
        u=np.zeros((n,n),np.float32);u[target]=1.;u[self.body>0]=0
        for _ in range(c.opportunity_iters):
            nb=.25*(shift(u,1,0)+shift(u,-1,0)+shift(u,0,1)+shift(u,0,-1))
            u=(1-c.opportunity_relax)*u+c.opportunity_relax*nb;u[~self.window]=0;u[self.body>0]=0;u[target]=1
        return u
    def _tree_frontier(self):return (self.body==0)&self.window&(self.degree4()==1)
    def grow_field_cell(self,which=None,outer=False):
        u=self._opportunity(which,outer);front=self._tree_frontier();cand=np.flatnonzero(front.ravel())
        if not len(cand):return None
        c=self.cfg;w=(np.power(np.clip(u,0,1)+1e-5,c.growth_eta)*self.morph*(.20+.85*np.clip(self.E,0,1))).ravel()[cand]
        if not np.isfinite(w).all() or w.sum()<=1e-30:w=np.ones(len(cand),float)
        i=int(self.rng.choice(cand,p=w/w.sum()));p=np.unravel_index(i,self.body.shape);self.body[p]=1;return p
    def bootstrap(self):
        c=self.cfg;events=0
        while events<c.bootstrap_max and not self.both_connected():
            k=events%2;self.trace(k,c.dev_trace_steps,True,True,'none');self.grow_field_cell(k,False);events+=1
        if not self.both_connected():return {'ok':False,'events':events,**self.branch_stats()}
        for k in (0,1):
            p=self.source_terminal(k);self.protect[p]=True
        j=0
        while self.mass()<c.bootstrap_mass and events<c.bootstrap_max+c.bootstrap_mass:
            k=j%2;self.trace(k,max(28,c.dev_trace_steps//2),True,True,'none');self.grow_field_cell(None,True);events+=1;j+=1
        assert self.is_tree();return {'ok':self.mass()==c.bootstrap_mass,'events':events,**self.branch_stats()}

    # ---------------- generic growth-cone / prune episode ----------------
    def _start_candidates(self):
        b=self.body.astype(bool);d=self.degree4();cand=np.argwhere(b&(d<=2)&(~self.protect))
        return [(int(y),int(x)) for y,x in cand]

    def _choose_start(self):
        cand=self._start_candidates()
        if not cand:return None
        c=self.cfg;w=np.asarray([.01+float(self.E[p])**c.start_power for p in cand],float);w/=w.sum()
        return cand[int(self.rng.choice(len(cand),p=w))]

    def _step_weight(self,parent,dest,mode,shuffle_angle=0.0):
        c=self.cfg;dy=dest[0]-parent[0];dx=dest[1]-parent[1]
        h=float(self.H[dest]);base=.12+c.magnitude_gain*h
        if mode=='none':return 1.0
        if mode=='magnitude':return max(base,1e-6)
        gx=float(self.Gx[parent]);gy=float(self.Gy[parent])
        if mode=='phase_shuffle':
            ca,sa=math.cos(shuffle_angle),math.sin(shuffle_angle);gx,gy=ca*gx-sa*gy,sa*gx+ca*gy
        norm=math.hypot(gx,gy)+1e-9;dot=(gx*dx+gy*dy)/norm
        return max(base*math.exp(np.clip(c.steer_beta*dot,-4,4)),1e-8)

    def _old_contacts(self,p,old,allowed):
        return [q for q in n4(*p,*old.shape) if old[q] and q not in allowed]

    def _grow_cone(self,mode):
        """Grow a local tip by one-cell extensions until it reconnects to old arbor.

        No U shape or target route is encoded. The tip makes an ordinary nearest-
        neighbour walk guided by the accumulated extracellular field (or ablation).
        """
        old=self.body.astype(bool);start=self._choose_start()
        if start is None:return None
        c=self.cfg;chain=[];cur=start;visited={start};angle=self.guide_rng.uniform(-math.pi,math.pi)
        for step in range(c.cone_max_steps):
            opts=[];weights=[]
            for q in n4(*cur,*old.shape):
                if not self.window[q] or q in visited or old[q]:continue
                # Avoid touching multiple old-arbor points before the allowed reconnect.
                contacts=self._old_contacts(q,old,{start,cur})
                # A candidate can be a reconnecting tip only after a minimum walk.
                if contacts and step+1<c.cone_min_steps:continue
                # Reject complex multi-contact reconnections.
                if len(contacts)>1:continue
                opts.append((q,contacts));weights.append(self._step_weight(cur,q,mode,angle))
            if not opts:return None
            weights=np.asarray(weights,float);weights/=weights.sum();q,contacts=opts[int(self.rng.choice(len(opts),p=weights))]
            chain.append(q);visited.add(q);cur=q
            if contacts:
                reconnect=contacts[0]
                if reconnect==start:return None
                return {'start':start,'reconnect':reconnect,'chain':chain.copy(),'guide_mode':mode,
                        'field_support':float(np.mean([self.H[p] for p in chain]))}
        return None

    def _tree_path_between(self,a,b,body):
        q=deque([a]);prev={a:None}
        while q:
            p=q.popleft()
            if p==b:
                out=[]
                while p is not None:out.append(p);p=prev[p]
                return out[::-1]
            for nb in n4(*p,*body.shape):
                if body[nb] and nb not in prev:prev[nb]=p;q.append(nb)
        return None

    def _removable_cells(self,body,exclude=()):
        ex=set(exclude);pts=[]
        for y,x in np.argwhere(body):
            p=(int(y),int(x))
            if p in ex or self.protect[p]:continue
            test=body.copy();test[p]=0
            if int(self.connected_component(test).sum())==int(test.sum()) and self.both_connected(test):pts.append(p)
        return pts

    def propose_growth_episode(self,guidance_mode='full'):
        """Generic branch extension/reconnection + connectivity-safe pruning.

        The new branch is created by a field-guided local walk. After it reconnects,
        one old cycle cell is pruned (the shortcut is *not* specified in advance),
        then additional weakest removable cells pay the rest of the mass budget.
        Final state must again be one connected tree with the original mass.
        """
        old=self.body.copy();oldmass=self.mass();oldpaths=(self.path(0),self.path(1))
        for _ in range(self.cfg.cone_attempts):
            ep=self._grow_cone(guidance_mode)
            if ep is None:continue
            start,reconnect,chain=ep['start'],ep['reconnect'],ep['chain'];L=len(chain)
            # Ensure no chain cell has unintended old contacts except final reconnect.
            legal=True
            for i,p in enumerate(chain):
                allowed={start} if i==0 else {chain[i-1]}
                if i==len(chain)-1:allowed.add(reconnect)
                contacts=[q for q in n4(*p,*old.shape) if old[q] and q not in allowed]
                if contacts:legal=False;break
            if not legal:continue
            tmp=old.copy()
            for p in chain:tmp[p]=1
            oldseg=self._tree_path_between(start,reconnect,old.astype(bool))
            if oldseg is None or len(oldseg)<3:continue
            # Any internal old-segment cell whose removal keeps connectivity is a
            # generic pruning candidate. Prefer low recent use, not A/B identity.
            cuts=[]
            for p in oldseg[1:-1]:
                if self.protect[p]:continue
                test=tmp.copy();test[p]=0
                if int(self.connected_component(test).sum())==int(test.sum()) and self.both_connected(test):cuts.append(p)
            if not cuts:continue
            cw=np.asarray([1.0/(.02+float(self.E[p])) for p in cuts]);cw/=cw.sum();cut=cuts[int(self.rng.choice(len(cuts),p=cw))]
            work=tmp.copy();work[cut]=0;pruned=[cut]
            # Added L cells and removed one. Remove L-1 other weakly used cells,
            # each time requiring that soma and both sensory terminals remain linked.
            while int(work.sum())>oldmass:
                rem=self._removable_cells(work,exclude=chain)
                if not rem:break
                # Prefer terminal/weak material but allow internal safe pruning.
                deg=self.degree4(work);score=[]
                for p in rem:
                    terminal_bonus=.35 if deg[p]==1 else 1.0
                    score.append(terminal_bonus*(.02+float(self.E[p])))
                q=rem[int(np.argmin(score))];work[q]=0;pruned.append(q)
            if int(work.sum())!=oldmass:continue
            if not self.is_tree(work) or not self.both_connected(work):continue
            onA=any(p in set(oldpaths[0] or []) for p in oldseg);onB=any(p in set(oldpaths[1] or []) for p in oldseg)
            self.body=work.astype(np.uint8)
            ep.update({'cut':cut,'pruned':pruned,'old_segment_edges':len(oldseg)-1,'new_branch_edges':len(chain)+1,
                       'onA_oldsegment':bool(onA),'onB_oldsegment':bool(onB)})
            return ep
        self.body=old;return None

    def snapshot(self):return self.body.copy()
    def restore(self,s):self.body=s.copy()
