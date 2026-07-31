"""kaitiaki-carbon CLI.

Entry point: `kaitiaki-carbon` (registered in pyproject.toml).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from kaitiaki_carbon.attest import Attestation, validate_attestation
from kaitiaki_carbon.attribution import attach_attestation
from kaitiaki_carbon.core import estimate_carbon
from kaitiaki_carbon.geojson import parse_parcel
from kaitiaki_carbon.i18n import t

__version__ = "0.1.0"


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """kaitiaki-carbon — iwi-attested carbon estimation."""
    pass


@main.command()
@click.argument("parcel_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--attestation",
    "attestation_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to an attestation JSON document.",
)
@click.option(
    "--locale",
    "locale",
    type=click.Choice(["en", "mi"]),
    default="en",
    help="Display locale for CLI messages.",
)
@click.option(
    "--verbose",
    "verbose",
    is_flag=True,
    default=False,
    help="Print full working output (not just the headline estimate).",
)
def estimate(
    parcel_path: Path,
    attestation_path: Path | None,
    locale: str,
    verbose: bool,
) -> None:
    """Compute biomass → stored carbon → CO2-equivalent for a parcel."""
    click.echo(t("cli.estimate.running", locale))

    try:
        raw = json.loads(parcel_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        click.echo(t("cli.estimate.input_missing", locale, path=str(parcel_path), reason=str(exc)))
        sys.exit(1)

    # Phase 2: parse_parcel accepts GeoJSON Polygon, MultiPolygon, Feature,
    # or pre-normalised parcel dicts.
    try:
        parcel = parse_parcel(raw)
    except ValueError as exc:
        click.echo(
            t(
                "cli.estimate.input_not_polygon",
                locale,
                type=str(exc),
            )
        )
        sys.exit(1)

    parcel_id = parcel.get("id") or parcel_path.stem
    if not parcel.get("id"):
        parcel["id"] = parcel_id

    try:
        carbon_estimate = estimate_carbon(parcel)
    except NotImplementedError:
        click.echo(
            "[estimate_carbon stub] Phase 1 pyfia fork not yet implemented.",
            err=True,
        )
        sys.exit(2)
    except ValueError as exc:
        click.echo(f"Validation failed: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover — defensive
        click.echo(f"Estimate failed: {exc}", err=True)
        sys.exit(1)

    attestation: Attestation | None = None
    if attestation_path is not None:
        try:
            payload = json.loads(attestation_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            click.echo(
                t(
                    "cli.errors.attestation_read",
                    locale,
                    path=str(attestation_path),
                    reason=str(exc),
                ),
                err=True,
            )
            sys.exit(1)

        try:
            attestation = validate_attestation(payload)
        except Exception as exc:
            click.echo(
                t("cli.estimate.schema_warn", locale, errors=str(exc)),
                err=True,
            )
            # Proceed with the raw payload to allow v0.2 migration.
            try:
                attestation = Attestation.model_construct(**payload)
            except Exception:
                attestation = None

    attributed = (
        attach_attestation(carbon_estimate, attestation) if attestation else carbon_estimate
    )

    # Headline: estimate + (if attested) provenance line.
    click.echo(
        t(
            "cli.estimate.result_headline",
            locale,
            estimate_tCO2e=carbon_estimate.estimate_total_tCO2e,
            ci_low=carbon_estimate.ci_95_pct_total[0],
            ci_high=carbon_estimate.ci_95_pct_total[1],
        )
    )

    if attestation is not None:
        click.echo(
            t(
                "cli.estimate.result_attested",
                locale,
                iwi=attestation.iwi,
                hapū_or_iwi=(attestation.hapū or "iwi-level"),
                kaitiaki=attestation.kaitiaki,
            )
        )
    else:
        click.echo(t("cli.estimate.no_attestation", locale))

    if verbose:
        click.echo(
            json.dumps(
                attributed.to_wire_format() if attestation else carbon_estimate.to_wire_format(),
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
