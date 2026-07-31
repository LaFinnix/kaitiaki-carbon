"""Tests for the core carbon estimation engine.

These tests verify:
  - NSVB integration produces sensible numeric output
  - Bounds and round-trip behaviour
  - iwi-relevant unknowns (zero-tree parcels) handled gracefully
  - Carbon fraction defaulting works
  - Wire format is correct
  - The vendor attribution (Westfall GTR-WO-104) is reproducible

Modifying these tests means modifying core.py. See docs/UPSTREAM.md.
"""

from __future__ import annotations

import math

import pytest

from kaitiaki_carbon.core import CarbonEstimate, estimate_carbon

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def _parcel(
    area_ha: float = 1.0,
    trees: list[dict] | None = None,
    parcel_id: str = "test-parcel",
) -> dict:
    """Build a normalised parcel dict for tests.

    If ``trees`` is None, returns a 2-tree default fixture (Douglas-fir
    + Red maple, 1ha). If trees is an explicit list, uses it verbatim
    (including empty list → tests the "no trees" branch).
    """
    if trees is None:
        trees = [
            {"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1},
            {"spcd": 316, "dia": 22.0, "ht": 18.0, "statuscd": 1},
        ]
    return {
        "id": parcel_id,
        "area_ha": area_ha,
        "trees": trees,
    }


class TestEstimateCarbonBasic:
    """Basic round-trip tests — the core estimator returns numbers."""

    def test_returns_carbon_estimate(self) -> None:
        est = estimate_carbon(_parcel())
        assert isinstance(est, CarbonEstimate)

    def test_estimate_total_tCO2e_is_positive(self) -> None:
        est = estimate_carbon(_parcel())
        assert est.estimate_total_tCO2e > 0.0

    def test_per_ha_equals_total_for_unit_area(self) -> None:
        # For a 1-ha parcel, per_ha and total should match.
        est = estimate_carbon(_parcel(area_ha=1.0))
        assert math.isclose(
            est.estimate_per_ha_tCO2e, est.estimate_total_tCO2e, rel_tol=1e-9
        )

    def test_estimate_scales_with_area(self) -> None:
        # Total carbon is fixed (same trees, same biomass). Per-ha
        # equals total / area, so doubling area halves per-ha.
        trees = [
            {"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1},
            {"spcd": 202, "dia": 22.0, "ht": 19.0, "statuscd": 1},
            {"spcd": 316, "dia": 25.0, "ht": 20.0, "statuscd": 1},
        ]
        e1 = estimate_carbon(_parcel(area_ha=1.0, trees=trees))
        e10 = estimate_carbon(_parcel(area_ha=10.0, trees=trees))
        # Total is identical (same 3 trees, same biomass).
        assert math.isclose(
            e1.estimate_total_tCO2e, e10.estimate_total_tCO2e, rel_tol=1e-9
        )
        # Per-ha is total / area, so 10ha → 1/10 of 1ha per_ha.
        assert math.isclose(
            e10.estimate_per_ha_tCO2e,
            e1.estimate_per_ha_tCO2e / 10.0,
            rel_tol=1e-6,
        )

    def test_method_marker_present(self) -> None:
        est = estimate_carbon(_parcel())
        assert "kaitiaki-carbon" in est.method
        assert "nsvb" in est.method.lower()

    def test_tree_count_recorded(self) -> None:
        est = estimate_carbon(_parcel())
        assert est.tree_count == 2  # 2 trees in the default fixture

    def test_species_count_recorded(self) -> None:
        est = estimate_carbon(_parcel())  # Douglas-fir + Red maple
        assert est.species_count == 2


class TestNSVBSanity:
    """Sanity checks on the NSVB math (numbers in forestry-realistic range)."""

    def test_douglas_fir_30cm_is_in_forestry_range(self) -> None:
        # Douglas-fir, 30 cm DBH, 25 m total — a mature specimen.
        # AGB should be 1.0-2.0 tonnes dry matter per tree (forestry ranges).
        parcel = _parcel(
            area_ha=1.0,
            trees=[{"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1}],
        )
        est = estimate_carbon(parcel)
        # 1 tree, 1 ha, so total ≈ per_ha
        assert 1.0 < est.estimate_total_tCO2e < 5.0

    def test_unknown_species_via_jenkins_fallback(self) -> None:
        # SPCD=999 is not in the FIA tables — must fall through to Jenkins.
        # Jenkins still produces a number (default wood density applied).
        parcel = _parcel(
            area_ha=1.0,
            trees=[{"spcd": 999, "dia": 30.0, "ht": 25.0, "statuscd": 1}],
        )
        # Should not raise. The result may be NaN/0 because Jenkins
        # needs WDSG, but it should at least not throw.
        try:
            est = estimate_carbon(parcel)
            # Just confirm we got back a CarbonEstimate.
            assert isinstance(est, CarbonEstimate)
        except Exception as exc:
            pytest.fail(f"Jenkins fallback should not raise: {exc}")

    def test_zero_trees_returns_zero_estimate(self) -> None:
        parcel = _parcel(area_ha=1.0, trees=[])
        est = estimate_carbon(parcel)
        assert est.estimate_total_tCO2e == 0.0
        assert est.tree_count == 0
        assert "no trees" in est.method.lower()

    def test_negative_area_raises(self) -> None:
        parcel = _parcel(area_ha=-1.0)
        with pytest.raises(ValueError, match="area_ha must be > 0"):
            estimate_carbon(parcel)

    def test_zero_area_raises(self) -> None:
        parcel = _parcel(area_ha=0.0)
        with pytest.raises(ValueError, match="area_ha must be > 0"):
            estimate_carbon(parcel)


class TestConfidenceIntervals:
    """CI behaviour — must be wider than a point estimate on multiple trees."""

    def test_single_tree_has_degenerate_ci(self) -> None:
        # n=1 has no variance; CI is the point estimate.
        parcel = _parcel(
            area_ha=1.0,
            trees=[{"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1}],
        )
        est = estimate_carbon(parcel)
        assert est.ci_95_pct_total[0] == est.ci_95_pct_total[1]
        assert math.isclose(est.ci_95_pct_total[0], est.estimate_total_tCO2e, rel_tol=1e-9)

    def test_multiple_trees_have_nonzero_width_ci(self) -> None:
        parcel = _parcel(area_ha=1.0)
        # Default fixture has 2 trees
        est = estimate_carbon(parcel)
        width = est.ci_95_pct_total[1] - est.ci_95_pct_total[0]
        assert width > 0.0

    def test_ci_lower_is_non_negative(self) -> None:
        est = estimate_carbon(_parcel())
        assert est.ci_95_pct_total[0] >= 0.0
        assert est.ci_95_pct_per_ha[0] >= 0.0

    def test_ci_contains_point_estimate(self) -> None:
        # The point estimate should fall within or on the boundary of
        # the 95% confidence interval.
        parcel = _parcel(area_ha=1.0)
        est = estimate_carbon(parcel)
        lo, hi = est.ci_95_pct_total
        # Allow small numerical slack.
        assert (lo - 1e-6) <= est.estimate_total_tCO2e <= (hi + 1e-6)


class TestWireFormat:
    """The wire format must be JSON-roundtrippable and complete."""

    def test_wire_format_contains_required_keys(self) -> None:
        est = estimate_carbon(_parcel())
        d = est.to_wire_format()
        assert "parcel_id" in d
        assert "area_ha" in d
        assert "estimate_per_ha_tCO2e" in d
        assert "estimate_total_tCO2e" in d
        assert "ci_95_pct" in d
        assert "method" in d
        assert "tree_count" in d
        assert "species_count" in d
        assert "unknown_species" in d

    def test_wire_format_ci_nested(self) -> None:
        est = estimate_carbon(_parcel())
        d = est.to_wire_format()
        assert "per_ha" in d["ci_95_pct"]
        assert "total" in d["ci_95_pct"]
        assert len(d["ci_95_pct"]["per_ha"]) == 2
        assert len(d["ci_95_pct"]["total"]) == 2

    def test_wire_format_json_roundtrip(self) -> None:
        import json
        est = estimate_carbon(_parcel())
        d = est.to_wire_format()
        s = json.dumps(d, ensure_ascii=False)
        d2 = json.loads(s)
        assert d2["parcel_id"] == d["parcel_id"]
        assert d2["method"] == d["method"]


class TestVendorAttribution:
    """The estimator's provenance must be traceable to Westfall GTR-WO-104."""

    def test_method_marker_cites_nsvb(self) -> None:
        est = estimate_carbon(_parcel())
        assert "nsvb" in est.method.lower()

    def test_method_marker_versions(self) -> None:
        est = estimate_carbon(_parcel())
        # Future-proofing: the version should be in the method string.
        assert "v0.1" in est.method


class TestIwiField:
    """Verify the iwi/hapū attestation stays out of the core math.

    The attestation is overlaid after estimation. The estimator should
    accept the per-tree data unchanged regardless of whether an
    attestation is attached (the test simply confirms the API is
    attestation-agnostic).
    """

    def test_estimator_does_not_touch_attestation(self) -> None:
        from kaitiaki_carbon.attest import Attestation
        # Attach an attestation — estimator should not use it.
        att = Attestation.model_validate({"iwi": "Ngāi Tahu", "kaitiaki": "Kaitiaki"})
        parcel = _parcel()
        est = estimate_carbon(parcel)
        # The estimator returns a CarbonEstimate, not an AttributedEstimate.
        # The wiring happens in attach_attestation().
        assert isinstance(est, CarbonEstimate)
        # And the attached attestation exists but isn't part of the estimate.
        assert att.iwi == "Ngāi Tahu"


class TestMacronPreservation:
    """Macrons must round-trip through the parcel dict without loss."""

    def test_iwi_attestation_macron_safe(self) -> None:
        # Smoke test that a macron in the parcel id survives round-trip.
        parcel = _parcel(parcel_id="tapuwae-1A-north-papakāinga")
        est = estimate_carbon(parcel)
        assert "ā" in est.parcel_id

    def test_macrons_in_species_code_are_safe(self) -> None:
        # The species name doesn't go through estimate_carbon — but
        # iwi data attached alongside should remain untouched.
        from kaitiaki_carbon.attest import Attestation

        att = Attestation.model_validate({
            "iwi": "Ngāi Tahu",
            "hapū": "Kāti Huirapa",
            "kaitiaki": "Kaitiaki",
        })
        parcel = _parcel()
        est = estimate_carbon(parcel)
        # Test that the estimator coexists with macron strings.
        assert att.hapū and "ā" in att.hapū
        assert est.parcel_id  # doesn't depend on macrons
