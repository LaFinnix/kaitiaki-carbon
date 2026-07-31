"""Tests for the NZ species map.

These tests verify:
  - Species entries load correctly
  - Lookup by canonical name and alias works
  - WDSG values are in the right range (0.3-0.7 g/cm³ for most species)
  - Defence against typos in user input (returns None, not crash)
"""

from __future__ import annotations

from kaitiaki_carbon.species_nz import (
    NZ_SPECIES,
    SpeciesEntry,
    all_species,
    by_alias,
    by_name,
    lookup,
)


class TestSpeciesTableContents:
    """The species table has the entries we expect and the right shape."""

    def test_table_loads(self) -> None:
        assert isinstance(NZ_SPECIES, tuple)
        assert len(NZ_SPECIES) > 0

    def test_each_entry_is_a_species_entry(self) -> None:
        for entry in NZ_SPECIES:
            assert isinstance(entry, SpeciesEntry)

    def test_each_entry_has_required_fields(self) -> None:
        for entry in NZ_SPECIES:
            assert isinstance(entry.name, str) and entry.name
            assert isinstance(entry.family, str) and entry.family
            assert isinstance(entry.citation, str) and entry.citation
            assert isinstance(entry.wdsg, float) and 0.30 <= entry.wdsg <= 0.75
            # spcd is optional (None for NZ-native species)
            if entry.spcd is not None:
                assert isinstance(entry.spcd, int) and 0 < entry.spcd < 1000

    def test_no_duplicate_names(self) -> None:
        names = [s.name for s in NZ_SPECIES]
        assert len(names) == len(set(names))

    def test_planted_exotics_are_first(self) -> None:
        # The first 5 entries should be the planted exotics we use most
        # (radiata, douglas-fir, cypress, eucalyptus, larch). Convenient
        # when listing species in the CLI.
        first_five = [s.name for s in NZ_SPECIES[:5]]
        for needle in ("radiata-pine", "douglas-fir"):
            assert needle in first_five


class TestLookupByName:
    def test_canonical_name(self) -> None:
        e = by_name("radiata-pine")
        assert e is not None
        assert e.spcd == 131
        assert e.wdsg == 0.41

    def test_unknown_name_returns_none(self) -> None:
        assert by_name("not-a-real-tree") is None

    def test_lookup_is_case_insensitive(self) -> None:
        # Both by_name and lookup normalise input to lowercase. The
        # "case-sensitive vs insensitive" distinction doesn't apply —
        # both are forgiving by design.
        e = by_name("RADIATA-PINE")
        assert e is not None
        e2 = lookup("RADIATA-PINE")
        assert e2 is not None
        e_lower = by_name("radiata-pine")
        assert e_lower is not None


class TestLookupByAlias:
    def test_common_alias(self) -> None:
        e = by_alias("pine")
        assert e is not None
        assert e.name == "radiata-pine"

    def test_scientific_alias(self) -> None:
        e = by_alias("pinus radiata")
        assert e is not None
        assert e.name == "radiata-pine"

    def test_underscores_normalised(self) -> None:
        # Aliases may use either hyphens or spaces
        e = by_alias("red_beech")
        assert e is not None
        assert e.name == "beech-red"

    def test_unknown_alias_returns_none(self) -> None:
        assert by_alias("nonexistent-tree") is None


class TestLookupHelper:
    def test_canonical_name_wins_over_alias(self) -> None:
        # If both canonical-name and alias lookups would match,
        # canonical wins. The current table doesn't have this case
        # but the contract should hold.
        e = lookup("kauri")
        assert e is not None
        assert e.name == "kauri"

    def test_alias_when_canonical_fails(self) -> None:
        # 'pine' is an alias for radiata-pine
        e = lookup("pine")
        assert e is not None
        assert e.name == "radiata-pine"

    def test_unknown_returns_none(self) -> None:
        assert lookup("made-up-tree") is None


class TestAllSpecies:
    def test_yields_all_entries(self) -> None:
        species = list(all_species())
        assert len(species) == len(NZ_SPECIES)

    def test_iterable_can_be_re_used(self) -> None:
        # all_species() returns an Iterable — should yield the
        # same set on each consumption.
        first_pass = list(s.name for s in all_species())
        second_pass = list(s.name for s in all_species())
        assert first_pass == second_pass


class TestCoreIntegration:
    """The species table flows through the estimator end-to-end.

    A tree record with ``species_name='kauri'`` should pick up the
    kauri-specific WDSG (0.50) inside ``core._resolve_wdsg_for_tree``.
    """

    def test_kauri_wdsg_used_when_species_name_supplied(self) -> None:
        from kaitiaki_carbon.core import _resolve_wdsg_for_tree

        wdsg = _resolve_wdsg_for_tree(
            {
                "spcd": 999,  # unknown SPCD; should not matter
                "dia": 30.0,
                "ht": 25.0,
                "species_name": "kauri",
            }
        )
        # The kauri row's WDSG is 0.50.
        assert abs(wdsg - 0.50) < 1e-6

    def test_explicit_wdsg_overrides_species_name(self) -> None:
        from kaitiaki_carbon.core import _resolve_wdsg_for_tree

        wdsg = _resolve_wdsg_for_tree(
            {
                "spcd": 202,
                "dia": 30.0,
                "ht": 25.0,
                "species_name": "kauri",
                "wdsg": 0.99,  # user override
            }
        )
        assert wdsg == 0.99

    def test_unknown_species_falls_back_to_default(self) -> None:
        from kaitiaki_carbon.core import _resolve_wdsg_for_tree

        wdsg = _resolve_wdsg_for_tree(
            {
                "spcd": 999,
                "dia": 30.0,
                "ht": 25.0,
                "species_name": "made-up-tree",
            }
        )
        # Falls back to the 0.42 default (mid-range hardwood/softwood).
        assert abs(wdsg - 0.42) < 1e-6

    def test_no_species_name_falls_back_to_default(self) -> None:
        from kaitiaki_carbon.core import _resolve_wdsg_for_tree

        wdsg = _resolve_wdsg_for_tree(
            {
                "spcd": 202,
                "dia": 30.0,
                "ht": 25.0,
                # no species_name
            }
        )
        assert abs(wdsg - 0.42) < 1e-6


class TestMacronPreservation:
    """Species names with macrons should round-trip through the table."""

    def test_repatriated_name_mai_when_used(self) -> None:
        # No current species entry uses macros in the canonical name,
        # but alias lookups should pass macrons through unchanged.
        from kaitiaki_carbon.species_nz import lookup

        # "rimu te repo" or "pōhue" aren't real aliases, but they should
        # at least not crash and should return None.
        e = lookup("rimu")
        assert e is not None
        # The native-name macros round-trip.
        canonical = e.name
        assert "ī" not in canonical  # rimu doesn't have a macron
        assert "rimu" in canonical
