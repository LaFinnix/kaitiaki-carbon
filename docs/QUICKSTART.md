# Quickstart

> Step-by-step walkthrough of running `kaitiaki-carbon estimate` end-to-end.

This walks through the canonical scenario:

1. A user has a **parcel** (a piece of whenua they kaitiaki).
2. They have an **inventory** (a list of trees + geometry).
3. They want a **carbon estimate** with an **iwi attestation**.

If you're just exploring, the CLI examples below are sufficient. For
production use you'll want to wire `estimate_carbon` into your own
inventory system.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run with the example fixture

```bash
# 1. Estimate (no attestation — raw number)
kaitiaki-carbon estimate tests/fixtures/parcel_auckland_radiata.geojson
# →  Wārā waro: 25.4 tCO2e (95% CI [18.3, 32.4])
```

For te reo Māori output:

```bash
kaitiaki-carbon estimate tests/fixtures/parcel_auckland_radiata.geojson \
    --attestation tests/fixtures/attestation/ngai-tahu-rakaipaaka.json \
    --locale mi
# →  E tatau ana...
#    Wārā waro: 25.4 tCO2e (95% CI [18.3, 32.4])
#    I taupātia e Ngāi Tahu (Kāti Huirapa), kaitiaki: Te Rūnanga o Ōtākou.
```

## Inputs

### Parcel: a GeoJSON Feature

A GeoJSON Feature with a Polygon + a `properties.trees` list:

```json
{
  "type": "Feature",
  "id": "my-parcel",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], [lon, lat], ...]]
  },
  "properties": {
    "trees": [
      {"spcd": 131, "dia": 30.0, "ht": 25.0, "statuscd": 1,
       "species_name": "radiata-pine"}
    ]
  }
}
```

The estimator auto-computes `area_ha` from the polygon.

### Attestation: a JSON file

An attestation binds the estimate to a kaitiaki body. See
[`docs/ATTESTATION-SCHEMA.md`](ATTESTATION-SCHEMA.md) for the schema.
The minimal example in `tests/fixtures/attestation/blank.json`:

```json
{
  "iwi": "Ngāi Tahu",
  "kaitiaki": "Te Rūnanga o Ōtākou"
}
```

Worked examples:

- `tests/fixtures/attestation/ngai-tahu-rakaipaaka.json` — full example
- `tests/fixtures/attestation/ngai-tahu-tuawhenua.json` — papakāinga-scope example
- `tests/fixtures/attestation/blank.json` — minimal

### Per-tree fields

| Field | Required | Notes |
|---|---|---|
| `spcd` | ✅ | FIA species code (NZ mapping is in `kaitiaki_carbon.species_nz`) |
| `dia` | ✅ | Diameter at breast height (cm) |
| `ht` | ✅ | Total tree height (m); defaults to 1m if missing |
| `species_name` | optional | NZ-context name; resolves to species-specific WDSG |
| `statuscd` | optional | 1 = live, 2 = dead. Defaults to live. |
| `cull` | optional | 0-100. Defaults to 0. |
| `wdsg` | optional | Override wood density (g/cm³). Defaults to species table or 0.42. |

## Output (verbose)

```bash
kaitiaki-carbon estimate tests/fixtures/parcel_auckland_radiata.geojson \
    --attestation tests/fixtures/attestation/ngai-tahu-rakaipaaka.json \
    --verbose
```

The `--verbose` flag prints the full wire-format JSON, including the
iwi attestation overlay.

## Programmatically (Python)

```python
import json
from kaitiaki_carbon.geojson import parse_parcel
from kaitiaki_carbon.attest import validate_attestation
from kaitiaki_carbon.attribution import attach_attestation
from kaitiaki_carbon import estimate_carbon

# Step 1: parse the GeoJSON Feature into our normalised parcel dict
with open("tests/fixtures/parcel_auckland_radiata.geojson") as f:
    parcel = parse_parcel(json.load(f))

# Step 2: load the iwi attestation
with open("tests/fixtures/attestation/ngai-tahu-rakaipaaka.json") as f:
    att = validate_attestation(json.load(f))

# Step 3: estimate carbon
estimate = estimate_carbon(parcel)

# Step 4: overlay the attestation
attributed = attach_attestation(estimate, att)

# Step 5: emit + persist
attributed.to_wire_format()
# → {estimate: {...}, attestation: {...}, schema_version: "0.1.0", ...}
```

## NZ ETS export (scaffolding)

For NZ Emissions Trading Scheme removals reporting, use
`emit_ets_record()`:

```python
from kaitiaki_carbon.nz_ets import emit_ets_record

record = emit_ets_record(
    attributed,
    facility="NZ-ET-12345",
    reporting_period="2026",
    species_composition=[
        {"spcd": 131, "species_name": "radiata-pine", "fraction_of_basal_area": 1.0},
    ],
)
```

The output is a JSON-compatible dict. The actual NZ-ETS API endpoint +
auth is environment-configured.

## Inventories you'll need

Real forestry inventories typically have one of:

- **Per-tree plot data** (FIA / NZ Forest Research formats) — convert each
  row to our `{"spcd", "dia", "ht", "species_name"}` shape.
- **Stand-level averages** (mean DBH, mean height) — replicate by the
  estimated stem count to get per-tree entries.
- **NDVI-derived biomass** — combine with field plot validation; v0.2
  adds an `ndvi` ingestion path.

When converting from a non-standard format, the key invariants
are:

1. SPCD matches the FIA scheme (or use `species_name` for NZ mapping).
2. DIA is cm, HT is m.
3. STATUSCD is 1 (live) for what you want counted in removals.

## Next steps

- Read [`docs/UPSTREAM.md`](UPSTREAM.md) for the vendored-NSVB lineage.
- Read [`docs/iwi-engagement.md`](iwi-engagement.md) before changing the
  attestation schema.
- Read [`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md) for the math
  chain.
