from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import deque
import math
import numpy as np
from scipy.fft import dstn, idstn

try:
    from v06_ephaptic_growth.ephaptic_arbor import EphapticConfig, EphapticFreeArbor, shift, n4
except ImportError:
    from ..v06_ephaptic_growth.ephaptic_arbor import EphapticConfig, EphapticFreeArbor, shift, n4


@dataclass
class V07Config(EphapticConfig):
    # Quasi-static extracellular medium. Grounded outer boundary.
    extracellular_sigma: float = 1.0
    extracellular_screen: float = 0.025
    field_stride: int = 1
    tm_axial_gain: float = 1.0
    tm_source_gain: float = 1.0

    # Slow chemistry and credit eligibility. Chemistry intentionally uses
    # extracellular field magnitude only, so phase ablations are chemistry-matched.
    chemistry_decay: float = 0.975
    chemistry_gain: float = 0.85
    phase_trace_decay: float = 0.965
    structural_elig_decay: float = 0.90
    support_decay: float = 0.996
    activity_support: float = 0.018
    chemistry_support: float = 0.010
    credit_support: float = 0.28
    new_cell_support: float = 0.36
    old_cell_support: float = 0.58
    reward_gain: float = 4.0

    # Persistent growth cones. No reconnect+prune macro-operation exists.
    max_tips: int = 6
    tip_initiate_prob: float = 0.55
    tip_branch_prob: float = 0.08
    tip_stall_limit: int = 4
    tip_persistence_beta: float = 0.70
    cone_steer_beta: float = 1.85
    cone_chem_gain: float = 1.8
    prune_temperature: float = 0.11
    new_cell_grace: int = 3

    # Development protocol.
    development_ticks: int = 36
    eval_interval: int = 3
    developmental_drive_steps: int = 64
    developmental_lag: int = 20

    def as_dict(self): return asdict(self)


class PersistentEphapticArbor(EphapticFreeArbor):
    """v0.7 arbor with explicit extracellular solve and persistent tips.

    The intracellular wave remains the fixed-speed binary transport substrate from
    v0.6. The extracellular potential is now obtained from a grounded quasi-static
    solve driven by an explicit current-source density derived from axial-current
    divergence plus imposed terminal current.

    Development is not an atomic structural proposal. Tips persist across ticks.
    A tick may initiate/extend/branch a tip; a separate homeostatic process may
    retract one connectivity-safe weak cell. Reconnection is simply what happens
    when an extending tip touches old arbor.
    """
    def __init__(self, cfg: V07Config | None = None):
        super().__init__(cfg or V07Config())
        self.cfg: V07Config
        n=self.cfg.size
        self.chem=np.zeros((n,n),np.float32)
        self.support=np.zeros((n,n),np.float32)
        self.struct_elig=np.zeros((n,n),np.float32)
        self.age=np.zeros((n,n),np.int16)
        self.tips=[]
        self.material_target=self.mass()
        self.dev_tick=0
        self.last_reward=0.0
        self.field_solves=0
        self.reconnections=0
        self.extensions=0
        self.retractions=0
        self.branches=0
        self.initiations=0
        self.field_power=[]
        self._phase_rng=np.random.default_rng(self.cfg.seed+991_337)
        self._build_poisson_spectrum()

    def _build_poisson_spectrum(self):
        n=self.cfg.size; m=n-2
        k=np.arange(1,m+1,dtype=np.float64)
        lam1=4*np.sin(np.pi*k/(2*(n-1)))**2
        self._poisson_denom=(self.cfg.extracellular_sigma*(lam1[:,None]+lam1[None,:])+
                             self.cfg.extracellular_screen).astype(np.float64)

    def copy(self):
        z=PersistentEphapticArbor(V07Config(**self.cfg.as_dict()))
        z.body=self.body.copy();z.morph=self.morph.copy();z.mature=self.mature
        z.chem=self.chem.copy();z.support=self.support.copy();z.struct_elig=self.struct_elig.copy();z.age=self.age.copy()
        z.material_target=self.material_target
        return z

    def prepare_development(self):
        self.mature=True
        self.material_target=self.mass()
        self.support.fill(0);self.support[self.body>0]=self.cfg.old_cell_support
        self.struct_elig.fill(0);self.chem.fill(0);self.age.fill(0);self.age[self.body>0]=99
        self.tips=[];self.dev_tick=0;self.last_reward=0.0
        self.field_solves=self.reconnections=self.extensions=self.retractions=self.branches=self.initiations=0
        self.field_power=[]
        self.reset_fast(clear_traces=True)

    # ---------------- explicit quasi-static extracellular solve ----------------
    def solve_extracellular(self, current_source):
        """Solve (-sigma Laplacian + screen) Ve = I_tm with Ve=0 on boundary."""
        s=np.asarray(current_source,np.complex128).copy()
        # Grounded finite bath can carry net current, but subtracting the interior
        # mean prevents a global DC offset from dominating the tiny lattice.
        interior=s[1:-1,1:-1]
        interior=interior-interior.mean()
        sh=dstn(interior,type=1,norm='ortho')
        vh=sh/self._poisson_denom
        vi=idstn(vh,type=1,norm='ortho')
        v=np.zeros_like(s);v[1:-1,1:-1]=vi
        return v

    @staticmethod
    def field_from_potential(v):
        ex=-.5*(shift(v,0,-1)-shift(v,0,1))
        ey=-.5*(shift(v,-1,0)-shift(v,1,0))
        return ex,ey

    def _accumulate_explicit_field(self, lap, source, mode='coherent'):
        c=self.cfg
        # Axial-current divergence is an explicit local source/sink density for
        # extracellular current. Imposed terminal injection is included explicitly.
        src = np.zeros_like(self.psi) if isinstance(source,(float,int)) else source
        itm=(c.tm_axial_gain*(-c.stiffness*lap)+c.tm_source_gain*src)*self.body
        ve=self.solve_extracellular(itm);ex,ey=self.field_from_potential(ve);self.field_solves+=1
        mag=np.sqrt(np.abs(ex)**2+np.abs(ey)**2).astype(np.float32)
        sc=np.quantile(mag,.98)+1e-10; mag_n=np.clip(mag/sc,0,1)
        self.field_power.append(float(np.mean(mag*mag)))

        # Same magnitude chemistry for coherent, reversed, scrambled and magnitude arms.
        # The no-field arm receives neither extracellular chemistry nor vector guidance.
        a=c.chemistry_decay
        if mode=='none':
            self.chem*=a;self.H=self.chem.copy()
            self.Gx*=c.phase_trace_decay;self.Gy*=c.phase_trace_decay
            return
        self.chem=a*self.chem+(1-a)*mag_n
        self.H=self.chem.copy()

        if mode=='magnitude':
            self.Gx*=c.phase_trace_decay;self.Gy*=c.phase_trace_decay
            return

        ref=self.psi[self.soma]
        if abs(ref)<1e-9:
            self.Gx*=c.phase_trace_decay;self.Gy*=c.phase_trace_decay;return
        ref=ref/(abs(ref)+1e-12)
        if mode=='phase_scramble':
            rot=np.exp(1j*self._phase_rng.uniform(-math.pi,math.pi));ex=ex*rot;ey=ey*rot
        elif mode=='phase_reverse':
            ex=-ex;ey=-ey
        gx=np.real(ex*np.conj(ref)).astype(np.float32);gy=np.real(ey*np.conj(ref)).astype(np.float32)
        gs=np.quantile(np.sqrt(gx*gx+gy*gy),.98)+1e-10;gx/=gs;gy/=gs
        a=c.phase_trace_decay;self.Gx=a*self.Gx+(1-a)*gx;self.Gy=a*self.Gy+(1-a)*gy

    def _accumulate_activity(self):
        c=self.cfg;amp=np.abs(self.vel).astype(np.float32)*self.body
        vals=amp[amp>0];sc=np.quantile(vals,.95)+1e-10 if vals.size else 1.
        use=np.clip(amp/sc,0,1);self.E=c.eligibility_decay*self.E+(1-c.eligibility_decay)*use
        self.struct_elig=c.structural_elig_decay*self.struct_elig+(1-c.structural_elig_decay)*use

    def advance(self,source=0.0,accumulate=True,mature=None,guidance_mode='coherent'):
        c=self.cfg;lap=self._lap(self.psi,mature)
        self.vel += c.dt*(c.stiffness*lap-c.damping*self.vel-c.restoring*self.psi+source)
        self.psi += c.dt*self.vel;self.psi=self.psi/(1+c.saturation*np.abs(self.psi)**2)
        if accumulate:
            self._accumulate_activity()
            if self.field_solves % max(c.field_stride,1)==0:
                self._accumulate_explicit_field(lap,source,guidance_mode)
        return float(np.abs(self.psi[self.soma])**2)

    def drive_sequence(self,lag=None,mode='coherent',steps=None):
        """Present A then B with exact equal dose; write activity + extracellular traces."""
        lag=int(self.cfg.developmental_lag if lag is None else lag)
        n=int(steps or self.cfg.developmental_drive_steps)
        self.psi.fill(0);self.vel.fill(0)
        for t in range(n):
            a=self.pulse_source(0,t,False);b=self.pulse_source(1,t-lag,False)
            if isinstance(a,float):src=b
            elif isinstance(b,float):src=a
            else:src=a+b
            self.advance(src,True,True,mode)

    # ---------------- persistent tip primitives ----------------
    def _tip_positions(self):return {tuple(t['pos']) for t in self.tips if t.get('alive',False)}

    def _start_candidates(self):
        d=self.degree4();b=self.body.astype(bool);cand=np.argwhere(b&(d<=2)&(~self.protect))
        return [(int(y),int(x)) for y,x in cand]

    def initiate_tip(self):
        if sum(t.get('alive',False) for t in self.tips)>=self.cfg.max_tips:return False
        cand=self._start_candidates()
        if not cand:return False
        w=np.asarray([.015+float(self.E[p])**self.cfg.start_power for p in cand],float);w/=w.sum()
        p=cand[int(self.rng.choice(len(cand),p=w))]
        self.tips.append({'pos':p,'prev':None,'age':0,'stall':0,'alive':True,'trail':[]})
        self.initiations+=1;return True

    def _direction_weight(self,tip,dest,mode):
        c=self.cfg;py,px=tip['pos'];dy=dest[0]-py;dx=dest[1]-px
        w=1.0
        if mode!='none':w*=.10+c.cone_chem_gain*float(self.chem[dest])
        if mode in ('coherent','phase_scramble','phase_reverse'):
            gx=float(self.Gx[py,px]);gy=float(self.Gy[py,px]);gn=math.hypot(gx,gy)+1e-9
            w*=math.exp(np.clip(c.cone_steer_beta*(gx*dx+gy*dy)/gn,-4,4))
        prev=tip.get('prev')
        if prev is not None:
            pdy=py-prev[0];pdx=px-prev[1];pn=math.hypot(pdy,pdx)+1e-9
            w*=math.exp(c.tip_persistence_beta*(pdy*dy+pdx*dx)/pn)
        return max(w,1e-9)

    def extend_tip(self,tip,mode='coherent'):
        if not tip.get('alive',False):return {'event':'dead'}
        cur=tuple(tip['pos']);opts=[];weights=[]
        for q in n4(*cur,*self.body.shape):
            if not self.window[q] or self.body[q]:continue
            contacts=[r for r in n4(*q,*self.body.shape) if self.body[r] and r!=cur]
            # A single old-arbor contact is a natural reconnection. More than one is
            # rejected to keep one-cell events local and interpretable.
            if len(contacts)>1:continue
            opts.append((q,contacts));weights.append(self._direction_weight(tip,q,mode))
        if not opts:
            tip['stall']+=1
            if tip['stall']>=self.cfg.tip_stall_limit:tip['alive']=False
            return {'event':'stall','pos':cur}
        w=np.asarray(weights,float);w/=w.sum();q,contacts=opts[int(self.rng.choice(len(opts),p=w))]
        self.body[q]=1;self.age[q]=0;self.support[q]=self.cfg.new_cell_support;self.struct_elig[q]=1.0
        old=cur;tip['prev']=old;tip['pos']=q;tip['trail'].append(q);tip['age']+=1;tip['stall']=0
        self.extensions+=1
        event='extend'
        if contacts:
            tip['alive']=False;self.reconnections+=1;event='reconnect'
        elif self.rng.random()<self.cfg.tip_branch_prob and sum(t.get('alive',False) for t in self.tips)<self.cfg.max_tips:
            self.tips.append({'pos':q,'prev':old,'age':0,'stall':0,'alive':True,'trail':[]});self.branches+=1
        return {'event':event,'from':old,'to':q,'contacts':contacts}

    def apply_credit(self,reward):
        c=self.cfg;self.last_reward=float(np.clip(reward,-1,1))
        b=self.body.astype(bool)
        self.support[b]*=c.support_decay
        self.support[b]+=c.activity_support*np.clip(self.E[b],0,1)
        young=b&(self.age<=c.new_cell_grace+3)
        self.support[young]+=c.chemistry_support*np.clip(self.chem[young],0,1)
        self.support[b]+=c.credit_support*self.last_reward*np.clip(self.struct_elig[b],0,1)
        self.support=np.clip(self.support,0,1)

    def age_tick(self):
        b=self.body.astype(bool);self.age[b]=np.minimum(self.age[b]+1,32000);self.struct_elig*=self.cfg.structural_elig_decay
        self.tips=[t for t in self.tips if t.get('alive',False) and self.body[tuple(t['pos'])]]

    def _safe_remove_candidates(self):
        b=self.body.astype(bool);active=self._tip_positions();out=[]
        for yy,xx in np.argwhere(b):
            p=(int(yy),int(xx))
            if self.protect[p] or p in active or self.age[p]<=self.cfg.new_cell_grace:continue
            test=self.body.copy();test[p]=0
            if int(self.connected_component(test).sum())==int(test.sum()) and self.both_connected(test):out.append(p)
        return out

    def retract_one(self):
        cand=self._safe_remove_candidates()
        if not cand:return None
        # Low trophic support retracts first; stochastic softmin avoids a hidden
        # deterministic route rule.
        s=np.asarray([float(self.support[p]) for p in cand],float);T=max(self.cfg.prune_temperature,1e-5)
        z=np.exp(-(s-s.min())/T);z/=z.sum();p=cand[int(self.rng.choice(len(cand),p=z))]
        self.body[p]=0;self.support[p]=0;self.struct_elig[p]=0;self.chem[p]*=.5;self.retractions+=1
        return p

    def structural_tick(self,mode='coherent'):
        """One developmental tick: local growth first; homeostatic retraction separately."""
        events=[]
        if not any(t.get('alive',False) for t in self.tips) or self.rng.random()<self.cfg.tip_initiate_prob:
            if self.initiate_tip():events.append({'event':'initiate'})
        alive=[t for t in self.tips if t.get('alive',False)]
        if alive:
            tip=alive[int(self.rng.integers(len(alive)))];events.append(self.extend_tip(tip,mode))
        # Material debt is repaid by an independent trophic retraction process.
        if self.mass()>self.material_target:
            p=self.retract_one();events.append({'event':'retract','pos':p})
        self.age_tick();self.dev_tick+=1
        assert self.both_connected()
        return events

    def settle_mass(self,max_steps=200):
        k=0
        while self.mass()>self.material_target and k<max_steps:
            if self.retract_one() is None:break
            self.age_tick();k+=1
        return self.mass()==self.material_target

    def state_receipt(self):
        return dict(stats=self.branch_stats(),mass=self.mass(),target_mass=self.material_target,
                    active_tips=sum(t.get('alive',False) for t in self.tips),extensions=self.extensions,
                    reconnections=self.reconnections,retractions=self.retractions,branches=self.branches,
                    initiations=self.initiations,field_solves=self.field_solves,
                    mean_field_power=float(np.mean(self.field_power)) if self.field_power else 0.0)
