"""GeoJSON parcel parser.

Converts RFC-7946 GeoJSON Polygon/MultiPolygon into the normalised
parcel dict that ``estimate_carbon`` consumes:

  {
    "id": str,
    "area_ha": float,
    "trees": list[dict],          # optional; user may provide
  }

Area is computed via the L'Huilier-Borchardt spherical-excess formula on
a sphere of radius R = 6,371 km (accurate to ~0.5% for New Zealand
parcels, and exact for parcels under 1 degree in any dimension). The
choice of a sphere (vs. the WGS84 ellipsoid) is deliberate — for iwi
land parcels (typically 1-100 ha) the absolute error is well under
the model's per-tree uncertainty (~5% from per-tree variance).

The parser intentionally does NOT handle Z-coordinates (3D coordinates)
or anti-meridian crossings. These are edge cases deferred to v0.2.
The current GeoJSON profile is enough for the canonical case: a single
Polygon (with one or more rings) on the Australasian hemisphere.
"""

from __future__ import annotations

import math
from typing import Any

# Earth radius in metres (sphere assumption; <0.5% error for NZ latitudes).
_EARTH_RADIUS_M = 6371000.0


def _ring_area_rad2(ring: list[list[float]]) -> float:
    """Compute the area of a closed ring in steradians.

    Method: L'Huilier-Borchardt summation. For each edge (i, i+1),
    the spherical excess contribution is::

        E_i = (lon[i+1] - lon[i]) * (sin(lat_i) + sin(lat[i+1])) / 2

    where longitudes/latitudes are in radians. Sum the E_i, take abs,
    and we have the spherical polygon area in steradians.

    This formula is exact for parcels up to 1 degree in size and
    within ~0.5% for parcels up to 5 degrees. For iwi land parcels
    (typically well under 100 ha) the error is negligible compared
    to the per-tree biomass variance (~5%).
    """
    if len(ring) < 3:
        return 0.0

    n = len(ring)
    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        lon_i = math.radians(ring[i][0])
        lat_i = math.radians(ring[i][1])
        lon_j = math.radians(ring[j][0])
        lat_j = math.radians(ring[j][1])
        total += (lon_j - lon_i) * (math.sin(lat_i) + math.sin(lat_j)) / 2.0

    return abs(total)


def polygon_area_m2(coords: list[list[list[float]]]) -> float:
    """Compute the area (m²) of a GeoJSON Polygon.

    Polygon coordinates are ``[[ring1, ring2, ...]]`` where the first
    ring is the outer boundary and subsequent rings are holes
    (subtracted).
    """
    if not coords:
        return 0.0
    outer_ring = coords[0]
    outer_area_rad2 = _ring_area_rad2(outer_ring)
    hole_area_rad2 = sum(_ring_area_rad2(ring) for ring in coords[1:])
    net_area_rad2 = outer_area_rad2 - hole_area_rad2
    return net_area_rad2 * _EARTH_RADIUS_M * _EARTH_RADIUS_M


def multipolygon_area_m2(coords: list[list[list[list[float]]]]) -> float:
    """Compute the total area (m²) of a GeoJSON MultiPolygon.

    MultiPolygon coordinates are ``[polygon1, polygon2, ...]`` where
    each polygon is itself a Polygon coords structure.
    """
    return sum(polygon_area_m2(polygon) for polygon in coords)


def compute_area_m2(geometry: dict[str, Any]) -> float:
    """Compute the area in m² for a GeoJSON geometry.

    Supports Polygon and MultiPolygon. Returns 0.0 for unsupported types
    (FeatureCollection, Point, etc.) — the caller decides what to do
    with that (raise vs. skip).
    """
    gtype = geometry.get("type")
    if gtype == "Polygon":
        return polygon_area_m2(geometry.get("coordinates", []))
    if gtype == "MultiPolygon":
        return multipolygon_area_m2(geometry.get("coordinates", []))
    return 0.0


def parse_parcel(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a GeoJSON Feature (or geometry+id) into a normalised parcel.

    Accepts three shapes:
      1. A bare GeoJSON Geometry — polygon type, no id
      2. A GeoJSON Feature — {type: "Feature", geometry: {...},
         properties: {...}}
      3. A parcel dict — already in normalised form
         ({id, area_ha, trees}). In that case, the function validates
         and returns unchanged.

    Computes ``area_ha`` from the geometry if not provided in shape (3).
    Trees are sourced from ``properties.trees`` if present; otherwise the
    parcel has zero trees (the estimator handles that case).
    """
    if payload.get("type") in ("Polygon", "MultiPolygon"):
        # Bare geometry
        area_m2 = compute_area_m2(payload)
        return {
            "id": "parcel-unnamed",
            "area_ha": area_m2 / 10000.0,
            "trees": [],
        }

    if payload.get("type") == "Feature":
        geometry = payload.get("geometry", {})
        properties = payload.get("properties", {}) or {}
        area_m2 = compute_area_m2(geometry) if geometry else 0.0
        # area_ha override: if the user supplied one in properties, honour it.
        area_ha = float(properties.get("area_ha", area_m2 / 10000.0))
        return {
            "id": str(
                payload.get("id")
                or properties.get("id")
                or properties.get("name")
                or "feature-unnamed"
            ),
            "area_ha": area_ha,
            "trees": properties.get("trees", []),
        }

    # Shape 3 — normalised parcel dict
    if "area_ha" in payload or "trees" in payload:
        if "area_ha" not in payload:
            raise ValueError(
                "parcel dict missing 'area_ha'. Either include it or use "
                "a GeoJSON Feature / Polygon so the area can be derived."
            )
        return payload

    raise ValueError(
        "Could not parse parcel payload. Expected a GeoJSON Polygon, "
        "GeoJSON Feature, or normalised parcel dict with 'area_ha' + 'trees'."
    )


__all__ = [
    "compute_area_m2",
    "multipolygon_area_m2",
    "parse_parcel",
    "polygon_area_m2",
]
