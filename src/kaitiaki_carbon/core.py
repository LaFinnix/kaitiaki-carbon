"""Core carbon-estimation engine for kaitiaki-carbon.

This module adapts the vendored NSVB math (in ``kaitiaki_carbon.nsvb``)
to a clean public API: ``estimate_carbon(parcel) -> CarbonEstimate``.

We use NSVB's vectorised Polars pipeline (``compute_nsvb_biomass``) and
pre-join the columns it expects (``CULL``, ``WDSG``, ``JENKINS_SPGRPCD``).
For v0.1, ``WDSG`` and ``JENKINS_SPGRPCD`` use mid-range defaults;
species-specific values land in v0.2 when the NZ species table lands.

Limitations (v0.1):
  - Default wood density (WDSG) of 0.42 g/cm³. Species-specific WDSG
    lookup deferred to v0.2 (when the NZ-context species table lands).
  - Default Jenkins species-group ID for all trees. v0.2: per-species.
  - Single carbon fraction per parcel (species of the first tree).
    v0.2: per-tree species-specific carbon via Polars join.
  - Analytic 95% CI from per-tree biomass variance. v0.2: NSVB-faithful
    variance propagation (Westfall GTR-WO-104 §6).
  - NZ-context species mapping deferred to v0.2 (FIA SPCD codes used
    as-is; Jenkins fallback handles unknowns gracefully).

See docs/UPSTREAM.md for the lineage.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

import polars as pl

from kaitiaki_carbon.nsvb.carbon_fractions import DEFAULT_LIVE_CARBON_FRACTION, get_carbon_fraction_live
from kaitiaki_carbon.nsvb.coefficients import VectorizedLookupTables, get_vectorized_lookup_tables
from kaitiaki_carbon.nsvb.equations import compute_nsvb_biomass


# Hardwood / softwood threshold per the FIA SPCD scheme.
_HARDWOOD_SPCD_THRESHOLD = 300


@dataclass
class CarbonEstimate:
    """A biomass → carbon estimate for one parcel.

    Units: ``*_per_ha`` are in metric tonnes / hectare; total figures
    are in metric tonnes. Carbon is total above-ground; below-ground
    biomass is **not yet** included (deferred to v0.2 with the upstream
    ``pyfia.carbon.live_tree`` belowground bridge).

    Lifecycle: immutable. Recompute to update.
    """

    parcel_id: str
    area_ha: float
    estimate_per_ha_tCO2e: float
    estimate_total_tCO2e: float
    method: str
    ci_95_pct_per_ha: tuple[float, float] = (0.0, 0.0)
    ci_95_pct_total: tuple[float, float] = (0.0, 0.0)
    tree_count: int = 0
    species_count: int = 0
    unknown_species: tuple[int, ...] = ()

    def to_wire_format(self) -> dict[str, Any]:
        """Render as a JSON-compatible dict for downstream systems."""
        lo_per_ha, hi_per_ha = self.ci_95_pct_per_ha
        lo_total, hi_total = self.ci_95_pct_total
        return {
            "parcel_id": self.parcel_id,
            "area_ha": self.area_ha,
            "estimate_per_ha_tCO2e": self.estimate_per_ha_tCO2e,
            "estimate_total_tCO2e": self.estimate_total_tCO2e,
            "ci_95_pct": {
                "per_ha": [lo_per_ha, hi_per_ha],
                "total": [lo_total, hi_total],
            },
            "method": self.method,
            "tree_count": self.tree_count,
            "species_count": self.species_count,
            "unknown_species": list(self.unknown_species),
        }


# Lookup vectorised tables once at module import. NSVB's loader
# caches all 5 component tables (above-ground biomass, bark, branch,
# foliage, stem-volume), each keyed on SPCD + (optional) DIVISION /
# STDORGCD. For v0.1 we use the species-level fallback (DIVISION=null,
# STDORGCD=null) which works for our non-FIADB inputs.
_LOOKUP: VectorizedLookupTables | None = None


def _get_lookup() -> VectorizedLookupTables:
    """Lazy loader for the NSVB vectorised lookup tables."""
    global _LOOKUP
    if _LOOKUP is None:
        _LOOKUP = get_vectorized_lookup_tables()
    return _LOOKUP


def _build_trees_frame(parcel_trees: list[dict[str, Any]]) -> pl.DataFrame:
    """Build the Polars DataFrame NSVB expects.

    NSVB's ``compute_nsvb_biomass`` requires ``UPPERCASE`` column
    names. It also expects ``CULL``, ``WDSG``, and ``JENKINS_SPGRPCD``
    to be present for the left-joins to succeed. We materialise the
    data eagerly (not as a LazyFrame) so we can re-think the shape
    before handing it to NSVB.

    For v0.1, ``WDSG`` uses a mid-range default of 0.42 g/cm³.
    Species-specific WDSG landing in v0.2 when the NZ species table
    is added.
    """
    rows: list[dict[str, Any]] = []
    spcds: list[int] = []
    for t in parcel_trees:
        spcd = int(t["spcd"])
        dia = float(t["dia"])
        ht = float(t["ht"])
        if ht <= 0.0:
            ht = 1.0  # NSVB requires HT > 0; default to 1m
        cull = float(t.get("cull", 0.0))
        # NSVB expects UPPERCASE column names.
        rows.append({
            "SPCD": spcd,
            "DIA": dia,
            "HT": ht,
            "STATUSCD": int(t.get("statuscd", 1)),
            "CULL": cull,
            "WDSG": 0.42,  # v0.1 default — v0.2 species-specific lookup
            # JENKINS_SPGRPCD is required for the Jenkins Model 5
            # fallback join to succeed even when a species-level
            # entry exists. Setting it to 1 covers ~all softwood
            # Jenkins groups; v0.2 will use a per-SPCD mapping.
            "JENKINS_SPGRPCD": 1,
        })
        spcds.append(spcd)
    return pl.DataFrame(rows)


def estimate_carbon(parcel: dict[str, Any], **kwargs: Any) -> CarbonEstimate:
    """Estimate stored carbon for a parcel.

    The ``parcel`` dict must contain:

      - ``id`` (or ``parcel_id``): a string label
      - ``area_ha``: total parcel area in hectares (must be > 0)
      - ``trees``: a list of normalised per-tree records. Each record:

        - ``spcd``: FIA species code (NZ-mapping deferred to v0.2)
        - ``dia``: diameter at breast height in centimetres
        - ``ht``: total tree height in metres
        - (optional) ``statuscd``: 1 = live, 2 = dead. Defaults to live.
        - (optional) ``cull``: cull percentage (0-100). Defaults to 0.

    Returns a CarbonEstimate with per-hectare + total tCO2e, plus a
    coarse 95% CI from the per-tree biomass variance.
    """
    parcel_id = (
        parcel.get("id")
        or parcel.get("parcel_id")
        or kwargs.get("parcel_id", "parcel-unknown")
    )
    area_ha = float(parcel.get("area_ha", 0.0))
    if area_ha <= 0.0:
        raise ValueError(
            "parcel.area_ha must be > 0; v0.2 will compute from GeoJSON."
        )

    trees: list[dict[str, Any]] = parcel.get("trees", [])
    species_seen: set[int] = {int(t["spcd"]) for t in trees} if trees else set()

    if not trees:
        return CarbonEstimate(
            parcel_id=parcel_id,
            area_ha=area_ha,
            estimate_per_ha_tCO2e=0.0,
            estimate_total_tCO2e=0.0,
            method="kaitiaki-carbon-v0.1-nsvb (no trees)",
            ci_95_pct_per_ha=(0.0, 0.0),
            ci_95_pct_total=(0.0, 0.0),
            tree_count=0,
            species_count=0,
        )

    lookup = _get_lookup()
    trees_df = _build_trees_frame(trees)

    # Run NSVB. This returns the per-tree biomass components as a
    # Polars LazyFrame. For unknown SPCD, the Jenkins Model 5 fallback
    # kicks in automatically via the left-join on JENKINS_SPGRPCD.
    trees_lf = trees_df.lazy()
    biomass_lf = compute_nsvb_biomass(trees=trees_lf, lookup=lookup)
    biomass_df = biomass_lf.collect()

    # Apply per-tree species-specific carbon fraction.
    # For v0.1 we use the species of the first tree as a representative
    # sample. v0.2 will compute per-species carbon-fraction joins via
    # ``data.join(carbon_fractions.lazy(), on="SPCD", how="left")``.
    if species_seen:
        representative_species = next(iter(species_seen))
        try:
            carbon_fraction = get_carbon_fraction_live(spcd=representative_species)
        except Exception:
            carbon_fraction = DEFAULT_LIVE_CARBON_FRACTION
    else:
        carbon_fraction = DEFAULT_LIVE_CARBON_FRACTION

    # Identify trees that NSVB couldn't resolve (NaN or zero agb = unknown SPCD).
    unknown_species: set[int] = set()
    if "agb" in biomass_df.columns:
        missing_mask = (
            biomass_df["agb"].is_null() | (biomass_df["agb"] == 0)
        )
        if missing_mask.any() and "SPCD" in biomass_df.columns:
            unknown_species = {
                int(s) for s in biomass_df.filter(missing_mask)["SPCD"].unique().to_list()
            }

    # NSVB outputs an "agb" column — total above-ground biomass in
    # kg dry matter per tree. Use it directly.
    if "agb" not in biomass_df.columns:
        return CarbonEstimate(
            parcel_id=parcel_id,
            area_ha=area_ha,
            estimate_per_ha_tCO2e=0.0,
            estimate_total_tCO2e=0.0,
            method="kaitiaki-carbon-v0.1-nsvb (no agb output)",
            ci_95_pct_per_ha=(0.0, 0.0),
            ci_95_pct_total=(0.0, 0.0),
            tree_count=len(trees),
            species_count=0,
            unknown_species=tuple(sorted(unknown_species)),
        )

    # Filter to trees with non-zero biomass (others we drop as unknowns).
    valid_df = biomass_df.filter(pl.col("agb") > 0)
    if valid_df.is_empty():
        return CarbonEstimate(
            parcel_id=parcel_id,
            area_ha=area_ha,
            estimate_per_ha_tCO2e=0.0,
            estimate_total_tCO2e=0.0,
            method="kaitiaki-carbon-v0.1-nsvb (all trees failed)",
            ci_95_pct_per_ha=(0.0, 0.0),
            ci_95_pct_total=(0.0, 0.0),
            tree_count=len(trees),
            species_count=0,
            unknown_species=tuple(sorted(unknown_species)),
        )

    total_biomass_kg = float(valid_df["agb"].sum())
    tree_biomass_values = valid_df["agb"].to_list()
    total_carbon_kg = total_biomass_kg * carbon_fraction

    # tCO2e = tC × (44 / 12)
    kg_to_t = 1 / 1000
    tCO2e_total = total_carbon_kg * kg_to_t * (44 / 12)
    tCO2e_per_ha = tCO2e_total / area_ha

    # Coarse 95% CI from per-tree biomass variance.
    if len(tree_biomass_values) > 1:
        mean_b = statistics.mean(tree_biomass_values)
        sd_b = statistics.stdev(tree_biomass_values)
        se_b = sd_b / math.sqrt(len(tree_biomass_values))
        ci_b_low = max(0.0, mean_b - 1.96 * se_b)
        ci_b_high = mean_b + 1.96 * se_b
        ci_total = (
            ci_b_low * len(tree_biomass_values) * carbon_fraction * kg_to_t * (44 / 12),
            ci_b_high * len(tree_biomass_values) * carbon_fraction * kg_to_t * (44 / 12),
        )
        ci_per_ha = (ci_total[0] / area_ha, ci_total[1] / area_ha)
    else:
        ci_per_ha = (tCO2e_per_ha, tCO2e_per_ha)
        ci_total = (tCO2e_total, tCO2e_total)

    return CarbonEstimate(
        parcel_id=parcel_id,
        area_ha=area_ha,
        estimate_per_ha_tCO2e=tCO2e_per_ha,
        estimate_total_tCO2e=tCO2e_total,
        method="kaitiaki-carbon-v0.1-nsvb",
        ci_95_pct_per_ha=ci_per_ha,
        ci_95_pct_total=ci_total,
        tree_count=len(tree_biomass_values),
        species_count=len(species_seen),
        unknown_species=tuple(sorted(unknown_species)),
    )


__all__ = ["CarbonEstimate", "estimate_carbon"]
