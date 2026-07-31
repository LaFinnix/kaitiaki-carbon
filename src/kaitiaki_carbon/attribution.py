"""Attestation overlay — attach iwi provenance to a carbon estimate.

This is the 2 of the 3 brand artefacts. It takes a raw carbon
estimate from `core.py` and overlays an iwi/hapū attestation. The
combined shape is what downstream systems should consume: a numeric
estimate *plus* the people who said it is fair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kaitiaki_carbon.attest import Attestation
    from kaitiaki_carbon.core import CarbonEstimate


@dataclass
class AttributedEstimate:
    """A carbon estimate carrying iwi/hapū attestation.

    This is the canonical output type. Downstream systems (NZ ETS
    export, voluntary market submissions, research artefact citations)
    all read this shape.

    Lifecycle: AttributedEstimate is immutable. To update the estimate
    or re-attest, create a new AttributedEstimate.
    """

    # The estimate (see core.py)
    estimate: Any  # CarbonEstimate, but importing here creates a cycle

    # The attestation that authorises the estimate
    attestation: Any  # Attestation

    # Provenance of the overlay itself
    overlaid_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Optional: an opaque correlation id for downstream systems
    correlation_id: str | None = None

    def to_wire_format(self) -> dict[str, Any]:
        """Render as a JSON-compatible dict for downstream systems."""
        return {
            "estimate": self.estimate.to_wire_format()
            if hasattr(self.estimate, "to_wire_format")
            else self.estimate,
            "attestation": self.attestation.to_wire_format(),
            "overlaid_at": self.overlaid_at.isoformat(),
            "correlation_id": self.correlation_id,
            "schema_version": self.attestation.schema_version,
        }


def attach_attestation(
    estimate: Any,
    attestation: Any,
) -> AttributedEstimate:
    """Wrap a CarbonEstimate and an Attestation into an AttributedEstimate.

    This is the explicit step that says: "the iwi named here has
    attested for the use of this estimate under the listed consents."

    No transformations are applied to the estimate — the math stands
    on its own. The attestation is layered on. Downstream systems
    consume both.
    """
    return AttributedEstimate(estimate=estimate, attestation=attestation)


__all__ = ["AttributedEstimate", "attach_attestation"]
