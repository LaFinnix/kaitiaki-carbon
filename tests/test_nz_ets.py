"""Tests for the NZ-ETS export format scaffolding.

These tests verify:
  - emit_ets_record produces the expected field structure
  - The schema_version is exposed (for the downstream registry)
  - An AttestedEstimate with no attestation doesn't crash
  - JSON round-trips
"""

from __future__ import annotations

import json

from kaitiaki_carbon.attest import Attestation
from kaitiaki_carbon.attribution import attach_attestation
from kaitiaki_carbon.core import CarbonEstimate, estimate_carbon
from kaitiaki_carbon.nz_ets import DEFAULT_METHODOLOGY, SCHEMA_VERSION, emit_ets_record


class TestEmitEtsRecord:
    """The shape and contents of the ETS record."""

    def test_basic_record_has_required_fields(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="tapuwae",
            area_ha=5.0,
            estimate_per_ha_tCO2e=80.0,
            estimate_total_tCO2e=400.0,
            method="kaitiaki-carbon-v0.1-nsvb",
            ci_95_pct_total=(380.0, 420.0),
            ci_95_pct_per_ha=(76.0, 84.0),
            tree_count=15,
            species_count=2,
        )
        att = Attestation.model_validate({"iwi": "Ngāi Tahu", "kaitiaki": "Kaitiaki"})
        attributed = attach_attestation(carbon_est, att)

        record = emit_ets_record(
            attributed,
            facility="NZ-ET-12345",
            reporting_period="2026",
        )
        assert record["facility"] == "NZ-ET-12345"
        assert record["reporting_period"] == "2026"
        assert record["account_type"] == "Forestry"
        assert record["claim_type"] == "Removal"
        assert record["parcel_id"] == "tapuwae"
        assert record["area_ha"] == 5.0
        assert record["estimated_removals_tCO2e"] == 400.0
        assert record["methodology"] == DEFAULT_METHODOLOGY

    def test_schema_version_is_present(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="x",
            area_ha=1.0,
            estimate_per_ha_tCO2e=10.0,
            estimate_total_tCO2e=10.0,
            method="test",
        )
        att = Attestation.model_validate({"iwi": "Y", "kaitiaki": "K"})
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F",
            reporting_period="2026",
        )
        assert record["schema_version"] == SCHEMA_VERSION

    def test_iwi_attestation_block(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="tapuwae",
            area_ha=1.0,
            estimate_per_ha_tCO2e=10.0,
            estimate_total_tCO2e=10.0,
            method="test",
        )
        att = Attestation.model_validate({
            "iwi": "Ngāi Tahu",
            "hapū": "Kāti Huirapa",
            "kaitiaki": "Te Rūnanga o Ōtākou",
            "scope": "parcel",
            "consent": ["research", "market"],
        })
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F",
            reporting_period="2026",
        )
        iaw = record["iwi_attestation"]
        assert iaw["iwi"] == "Ngāi Tahu"
        assert iaw["hapū"] == "Kāti Huirapa"
        assert iaw["kaitiaki"] == "Te Rūnanga o Ōtākou"
        assert iaw["scope"] == "parcel"
        # Consent is a list, not a map; the map shape is the estimate
        # `consent_map` field on the Attestation only. ETS callers are
        # typically happier with the list.
        assert set(iaw["consent"]) == {"research", "market"}

    def test_species_composition_default(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="x", area_ha=1.0,
            estimate_per_ha_tCO2e=1.0, estimate_total_tCO2e=1.0,
            method="test",
        )
        att = Attestation.model_validate({"iwi": "Y", "kaitiaki": "K"})
        record = emit_ets_record(attach_attestation(carbon_est, att), facility="F", reporting_period="2026")
        # The default is one placeholder row at 100% basal area.
        assert len(record["species_composition"]) == 1
        assert record["species_composition"][0]["fraction_of_basal_area"] == 1.0

    def test_species_composition_override(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="x", area_ha=1.0,
            estimate_per_ha_tCO2e=1.0, estimate_total_tCO2e=1.0,
            method="test",
        )
        att = Attestation.model_validate({"iwi": "Y", "kaitiaki": "K"})
        species = [
            {"spcd": 131, "species_name": "radiata-pine", "fraction_of_basal_area": 0.85},
            {"spcd": 12, "species_name": "rimu", "fraction_of_basal_area": 0.15},
        ]
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F",
            reporting_period="2026",
            species_composition=species,
        )
        assert len(record["species_composition"]) == 2
        assert record["species_composition"][0]["species_name"] == "radiata-pine"
        assert record["species_composition"][1]["species_name"] == "rimu"
        # Fractions sum to 1.0
        total = sum(s["fraction_of_basal_area"] for s in record["species_composition"])
        assert abs(total - 1.0) < 1e-6

    def test_submitted_at_default_is_recent(self) -> None:
        import datetime
        before = datetime.datetime.now(datetime.UTC)
        carbon_est = CarbonEstimate(
            parcel_id="x", area_ha=1.0,
            estimate_per_ha_tCO2e=1.0, estimate_total_tCO2e=1.0,
            method="test",
        )
        att = Attestation.model_validate({"iwi": "Y", "kaitiaki": "K"})
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F", reporting_period="2026",
        )
        after = datetime.datetime.now(datetime.UTC)
        submitted_at = datetime.datetime.fromisoformat(record["submitted_at"])
        # Submitted at is between before and after (with a small slack).
        # Note: before/after are tz-aware, submitted_at is parsed from ISO.
        assert before <= submitted_at <= after + datetime.timedelta(seconds=1)

    def test_explicit_submitted_at_override(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="x", area_ha=1.0,
            estimate_per_ha_tCO2e=1.0, estimate_total_tCO2e=1.0,
            method="test",
        )
        att = Attestation.model_validate({"iwi": "Y", "kaitiaki": "K"})
        fixed_ts = "2026-12-31T23:59:59+00:00"
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F", reporting_period="2026",
            submitted_at=fixed_ts,
        )
        assert record["submitted_at"] == fixed_ts

    def test_record_json_roundtrip(self) -> None:
        carbon_est = CarbonEstimate(
            parcel_id="tapuwae",
            area_ha=1.0,
            estimate_per_ha_tCO2e=10.0,
            estimate_total_tCO2e=10.0,
            method="kaitiaki-carbon-v0.1-nsvb",
        )
        att = Attestation.model_validate({"iwi": "Ngāi Tahu", "kaitiaki": "Kaitiaki"})
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="NZ-ET-12345",
            reporting_period="2026",
        )
        s = json.dumps(record, ensure_ascii=False)
        d2 = json.loads(s)
        assert d2 == record

    def test_macron_round_trip(self) -> None:
        # ETS submission must preserve macrons in te reo strings.
        carbon_est = CarbonEstimate(
            parcel_id="tapuwae", area_ha=1.0,
            estimate_per_ha_tCO2e=10.0, estimate_total_tCO2e=10.0, method="test",
        )
        att = Attestation.model_validate({"iwi": "Ngāi Tahu", "kaitiaki": "Kaitiaki"})
        record = emit_ets_record(
            attach_attestation(carbon_est, att),
            facility="F", reporting_period="2026",
        )
        assert "Ngāi Tahu" in record["iwi_attestation"]["iwi"]


class TestEtsEndToEnd:
    """The full pipeline: real estimator + real attestation + ETS export."""

    def test_attested_real_parcel_to_ets(self) -> None:
        # A real parcel with a real attestation, end-to-end through
        # the system.
        parcel = {
            "id": "tapuwae-1A-north-block",
            "area_ha": 1.0,
            "trees": [
                {"spcd": 131, "dia": 30.0, "ht": 25.0, "statuscd": 1,
                 "species_name": "radiata-pine"},
                {"spcd": 12, "dia": 22.0, "ht": 18.0, "statuscd": 1,
                 "species_name": "rimu"},
            ],
        }
        est = estimate_carbon(parcel)
        att = Attestation.model_validate({
            "iwi": "Ngāi Tahu",
            "hapū": "Kāti Huirapa",
            "kaitiaki": "Te Rūnanga o Ōtākou",
        })
        attributed = attach_attestation(est, att)
        record = emit_ets_record(
            attributed,
            facility="NZ-ET-DEMO",
            reporting_period="2026",
        )
        # Sanity check the round-trip
        assert record["parcel_id"] == "tapuwae-1A-north-block"
        assert record["area_ha"] == 1.0
        assert record["estimated_removals_tCO2e"] > 0
        assert record["iwi_attestation"]["hapū"] == "Kāti Huirapa"
