"""kaitiaki-carbon — iwi-attested carbon estimation for whenua tōpū.

This package is part of Anamata Kāhui Limited's dev-tools arm.
See README.md for the why + how.

Public API:

    from kaitiaki_carbon import (
        estimate_carbon,
        Attestation,
        attach_attestation,
    )
"""

from kaitiaki_carbon.attest import Attestation, validate_attestation
from kaitiaki_carbon.attribution import attach_attestation
from kaitiaki_carbon.core import estimate_carbon

__version__ = "0.1.0"
__all__ = [
    "Attestation",
    "attach_attestation",
    "estimate_carbon",
    "validate_attestation",
]
