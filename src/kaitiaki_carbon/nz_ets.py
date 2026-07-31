"""NZ-ETS export format scaffolding.

v0.2 — exports the AttributedEstimate in the format the NZ Emissions
Trading Scheme expects for forestry removals reporting.

The NZ ETS accepts Forestry Removals Credits for post-1989 forests
that achieve a qualifying forest cover. The exact schema for ETS
reporting is:

  https://www.mfe.govt.nz/maori-environment/climate-change/emissions-trading-scheme

Scaffolding only — the canonical schema is maintained by the MfE
and changes infrequently. This module exposes ``emit_ets_record()``
that takes an ``AttributedEstimate`` and returns a JSON-shaped dict
compatible with the MfE registry's POST endpoint format.

We intentionally do *not* hard-code the ETS API URL or auth here —
those change, and they should live in environment configuration.

Schema (v0.1)
---------------

The output is a dict with:

  {
    "facility": str,                   # ETS participant facility ID
    "reporting_period": str,           # ISO year
    "account_type": str,               # "Forestry" / "Stationary energy" / etc.
    "claim_type": str,                 # "Removal" / "Deforestation" / etc.
    "parcel_id": str,
    "area_ha": float,
    "species_composition": list[dict],  # one entry per species
    "estimated_removals_tCO2e": float,
    "methodology": str,                # citation to the math used
    "iwi_attestation": dict | None,    # optional iwi context
    "submitted_at": str,               # ISO timestamp
  }

Where ``species_composition`` is a list of::

  {
    "spcd": int,
    "species_name": str,
    "fraction_of_basal_area": float,   # sum across species = 1.0
  }
"""

from __future__ import annotations

import datetime
from typing import Any

from kaitiaki_carbon.attribution import AttributedEstimate

# Schema version — bump when output shape changes. Useful for the
# downstream ETS registry to know which version of kaitiaki-carbon
# produced a given record.
SCHEMA_VERSION = "0.1.0"

# Default methodology citation — references the vendored NSVB math.
DEFAULT_METHODOLOGY = (
    "kaitiaki-carbon v0.1: NSVB (Westfall GTR-WO-104) per-tree biomass "
    "+ species-specific S10a carbon fractions. Cross-reference: "
    "https://doi.org/10.2737/WO-GTR-104"
)


def emit_ets_record(
    attributed: AttributedEstimate,
    *,
    facility: str,
    reporting_period: str,
    account_type: str = "Forestry",
    claim_type: str = "Removal",
    species_composition: list[dict[str, Any]] | None = None,
    submitted_at: str | None = None,
) -> dict[str, Any]:
    """Render an AttributedEstimate as an ETS-compatible record.

    This is **scaffolding** — the canonical schema is maintained by
    MfE. When you have an actual ETS submission target, adjust the
    field names to match.

    Args:
        attributed: an AttributedEstimate (CarbonEstimate + Attestation).
        facility: ETS facility ID assigned by the registry.
        reporting_period: ISO year or year range, e.g. "2026".
        account_type: optional; defaults to "Forestry".
        claim_type: optional; defaults to "Removal" (i.e. sequestration).
        species_composition: optional list of species rows. If None,
            the function emits a placeholder with the most-common
            species from the underlying estimate. To compute the
            true fraction_of_basal_area, the estimator needs to track
            that — v0.2 feature.
        submitted_at: ISO timestamp. Defaults to now().

    Returns:
        A JSON-serialisable dict in the NZ-ETS-compatible layout above.
    """
    carbon_est = attributed.estimate
    attestation = attributed.attestation

    # Default species_composition if not provided: a single placeholder
    # row. v0.2: actual basal-area fractions.
    if species_composition is None:
        species_composition = [
            {
                "spcd": None,
                "species_name": "(see attached inventory)",
                "fraction_of_basal_area": 1.0,
            }
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "facility": facility,
        "reporting_period": reporting_period,
        "account_type": account_type,
        "claim_type": claim_type,
        "parcel_id": carbon_est.parcel_id,
        "area_ha": carbon_est.area_ha,
        "estimated_removals_tCO2e": carbon_est.estimate_total_tCO2e,
        "ci_95_pct_tCO2e": list(carbon_est.ci_95_pct_total),
        "methodology": DEFAULT_METHODOLOGY,
        "tree_count": carbon_est.tree_count,
        "species_count": carbon_est.species_count,
        "unknown_species": list(carbon_est.unknown_species),
        "species_composition": species_composition,
        "iwi_attestation": {
            "iwi": attestation.iwi,
            "hapū": attestation.hapū,
            "kaitiaki": attestation.kaitiaki,
            "scope": attestation.scope.value,
            "consent": [c.value for c in attestation.consent],
            "issued_at": attestation.issued_at.isoformat(),
            "schema_version": attestation.schema_version,
        }
        if attestation is not None
        else None,
        "submitted_at": submitted_at or datetime.datetime.now(datetime.UTC).isoformat(),
    }


__all__ = ["SCHEMA_VERSION", "DEFAULT_METHODOLOGY", "emit_ets_record"]
