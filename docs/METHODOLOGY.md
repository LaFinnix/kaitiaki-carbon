# kaitiaki-carbon — Methodology

**Author:** Ngaika Smith (ORCID [0009-0002-1952-7454](https://orcid.org/0009-0002-1952-7454))
**Affiliation:** Anamata Kāhui Limited — [anamatakahui.co.nz](https://anamatakahui.co.nz)
**Version:** 1.0
**Date:** 2026-08-18
**DOI:** [10.5281/zenodo.21718269](https://doi.org/10.5281/zenodo.21718269)
**Status:** Public — citable. Modifications require iwi consultation per `iwi-engagement.md`.

---

## Citation

```bibtex
@techreport{smith_kaitiaki_carbon_methodology_2026,
  author      = {Smith, Ngaika},
  title       = {kaitiaki-carbon: Methodology for iwi-attested carbon estimation in Aotearoa},
  institution = {Anamata Kāhui Limited},
  year        = {2026},
  version     = {1.0},
  doi         = {10.5281/zenodo.21718269},
  url         = {https://github.com/LaFinnix/kaitiaki-carbon/blob/main/docs/METHODOLOGY.md},
}
```

## 1. Scope

This document describes the methods used by `kaitiaki-carbon` to estimate above-ground biomass (AGB) and stored carbon on New Zealand whenua tōpū (collective Māori land) from forest-inventory-style plot data. The methodology is derived from the USDA Forest Inventory & Analysis (FIA) design-based estimation framework, adapted for Aotearoa-specific species and overlaid with an iwi/hapū attestation layer.

This is **not** an allometric model paper. It is a methodology statement for the software tool that implements the estimation pipeline.

## 2. Estimation pipeline

The pipeline operates on plot-level observations and produces a per-hectare estimate with 95% confidence intervals. Stages:

1. **Plot ingestion** — GeoJSON Polygon or MultiPolygon defining the parcel; plot records with species, DBH (diameter at breast height), height, and tree count.
2. **Species classification** — NZ-context species table maps local species to the FIA genus groups the biomass equations are parameterised against.
3. **Per-tree AGB calculation** — `AGB = a × DBH^b` allometric, with species-specific `a`, `b` from Jenkins et al. (2003) for the FIA generalised groups, and NZ-specific overrides for *Pinus radiata* and *Pseudotsuga menziesii* from New Zealand Forest Service data where the FIA defaults are conservative.
4. **Plot-to-hectare expansion** — design-based expansion factor `EF = (parcel_area_ha × plot_expansion_factor) / plot_area_ha`, applying the standard FIA post-stratification.
5. **Carbon conversion** — `C = 0.5 × AGB`, the IPCC default carbon fraction for forest biomass.
6. **CO₂e conversion** — `CO₂e = C × (44 / 12)`.
7. **Variance propagation** — analytical 95% CI from plot-level variance under the FIA assumption of simple random sampling within stratum; documented in `core.py`.

## 3. NZ-specific adaptations

Three additions on top of the upstream `pyfia` method:

- **Te reo Māori macron layer** — `i18n/mi.json` and `cli.py` carry macronised te reo for all user-facing strings. This is not cosmetic; iwi users reviewing estimates need to see place names and species terms correctly.
- **Iwi/hapū attestation overlay** — the JSON-Schema in `attest.py` attaches a provenance record (`iwi`, `hapū`, `kaitiaki`, `scope`, `consent`) to every estimate. The estimate cannot be persisted without an attestation block, by design. This is the cultural-protocol layer described in `iwi-engagement.md`.
- **NZ biomass expansion factors** — where FIA defaults underestimate *Pinus radiata* (the dominant NZ plantation species), local factors from peer-reviewed NZ forestry literature are substituted. The override is logged in the estimate's provenance record.

## 4. Limitations

- Estimates are only as good as the plot data. If plot locations are imprecise or species misidentified, the estimate inherits those errors.
- The tool does not include below-ground biomass (roots) by default. ETS reporting requires below-ground — see the `--include-bgb` flag (planned, not yet implemented in v0.1.0).
- The attestation overlay is culturally authoritative but not a legal title instrument. It records that an iwi/hapū attests to the data, not that they hold legal title to the whenua.
- v0.1.0 is alpha. Estimates should be reviewed by a qualified forestry practitioner before submission to the ETS or any compliance regime.

## 5. Provenance and verifiability

Every estimate carries a SHA-256 hash of the input plot file and the configuration used, written to the provenance record. This means a future reviewer can replay the estimate byte-for-byte and confirm it has not been altered.

## 6. Modification protocol

Changes to the methodology — i.e., changes to `core.py` or to this document that affect the math, the data sources, or the formula — are governed by `iwi-engagement.md`. The schema (`attest.py`) and the i18n layer (`i18n/mi.json`) are also governed. The engagement document defines the consultation rules; schema and methodology PRs are not merged without iwi sign-off.

## 7. Versioning

- **v1.0** (this document, 2026-08-18) — initial public methodology statement alongside Zenodo DOI `10.5281/zenodo.21718269`.

Future versions increment the minor number for additive changes (new species, new optional flags) and the major number for any change to the core estimation math. Major version bumps require re-consultation per `iwi-engagement.md`.

---

**Author contact:** Ngaika Smith · ngaika@anamatakahui.co.nz
**Repository:** https://github.com/LaFinnix/kaitiaki-carbon
**License of this document:** Apache-2.0 (same as the code it describes).
