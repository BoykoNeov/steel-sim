"""Steel production simulator — *cooling curve in, microstructure out*.

The flagship project (Steel plan, ``docs/plans/steel-production.md``). It builds &
freezes the diffusion/heat spine (Phase 1a, ``engines.diffusion``) and layers the
Fe-C thermodynamics and transformation kinetics on top.

Phase 1b public API (this module) — metastable Fe–Fe₃C equilibrium:

    from steel.fe_c import (
        phase_fractions, equilibrium_constituents, Constituents,
        A1, A3, Acm,
        C_EUTECTOID, T_EUTECTOID, C_GAMMA_MAX, C_ALPHA_MAX, C_CEMENTITE,
    )
"""
