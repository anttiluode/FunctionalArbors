from dataclasses import dataclass, asdict

@dataclass
class Config:
    size: int = 64
    seed: int = 0
    device: str = 'cpu'  # numpy implementation; kept for CLI compatibility

    # Geometry / drive
    n_patches: int = 4
    patch_radius_frac: float = 0.35
    patch_sigma: float = 3.0
    root_sigma: float = 2.2
    dwell: int = 64
    pulse_frames: int = 12
    carrier_omega: float = 0.42
    source_amp: float = 0.55

    # Fast complex field
    dt: float = 0.12
    diffusion: float = 1.0  # wave stiffness multiplier (legacy name retained)
    dispersion: float = 0.0
    damping: float = 0.075
    restoring: float = 0.18  # on-site spring; removes the static-displacement zero mode
    saturation: float = 0.002

    # Conductivity: permissive embryo -> structure-dependent mature arbor
    dev_base_k: float = 0.34
    dev_structure_k: float = 0.80
    dev_final_base_k: float = 0.055
    dev_final_structure_k: float = 1.85
    mature_base_k: float = 0.010
    mature_structure_k: float = 2.50
    structure_power: float = 1.35
    substrate_noise: float = 0.12

    # Growth opportunity / exposed interface
    root_radius: float = 3.0
    solid_threshold: float = 0.36
    opportunity_iters: int = 22
    opportunity_relax: float = 0.60
    growth_eta: float = 3.0
    growth_pressure_floor: float = 0.02

    # Local eligibility + soma credit
    eligibility_decay: float = 0.90
    eligibility_gain: float = 0.50
    eligibility_power: float = 0.75
    reward_gain: float = 3.0
    reward_clip: float = 1.5
    credit_strength: float = 2.5

    # Development protocol
    train_cycles: int = 18
    material_budget_per_event: float = 0.85
    edge_margin: int = 3
    probe_cycles: int = 4
    settle_frames: int = 48

    # Lesion/regrowth
    lesion_fraction_of_mass: float = 0.06
    lesion_inner_frac: float = 0.18
    lesion_outer_frac: float = 0.95
    regrow_cycles: int = 8

    def as_dict(self):
        return asdict(self)
