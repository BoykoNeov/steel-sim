"""1-D conservative parabolic (diffusion / heat) solver — the spine of the trio.

Public API (frozen at the end of Steel Phase 1a — see CONTRACT.md):

    from engines.diffusion import (
        Diffusion1D, Grid, uniform_grid, grid_from_edges,
        Dirichlet, Neumann, Robin,
    )
"""
from .diffusion1d import (
    Diffusion1D,
    Grid,
    uniform_grid,
    grid_from_edges,
    Dirichlet,
    Neumann,
    Robin,
)

__all__ = [
    "Diffusion1D",
    "Grid",
    "uniform_grid",
    "grid_from_edges",
    "Dirichlet",
    "Neumann",
    "Robin",
]
