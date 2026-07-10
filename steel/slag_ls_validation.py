"""Holdout PROBE of the cited C_S→L_S conversion against measured sulfur distribution (front-end B3, sulfur metal-partition leg).

*Does :mod:`steel.slag`'s capacity→metal-partition conversion — the step that turns a validated sulfide
capacity ``C_S`` into the sulfur distribution ratio ``L_S = (%S)_slag/[%S]_metal`` that
:func:`steel.slag.desulfurize` actually uses — carry out-of-sample, or is its "order-of-magnitude only"
posture forced?* This is the **sulfur twin of** :mod:`steel.slag_lp_validation`: the C_S leg (ADR 0006)
holdout-validated the *capacity* ``C_S`` (gas–slag), and the two L_P legs (ADR 0007/0008) graded the
*phosphorus* metal-partition — but **L_S, the sulfur metal-partition the pipeline computes, was never
graded**. It reads :func:`steel.slag.sulfur_partition`; it touches no engine and fits nothing.

WHAT THE CONVERSION ADDS (the piece under test). ``sulfide_capacity`` gives ``C_S`` from optical
basicity; ``sulfur_partition`` then applies ``log L_S = log C_S − log a_O − 770/T + 1.30`` — the metal
side of ``[S] + (O²⁻) = (S²⁻) + [O]``. The **−log a_O** term (the mirror of Healy's +2.5·log %Fe_t) is
the module's headline desulfurization physics, and it is *only* introduced here. So an L_S holdout is
the only thing that tests whether that reducing dependence is right in **magnitude**, not just sign.

THE a_O-PROVENANCE GATE (why this dataset, and why almost no other). The whole point of L_S is the
``−log a_O`` term, so the test is clean **only if the metal oxygen is set independently** — not
back-derived from a deoxidation equilibrium ([Al]/[O], [Si]/[O]), which would import an external deox
model into the exact term under test (the L_S analog of the carbon-saturation strawman ADR 0008
rejected). That rules out most ladle-metallurgy L_S data (Al-killed, a_O from [Al]–[O]). The clean
shape is **controlled-atmosphere gas–slag–metal equilibration**, where pO₂ (hence a_O) is fixed by the
gas — the exact analog of Nzotta's gas–slag method that made the C_S leg clean.

THE HOLDOUT. Mohassab-Ahmed, Sohn & Kim measured L_S between MgO-saturated CaO–FeO–Al₂O₃–SiO₂ slag and
**liquid low-carbon iron** under **H₂/H₂O/SO₂, CO/CO₂/H₂/H₂O and CO/CO₂ gas mixtures** at 1550–1650 °C,
with pO₂ (**hence a_O**) fixed by the gas phase and computed by HSC — an independent oxygen lever, the
gate passed. Published peer-reviewed (*Ind. Eng. Chem. Res.* **51** (2012) 3639, DOI 10.1021/ie201970r;
*Steel Research Int.* **86** (2015) 753); the tabulated data used here is from the open PhD dissertation
Y. Mohassab, *Phase Equilibria between Iron and Slag in CO/CO₂/H₂/H₂O Atmospheres Relevant to a Novel
Flash Ironmaking Technology* (Univ. of Utah, 2013; collections.lib.utah.edu/ark:/87278/s6mp8bdj),
Chapter 4, Tables 4-1/4-2 (36 H₂/H₂O heats) and Table 4-3 (20 heats across the three atmospheres). The
dissertation is **All Rights Reserved**, so — unlike the CC-BY-NC-ND sources — its PDF is **cited and
transcribed, not committed** (numerical data are facts; the transcription guards below stand in for
"primary source in hand"). Independence: measured 2012–13 at Utah, decades after the 1970 Healy / 1986
Sosinsky–Sommerville fits, and neither correlation reads any Mohassab number.

WHY THIS IS A **PROBE**, NOT A "VALIDATION" — three structural confounds the data cannot separate
(computed before framed — the ADR-0008 discipline; see :func:`summary`):

1. **The conversion is inseparable from the C_S baseline, which is itself unvalidated here.** The
   graded number is the whole chain ``Λ → C_S → (−log a_O) → L_S``. The C_S leg validated ``C_S`` only
   for **FeO-free** basic slags (Nzotta Table 6); these slags carry **10–53 % FeO**, whose Duffy–Ingram
   Λ = 1.00 is the *fitted* value the C_S leg was careful to exclude. So any L_S residual is a sum of
   C_S-baseline error and conversion error that **cannot be apportioned** to either.
2. **The −log a_O slope cannot be isolated.** In gas-controlled equilibration the slag **FeO is set by
   the gas**, so pO₂ and FeO co-vary — and FeO is a *basic* oxide (Λ = 1.00). The desulfurization
   ``−log a_O`` penalty and FeO's basicity benefit are structurally coupled; there are no
   matched-composition/different-pO₂ pairs. (This is the **desulfurization analog of the L_P
   single-temperature confound** — the term one wants to test co-varies with composition in *all* clean
   data. Both B3 residual gaps hit the same wall.)
3. **A chunk of the absolute offset is a standard-state artifact, not the engine.** The conversion's
   ``+1.30`` constant embeds an oxygen standard-state term; reconstructing a_O from pO₂ uses an
   *independent* Fe–O equilibrium constant (:data:`_DG_O_A`/`_DG_O_B`, Sigworth–Elliott). A mismatch
   between the two is a **constant method offset** — which is exactly why the gas-a_O grade and the
   engine's own FeO-anchor grade (:func:`metal_oxygen_for_feo`) differ by ~×2. So the *magnitude* of
   the bias is not trustworthy; only its **direction and order of magnitude** are.

THE VERDICT THE DATA GIVES (computed, not asserted — see :func:`summary`): **a probe that CONFIRMS the
engine's "order-of-magnitude only" posture for the C_S→L_S conversion across a new (BF-slag) regime, and
does NOT upgrade it** (unlike C_S). Concretely:

  * **Order-of-magnitude, with a systematic under-prediction on the clean-a_O reducing set.** On the 8
    **waterless CO/CO₂** heats (dilute metal S ⇒ ``f_S ≈ 1`` well satisfied — the cleanest subset) the
    full chain under-predicts L_S by a **factor of several**, and *both* a_O methods agree on the
    direction (gas-a_O and the FeO-anchor both land low). The 36 **H₂/H₂O** heats (an oxidizing
    supplement, ``a_O`` up to ~0.18 %) straddle unity but carry a **broken ``f_S``** ([S] = 5–12 wt %,
    SO₂-imposed) — so they are shown, not headlined. Across both regimes the agreement is
    order-of-magnitude — matching :mod:`steel.slag`'s existing L_S posture in a *new* regime (BF slags,
    moderate basicity, higher oxygen) than the ladle anchor it was written for.
  * **A signed atmosphere edge — the paper's own result, and the reason the H₂/H₂O subset is
    disqualified for grading.** At matched pO₂/basicity/T the **measured** L_S rises
    ``CO/CO₂ (≈1.0) → CO/CO₂/H₂/H₂O (≈2.3) → H₂/H₂O (≈5.0)`` — water dissolving in the slag lowers the
    sulfide activity coefficient ``f_S²⁻`` (Mohassab, Figs 4-8/4-9). The engine has **no atmosphere
    term**, so it cannot see this — which is *why* the clean grade uses the **waterless CO/CO₂** subset
    and treats H₂/H₂O as a supplement, not a matched-condition engine failure (a real ladle is not
    under a controlled H₂/H₂O atmosphere).
  * **A clean side-finding on the shared-axis anchor.** ``metal_oxygen_for_feo`` (the ``a_FeO ≈ X_FeO``
    Raoultian bridge from slag FeO to metal oxygen) sits ~×2 **below** the gas-equilibrium a_O across
    the set — a located order-of-magnitude bias in the anchor, from Raoultian FeO activity under-reading
    the positive deviation of FeO in these basic slags.

CITED vs CALIBRATED. *Cited:* every measured number (Mohassab 2013 Ch. 4), the S–S ``C_S`` +
conversion + Duffy–Ingram Λ (from :mod:`steel.slag`, unchanged), and the Sigworth–Elliott Fe–O
equilibrium used only to put pO₂ on the a_O axis. *Calibrated:* **nothing** — this study fits no
parameter; it scores the existing model. The decision it informs (keep the conversion unchanged; leave
L_S **order-of-magnitude**, now probed across a second regime; record the atmosphere and anchor edges)
is in ADR 0009.

Run headless (prints the grading + the verdict):

    python -m steel.demo_slag_ls_validation
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from .kinetics import ABS_ZERO
from .slag import Slag, metal_oxygen_for_feo, sulfide_capacity, sulfur_partition

# --------------------------------------------------------------------------- #
# 0. Provenance
# --------------------------------------------------------------------------- #
HOLDOUT_SOURCE = ("Y. Mohassab, 'Phase Equilibria between Iron and Slag in CO/CO2/H2/H2O Atmospheres "
                  "Relevant to a Novel Flash Ironmaking Technology', PhD dissertation, Univ. of Utah "
                  "(2013), Ch. 4, Tables 4-1/4-2/4-3 (open: collections.lib.utah.edu/ark:/87278/s6mp8bdj; "
                  "All Rights Reserved → data transcribed + cited, PDF NOT committed). Peer-reviewed loci: "
                  "Mohassab-Ahmed, Sohn, Kim, Ind. Eng. Chem. Res. 51 (2012) 3639 (DOI 10.1021/ie201970r); "
                  "Mohassab & Sohn, Steel Research Int. 86 (2015) 753.")
MODEL_UNDER_TEST = ("Sosinsky-Sommerville C_S → metal partition (steel.slag): "
                    "log L_S = log C_S − log a_O − 770/T + 1.30, L_S = (%S)_slag/[%S]_metal; a_O from "
                    "gas pO2 via 1/2 O2 = [O] (Sigworth-Elliott). Reads no gas-atmosphere term.")

# 1/2 O2(g) = [O]_(1 wt% Henrian):  ΔG° = _DG_O_A + _DG_O_B·T  (J/mol, Sigworth & Elliott 1974).
# a_O = [%O] = K·pO2^0.5 with log10 K = −ΔG°/(2.303·R·T). Used ONLY to place the gas pO2 on the a_O axis
# the conversion reads; a DIFFERENT oxygen standard-state constant than the one folded into the +1.30 of
# sulfur_partition, so the ABSOLUTE bias carries a constant method offset (a named limit — see docstring).
_DG_O_A = -117152.0
_DG_O_B = -2.887
_R = 8.314

# Di-crosscheck: one Table 4-1 row (S8) is internally inconsistent in the SOURCE itself (printed
# (S)=2.03, [%S]=6.21, Log(Ls)=-0.10 → but log10(2.03/6.21)=-0.49), verified against the rendered PDF.
# It is excluded from HOLDOUT_H2O (an unresolvable source typo is dropped, not baked); recorded here so
# the exclusion is a pinned fact, not a silent omission.
SOURCE_INCONSISTENT_ROW = "S8"

# The measured metal S is dilute in Table 4-3 (f_S ≈ 1) but NOT in Table 4-1 (5-12 wt%, SO2-imposed):
# the threshold below which a heat is treated as clean-f_S for the headline grade.
_DILUTE_S_MAX_PCT = 1.0

# Transcription tolerances (NOT physics). The Table-4-1 Log(Ls) self-consistency (its three chemistry
# columns are chemically linked: Log Ls = log10[(S)/[S]]); the oxide-column sum band (MgO-saturated slags
# carry analytical closure ~100-112, so the band is loose — a dropped/duplicated-column catch, not a
# closure check).
_LOGLS_TOL = 0.02
_OXIDE_SUM_LO = 93.0
_OXIDE_SUM_HI = 114.0


# --------------------------------------------------------------------------- #
# 1. The measured points (transcribed from the rendered dissertation PDF — Tables 4-1 & 4-3, NOT figures)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SulfurPoint:
    """One measured sulfur-distribution datum from Mohassab 2013 Ch. 4.

    ``atmosphere`` is the controlling gas (``"H2/H2O"`` / ``"CO/CO2"`` / ``"mix"``) — the axis the engine
    is blind to. ``pO2`` (atm) fixes the metal oxygen independently (the a_O-provenance gate). The oxide
    fields are the tabulated slag **mass %** (Healy/S–S read them directly). ``ls`` is the measured
    ``(%S)_slag/[%S]_metal``. ``s_metal`` is the tabulated metal [%S] where given (Table 4-1 only — used by
    the Log(Ls) self-consistency guard; ``None`` for Table 4-3, which tabulates L_S directly).
    """

    label: str
    atmosphere: str
    T_K: float
    pO2: float
    CaO: float
    SiO2: float
    FeO: float
    MgO: float
    Al2O3: float
    s_slag: float          # (%S) in slag, mass %
    ls: float              # measured L_S = (%S)_slag / [%S]_metal
    s_metal: float | None  # [%S] in metal, mass % (Table 4-1 only)

    @property
    def T_C(self) -> float:
        return self.T_K - ABS_ZERO

    @property
    def log_ls(self) -> float:
        return math.log10(self.ls)

    @property
    def dilute(self) -> bool:
        """Metal S dilute enough that f_S ≈ 1 holds (Table 4-3); False for the SO2-loaded Table 4-1 heats."""
        ref = self.s_metal if self.s_metal is not None else self.s_slag / self.ls
        return ref <= _DILUTE_S_MAX_PCT


def _t41(label, T_C, s_slag, FeO, MgO, CaO, Al2O3, SiO2, s_metal, log_ls, pO2):
    """A Table 4-1 row (H2/H2O; ls from the tabulated Log(Ls); metal [S] carried for the guard)."""
    return SulfurPoint(label, "H2/H2O", T_C + ABS_ZERO, pO2, CaO, SiO2, FeO, MgO, Al2O3,
                       s_slag, 10.0 ** log_ls, s_metal)


def _t43(label, atm, T_C, pO2, s_slag, FeO, MgO, CaO, Al2O3, SiO2, ls):
    """A Table 4-3 row (three atmospheres; L_S tabulated directly, no metal [S] column)."""
    return SulfurPoint(label, atm, T_C + ABS_ZERO, pO2, CaO, SiO2, FeO, MgO, Al2O3, s_slag, ls, None)


# --- Table 4-1 + 4-2: 36 H2/H2O heats, pO2 by gas ratio (the oxidizing supplement, f_S broken) ------- #
# pO2 (atm) from Table 4-2, keyed to sample groups: (T, group) → pO2.
HOLDOUT_H2O: tuple = (
    _t41("S1", 1550, 1.55, 25.3, 17.3, 20.7, 6.26, 29.8, 11.9, -0.89, 2.2e-9),
    _t41("S2", 1550, 2.72, 35.4, 12.9, 20.6, 6.72, 24.6, 6.11, -0.35, 2.2e-9),
    _t41("S3", 1550, 2.88, 33.1, 11.7, 26.3, 7.81, 28.5, 7.16, -0.40, 2.2e-9),
    _t41("S4", 1550, 4.77, 41.3, 10.8, 21.5, 6.20, 21.0, 6.03, -0.10, 2.2e-9),
    _t41("S5", 1550, 0.93, 21.6, 19.2, 20.9, 8.74, 28.3, 7.15, -0.89, 7.0e-10),
    _t41("S6", 1550, 1.01, 19.9, 20.2, 23.0, 7.99, 33.0, 6.96, -0.84, 7.0e-10),
    _t41("S7", 1550, 1.85, 22.3, 15.2, 29.8, 9.48, 26.4, 7.79, -0.62, 7.0e-10),
    # S8 is EXCLUDED: the dissertation's own row is internally inconsistent — it prints (S)=2.03,
    # [%S]=6.21, Log(Ls)=-0.10, but log10(2.03/6.21) = -0.49 (a printed-column typo; the twin row S4,
    # also Log Ls -0.10, has (S)/[S]=0.79 so which column is wrong is unresolvable). The Log(Ls)
    # self-consistency guard catches it (:data:`SOURCE_INCONSISTENT_ROW`) — di-crosscheck: an
    # unresolvable source inconsistency is dropped, not baked. Verified against the rendered PDF (my
    # transcription is faithful; the source itself is inconsistent). Costs nothing — S8 is one of 36
    # oxidizing-supplement heats, not in the clean CO/CO2 grade.
    _t41("S9", 1550, 1.08, 11.5, 22.4, 24.9, 8.18, 32.3, 11.2, -1.02, 1.1e-10),
    _t41("S10", 1550, 1.34, 12.0, 18.7, 29.0, 9.71, 29.9, 9.67, -0.86, 1.1e-10),
    _t41("S11", 1550, 1.56, 12.4, 17.0, 30.9, 10.7, 29.0, 9.32, -0.78, 1.1e-10),
    _t41("S12", 1550, 2.16, 14.2, 14.5, 34.7, 9.82, 31.0, 9.38, -0.64, 1.1e-10),
    _t41("S13", 1550, 0.81, 12.2, 22.5, 25.1, 9.41, 32.6, 8.43, -1.02, 2.4e-10),
    _t41("S14", 1550, 1.20, 12.6, 16.9, 27.4, 8.77, 39.7, 8.28, -0.84, 2.4e-10),
    _t41("S15", 1550, 2.27, 18.7, 15.4, 34.7, 10.2, 16.4, 8.42, -0.57, 2.4e-10),
    _t41("S16", 1550, 1.72, 15.3, 16.3, 32.4, 10.4, 28.4, 9.49, -0.74, 2.4e-10),
    _t41("S17", 1600, 4.17, 41.1, 15.1, 15.8, 6.15, 19.5, 6.85, -0.22, 4.8e-9),
    _t41("S18", 1600, 3.44, 34.6, 13.6, 20.4, 7.37, 24.4, 6.69, -0.29, 4.8e-9),
    _t41("S19", 1600, 4.81, 42.8, 11.3, 18.1, 6.25, 17.0, 5.59, -0.06, 4.8e-9),
    _t41("S20", 1600, 5.26, 52.8, 12.4, 14.9, 4.90, 12.2, 4.99, 0.02, 4.8e-9),
    _t41("S21", 1600, 1.31, 20.4, 22.6, 20.7, 7.55, 27.7, 10.2, -0.89, 1.8e-9),
    _t41("S21b", 1600, 2.12, 20.3, 22.6, 20.7, 8.63, 27.6, 6.08, -0.46, 1.8e-9),
    _t41("S22", 1600, 2.52, 27.1, 15.7, 22.7, 8.24, 23.5, 9.42, -0.57, 1.8e-9),
    _t41("S22b", 1600, 1.66, 27.0, 17.6, 22.6, 8.23, 23.2, 8.24, -0.69, 1.8e-9),
    _t41("S23", 1600, 3.55, 29.7, 14.2, 26.2, 8.77, 22.0, 9.20, -0.41, 1.8e-9),
    _t41("S23b", 1600, 2.37, 29.7, 14.2, 23.7, 8.34, 22.0, 8.83, -0.57, 1.8e-9),
    _t41("S24", 1600, 4.46, 31.1, 14.7, 24.9, 7.93, 21.7, 10.1, -0.35, 1.8e-9),
    _t41("S25", 1600, 0.78, 8.7, 25.5, 24.3, 9.71, 36.0, 5.60, -0.85, 2.7e-10),
    _t41("S26", 1600, 1.17, 9.3, 21.2, 27.1, 9.83, 31.5, 5.30, -0.66, 2.7e-10),
    _t41("S27", 1600, 1.80, 11.8, 18.7, 29.1, 10.1, 28.2, 7.45, -0.62, 2.7e-10),
    _t41("S28", 1600, 2.48, 13.2, 19.4, 31.0, 9.89, 23.9, 6.26, -0.40, 2.7e-10),
    _t41("S29", 1600, 1.02, 7.1, 23.9, 23.9, 9.62, 31.5, 8.56, -0.92, 5.3e-10),
    _t41("S30", 1600, 1.77, 14.7, 20.9, 25.5, 9.55, 28.9, 9.71, -0.74, 5.3e-10),
    _t41("S31", 1600, 1.97, 14.9, 25.3, 25.2, 8.90, 23.6, 9.37, -0.68, 5.3e-10),
    _t41("S37", 1650, 1.34, 32.6, 20.5, 17.8, 7.62, 23.5, 4.85, -0.56, 4.2e-9),
    _t41("S38", 1650, 4.15, 47.5, 14.2, 13.5, 5.52, 16.3, 4.71, -0.06, 4.2e-9),
)

# --- Table 4-3: 20 heats, three atmospheres, slag II (BF-like), DILUTE metal S (f_S ≈ 1) ------------- #
# Columns as rendered: label, gas, T, pO2, CaO/SiO2, (S), FeO, MgO, CaO, Al2O3, SiO2, Ls.
HOLDOUT_CO: tuple = (      # the WATERLESS subset — the clean-a_O grade
    _t43("R46", "CO/CO2", 1550, 1.6e-10, 0.046, 35.5, 10.2, 24.5, 13.9, 22.8, 0.96),
    _t43("R48", "CO/CO2", 1550, 1.6e-10, 0.051, 16.9, 26.2, 26.3, 15.0, 23.6, 0.56),
    _t43("R49", "CO/CO2", 1600, 3.6e-10, 0.057, 14.7, 22.1, 25.7, 15.2, 31.9, 0.46),
    _t43("R50", "CO/CO2", 1600, 3.6e-10, 0.068, 16.9, 16.9, 28.5, 15.2, 29.4, 1.42),
    _t43("R51", "CO/CO2", 1600, 3.6e-10, 0.059, 15.3, 14.7, 30.7, 16.6, 26.7, 1.42),
    _t43("R52", "CO/CO2", 1630, 6.4e-10, 0.064, 13.7, 15.7, 24.7, 23.4, 32.9, 1.86),
    _t43("R53", "CO/CO2", 1630, 6.4e-10, 0.061, 14.6, 14.3, 28.0, 17.0, 36.4, 0.93),
    _t43("R54", "CO/CO2", 1630, 6.4e-10, 0.047, 26.4, 14.8, 25.2, 14.3, 27.4, 0.62),
)
HOLDOUT_MIX: tuple = (     # CO/CO2/H2/H2O (partial water) — the atmosphere ladder's middle rung
    _t43("R10", "mix", 1550, 1.9e-9, 0.057, 21.7, 24.6, 20.3, 13.0, 25.5, 1.33),
    _t43("R19", "mix", 1550, 1.6e-10, 0.039, 10.1, 24.4, 26.2, 16.3, 34.8, 1.60),
    _t43("R20", "mix", 1550, 1.6e-10, 0.057, 9.8, 17.9, 30.7, 8.4, 31.8, 1.96),
    _t43("R21", "mix", 1550, 1.6e-10, 0.044, 10.8, 16.8, 33.5, 18.8, 29.8, 2.54),
    _t43("R22", "mix", 1600, 3.6e-10, 0.040, 13.0, 23.4, 26.0, 15.7, 32.3, 2.96),
    _t43("R23", "mix", 1600, 3.6e-10, 0.043, 12.7, 19.2, 30.0, 17.0, 30.9, 2.74),
    _t43("R24", "mix", 1600, 3.6e-10, 0.044, 12.4, 16.6, 32.8, 17.2, 28.6, 3.27),
    _t43("R27", "mix", 1630, 6.4e-10, 0.044, 11.2, 19.2, 30.1, 17.0, 30.5, 2.04),
)
HOLDOUT_H2_T43: tuple = (  # H2/H2O rows of Table 4-3 — the top rung (water raises L_S)
    _t43("R74", "H2/H2O", 1550, 1.6e-10, 0.052, 9.9, 20.7, 34.9, 5.1, 27.8, 3.84),
    _t43("R75", "H2/H2O", 1550, 1.6e-10, 0.075, 9.6, 19.7, 31.2, 17.1, 32.1, 3.33),
    _t43("R78", "H2/H2O", 1600, 3.6e-10, 0.041, 10.5, 16.1, 33.7, 17.7, 29.5, 7.78),
    _t43("R'78", "H2/H2O", 1600, 3.6e-10, 0.046, 9.5, 16.9, 33.8, 18.1, 29.6, 4.88),
)

# The atmosphere ladder (Table 4-3, matched pO2/basicity/T across the three gas mixtures).
ATMOSPHERE_LADDER = {"CO/CO2": HOLDOUT_CO, "mix": HOLDOUT_MIX, "H2/H2O": HOLDOUT_H2_T43}

# Everything, for the guards.
HOLDOUT: tuple = HOLDOUT_H2O + HOLDOUT_CO + HOLDOUT_MIX + HOLDOUT_H2_T43


# --------------------------------------------------------------------------- #
# 2. The transcription guards (di-crosscheck — the dissertation table is a rendered PDF image)
# --------------------------------------------------------------------------- #
def validate_logls_consistency(points: tuple = HOLDOUT_H2O, tol: float = _LOGLS_TOL) -> list:
    """Table 4-1: the tabulated Log(Ls) must equal log₁₀[(%S)_slag/[%S]_metal] (a three-column chemistry tie).

    ``(%S)``, ``[%S]`` and ``Log(Ls)`` are separate printed columns chemically linked by
    ``Ls = (%S)/[%S]``; recomputing Log Ls from the other two must match to ``tol`` (last-digit rounding).
    A fat-fingered digit in any of the three breaks it. Returns the offending ``(label, recomputed,
    tabulated)`` (empty = all rows consistent). Table 4-3 tabulates Ls directly (no [%S] column), so this
    guard applies to the H₂/H₂O set only; its oxide columns are covered by :func:`validate_oxide_sum`.
    """
    bad = []
    for p in points:
        if p.s_metal is None:
            continue
        recomputed = math.log10(p.s_slag / p.s_metal)
        if abs(recomputed - p.log_ls) > tol:
            bad.append((p.label, recomputed, p.log_ls))
    return bad


def validate_oxide_sum(points: tuple = HOLDOUT, lo: float = _OXIDE_SUM_LO, hi: float = _OXIDE_SUM_HI) -> list:
    """Every row's five oxide columns sum into ``[lo, hi]`` — a dropped/duplicated-column catch.

    The slags are MgO-saturated with analytical closure running ~100–112 %, so the band is deliberately
    loose (it catches a dropped ~10–36 % oxide, not a closure defect). Returns the offending
    ``(label, sum)`` (empty = all rows within the band).
    """
    bad = []
    for p in points:
        s = p.FeO + p.MgO + p.CaO + p.Al2O3 + p.SiO2
        if not (lo <= s <= hi):
            bad.append((p.label, s))
    return bad


# --------------------------------------------------------------------------- #
# 3. The model under test — a_O from gas pO2, then read slag.sulfur_partition
# --------------------------------------------------------------------------- #
def a_O_from_po2(pO2: float, T_celsius: float) -> float:
    """Metal dissolved oxygen a_O = [%O] in equilibrium with gas ``pO2`` (atm) at ``T_celsius`` (Sigworth-Elliott).

    ``1/2 O2(g) = [O]_(1 wt%)``, ``a_O = K·pO2^0.5`` with ``log₁₀ K = −(ΔG°)/(2.303 R T)`` — the
    **independent** oxygen lever (fixed by the gas, not a deox equilibrium) that makes this a clean L_S
    holdout. A different oxygen standard-state constant than the one folded into ``sulfur_partition``'s
    ``+1.30``, so it contributes a constant method offset to the absolute bias (a named limit).
    """
    T_K = T_celsius + ABS_ZERO
    log_K = -(_DG_O_A + _DG_O_B * T_K) / (2.303 * _R * T_K)
    return (10.0 ** log_K) * math.sqrt(pO2)


def slag_from_point(p: SulfurPoint) -> Slag:
    """Reconstruct a :class:`steel.slag.Slag` (wt %) — S–S reads Λ from CaO/SiO₂/FeO/Al₂O₃/MgO.

    The foreign nothing: the slag carries no gas-atmosphere field, because the engine has none — that
    blindness is exactly what the atmosphere edge measures.
    """
    return Slag(CaO=p.CaO, SiO2=p.SiO2, FeO=p.FeO, Al2O3=p.Al2O3, MgO=p.MgO)


def oxygen_ppm_gas(p: SulfurPoint) -> float:
    """The independent (gas-pO₂) metal oxygen in **ppm** — the a_O :func:`sulfur_partition` consumes."""
    return a_O_from_po2(p.pO2, p.T_C) * 1.0e4


def oxygen_ppm_feo(p: SulfurPoint) -> float:
    """The engine's OWN metal oxygen (ppm) from slag FeO (:func:`metal_oxygen_for_feo`) — the anchor cross-check."""
    return metal_oxygen_for_feo(slag_from_point(p), T_celsius=p.T_C)


def predicted_log_ls(p: SulfurPoint, *, from_feo: bool = False) -> float:
    """Model log₁₀ L_S: :func:`steel.slag.sulfur_partition` at the gas-a_O (or the FeO-anchor a_O)."""
    ppm = oxygen_ppm_feo(p) if from_feo else oxygen_ppm_gas(p)
    return math.log10(sulfur_partition(slag_from_point(p), ppm, T_celsius=p.T_C))


# --------------------------------------------------------------------------- #
# 4. Grading (log-residual = bias + scatter; per-atmosphere; the anchor cross-check)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Residual:
    """One point's prediction vs measurement in log₁₀ L_S (the natural metric — L_S spans decades)."""

    label: str
    atmosphere: str
    T_K: float
    pO2: float
    dilute: bool
    predicted: float                # log10 L_S, model (gas-a_O)
    measured: float                 # log10 L_S, experiment
    resid: float                    # predicted − measured (>0 ⇒ model over-predicts)


def residuals(points: tuple, *, from_feo: bool = False) -> list:
    """Per-point :class:`Residual` list (gas-a_O by default; ``from_feo`` for the anchor comparison)."""
    return [
        Residual(p.label, p.atmosphere, p.T_K, p.pO2, p.dilute,
                 predicted_log_ls(p, from_feo=from_feo), p.log_ls,
                 predicted_log_ls(p, from_feo=from_feo) - p.log_ls)
        for p in points
    ]


@dataclass(frozen=True)
class BiasScatter:
    """Pooled magnitude verdict: mean log-residual (bias) and its std (scatter), both as ``×`` factors."""

    n: int
    mean_log: float                 # mean(predicted − measured); ×10**this = systematic bias factor
    std_log: float                  # std of the residual; ×10**this = scatter factor


def bias_scatter(points: tuple, *, from_feo: bool = False) -> BiasScatter:
    """Pooled bias + scatter over ``points`` (the 'how far off, on average' number)."""
    rs = [r.resid for r in residuals(points, from_feo=from_feo)]
    return BiasScatter(len(rs), statistics.mean(rs), statistics.pstdev(rs))


@dataclass(frozen=True)
class AtmosphereRung:
    """One rung of the measured atmosphere ladder — the mean measured log₁₀ L_S under a gas mixture."""

    atmosphere: str
    n: int
    mean_log_ls: float              # mean measured log10 L_S (engine-independent — the paper's own result)


def atmosphere_ladder() -> list:
    """The measured L_S ladder CO/CO₂ → mix → H₂/H₂O (matched pO₂/basicity/T) — the water edge, from data."""
    out = []
    for atm, pts in ATMOSPHERE_LADDER.items():
        logs = [p.log_ls for p in pts]
        out.append(AtmosphereRung(atm, len(logs), statistics.mean(logs)))
    return out


@dataclass(frozen=True)
class AnchorBias:
    """The shared-axis anchor cross-check: gas-equilibrium a_O vs metal_oxygen_for_feo, as a ``×`` factor."""

    n: int
    mean_log_ratio: float           # mean log10(ppm_gas / ppm_feo); >0 ⇒ the FeO anchor reads LOW


def anchor_bias(points: tuple = HOLDOUT) -> AnchorBias:
    """How far ``metal_oxygen_for_feo`` (Raoultian a_FeO≈X_FeO) sits below the independent gas-equilibrium a_O."""
    ratios = [math.log10(oxygen_ppm_gas(p) / oxygen_ppm_feo(p)) for p in points]
    return AnchorBias(len(ratios), statistics.mean(ratios))


# --------------------------------------------------------------------------- #
# 5. The assembled verdict
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Verdict:
    """Everything the demo / figure / tests read — computed from the data, asserted nowhere."""

    co_gas: BiasScatter             # waterless CO/CO2 (Table 4-3), gas-a_O — the CLEAN grade (f_S ≈ 1)
    co_feo: BiasScatter             # waterless CO/CO2, FeO-anchor a_O — direction cross-check
    h2o_gas: BiasScatter            # 36 H2/H2O (Table 4-1), gas-a_O — the oxidizing supplement (f_S broken)
    h2o_feo: BiasScatter            # 36 H2/H2O, FeO-anchor a_O
    ladder: list                    # the measured atmosphere ladder (the water edge)
    anchor: AnchorBias              # metal_oxygen_for_feo vs gas a_O
    logls_consistency_clean: bool   # the Table-4-1 Log(Ls) three-column guard passed
    oxide_sum_clean: bool           # every row's oxides sum into the band


def summary() -> Verdict:
    """Assemble the full verdict (the single entry point the demo and tests consume)."""
    return Verdict(
        co_gas=bias_scatter(HOLDOUT_CO),
        co_feo=bias_scatter(HOLDOUT_CO, from_feo=True),
        h2o_gas=bias_scatter(HOLDOUT_H2O),
        h2o_feo=bias_scatter(HOLDOUT_H2O, from_feo=True),
        ladder=atmosphere_ladder(),
        anchor=anchor_bias(),
        logls_consistency_clean=(len(validate_logls_consistency()) == 0),
        oxide_sum_clean=(len(validate_oxide_sum()) == 0),
    )
