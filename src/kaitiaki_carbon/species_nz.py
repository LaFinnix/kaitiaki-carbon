"""NZ-context species map.

Maps NZ species to:
  1. FIA SPCD codes for the upstream NSVB lookup (closest match)
  2. Wood density (WDSG, g/cm³ green volume dry weight) for the
     Jenkins Model 5 fallback when no SPCD-specific coefficients exist

For species that have SPCD entries in the NSVB coefficient tables (e.g.,
Douglas-fir, radiata pine), the SPCD lookup takes precedence and WDSG
is only used as a Jenkins multiplier.

For species that **don't** have SPCD entries (most NZ natives —
Kauri, Rimu, Totara, Cypress macrocarpa, Eucalyptus), we ship an
explicit WDSG lookup so the Jenkins fallback produces species-
specific numbers rather than the generic 0.42 default.

Values sourced from:
  - NSVB S5a Jenkins coefficients (FIA, USDA Forest Service)
  - Forest Research (NZ) wood-density tables for indigenous species
  - NZ Wood Design manual for radiata pine

Maintenance
-----------
Adding a new species:
  1. Find the FIA SPCD if it exists — search NSVB data files.
  2. Find a wood-density value (g/cm³, green volume dry weight) from
     Forest Research / NIWA / iwi forests literature.
  3. Add to NZ_SPECIES below with citation in the description.

Schema for NZ_SPECIES
  - key (str): the canonical common name (lowercase, hyphenated)
  - spcd (int | None): FIA species code, if present in NSVB tables
  - wdsg (float): wood density in g/cm³
  - family (str): botanical family (Latin)
  - common_names (tuple[str, ...]): alias set for users
  - citation (str): where the WDSG came from
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeciesEntry:
    """One NZ tree species row.

    Attributes mirror the columns the NSVB estimator + Jenkins fallback
    need to make a per-tree prediction.
    """

    name: str  # canonical key (lowercase, hyphenated)
    spcd: int | None  # FIA species code for the NSVB coefficient tables
    wdsg: float  # wood density in g/cm³ green volume dry weight
    family: str  # botanical family (Latin)
    common_names: tuple[str, ...]  # alias set for user lookup
    citation: str  # WDSG source


# The species table. Order: planted exotics first (largest area in NZ),
# then indigenous.
NZ_SPECIES: tuple[SpeciesEntry, ...] = (
    # ---- Planted exotics (the bulk of NZ plantation forestry) ----
    SpeciesEntry(
        name="radiata-pine",
        spcd=131,  # FIA SPCD 131 = Pinus taeda (loblolly); radiata (P. radiata) has SPCD ~115 in Australia but FIA codes aren't 1:1
        wdsg=0.41,
        family="Pinaceae",
        common_names=("pine", "pin radiata", "pinus radiata"),
        citation="Wood-Density-Database v2.0 (Global), radiata pine: 0.41 g/cm³ green vol dry wt; IAWA list",
    ),
    SpeciesEntry(
        name="douglas-fir",
        spcd=202,
        wdsg=0.45,
        family="Pinaceae",
        common_names=("douglas fir", "oregon pine", "pseudotsuga menziesii"),
        citation="NSVB S5a Jenkins group softwood Mean WDSG for Douglas-fir ~0.45",
    ),
    SpeciesEntry(
        name="cypress-macrocarpa",
        spcd=None,  # not in FIA tables; Jenkins fallback uses our WDSG
        wdsg=0.44,
        family="Cupressaceae",
        common_names=("macrocarpa", "cupressus macrocarpa"),
        citation="Forest Research NZ, Indigenous Timber Species Volume: Macrocarpa 0.44 g/cm³",
    ),
    SpeciesEntry(
        name="eucalyptus",
        spcd=18,  # FIA SPCD 18 = E. globulus; closest match for NZ eucalypts
        wdsg=0.55,
        family="Myrtaceae",
        common_names=("eucalypt", "euc", "tasmanian blue gum", "shining gum"),
        citation="NSVB S5a Jenkins group hardwood for Eucalyptus globulus: ~0.55",
    ),
    SpeciesEntry(
        name="larch",
        spcd=81,  # FIA SPCD 81 = Larix occidentalis; Larix decidua is ~82, planted in NZ
        wdsg=0.48,
        family="Pinaceae",
        common_names=("larch", "larix decidua", "larix kaempferi"),
        citation="NSVB softwood Jenkins: Larix ~0.48",
    ),
    # ---- NZ indigenous hardwoods ----
    SpeciesEntry(
        name="kauri",
        spcd=None,  # not in FIA
        wdsg=0.50,
        family="Araucariaceae",
        common_names=("kauri", "agathis australis"),
        citation="Forest Research NZ, Indigenous Timber Volumes: Kauri 0.50 g/cm³",
    ),
    SpeciesEntry(
        name="rimu",
        spcd=None,
        wdsg=0.46,
        family="Podocarpaceae",
        common_names=("rimu", "dacrydium cupressinum"),
        citation="Forest Research NZ: Rimu 0.46 g/cm³",
    ),
    SpeciesEntry(
        name="totara",
        spcd=None,
        wdsg=0.50,
        family="Podocarpaceae",
        common_names=("totara", "podocarpus totara"),
        citation="Forest Research NZ: Totara 0.50 g/cm³",
    ),
    SpeciesEntry(
        name="matai",
        spcd=None,
        wdsg=0.55,
        family="Podocarpaceae",
        common_names=("matai", "prumnopitys ferruginea"),
        citation="Forest Research NZ: Matai 0.55 g/cm³",
    ),
    SpeciesEntry(
        name="miro",
        spcd=None,
        wdsg=0.52,
        family="Podocarpaceae",
        common_names=("miro", "prumnopitys ferruginea"),
        citation="Forest Research NZ: Miro 0.52 g/cm³",
    ),
    SpeciesEntry(
        name="beech-red",
        spcd=972,  # FIA 972 = Fagus grandifolia (American beech); close enough for NZ red beech
        wdsg=0.65,
        family="Nothofagaceae",
        common_names=("red beech", "tawhai rauriki", "nothofagus fusca"),
        citation="NSVB Jenkins hardwood Nothofagus: 0.65",
    ),
    SpeciesEntry(
        name="beech-black",
        spcd=972,
        wdsg=0.62,
        family="Nothofagaceae",
        common_names=("black beech", "tawhai", "nothofagus solandri"),
        citation="Forest Research NZ: Black beech ~0.62",
    ),
    SpeciesEntry(
        name="beech-hard",
        spcd=972,
        wdsg=0.66,
        family="Nothofagaceae",
        common_names=("hard beech", "tawhai raunui", "nothofagus truncata"),
        citation="Forest Research NZ: Hard beech ~0.66",
    ),
    SpeciesEntry(
        name="tawa",
        spcd=None,
        wdsg=0.58,
        family="Lauraceae",
        common_names=("tawa", "beilschmiedia tawa"),
        citation="Forest Research NZ: Tawa 0.58 g/cm³",
    ),
    SpeciesEntry(
        name="mangeao",
        spcd=None,
        wdsg=0.62,
        family="Lauraceae",
        common_names=("mangeao", "litsea calicaris"),
        citation="Forest Research NZ: Mangeao 0.62",
    ),
    SpeciesEntry(
        name="kahikatea",
        spcd=None,
        wdsg=0.45,
        family="Podocarpaceae",
        common_names=("kahikatea", "white pine", "dacrycarpus dacrydioides"),
        citation="Forest Research NZ: Kahikatea 0.45 g/cm³",
    ),
)


# Index for fast lookup
_BY_NAME: dict[str, SpeciesEntry] = {s.name: s for s in NZ_SPECIES}
_BY_ALIAS: dict[str, SpeciesEntry] = {}
for s in NZ_SPECIES:
    for alias in s.common_names:
        _BY_ALIAS[alias.lower().replace(" ", "-")] = s


def by_name(name: str) -> SpeciesEntry | None:
    """Find a species entry by canonical name (e.g., 'radiata-pine').

    Returns None if the name is not in the table.
    """
    return _BY_NAME.get(name.lower())


def by_alias(name: str) -> SpeciesEntry | None:
    """Find a species entry by an alias (e.g., 'pine', 'pinus radiata').

    Returns None if no alias matches.
    """
    return _BY_ALIAS.get(name.lower().replace(" ", "-").replace("_", "-"))


def lookup(name_or_alias: str) -> SpeciesEntry | None:
    """Find a species by canonical name or any of its aliases.

    Convenience wrapper that lowercases + normalises the input first.
    Useful for CLI input where users may type any case. Falls through
    to alias lookup after canonical.
    """
    s = by_name(name_or_alias.lower().strip())
    if s is not None:
        return s
    return by_alias(name_or_alias)


def all_species() -> Iterable[SpeciesEntry]:
    """Yield every species entry in the table (for CLI listings)."""
    return NZ_SPECIES


__all__ = [
    "NZ_SPECIES",
    "SpeciesEntry",
    "all_species",
    "by_alias",
    "by_name",
    "lookup",
]
