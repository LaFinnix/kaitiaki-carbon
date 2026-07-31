"""Attestation overlay tests."""

from datetime import UTC, datetime

from kaitiaki_carbon.attest import Attestation
from kaitiaki_carbon.attribution import AttributedEstimate, attach_attestation


def _carbon_estimate():
    from kaitiaki_carbon.core import CarbonEstimate

    return CarbonEstimate(
        parcel_id="test-parcel",
        area_ha=10.0,
        estimate_per_ha_tCO2e=120.0,
        estimate_total_tCO2e=1200.0,
        method="pyfia-biomass-v0.1",
        ci_95_pct_per_ha=(110.0, 130.0),
        ci_95_pct_total=(1100.0, 1300.0),
    )


def _attestation():
    return Attestation.model_validate(
        {
            "iwi": "Ngāi Tahu",
            "hapū": "Kāti Huirapa",
            "kaitiaki": "Te Rūnanga o Ōtākou",
        }
    )


class TestAttachAttestation:
    def test_basic_attach(self) -> None:
        est = _carbon_estimate()
        att = _attestation()
        attributed = attach_attestation(est, att)

        assert isinstance(attributed, AttributedEstimate)
        assert attributed.estimate is est
        assert attributed.attestation is att

    def test_default_overlaid_at_is_now(self) -> None:
        before = datetime.now(UTC)
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        after = datetime.now(UTC)
        assert before <= attributed.overlaid_at <= after

    def test_correlation_id_optional(self) -> None:
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        assert attributed.correlation_id is None

        attributed = attach_attestation(_carbon_estimate(), _attestation())
        attributed.correlation_id = "abc-123"
        assert attributed.correlation_id == "abc-123"


class TestAttributedEstimateWireFormat:
    def test_keys_present(self) -> None:
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        d = attributed.to_wire_format()
        assert "estimate" in d
        assert "attestation" in d
        assert "overlaid_at" in d
        assert "schema_version" in d

    def test_estimate_propagates(self) -> None:
        est = _carbon_estimate()
        attributed = attach_attestation(est, _attestation())
        d = attributed.to_wire_format()
        assert d["estimate"]["parcel_id"] == "test-parcel"
        assert d["estimate"]["estimate_total_tCO2e"] == 1200.0

    def test_attestation_propagates(self) -> None:
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        d = attributed.to_wire_format()
        assert d["attestation"]["iwi"] == "Ngāi Tahu"
        assert d["attestation"]["hapū"] == "Kāti Huirapa"
        assert "consent_map" in d["attestation"]

    def test_schema_version_propagates(self) -> None:
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        d = attributed.to_wire_format()
        assert d["schema_version"] == "0.1.0"

    def test_correlation_id_in_wire_format(self) -> None:
        attributed = attach_attestation(_carbon_estimate(), _attestation())
        attributed.correlation_id = "trace-789"
        d = attributed.to_wire_format()
        assert d["correlation_id"] == "trace-789"
