# Upstream lineage — what's ours, what's forked

This document describes the relationship between `kaitiaki-carbon` and
its upstream `mihiarc/pyfia` (MIT, Copyright (c) 2025 Chris Mihiar).

## Why we forked

Forestry carbon estimation is **not** a new problem. The methodology
exists, the code exists, and the upstream `pyfia` has done the work to
implement the NSVB (Westfall GTR-WO-104) allometric equations plus
species-specific S10a/S10b carbon fractions — the same equations USDA
FIA uses for the FIADB inventory.

What `pyfia` doesn't do — and what `kaitiaki-carbon` exists to do — is
**wrap those equations in a JSON-first API that travels with iwi/hapū
attestation**. The cultural-protocol layer is the brand artefact; the
biomass math is borrowed science we owe upstream.

We vendor rather than depend at runtime because:

1. **Auditability**. Downstream users can read every line of the
   carbon math without network access.
2. **Modified-lineage clarity**. Vendored files carry a
   `MODIFIED FOR KAITIAKI-CARBON` header so the fork boundary is
   obvious.

## Vendored files

| File | Upstream path | Modifications |
|---|---|---|
| `src/kaitiaki_carbon/nsvb/equations.py` | `src/pyfia/carbon/nsvb/equations.py` | Header comment added; math unchanged |
| `src/kaitiaki_carbon/nsvb/coefficients.py` | `src/pyfia/carbon/nsvb/coefficients.py` | Header comment + `pyfia.carbon.nsvb.data` → `kaitiaki_carbon.nsvb.data` (4 sites) |
| `src/kaitiaki_carbon/nsvb/carbon_fractions.py` | `src/pyfia/carbon/nsvb/carbon_fractions.py` | Header comment + 2 sites same |
| `src/kaitiaki_carbon/nsvb/__init__.py` | `src/pyfia/carbon/nsvb/__init__.py` | Header comment + import paths |
| `src/kaitiaki_carbon/nsvb/data/*.csv` (15 files) | `src/pyfia/carbon/nsvb/data/*.csv` | None — vendored byte-for-byte |
| `src/kaitiaki_carbon/nsvb/data/README.md` | `src/pyfia/carbon/nsvb/data/README.md` | None |

## Files deliberately NOT vendored

| Upstream path | Why excluded |
|---|---|
| `src/pyfia/carbon/_estimator_base.py` | Firestore of FIA estimator scaffolding (variance propagation, plot stratification). v0.2 will extract a minimal CI helper from here; for v0.1 we use a coarse analytic CI. |
| `src/pyfia/carbon/live_tree.py` | The live tree class wraps NSVB behind FIA's `apply_filters` + `calculate_values` interface. We're calling `compute_nsvb_biomass` directly because we don't have a `FIA` core to plug into. |
| `src/pyfia/carbon/standing_dead.py` | Standing-dead biomass (DECAYCD-aware). Out of scope for v0.1. |
| `src/pyfia/core/` (FIA class, DuckDB backend, motherduck backend) | All FIADB-specific. Kaitiaki-carbon consumes pre-normalised per-tree records, not FIADB data. |
| `src/pyfia/constants/` | FIA column-name constants. We use UPPERCASE column names directly. |
| `src/pyfia/estimation/` | FIADB post-stratified estimator (per-stratum variance). Coarse analytic CI is good enough for v0.1. |
| `notebooks/`, `examples/`, `reference/`, `scripts/`, `benchmarks/`, `dev/`, `docs/` (upstream) | We don't need the upstream docs or examples; ours are separate. |

## Upstream contributions we will offer

When Phase 4 ships, the following PRs go to `mihiarc/pyfia`:

1. **te reo Māori i18n hooks for CLI** — package all the upstream
   `print(...)` strings into a translation layer, with `mi.json` as
   the first non-English locale.
2. **NZ-context biomass expansion factors** — `Douglas-fir` (radiata
   pine is supported upstream; we add a `cypress` + `totara` etc.
   adjustment).
3. **Kaitiaki-Attestation schema reference** — link the
   `attest.py` schema definition from the upstream docs.

The PRs benefit upstream: the upstream tooling gains i18n hooks that
no other Forest Inventory project has.

## Verification lineage

`pyfia` was validated against FIADB EVALID 132401 (130,952 trees) on
Georgia — median per-tree relative error 0.085%. We inherit that
validation by using the same vendored equations. Our integration
tests (in `tests/test_core.py`) target the same equations but with
unnormalised inputs (per-tree dicts → Polars LazyFrame → NSVB → tCO₂e).
A round-trip test against a known worked example from GTR-WO-104 is
on the v0.2 roadmap.

## Why MIT → Apache-2.0 license transition is safe

`pyfia` is MIT. Our package is Apache-2.0. Apache-2.0 is more
restrictive than MIT in two areas:

1. **Patent grant**. Apache-2.0 includes an explicit patent license
   that terminates if you sue the contributors. Upstream MIT grants
   no patents. We're not licensing anyone else's patents — we're
   granting ours.
2. **Trademark restrictions**. Same as MIT.

The NOTICE file (Apache-2.0 requirement) explicitly preserves the MIT
notice for the vendored pyfia code, satisfying the MIT "include the
notice" clause.

We're not redistributing upstream's patents; we're shipping their
math under our license. MIT allows this. Apache-2.0 forbids a
downstream user from suing us over our (newly-added) patents. Both
licenses coexist in our package.

## How to update the vendored code

When upstream `mihiarc/pyfia` ships a release we want to integrate:

1. `git fetch upstream`
2. `git log upstream/main -- src/pyfia/carbon/nsvb` to see new commits
3. For each vendored file, diff vs upstream and merge, keeping our
   `MODIFIED FOR KAITIAKI-CARBON` header and the `kaitiaki_carbon.`
   package-name paths.
4. Rerun `tests/test_core.py` — the math should round-trip with zero
   output changes (modulo bug fixes we've merged in).
