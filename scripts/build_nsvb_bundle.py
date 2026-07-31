"""Generate a JSON bundle of NSVB coefficients for the TypeScript port.

The Python implementation reads coefficients from CSV files at runtime
(via Polars). For the TypeScript port inside the anamata-kahui platform,
we need a static JSON bundle that loads instantly with `import json`.

This script reads all the CSVs in src/kaitiaki_carbon/nsvb/data/ and
emits a single `nsvb-coefficients.json` file. The TypeScript code will
import this JSON and look up coefficients the same way the Python code
does, but with O(1) Map access instead of a Polars join.

Output:
  kaitiaki-carbon-platform-bundle/2026-07-31-nsvb-coefficients.json
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "src" / "kaitiaki_carbon" / "nsvb" / "data"
OUT_DIR = Path("/opt/data/Repos/kaitiaki-carbon-platform-bundle")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "2026-07-31-nsvb-coefficients.json"


def load_csv(name: str) -> list[dict]:
    """Read one NSVB coefficient CSV into a list of row dicts."""
    with open(DATA / name, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Cast numeric columns
            for k, v in row.items():
                if v is None or v == "":
                    row[k] = None
                    continue
                try:
                    if "." in v or "e" in v.lower():
                        row[k] = float(v)
                    else:
                        row[k] = int(v)
                except (ValueError, TypeError):
                    row[k] = v
            rows.append(row)
    return rows


def _split_by_tier(rows: list[dict]) -> dict:
    """Split a *_spcd rows list into the 4 NSVB precedence tiers.

    Tiers:
      * 0 (DIV+STDORG): DIVISION non-null AND STDORGCD non-null
      * 1a (DIV only):  DIVISION non-null AND STDORGCD null
      * 1b (STDORG only): DIVISION null AND STDORGCD non-null
      * 3 (SPCD only):  DIVISION null AND STDORGCD null

    Each tier keeps the same row shape; the TypeScript port implements
    the precedence chain: try tier 0, then 1a, then 1b, then 3.
    """
    out = {"divorg": [], "div": [], "org": [], "spcd": []}
    for r in rows:
        div = r.get("DIVISION")
        stdorg = r.get("STDORGCD")
        if div is not None and stdorg is not None:
            out["divorg"].append(r)
        elif div is not None:
            out["div"].append(r)
        elif stdorg is not None:
            out["org"].append(r)
        else:
            out["spcd"].append(r)
    return out


def build_bundle() -> dict:
    """Build the complete NSVB coefficient bundle."""
    # Split each *_spcd table into 4 precedence tiers.
    volib = _split_by_tier(load_csv("volib_spcd.csv"))
    volbk = _split_by_tier(load_csv("volbk_spcd.csv"))
    bark = _split_by_tier(load_csv("bark_biomass_spcd.csv"))
    branch = _split_by_tier(load_csv("branch_biomass_spcd.csv"))
    total = _split_by_tier(load_csv("total_biomass_spcd.csv"))

    return {
        # SPCD-specific tables split by NSVB precedence tier.
        # The TypeScript port walks tier 0 → 1a → 1b → 3.
        "volib_divorg": volib["divorg"],
        "volib_div": volib["div"],
        "volib_org": volib["org"],
        "volib_spcd": volib["spcd"],
        "volbk_divorg": volbk["divorg"],
        "volbk_div": volbk["div"],
        "volbk_org": volbk["org"],
        "volbk_spcd": volbk["spcd"],
        "bark_bio_divorg": bark["divorg"],
        "bark_bio_div": bark["div"],
        "bark_bio_org": bark["org"],
        "bark_bio_spcd": bark["spcd"],
        "branch_bio_divorg": branch["divorg"],
        "branch_bio_div": branch["div"],
        "branch_bio_org": branch["org"],
        "branch_bio_spcd": branch["spcd"],
        "total_agb_divorg": total["divorg"],
        "total_agb_div": total["div"],
        "total_agb_org": total["org"],
        "total_agb_spcd": total["spcd"],
        # Jenkins-group fallback tables
        "volib_jenkins": load_csv("volib_jenkins.csv"),
        "volbk_jenkins": load_csv("volbk_jenkins.csv"),
        "bark_biomass_jenkins": load_csv("bark_biomass_jenkins.csv"),
        "branch_biomass_jenkins": load_csv("branch_biomass_jenkins.csv"),
        "total_biomass_jenkins": load_csv("total_biomass_jenkins.csv"),
        # Carbon fractions
        "carbon_fraction_live": load_csv("carbon_fraction_live.csv"),
        "carbon_fraction_dead": load_csv("carbon_fraction_dead.csv"),
        # Metadata
        "meta": {
            "source": "USDA Forest Service GTR-WO-104 (Westfall et al. 2023)",
            "vendored_from": "https://github.com/mihiarc/pyfia",
            "license": "Public domain (US Government work)",
            "carbon_fraction_default": 0.4741,
            "co2e_per_c_ratio": 44.0 / 12.0,  # 1 tC → 3.667 tCO2e
            "kg_per_pound": 0.45359237,
            "k_softwood": 9.0,
            "k_hardwood": 11.0,
            "hardwood_spcd_threshold": 300,
            "cull_dens_prop": {"hardwood": 0.54, "softwood": 0.92},
            "cull_default": 0.0,
            "min_dia_inches": 1.0,
        },
    }


def main() -> None:
    bundle = build_bundle()
    # Count rows per table for verification
    sizes = {k: len(v) for k, v in bundle.items() if isinstance(v, list)}
    print("Bundle row counts:")
    for k, n in sizes.items():
        print(f"  {k}: {n}")
    print(f"  meta: {len(bundle['meta'])} keys")

    with open(OUT, "w") as f:
        json.dump(bundle, f, separators=(",", ":"))
    print(f"\nWrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()