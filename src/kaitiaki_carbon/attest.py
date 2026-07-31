"""iwi/hapū attestation schema — kaitiaki-carbon v0.1.

The attestation overlay is the brand artefact of this tool. It is the
piece that distinguishes "yet another carbon estimator" from "a tool
that respects the people whose whenua this is".

Schema v0.1 — design principles:

  1. **No claim without consent.** Every field either declares a fact
     ("the iwi named Ngāi Tahu") or records an explicit decision
     ("the kaitiaki has attested for use under research consent"). No
     defaults that presume.
  2. **Hierarchical respect.** iwi > hapū > marae > whānau > tangata
     whenua. The schema supports all levels, not just one. A hapū may
     attest on behalf of their papakāinga without ratifying an iwi;
     a whānau may attest for their own urupā.
  3. **Whakapapa, not bureaucracy.** Names are strings with optional
     rōpū links, not foreign-key IDs to a users table. The schema
     travels; it doesn't tie iwi into our database.
  4. **Document the consent scope.** "research", "market", "policy",
     "compliance" — the iwi can declare which consents apply to this
     attestation. The tool does not assert consents; it records them.

Modifications to this schema require iwi consultation. See
docs/iwi-engagement.md.

---

Schema version: 0.1.0 (alpha)
Released: 2026-07
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "0.1.0"


class AttestationScope(StrEnum):
    """How broadly the attestation applies.

    * `parcel` — the specific parcel named (most common).
    * `papakainga` — a papakāinga home-base, usually a small parcel.
    * `collective` — a collective area managed by multiple iwi/hapū.
    * `research` — the attestation is for a research artefact only.
      Numbers produced under this scope cannot be used for market or
      compliance without a re-attestation.
    """

    PARCEL = "parcel"
    PAPAKĀINGA = "papakainga"
    COLLECTIVE = "collective"
    RESEARCH = "research"


class ConsentChannel(StrEnum):
    """What the attestation authorises the number to be used for.

    Each is independent. An attestation can list multiple — a single
    iwi may attest "this number is for research AND market reporting"
    and that single attestation can accompany both use-cases.
    """

    RESEARCH = "research"
    MARKET = "market"
    POLICY = "policy"
    COMPLIANCE = "compliance"
    INTERNAL = "internal"


class Attestation(BaseModel):
    """A kaitiaki-attested overlay on top of a carbon estimate.

    All fields are intentionally optional except `iatwi_name` and
    `kaitiaki`. The reasoning: even minimal attestations need to
    identify *who* is making the call and *who* they represent. Other
    fields can be added in subsequent attestations.

    Lifecycle: an Attestation is immutable once created (audit-trail
    friendly). To revise, create a new Attestation and supersede the
    old one in your downstream system.
    """

    # --- Required ---
    iwi: str = Field(
        min_length=1,
        description="Iwi name. Either te reo Māori or anglicised as appropriate.",
    )
    kaitiaki: str = Field(
        min_length=1,
        description=(
            "The body or individual attesting for the iwi/hapū. E.g. a rūnanga, "
            "a marae committee, a hapū trust, or named individual with explicit mandate."
        ),
    )

    # --- Recommended ---
    hapū: str | None = Field(
        default=None,
        description="Hapū name(s) if the attestation is at hapū (not iwi) level.",
    )
    iwi_runanga: str | None = Field(
        default=None,
        description="Mandated iwi authority (rūnanga or equivalent).",
    )
    scope: AttestationScope = Field(
        default=AttestationScope.PARCEL,
        description="How broadly the attestation applies.",
    )
    consent: list[ConsentChannel] = Field(
        default_factory=lambda: [ConsentChannel.RESEARCH],
        description="Channels the kaitiaki authorises the number to be used under.",
    )

    # --- Provenance ---
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the attestation was issued.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiry. After this date the attestation is informational-only.",
    )
    supersedes: str | None = Field(
        default=None,
        description=(
            "Optional identifier of a previous attestation this one replaces. "
            "Use a UUID or your own attestation store's reference."
        ),
    )

    # --- Optional context ---
    notes: str | None = Field(
        default=None,
        max_length=4000,
        description="Free-form notes (cultural context, methodology caveats, etc).",
    )
    contact_for_consent: str | None = Field(
        default=None,
        description="Contact line for downstream parties to seek consent questions.",
    )

    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="The schema version this attestation was authored against.",
    )

    @field_validator("consent", mode="after")
    @classmethod
    def _consent_not_empty(cls, v: list[ConsentChannel]) -> list[ConsentChannel]:
        if not v:
            raise ValueError("consent list cannot be empty — even RESEARCH must be explicit.")
        return v

    @model_validator(mode="after")
    def _expires_after_issued(self) -> Attestation:
        if self.expires_at is not None and self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at.")
        return self

    def to_wire_format(self) -> dict[str, Any]:
        """Render the attestation as a JSON-compatible dict.

        Boolean consent flags surface as a `consent` map for easy
        downstream consumption:

            "consent": {"research": true, "market": false, ...}

        We emit both the list (canonical) and the map (convenience)
        so downstream systems can use either.
        """
        d = self.model_dump(mode="json", exclude_none=True)
        consent_map = {ch.value: (ch in self.consent) for ch in ConsentChannel}
        d["consent_map"] = consent_map
        return d


def validate_attestation(payload: dict[str, Any]) -> Attestation:
    """Parse and validate an attestation from a JSON payload.

    Raises pydantic.ValidationError on schema mismatch.
    """
    return Attestation.model_validate(payload)


__all__ = [
    "Attestation",
    "AttestationScope",
    "ConsentChannel",
    "SCHEMA_VERSION",
    "validate_attestation",
]
