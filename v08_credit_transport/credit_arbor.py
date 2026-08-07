from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import deque
import numpy as np

try:
    from v07_persistent_ephaptic.persistent_arbor import V07Config, PersistentEphapticArbor
    from v06_ephaptic_growth.ephaptic_arbor import shift, n4
except ImportError:
    from ..v07_persistent_ephaptic.persistent_arbor import V07Config, PersistentEphapticArbor
    from ..v06_ephaptic_growth.ephaptic_arbor import shift, n4


@dataclass
class V08Config(V07Config):
    # Delayed credit carriers. v0.7 wave/field/growth parameters are inherited.
    # Grace exceeds typical distal graph transit so retrograde credit is not
    # defeated before it can physically arrive.
    new_cell_grace: int = 18
    global_credit_delay: int = 2
    global_credit_gain: float = 0.28
    retrograde_credit_gain: float = 0.48
    retrograde_decay: float = 0.975
    trophic_credit_gain: float = 0.42
    trophic_diffusion: float = 0.16
    trophic_decay: float = 0.93
    hybrid_scale: float = 0.60

    def as_dict(self):
        return asdict(self)


class CreditTransportArbor(PersistentEphapticArbor):
    """Exact v0.7 arbor plus explicit delayed soma->structure credit carriers.

    No proposal/guidance physics is changed here. `drive_sequence`, the grounded
    quasi-static extracellular solve, persistent tip extension/branching, and
    connectivity-safe retraction all come directly from v0.7.
    """
    def __init__(self, cfg: V08Config | None = None):
        super().__init__(cfg or V08Config())
        self.cfg: V08Config
        self.trophic_credit = np.zeros_like(self.support, np.float32)
        self.global_credit_queue = []
        self.retrograde_packets = []
        self.credit_deliveries = 0
        self.credit_mass = 0.0
        self.credit_localization = []
        self._credit_rng = np.random.default_rng(self.cfg.seed + 808_808)

    def copy(self):
        z = CreditTransportArbor(V08Config(**self.cfg.as_dict()))
        z.body = self.body.copy()
        z.morph = self.morph.copy()
        z.mature = self.mature
        z.material_target = self.material_target
        return z

    def prepare_development(self):
        super().prepare_development()
        self.trophic_credit.fill(0)
        self.global_credit_queue = []
        self.retrograde_packets = []
        self.credit_deliveries = 0
        self.credit_mass = 0.0
        self.credit_localization = []

    def graph_distance_from_soma(self):
        b = self.body.astype(bool)
        d = np.full(b.shape, -1, np.int16)
        if not b[self.soma]:
            return d
        q = deque([self.soma]); d[self.soma] = 0
        while q:
            p = q.popleft(); nd = int(d[p]) + 1
            for r in n4(*p, *b.shape):
                if b[r] and d[r] < 0:
                    d[r] = nd; q.append(r)
        return d

    def background_support_tick(self):
        """Apply v0.7 support/chemistry dynamics with zero instantaneous reward."""
        super().apply_credit(0.0)

    def launch_credit(self, reward, carrier):
        r = float(np.clip(reward, -1, 1))
        if carrier == 'none' or abs(r) < 1e-12:
            return
        b = self.body.astype(bool)
        snap = self.struct_elig.copy()
        if carrier == 'global':
            self.global_credit_queue.append({'delay': int(self.cfg.global_credit_delay), 'reward': r})
        elif carrier in ('retrograde', 'scrambled_retrograde', 'hybrid'):
            es = snap.copy()
            if carrier == 'scrambled_retrograde':
                vals = es[b].copy(); self._credit_rng.shuffle(vals); es.fill(0); es[b] = vals
            self.retrograde_packets.append({
                'age': 0, 'reward': r, 'distance': self.graph_distance_from_soma(),
                'eligibility': es, 'carrier': carrier,
            })
        if carrier in ('trophic', 'hybrid'):
            self.trophic_credit[self.soma] += r

    def _record_credit(self, delta, eligibility):
        a = np.abs(delta)
        mass = float(a.sum())
        if mass <= 0:
            return
        self.credit_mass += mass
        self.credit_deliveries += 1
        self.credit_localization.append(float((a * np.clip(eligibility, 0, 1)).sum() / (mass + 1e-12)))

    def transport_credit_tick(self, carrier):
        c = self.cfg; b = self.body.astype(bool)

        # v0.7-like delayed global scalar, gated by CURRENT eligibility.
        keep = []
        for ev in self.global_credit_queue:
            ev['delay'] -= 1
            if ev['delay'] <= 0:
                delta = c.global_credit_gain * ev['reward'] * np.clip(self.struct_elig, 0, 1) * b
                self.support += delta.astype(np.float32)
                self._record_credit(delta, self.struct_elig)
            else:
                keep.append(ev)
        self.global_credit_queue = keep

        # Retrograde packet: one graph edge per developmental tick. Crucially it
        # carries the eligibility SNAPSHOT that existed when the soma consequence
        # was computed, rather than consulting a later decayed trace.
        keep = []
        for ev in self.retrograde_packets:
            ev['age'] += 1
            ring = (ev['distance'] == ev['age']) & b
            if ring.any():
                scale = c.retrograde_credit_gain * (c.retrograde_decay ** ev['age'])
                if ev['carrier'] == 'hybrid':
                    scale *= c.hybrid_scale
                delta = np.zeros_like(self.support)
                delta[ring] = scale * ev['reward'] * np.clip(ev['eligibility'][ring], 0, 1)
                self.support += delta
                self._record_credit(delta, ev['eligibility'])
            if ev['age'] <= int(ev['distance'].max()) + 1:
                keep.append(ev)
        self.retrograde_packets = keep

        # Signed soma-origin trophic field in the slow 2-D bath. Structural
        # eligibility gates its effect locally; the carrier itself is not told A/B.
        if carrier in ('trophic', 'hybrid') or np.any(np.abs(self.trophic_credit) > 1e-10):
            f = self.trophic_credit
            lap = shift(f,1,0)+shift(f,-1,0)+shift(f,0,1)+shift(f,0,-1)-4*f
            self.trophic_credit = (c.trophic_decay*f + c.trophic_diffusion*lap).astype(np.float32)
            gain = c.trophic_credit_gain * (c.hybrid_scale if carrier == 'hybrid' else 1.0)
            delta = gain * self.trophic_credit * np.clip(self.struct_elig,0,1) * b
            self.support += delta.astype(np.float32)
            self._record_credit(delta, self.struct_elig)

        self.support[:] = np.clip(self.support, 0, 1)

    def credit_receipt(self):
        return dict(
            credit_deliveries=int(self.credit_deliveries),
            credit_mass=float(self.credit_mass),
            mean_credit_localization=float(np.mean(self.credit_localization)) if self.credit_localization else 0.0,
            queued_global=len(self.global_credit_queue),
            queued_retrograde=len(self.retrograde_packets),
            trophic_mass=float(np.abs(self.trophic_credit).sum()),
        )
