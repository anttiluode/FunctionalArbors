from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import deque
import numpy as np

try:
    from v08_credit_transport.credit_arbor import V08Config, CreditTransportArbor
    from v06_ephaptic_growth.ephaptic_arbor import n4
except ImportError:
    from ..v08_credit_transport.credit_arbor import V08Config, CreditTransportArbor
    from ..v06_ephaptic_growth.ephaptic_arbor import n4


@dataclass
class V09Config(V08Config):
    """v0.9 changes eligibility semantics, not carrier physics."""
    timing_deadband: float = 1.0
    shuffled_age_weight: float = 0.30
    shuffled_distance_weight: float = 1.0

    def as_dict(self):
        return asdict(self)


class CausalEligibilityArbor(CreditTransportArbor):
    """Exact v0.8 retrograde carrier plus explicit structural-event tags.

    v0.8 established that reward can physically return to distal structure and
    alter survival when the correct branch is tagged. v0.9 leaves that carrier
    unchanged and varies only *what spatial eligibility snapshot is attached to
    a reward packet*.
    """
    def __init__(self, cfg: V09Config | None = None):
        super().__init__(cfg or V09Config())
        self.cfg: V09Config
        n = self.cfg.size
        self.birth_tick = np.full((n, n), -10000, np.int32)
        self.competition_events = []
        self.tag_launches = 0
        self.tag_mass = 0.0
        self.tag_kind_mass = {}
        self._tag_rng = np.random.default_rng(self.cfg.seed + 909_909)

    def copy(self):
        z = CausalEligibilityArbor(V09Config(**self.cfg.as_dict()))
        z.body = self.body.copy()
        z.morph = self.morph.copy()
        z.mature = self.mature
        z.material_target = self.material_target
        return z

    def prepare_development(self):
        super().prepare_development()
        self.birth_tick.fill(-10000)
        self.competition_events = []
        self.tag_launches = 0
        self.tag_mass = 0.0
        self.tag_kind_mass = {}
        # Existing bootstrap anatomy is "old"; only subsequent structural events
        # receive a finite birth tick.
        self.birth_tick[self.body > 0] = -1000

    # ---------------- structural event bookkeeping ----------------
    @staticmethod
    def _path_between(body, start, goal):
        b = np.asarray(body, bool)
        start = tuple(start); goal = tuple(goal)
        if start == goal:
            return [start]
        q = deque([start]); prev = {start: None}
        while q:
            p = q.popleft()
            for r in n4(*p, *b.shape):
                if not b[r] or r in prev:
                    continue
                prev[r] = p
                if r == goal:
                    out = [r]
                    while out[-1] != start:
                        out.append(prev[out[-1]])
                    return out[::-1]
                q.append(r)
        return None

    def initiate_tip(self):
        before = len(self.tips)
        ok = super().initiate_tip()
        if ok:
            for t in self.tips[before:]:
                t.setdefault('origin', tuple(t['pos']))
        return ok

    def extend_tip(self, tip, mode='coherent'):
        # Preserve the old body so that a natural reconnection can be decomposed
        # into the new bypass and the old shortcut that it competes with.
        old_body = self.body.copy()
        origin = tuple(tip.get('origin', tuple(tip['pos'])))
        trail_before = [tuple(p) for p in tip.get('trail', [])]
        n_before = len(self.tips)
        ev = super().extend_tip(tip, mode)

        if ev.get('event') in ('extend', 'reconnect') and ev.get('to') is not None:
            p = tuple(ev['to'])
            self.birth_tick[p] = int(self.dev_tick)

            # A child tip created by ordinary branching starts a new structural
            # event chain at the branch point; no detour shape is named.
            for t in self.tips[n_before:]:
                t.setdefault('origin', p)

            if ev.get('event') == 'reconnect' and ev.get('contacts'):
                contact = tuple(ev['contacts'][0])
                old_path = self._path_between(old_body, origin, contact)
                new_cells = []
                for q in trail_before + [p]:
                    if self.body[q] and q != origin and q != contact and q not in new_cells:
                        new_cells.append(q)
                old_cells = []
                if old_path is not None:
                    for q in old_path[1:-1]:
                        if self.body[q] and q not in new_cells:
                            old_cells.append(q)
                self.competition_events.append({
                    'tick': int(self.dev_tick),
                    'origin': origin,
                    'contact': contact,
                    'new': new_cells,
                    'old': old_cells,
                })
        return ev

    def retract_one(self):
        p = super().retract_one()
        if p is not None:
            self.birth_tick[p] = -10000
        return p

    # ---------------- eligibility semantics ----------------
    def activity_tag(self):
        return np.clip(self.struct_elig, 0, 1).astype(np.float32) * self.body

    def event_tag(self, since_tick):
        """Exact cells added since the previous soma evaluation."""
        mask = (self.body > 0) & (self.birth_tick >= int(since_tick))
        out = np.zeros_like(self.support, np.float32)
        out[mask] = 1.0
        return out

    def shuffled_event_tag(self, event_tag):
        """Same number of tags, moved to wrong locations with matched latency/age as closely as possible.

        Matching cost uses current graph distance and cell age. Candidate cells are
        excluded from the true event set and protected soma/source cells. Because
        newborn grace is long in v0.8/v0.9, the optimizer preferentially chooses
        other young cells when such cells exist.
        """
        true_cells = [tuple(p) for p in np.argwhere(event_tag > 0)]
        out = np.zeros_like(event_tag, np.float32)
        if not true_cells:
            return out
        dist = self.graph_distance_from_soma()
        body_cells = [tuple(p) for p in np.argwhere((self.body > 0) & (~self.protect) & (event_tag <= 0))]
        chosen = set()
        for src in true_cells:
            if not body_cells:
                break
            src_age = max(0, int(self.dev_tick) - int(self.birth_tick[src]))
            src_d = int(dist[src])
            scored = []
            for q in body_cells:
                if q in chosen:
                    continue
                bt = int(self.birth_tick[q])
                age = (int(self.dev_tick) - bt) if bt >= 0 else (self.cfg.new_cell_grace + 6)
                cost = (self.cfg.shuffled_distance_weight * abs(int(dist[q]) - src_d) +
                        self.cfg.shuffled_age_weight * abs(age - src_age))
                scored.append((float(cost), self._tag_rng.random(), q))
            if not scored:
                break
            scored.sort(key=lambda z: (z[0], z[1]))
            q = scored[0][2]
            chosen.add(q); out[q] = 1.0
        return out

    def competition_tags(self, since_tick):
        """New bypass versus pre-existing shortcut for reconnect events in this interval."""
        new = np.zeros_like(self.support, np.float32)
        old = np.zeros_like(self.support, np.float32)
        n_events = 0
        for ev in self.competition_events:
            if int(ev['tick']) < int(since_tick):
                continue
            n_events += 1
            for p in ev['new']:
                if self.body[p]: new[p] = 1.0
            for p in ev['old']:
                if self.body[p] and not self.protect[p]: old[p] = 1.0
        return new, old, n_events

    def timing_tags(self, event_tag, desired_lag, measured_edge50):
        """Signed event tag using current early/late transport error.

        The mark remains structural and sparse: only cells born in the current
        evaluation interval are eligible. Source-shared trunk cells are ignored.
        If A-B is too small, a new A-only segment is potentially helpful and a
        new B-only segment potentially harmful; the signs reverse when A-B is too
        large. This is a deliberately stronger candidate eligibility rule, not a
        claim about a known biological molecule.
        """
        err = float(desired_lag) - float(measured_edge50)
        pos = np.zeros_like(event_tag, np.float32)
        neg = np.zeros_like(event_tag, np.float32)
        if abs(err) <= self.cfg.timing_deadband:
            return pos, neg, err
        pa = set(self.path(0) or [])
        pb = set(self.path(1) or [])
        a_only = pa - pb; b_only = pb - pa
        help_a = err > 0
        for p in map(tuple, np.argwhere(event_tag > 0)):
            if p in a_only:
                (pos if help_a else neg)[p] = 1.0
            elif p in b_only:
                (neg if help_a else pos)[p] = 1.0
        return pos, neg, err

    # ---------------- frozen v0.8 retrograde transport, custom tag ----------------
    def launch_tagged_retrograde(self, reward, tag, kind='tag', sign=1.0):
        r = float(np.clip(reward, -1, 1)) * float(sign)
        es = np.clip(np.asarray(tag, np.float32), 0, 1) * self.body
        mass = float(es.sum())
        if abs(r) < 1e-12 or mass <= 0:
            return False
        self.retrograde_packets.append({
            'age': 0,
            'reward': r,
            'distance': self.graph_distance_from_soma(),
            'eligibility': es.copy(),
            'carrier': 'retrograde',
            'kind': kind,
        })
        self.tag_launches += 1
        self.tag_mass += mass
        self.tag_kind_mass[kind] = self.tag_kind_mass.get(kind, 0.0) + mass
        return True

    def tag_receipt(self):
        return {
            'tag_launches': int(self.tag_launches),
            'tag_mass': float(self.tag_mass),
            'tag_kind_mass': dict(self.tag_kind_mass),
            'competition_events': int(len(self.competition_events)),
        }
