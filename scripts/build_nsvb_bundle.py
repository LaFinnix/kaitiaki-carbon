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


def build_bundle() -> dict:
    """Build the complete NSVB coefficient bundle."""
    return {
        # SPCD-specific tables
        "volib_spcd": load_csv("volib_spcd.csv"),
        "volbk_spcd": load_csv("volbk_spcd.csv"),
        "bark_biomass_spcd": load_csv("bark_biomass_spcd.csv"),
        "branch_biomass_spcd": load_csv("branch_biomass_spcd.csv"),
        "total_biomass_spcd": load_csv("total_biomass_spcd.csv"),
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