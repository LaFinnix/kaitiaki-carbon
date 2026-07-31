"""Attestation schema tests — the brand artefact.

These tests verify:

  - Required fields are required
  - Hierarchy (iwi, hapū, iwi_runanga) is allowed at any level
  - Consent list cannot be empty
  - expires_at > issued_at
  - to_wire_format produces the consent_map
  - The schema version is exposed

Modifications to this file imply modifications to the schema. See
docs/iwi-engagement.md for the consultation rules.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from kaitiaki_carbon.attest import (
    SCHEMA_VERSION,
    Attestation,
    AttestationScope,
    ConsentChannel,
    validate_attestation,
)


def _minimal() -> dict[str, Any]:
    """Return a minimal valid attestation payload."""
    return {
        "iwi": "Ngāi Tahu",
        "kaitiaki": "Te Rūnanga o Ōtākou",
    }


class TestAttestationRequiredFields:
    def test_minimal_payload_validates(self) -> None:
        att = Attestation.model_validate(_minimal())
        assert att.iwi == "Ngāi Tahu"
        assert att.kaitiaki == "Te Rūnanga o Ōtākou"

    def test_missing_iwi_fails(self) -> None:
        payload = _minimal()
        del payload["iwi"]
        with pytest.raises(ValidationError) as excinfo:
            Attestation.model_validate(payload)
        assert "iwi" in str(excinfo.value)

    def test_missing_kaitiaki_fails(self) -> None:
        payload = _minimal()
        del payload["kaitiaki"]
        with pytest.raises(ValidationError) as excinfo:
            Attestation.model_validate(payload)
        assert "kaitiaki" in str(excinfo.value)

    def test_empty_iwi_fails(self) -> None:
        payload = _minimal()
        payload["iwi"] = ""
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)


class TestAttestationHierarchy:
    def test_hapu_optional(self) -> None:
        att = Attestation.model_validate({**_minimal(), "hapū": "Kāti Huirapa"})
        assert att.hapū == "Kāti Huirapa"

    def test_iwi_runanga_optional(self) -> None:
        att = Attestation.model_validate({**_minimal(), "iwi_runanga": "Te Rūnanga o Ngāi Tahu"})
        assert att.iwi_runanga is not None

    def test_full_hierarchy(self) -> None:
        att = Attestation.model_validate(
            {
                "iwi": "Ngāi Tahu",
                "hapū": "Kāti Huirapa",
                "iwi_runanga": "Te Rūnanga o Ōtākou",
                "kaitiaki": "Kaumātua P. Smith",
            }
        )
        assert att.iwi == "Ngāi Tahu"
        assert att.hapū == "Kāti Huirapa"
        assert att.iwi_runanga == "Te Rūnanga o Ōtākou"
        assert att.kaitiaki == "Kaumātua P. Smith"


class TestAttestationScope:
    def test_default_scope_is_parcel(self) -> None:
        att = Attestation.model_validate(_minimal())
        assert att.scope == AttestationScope.PARCEL

    def test_research_scope(self) -> None:
        att = Attestation.model_validate({**_minimal(), "scope": AttestationScope.RESEARCH.value})
        assert att.scope == AttestationScope.RESEARCH

    def test_invalid_scope_fails(self) -> None:
        payload = {**_minimal(), "scope": "everywhere"}
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)


class TestAttestationConsent:
    def test_default_consent_is_research(self) -> None:
        att = Attestation.model_validate(_minimal())
        assert att.consent == [ConsentChannel.RESEARCH]

    def test_explicit_empty_consent_fails(self) -> None:
        # A pydantic-2 model_validator rejects empty.
        payload = {**_minimal(), "consent": []}
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)

    def test_multiple_consents(self) -> None:
        att = Attestation.model_validate({**_minimal(), "consent": ["research", "market"]})
        assert ConsentChannel.RESEARCH in att.consent
        assert ConsentChannel.MARKET in att.consent

    def test_invalid_consent_fails(self) -> None:
        payload = {**_minimal(), "consent": ["research", "weapon-trading"]}
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)


class TestAttestationTimestamps:
    def test_default_issued_at_is_utc_now(self) -> None:
        before = datetime.now(UTC)
        att = Attestation.model_validate(_minimal())
        after = datetime.now(UTC)
        assert before <= att.issued_at <= after

    def test_expires_after_issued(self) -> None:
        future = (datetime.now(UTC) + timedelta(days=365)).isoformat()
        payload = {**_minimal(), "expires_at": future}
        att = Attestation.model_validate(payload)
        assert att.expires_at is not None

    def test_expires_before_issued_fails(self) -> None:
        past = (datetime.now(UTC) - timedelta(days=365)).isoformat()
        payload = {**_minimal(), "issued_at": datetime.now(UTC).isoformat(), "expires_at": past}
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)


class TestAttestationWireFormat:
    def test_to_wire_format_includes_consent_map(self) -> None:
        att = Attestation.model_validate({**_minimal(), "consent": ["research", "market"]})
        d = att.to_wire_format()
        assert "consent_map" in d
        assert d["consent_map"]["research"] is True
        assert d["consent_map"]["market"] is True
        assert d["consent_map"]["policy"] is False

    def test_to_wire_format_strips_none(self) -> None:
        att = Attestation.model_validate(_minimal())
        d = att.to_wire_format()
        # hapū wasn't set on the minimal payload
        assert "hapū" not in d or d.get("hapū") is None

    def test_schema_version_is_exposed(self) -> None:
        att = Attestation.model_validate(_minimal())
        assert att.schema_version == SCHEMA_VERSION

    def test_validate_attestation_helper(self) -> None:
        # Round-trip via the helper.
        att = validate_attestation(_minimal())
        assert isinstance(att, Attestation)


class TestAttestationNotes:
    def test_notes_optional(self) -> None:
        att = Attestation.model_validate({**_minimal(), "notes": "Kōrero here."})
        assert att.notes == "Kōrero here."

    def test_notes_max_length(self) -> None:
        payload = {**_minimal(), "notes": "x" * 4001}
        with pytest.raises(ValidationError):
            Attestation.model_validate(payload)


class TestAttestationMacronPreservation:
    """The simplest possible macron preservation test.

    If we ever switch the storage layer or edit this file with an
    encoding-aware editor, we want a canary that catches macrons
    silently becoming ASCII.
    """

    def test_macrons_in_iwi_name_preserved(self) -> None:
        att = Attestation.model_validate({"iwi": "Ngāi Tahu", "kaitiaki": "Kaitiaki"})
        assert "ā" in att.iwi

    def test_macrons_in_hapu_preserved(self) -> None:
        att = Attestation.model_validate(
            {
                "iwi": "Ngāi Tahu",
                "kaitiaki": "Kaitiaki",
                "hapū": "Kāti Huirapa",
            }
        )
        assert "ā" in (att.hapū or "")

    def test_unicode_in_notes_preserved(self) -> None:
        att = Attestation.model_validate(
            {
                "iwi": "Ngāi Tahu",
                "kaitiaki": "Kaitiaki",
                "notes": "Whakapapa me ngā tikanga.",
            }
        )
        assert "ā" in (att.notes or "")
