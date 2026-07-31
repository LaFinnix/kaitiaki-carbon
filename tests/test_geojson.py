"""Tests for the GeoJSON parcel parser.

The parser does *area computation*. That's a numerical method with a
ground-truth to compare against (the textbook spherical-excess formula
on a unit sphere). These tests verify correctness, edge cases, and the
handoff to estimate_carbon.
"""

from __future__ import annotations

import math

import pytest

from kaitiaki_carbon.geojson import (
    multipolygon_area_m2,
    parse_parcel,
    polygon_area_m2,
)

# ----------------------------------------------------------------------
# Constants used for ground-truth checks
# ----------------------------------------------------------------------

# At the equator, 1° of latitude ≈ 1° of longitude ≈ 111,319.49 m.
# So 1° × 1° at the equator ≈ 12,392,300,000 m² = 1,239,230 ha.
# Our L'Huilier-Borchardt formula should be within 0.5%.
_DEG_TO_M_AT_EQUATOR = 111319.49


def _expected_area_ha(rect: list[list[float]], lat_deg: float) -> float:
    """Compute the expected area of a small rectangular polygon.

    For a rectangle of dlon × dlat degrees centred at lat_deg latitude::
        height_m ≈ dlat * 111 km
        width_m  ≈ dlon * 111 km * cos(lat_deg)
        area_m2  ≈ height_m * width_m
    Accurate to within ~0.5% for parcels under 1°×1°.
    """
    # Find lon/lat extent
    lons = [p[0] for p in rect]
    lats = [p[1] for p in rect]
    dlon = max(lons) - min(lons)
    dlat = max(lats) - min(lats)
    height_m = dlat * 111320.0
    width_m = dlon * 111320.0 * math.cos(math.radians(lat_deg))
    return height_m * width_m / 10000.0  # m² → ha


# ----------------------------------------------------------------------
# Tests for area computation
# ----------------------------------------------------------------------


class TestPolygonArea:
    """Polygon area computation accuracy and edge cases."""

    def test_degenerate_polygon_returns_zero(self) -> None:
        # 0, 1, 2 vertices → no real polygon
        for n in (0, 1, 2):
            coords = [[[0, 0]] * n]
            assert polygon_area_m2(coords) == 0.0

    def test_empty_coords_returns_zero(self) -> None:
        assert polygon_area_m2([]) == 0.0

    def test_triangle_returns_nonzero(self) -> None:
        coords = [[[0, 0], [0, 1], [1, 0], [0, 0]]]
        area_m2 = polygon_area_m2(coords)
        assert area_m2 > 0.0

    def test_square_at_equator_within_1_percent(self) -> None:
        # 1° × 1° at the equator. The L'Huilier-Borchardt should give
        # approximately 12,392 million m² (1,239,200 ha).
        rect = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
        area_m2 = polygon_area_m2([rect])
        expected = _DEG_TO_M_AT_EQUATOR**2
        # Allow 1% tolerance for the L'Huilier approximation at this scale
        assert abs(area_m2 - expected) / expected < 0.01

    def test_small_polygon_near_auckland_within_2_percent(self) -> None:
        # 0.02° × 0.02° near Auckland (lat -36.85°)
        # Expected area: 0.02° × 0.02° × cos(36.85°) × R² (in m²) ≈ 395 ha
        rect = [
            [174.76, -36.85],
            [174.78, -36.85],
            [174.78, -36.83],
            [174.76, -36.83],
            [174.76, -36.85],
        ]
        area_ha = polygon_area_m2([rect]) / 10000.0
        expected = _expected_area_ha(rect, lat_deg=-36.85)
        assert abs(area_ha - expected) / expected < 0.02

    def test_polygon_with_hole_subtracts(self) -> None:
        # An outer ring at 0.02°×0.02° minus a smaller hole.
        outer = [
            [174.76, -36.85],
            [174.78, -36.85],
            [174.78, -36.83],
            [174.76, -36.83],
            [174.76, -36.85],
        ]
        hole = [
            [174.765, -36.845],
            [174.775, -36.845],
            [174.775, -36.835],
            [174.765, -36.835],
            [174.765, -36.845],
        ]
        area_with_hole = polygon_area_m2([outer, hole])
        area_without_hole = polygon_area_m2([outer])
        # Adding a hole should reduce area
        assert area_with_hole < area_without_hole
        # The reduction equals the hole area
        assert math.isclose(
            area_without_hole - area_with_hole,
            polygon_area_m2([hole]),
            rel_tol=1e-9,
        )

    def test_winding_order_does_not_matter(self) -> None:
        # L'Huilier-Borchardt uses abs() so winding order is irrelevant
        coords_cw = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        coords_ccw = [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
        # Same area regardless of order
        assert math.isclose(
            polygon_area_m2(coords_cw),
            polygon_area_m2(coords_ccw),
            rel_tol=1e-9,
        )


class TestMultiPolygonArea:
    """MultiPolygon area = sum of polygon areas."""

    def test_empty_multipolygon(self) -> None:
        assert multipolygon_area_m2([]) == 0.0

    def test_single_polygon_multipolygon(self) -> None:
        # Same as a Polygon of the same coords
        coords = [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]]
        area = multipolygon_area_m2(coords)
        poly_area = polygon_area_m2(coords[0])
        assert math.isclose(area, poly_area, rel_tol=1e-9)

    def test_multiple_polygons_sum(self) -> None:
        # Two adjacent squares at Auckland. Their combined area should
        # equal the sum of their individual areas.
        poly1 = [
            [
                [174.76, -36.85],
                [174.78, -36.85],
                [174.78, -36.83],
                [174.76, -36.83],
                [174.76, -36.85],
            ]
        ]
        poly2 = [
            [
                [174.79, -36.85],
                [174.81, -36.85],
                [174.81, -36.83],
                [174.79, -36.83],
                [174.79, -36.85],
            ]
        ]
        combined = multipolygon_area_m2([poly1, poly2])
        indiv = polygon_area_m2(poly1) + polygon_area_m2(poly2)
        assert math.isclose(combined, indiv, rel_tol=1e-9)


# ----------------------------------------------------------------------
# Tests for parse_parcel
# ----------------------------------------------------------------------


class TestParseParcel:
    """parse_parcel converts inputs to normalised parcel dicts."""

    def test_bare_polygon_returns_normalised(self) -> None:
        polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        parcel = parse_parcel(polygon)
        assert "id" in parcel
        assert "area_ha" in parcel
        assert "trees" in parcel
        assert parcel["trees"] == []
        assert parcel["area_ha"] > 0.0

    def test_bare_multipolygon_returns_normalised(self) -> None:
        mp = {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]],
        }
        parcel = parse_parcel(mp)
        assert parcel["area_ha"] > 0.0

    def test_feature_with_id_and_trees(self) -> None:
        feature = {
            "type": "Feature",
            "id": "tapuwae-1A",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
            "properties": {
                "trees": [
                    {"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1},
                ],
            },
        }
        parcel = parse_parcel(feature)
        assert parcel["id"] == "tapuwae-1A"
        assert len(parcel["trees"]) == 1
        assert parcel["trees"][0]["spcd"] == 202

    def test_feature_id_falls_back_to_properties(self) -> None:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
            "properties": {"name": "custom-id", "trees": []},
        }
        parcel = parse_parcel(feature)
        assert parcel["id"] == "custom-id"

    def test_feature_id_falls_back_to_unknown(self) -> None:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        }
        parcel = parse_parcel(feature)
        # Falls back to a default
        assert parcel["id"] == "feature-unnamed"

    def test_already_normalised_parcel_passes_through(self) -> None:
        existing = {"id": "x", "area_ha": 5.0, "trees": []}
        result = parse_parcel(existing)
        assert result == existing

    def test_already_normalised_without_area_raises(self) -> None:
        existing = {"id": "x", "trees": []}
        with pytest.raises(ValueError, match="area_ha"):
            parse_parcel(existing)

    def test_unrecognised_payload_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_parcel({"random": "stuff"})

    def test_area_ha_override_in_features_properties(self) -> None:
        # If the user supplied an area_ha in features.properties, honour it
        # over the computed area.
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
            "properties": {"area_ha": 42.5},
        }
        parcel = parse_parcel(feature)
        assert parcel["area_ha"] == 42.5


# ----------------------------------------------------------------------
# Integration tests — parse_parcel → estimate_carbon
# ----------------------------------------------------------------------


class TestGeojsonEndToEnd:
    """The full pipeline from GeoJSON Feature to CarbonEstimate."""

    def test_feature_round_trip_to_estimate(self) -> None:
        # A small parcel near Auckland with 1 tree.
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [174.76, -36.85],
                        [174.78, -36.85],
                        [174.78, -36.83],
                        [174.76, -36.83],
                        [174.76, -36.85],
                    ]
                ],
            },
            "properties": {
                "trees": [
                    {"spcd": 202, "dia": 30.0, "ht": 25.0, "statuscd": 1},
                ],
            },
        }
        parcel = parse_parcel(feature)

        # Now run the actual estimator
        from kaitiaki_carbon import estimate_carbon

        est = estimate_carbon(parcel)
        assert est.parcel_id == "feature-unnamed"
        assert est.area_ha > 0.0
        assert est.estimate_total_tCO2e > 0.0
        assert est.tree_count == 1
        assert est.species_count == 1
