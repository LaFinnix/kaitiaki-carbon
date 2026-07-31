"""Stub for the carbon-estimation core.

The full body of this file will be replaced in Phase 1 with the
forked biomass-to-carbon math from `mihiarc/pyfia` (MIT licensed).
This stub keeps the public API surface stable while Phase 0 ships.

Public API (stable across the Phase 1 swap):

    from kaitiaki_carbon.core import (
        CarbonEstimate,
        estimate_carbon,
    )

The mathematics: biomass (t dry matter / ha) is converted to
above-ground carbon (tC / ha) via a carbon fraction (default 0.5,
per IPCC); then to CO2-equivalent via molecular-weight ratio (44/12).
Uncertainty (95% CI) is propagated from the input plot-count and
species-mix assumptions.

In Phase 1 this entire module will be replaced with the forked pyfia
content. Until then, this stub raises NotImplementedError so any
accidental import surfaces an obvious failure rather than a silent
zero estimate.

See NOTICE for the upstream attribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CarbonEstimate:
    """A biomass → carbon estimate for one parcel.

    Fields match the wire format used downstream (NZ ETS exports,
    voluntary market submissions, research papers).

    Lifecycle: a CarbonEstimate is immutable. Recompute to update.

    Units: all "per hectare" values are in metric tonnes. The
    `total_tCO2e`, `tCO2e_total_low_pct`, and `tCO2e_total_high_pct`
    fields are the parcel total in tCO2-equivalent; `*_per_ha`
    fields are the same quantity divided by parcel area.
    """

    parcel_id: str
    area_ha: float
    estimate_per_ha_tCO2e: float
    estimate_total_tCO2e: float
    method: str
    ci_95_pct_per_ha: tuple[float, float] = (0.0, 0.0)
    ci_95_pct_total: tuple[float, float] = (0.0, 0.0)

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
        }


def estimate_carbon(parcel: dict[str, Any], **kwargs: Any) -> CarbonEstimate:
    """Estimate stored carbon for a GeoJSON parcel.

    The full implementation arrives in Phase 1 (pyfia fork). Until
    then this stub raises so a stray call surfaces loudly rather than
    silently producing a misleading zero.
    """
    raise NotImplementedError(
        "estimate_carbon is the Phase 1 pyfia fork; not yet implemented. "
        "See docs/UPSTREAM.md for the lineage and docs/iwi-engagement.md "
        "for the consultation rules."
    )


__all__ = ["CarbonEstimate", "estimate_carbon"]
