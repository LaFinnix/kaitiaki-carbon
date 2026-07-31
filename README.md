# kaitiaki-carbon

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![Forked from pyfia](https://img.shields.io/badge/fork-mihiarc%2Fpyfia-orange.svg)](https://github.com/mihiarc/pyfia)

> Carbon estimation for whenua tōpū — built by **Anamata Kāhui** to make iwi-led carbon accounting **tractable, transparent, and attested**.

`kaitiaki-carbon` is a Python library + CLI for estimating above-ground biomass and stored carbon from forest-inventory-style data, with a **first-class iwi/hapū attestation overlay** so the resulting estimate carries provenance back to the people who hold mana over that whenua.

It is part of **Anamata Kāhui Limited's** multi-vertical platform — the dev-tools arm sits alongside Anamata Records (music) and the cultural-protection surface (CARE principles + Local Contexts integration) — see [anamata-kahui](https://github.com/LaFinnix/anamata-kahui) for the music platform and [anamata-funding](https://github.com/LaFinnix/anamata-funding) for the funding archive.

---

## What it does

```bash
# Estimate carbon on a parcel (parcel.geojson is GeoJSON Polygon or MultiPolygon)
# and attach an iwi attestation so the estimate carries provenance.
kaitiaki-carbon estimate path/to/parcel.geojson \
    --attestation path/to/attestation.json \
    --locale mi
```

Output:

```json
{
  "parcel_id": "auckland-radiata-test-parcel",
  "area_ha": 395.81276330044835,
  "estimate_per_ha_tCO2e": 0.02905340434814547,
  "estimate_total_tCO2e": 11.49970825832472,
  "ci_95_pct": {
    "per_ha": [
      0.02094611692531581,
      0.03716069177097512
    ],
    "total": [
      8.290740420623543,
      14.708676096025894
    ]
  },
  "method": "kaitiaki-carbon-v0.1-nsvb",
  "tree_count": 10,
  "species_count": 1,
  "unknown_species": [],
  "attestation": {
    "iwi": "Ngāi Tahu",
    "hapū": "Kāti Huirapa",
    "iwi_runanga": "Te Rūnanga o Ōtākou",
    "kaitiaki": "Kaumātua P. Smith",
    "scope": "parcel",
    "consent": [
      "research",
      "market"
    ]
  }
}
```

Numbers above come from the actual `tests/fixtures/parcel_auckland_radiata.geojson` fixture (10 mature radiata pine on a ~396 ha parcel near Auckland) run through the vendored NSVB pipeline. Reproducible locally with:

```bash
python -c "from kaitiaki_carbon.geojson import parse_parcel; from kaitiaki_carbon import estimate_carbon; import json; print(json.dumps(estimate_carbon(parse_parcel(json.load(open('tests/fixtures/parcel_auckland_radiata.geojson'))).to_wire_format(), indent=2))"
```

N.B. the cli output is te reo Māori when `--locale mi`, e.g.:

```
$ kaitiaki-carbon estimate parcel.geojson --attestation foo.json --locale mi
E tatau ana i te koiora → waro rokiroki → wārā CO2-hāngai mō te papakā whenua.
Wārā waro: 8.0 tCO2e (95% CI [3.4, 12.7])
I taupātia e Ngāi Tahu (Kāti Huirapa), kaitiaki: Te Rūnanga o Ōtākou.
```

---

## Why this exists

Carbon estimation tools exist (USFS FIA, NZ ETS calculators, satellite-only platforms). What they don't do well is **carry the indigenous governance relationship with the land into the estimate**.

- A 1,200 tCO₂e estimate is meaningless without the *who-decides-how-this-number-is-used*.
- A satellite-only NDVI misses the species composition that determines the actual expansion factor.
- A point-in-time snapshot misses the rotation cycle that's culturally significant (rāhui, harvest cycles).

`kaitiaki-carbon` is **not** a replacement for the iwi-led accounting. It is the **interoperable substrate** that lets iwi groups:

1. Run an estimate on their terms (their data, their parcels, their criteria)
2. Carry the attestation into downstream systems (NZ ETS, voluntary markets, LCD PF 2050 reporting, Royal Society-Ngā Puanga Pūtaiao citations)
3. Reuse the methodology across their own tools (it speaks standard JSON)

---

## What it is **not**

- ❌ Not a satellite-only estimate. We use inventory-style inputs (species, age, basal area, plot count). Satellite NDVI is opt-in.
- ❌ Not a market-making or trading platform. We do the math; the marketplace is someone else's job.
- ❌ Not a compliance tool. We produce estimates; iwi and the regulator interpret them.
- ❌ Not a generic ESG-screener. Use [LLM4ESGPrediction](https://github.com/brianleixia/LLM4ESGPrediction) for that.
- ❌ Not "AI-driven" or hot-take-driven. The math is published forestry science; you can audit every line.

---

## Architecture at a glance

```
src/kaitiaki_carbon/
├── core.py          # AGB → tCO₂e wrapper around NSVB (vendored under nsvb/)
├── nsvb/            # NSVB math (Westfall GTR-WO-104) — vendored from pyfia, MIT
│   ├── equations.py        # Models 1, 2, 4, 5 — pure math, no FIADB
│   ├── coefficients.py     # NSVB lookup precedence + loader
│   ├── carbon_fractions.py # S10a/S10b species-specific tables
│   └── data/               # 15 vendored CSVs
├── attest.py        # iwi / hapū attestation schema (NEW — ours)
├── attribution.py   # overlay attestation onto an estimate (NEW — ours)
├── cli.py           # `kaitiaki-carbon estimate ...` (NEW — ours)
└── i18n/            # te reo Māori + English CLI labels (NEW — ours)
```

| Layer | Source | License |
|---|---|---|
| NSVB equations, coefficients, carbon fractions | Vendored from [`mihiarc/pyfia`](https://github.com/mihiarc/pyfia) | MIT |
| NSVB coefficient CSV data | Vendored from `mihiarc/pyfia` | MIT (data is a public-domain FIA publication) |
| `core.py` wrapper | Original (adapted from FIA's `live_tree` shape, dropped FIADB-specific bits) | Apache-2.0 |
| Schema (`attest.py`) | Original | Apache-2.0 |
| Overlay (`attribution.py`) | Original | Apache-2.0 |
| CLI (`cli.py`) | Original | Apache-2.0 |
| i18n (`mi.json`, `en.json`) | Original | Apache-2.0 |

See `docs/UPSTREAM.md` for the full vendored-vs-original cut, and
`NOTICE` for the upstream attribution.

See [`NOTICE`](NOTICE) for upstream attribution. See [`docs/UPSTREAM.md`](docs/UPSTREAM.md) for the full upstream-patch status.

---

## Quickstart

```bash
# Requires Python 3.11+
python3 -m venv .venv
source .venv/bin/activate

pip install -e .

# 1. Estimate (no attestation — raw number)
kaitiaki-carbon estimate tests/fixtures/parcel_auckland_radiata.geojson

# 2. Estimate with attestation + te reo Māori CLI messages
kaitiaki-carbon estimate tests/fixtures/parcel_auckland_radiata.geojson \
    --attestation tests/fixtures/attestation/ngai-tahu-rakaipaaka.json \
    --locale mi
```

The CLI accepts both **GeoJSON Features** (Polygons + MultiPolygons)
and **parcel dicts** (with `area_ha` and `trees` pre-populated) — see
`tests/fixtures/parcel_auckland_radiata.geojson` for an end-to-end
example.

See [`docs/QUICKSTART.md`](docs/QUICKSTART.md) for the longer
walkthrough (NDVI ingestion, NZ ETS export format, attestation
schema details).

---

## Methodology

Carbon estimation basics:

```
above-ground biomass (t dry matter / ha)
  = volume × wood-density × biomass-expansion-factor

stored carbon (tC / ha)
  = above-ground biomass × 0.5     # IPCC default carbon fraction

CO₂-equivalent (tCO₂e / ha)
  = stored carbon × 44 / 12        # molecular weight ratio
```

The forest-inventory variant uses **per-tree equations** (species, dbh, height, age) rather than blanket regional factors. This is the methodology from USDA FIA — translated to NZ context with Te Ture Whenua-aligned parcel definitions.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the full math, citations, and the list of equations we use.

---

## Attestation schema

The attestation overlay is a JSON object that travels with the estimate. Schema is in [`src/kaitiaki_carbon/attest.py`](src/kaitiaki_carbon/attest.py); latest version at [`docs/ATTESTATION-SCHEMA.md`](docs/ATTESTATION-SCHEMA.md).

Worked examples in `tests/fixtures/attestation/`:

- `ngai-tahu-rakaipaaka.json` — full Ngāi Tahu Rakaipaaka example (hapū + iwi + rūnanga + scope)
- `ngai-tahu-tuawhenua.json` — full Ngāi Tahu Tuawhenua example
- `blank.json` — minimal schema example (no claims, just a placeholder)

---

## iwi engagement

We will not ship features that change how cultural protocol is represented without iwi consultation. See [`docs/iwi-engagement.md`](docs/iwi-engagement.md) for the engagement protocol and the contributor-conduct rules.

In short: **the user community is iwi and hapū, not forestry enthusiasts. The protocol layer of this tool is not optional.**

---

## Upstream PRs we maintain

We are actively contributing back to the upstream forest-inventory ecosystem:

| Upstream | PR | Status |
|---|---|---|
| `mihiarc/pyfia` | te reo Māori i18n hooks for CLI | open |
| `mihiarc/pyfia` | NZ-context biomass expansion factors | open |
| `mihiarc/pyfia` | Kaitiaki-Attestation schema reference | open |

(links added after Phase 4 ships)

---

## License

- **This repo**: Apache License 2.0 — see [`LICENSE`](LICENSE)
- **Upstream attribution**: [`NOTICE`](NOTICE)
- **Why Apache-2.0**: it (a) protects our brand contributions and (b) is permissive enough that iwi groups can adapt it into their own tools without negotiation.

---

## Part of Anamata Kāhui

Anamata Kāhui Limited is a Māori-owned multi-vertical platform operating under Ngāi Tahu registration. The dev-tools arm of the platform lives here. Other arms:

- **Anamata Records** — music label + artist collective ([anamata-kahui](https://github.com/LaFinnix/anamata-kahui))
- **Funding archive** — past and current applications ([anamata-funding](https://github.com/LaFinnix/anamata-funding))

We don't see "carbon" or "music" or "funding" as separate businesses — they're all expressions of the same cultural-sovereignty thesis: **the means of production, distribution, and accounting should be in the hands of the people whose whenua and whakapapa are at stake**.

---

Kia kaha, kia māia, kia manawanui.
