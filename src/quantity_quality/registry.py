from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional

from .units import split_unit

CARRIER_REGISTRY_VERSION = "0.3"


@dataclass(frozen=True)
class CarrierRegistryEntry:
    """One carrier suffix from the Quantity + Quality registry."""

    suffix: str
    meaning: str
    family: str
    reporting_implication: str
    required_metadata: tuple[str, ...] = field(default_factory=tuple)
    examples: tuple[str, ...] = field(default_factory=tuple)
    core: bool = True

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["required_metadata"] = list(self.required_metadata)
        payload["examples"] = list(self.examples)
        return payload


CORE_CARRIER_REGISTRY: tuple[CarrierRegistryEntry, ...] = (
    CarrierRegistryEntry(
        suffix="_e",
        meaning="electricity",
        family="electrical",
        reporting_implication="High-grade work potential at the delivery boundary; fx is normally 1 unless boundary losses are included.",
        examples=("MWh_e", "MW_e"),
    ),
    CarrierRegistryEntry(
        suffix="_m",
        meaning="mechanical or shaft work",
        family="mechanical",
        reporting_implication="Separate from electricity so shaft work is not mislabeled as electrical work.",
        examples=("MWh_m", "MW_m"),
    ),
    CarrierRegistryEntry(
        suffix="_em",
        meaning="stored or transmitted electromagnetic field energy",
        family="electromagnetic",
        reporting_implication="Use for field energy or Poynting flux at a declared boundary; incoherent photon radiation is reported as _rad.",
        required_metadata=("field or flux model", "boundary", "material model when applicable"),
        examples=("kWh_em", "J_em"),
    ),
    CarrierRegistryEntry(
        suffix="_th",
        meaning="thermal energy",
        family="thermal",
        reporting_implication="Temperature grade is represented by fx and metadata, not by separate low/high-temperature suffixes.",
        required_metadata=("source temperature", "reference sink"),
        examples=("MWh_th", "kWh_th", "MW_th"),
    ),
    CarrierRegistryEntry(
        suffix="_solar",
        meaning="incident solar radiation",
        family="radiative",
        reporting_implication="Use for solar resource at a declared receiving boundary; PV output is MWh_e and solar-thermal delivery is MWh_th.",
        required_metadata=("receiving boundary", "radiation model or spectrum"),
        examples=("MWh_solar", "W_solar"),
    ),
    CarrierRegistryEntry(
        suffix="_rad",
        meaning="non-solar radiation",
        family="radiative",
        reporting_implication="Use for a declared blackbody, coherent, or spectral radiation model; source state and receiving boundary are required.",
        required_metadata=("radiation model", "source state", "receiving boundary"),
        examples=("MWh_rad", "W_rad"),
    ),
    CarrierRegistryEntry(
        suffix="_cooling",
        meaning="cooling-service heat removal",
        family="thermal service",
        reporting_implication="A service-demand quantity rather than stored cold; quality depends on cold and heat-rejection temperatures.",
        required_metadata=("cold-service temperature", "heat-rejection temperature"),
        examples=("MWh_cooling", "ton_hour_cooling"),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_CH4",
        meaning="methane on HHV basis",
        family="chemical",
        reporting_implication="Recommended public methane basis; composition and reference table are metadata when material.",
        required_metadata=("HHV basis", "chemical-exergy table"),
        examples=("MWh_HHV_CH4", "MMBtu_HHV_CH4"),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_CH4",
        meaning="methane on LHV basis",
        family="chemical",
        reporting_implication="Explicitly labels a denominator that may yield fx greater than 1.",
        required_metadata=("LHV basis", "chemical-exergy table"),
        examples=("MWh_LHV_CH4", "MMBtu_LHV_CH4"),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_NG",
        meaning="natural gas mixture on HHV basis",
        family="chemical",
        reporting_implication="Use for commodity gas mixtures rather than pure methane; gas quality belongs in metadata.",
        required_metadata=("HHV basis", "composition or tariff gas quality"),
        examples=("MWh_HHV_NG", "MMBtu_HHV_NG"),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_H2",
        meaning="hydrogen on HHV basis",
        family="chemical",
        reporting_implication="Recommended public hydrogen basis for cross-sector comparisons.",
        required_metadata=("HHV basis", "water reference state"),
        examples=("MWh_HHV_H2",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_H2",
        meaning="hydrogen on LHV basis",
        family="chemical",
        reporting_implication="Use only when LHV is the declared denominator.",
        required_metadata=("LHV basis", "water reference state"),
        examples=("MWh_LHV_H2",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_NH3",
        meaning="ammonia on HHV basis",
        family="chemical",
        reporting_implication="Chemical-carrier token; cracking pathway and end-use boundary remain metadata.",
        required_metadata=("HHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_HHV_NH3",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_CH3OH",
        meaning="methanol on HHV basis",
        family="chemical",
        reporting_implication="Liquid synthetic-fuel token; purity and water content should be declared when material.",
        required_metadata=("HHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_HHV_CH3OH",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_diesel",
        meaning="diesel on HHV basis",
        family="chemical",
        reporting_implication="Commodity petroleum-product token; grade, sulfur specification, blend, and table source are metadata.",
        required_metadata=("HHV basis", "grade or table source"),
        examples=("MWh_HHV_diesel",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_diesel",
        meaning="diesel on LHV basis",
        family="chemical",
        reporting_implication="Explicit LHV petroleum-product token for existing fuel accounting systems.",
        required_metadata=("LHV basis", "grade or table source"),
        examples=("MWh_LHV_diesel",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_gasoline",
        meaning="gasoline on HHV basis",
        family="chemical",
        reporting_implication="Commodity petroleum-product token; blendstock and ethanol content are metadata.",
        required_metadata=("HHV basis", "blend or table source"),
        examples=("MWh_HHV_gasoline",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_gasoline",
        meaning="gasoline on LHV basis",
        family="chemical",
        reporting_implication="Explicit LHV gasoline token for existing fuel accounting systems.",
        required_metadata=("LHV basis", "blend or table source"),
        examples=("MWh_LHV_gasoline",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_crude",
        meaning="crude oil on HHV basis",
        family="chemical",
        reporting_implication="Heterogeneous feedstock token; assay, API gravity, sulfur, and table source are metadata.",
        required_metadata=("HHV basis", "assay or table source"),
        examples=("MWh_HHV_crude",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_crude",
        meaning="crude oil on LHV basis",
        family="chemical",
        reporting_implication="Explicit LHV crude token for datasets already using LHV denominators.",
        required_metadata=("LHV basis", "assay or table source"),
        examples=("MWh_LHV_crude",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_coal",
        meaning="coal on HHV basis",
        family="chemical",
        reporting_implication="Heterogeneous solid-fuel token; rank, moisture, ash, sulfur, and analysis method are metadata.",
        required_metadata=("HHV basis", "rank or proximate analysis"),
        examples=("MWh_HHV_coal",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_coal",
        meaning="coal on LHV basis",
        family="chemical",
        reporting_implication="Explicit LHV coal token for datasets already using LHV denominators.",
        required_metadata=("LHV basis", "rank or proximate analysis"),
        examples=("MWh_LHV_coal",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_biomass",
        meaning="biomass on HHV basis",
        family="chemical",
        reporting_implication="Heterogeneous biogenic-fuel token; moisture and feedstock class are mandatory for comparison.",
        required_metadata=("HHV basis", "moisture content", "feedstock class"),
        examples=("MWh_HHV_biomass",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_biomass",
        meaning="biomass on LHV basis",
        family="chemical",
        reporting_implication="Moisture, ash, feedstock class, and as-received versus dry basis must be explicit.",
        required_metadata=("LHV basis", "moisture content", "feedstock class"),
        examples=("MWh_LHV_biomass",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_biogas",
        meaning="biogas mixture on HHV basis",
        family="chemical",
        reporting_implication="Methane, carbon-dioxide, moisture, and contaminant composition determine both quantity and quality.",
        required_metadata=("HHV basis", "composition", "chemical-exergy table"),
        examples=("MWh_HHV_biogas",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_biogas",
        meaning="biogas mixture on LHV basis",
        family="chemical",
        reporting_implication="Use only with declared composition and LHV denominator.",
        required_metadata=("LHV basis", "composition", "chemical-exergy table"),
        examples=("MWh_LHV_biogas",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_syngas",
        meaning="synthesis-gas mixture on HHV basis",
        family="chemical",
        reporting_implication="Composition and water content are required because syngas is not a fixed substance.",
        required_metadata=("HHV basis", "composition", "chemical-exergy table"),
        examples=("MWh_HHV_syngas",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_syngas",
        meaning="synthesis-gas mixture on LHV basis",
        family="chemical",
        reporting_implication="Composition and LHV basis must travel with the quantity.",
        required_metadata=("LHV basis", "composition", "chemical-exergy table"),
        examples=("MWh_LHV_syngas",),
    ),
    CarrierRegistryEntry(
        suffix="_HHV_C2H5OH",
        meaning="ethanol on HHV basis",
        family="chemical",
        reporting_implication="Purity, water content, and blend fraction remain metadata.",
        required_metadata=("HHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_HHV_C2H5OH",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_C2H5OH",
        meaning="ethanol on LHV basis",
        family="chemical",
        reporting_implication="Purity, water content, and blend fraction remain metadata.",
        required_metadata=("LHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_LHV_C2H5OH",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_CH3OH",
        meaning="methanol on LHV basis",
        family="chemical",
        reporting_implication="Purity and water content should be declared when material.",
        required_metadata=("LHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_LHV_CH3OH",),
    ),
    CarrierRegistryEntry(
        suffix="_LHV_NH3",
        meaning="ammonia on LHV basis",
        family="chemical",
        reporting_implication="Purity, cracking pathway, and nitrogen reference environment remain metadata.",
        required_metadata=("LHV basis", "purity", "chemical-exergy table"),
        examples=("MWh_LHV_NH3",),
    ),
    CarrierRegistryEntry(
        suffix="_fission",
        meaning="nuclear fission energy potential",
        family="nuclear",
        reporting_implication="Fuel-inventory token only; reactor heat is MWh_th and nuclear electricity is MWh_e.",
        required_metadata=("isotope", "enrichment", "burnup", "fuel-cycle boundary"),
        examples=("MWh_fission",),
    ),
    CarrierRegistryEntry(
        suffix="_nuclear",
        meaning="total released nuclear-reaction product energy",
        family="nuclear",
        reporting_implication="Use only at a reaction-product boundary with a declared Q-value and product-channel accounting.",
        required_metadata=("reaction", "Q-value", "reaction count or extent", "product channels"),
        examples=("MWh_nuclear",),
    ),
    CarrierRegistryEntry(
        suffix="_neutron",
        meaning="neutron kinetic-energy stream",
        family="nuclear particle",
        reporting_implication="Neutrons are particles, not electromagnetic radiation; transport and deposition belong in downstream process records.",
        required_metadata=("energy spectrum or reaction channel", "boundary"),
        examples=("MWh_neutron",),
    ),
    CarrierRegistryEntry(
        suffix="_charged_particle",
        meaning="charged-particle kinetic-energy stream",
        family="nuclear particle",
        reporting_implication="Use for alpha, proton, ion, or other charged-particle kinetic energy at its physical boundary.",
        required_metadata=("particle species", "energy spectrum or reaction channel", "boundary"),
        examples=("MWh_charged_particle",),
    ),
    CarrierRegistryEntry(
        suffix="_neutrino",
        meaning="neutrino energy stream",
        family="nuclear particle",
        reporting_implication="Physical energy may leave the boundary while practical capture is negligible; the declared factor must match that boundary.",
        required_metadata=("reaction channel", "boundary", "declared accessibility convention"),
        examples=("MWh_neutrino",),
    ),
    CarrierRegistryEntry(
        suffix="_plasma",
        meaning="plasma state energy inventory",
        family="plasma",
        reporting_implication="A composite inventory of declared species, distributions, motion, internal state, and optional field energy.",
        required_metadata=(
            "species",
            "distribution model",
            "reference state",
            "volume",
            "boundary",
        ),
        examples=("kWh_plasma", "MJ_plasma"),
    ),
)


def list_carrier_registry(*, family: Optional[str] = None) -> tuple[CarrierRegistryEntry, ...]:
    """Return carrier registry entries, optionally filtered by family."""

    if family is None:
        return CORE_CARRIER_REGISTRY
    query = family.lower()
    return tuple(entry for entry in CORE_CARRIER_REGISTRY if entry.family.lower() == query)


def get_carrier_entry(suffix_or_unit: str) -> CarrierRegistryEntry:
    """Return the registry entry matching a suffix or typed unit."""

    suffix = carrier_suffix(suffix_or_unit)
    for entry in CORE_CARRIER_REGISTRY:
        if entry.suffix.lower() == suffix.lower():
            return entry
    raise KeyError(f"unknown carrier suffix: {suffix}")


def carrier_suffix(suffix_or_unit: str) -> str:
    """Extract a registry suffix from `_th` or `MWh_th` style input."""

    if not suffix_or_unit:
        raise ValueError("suffix_or_unit is required")
    text = suffix_or_unit.strip()
    if text.startswith("_"):
        return text
    _, suffix = split_unit(text)
    if not suffix:
        raise ValueError(f"unit has no carrier suffix: {suffix_or_unit}")
    return suffix


def carrier_family(unit: str) -> Optional[str]:
    """Return the registry family for a typed unit, if known."""

    try:
        return get_carrier_entry(unit).family
    except (KeyError, ValueError):
        return None


def registry_as_dict(records: Optional[Iterable[CarrierRegistryEntry]] = None) -> list[dict]:
    """Return registry entries as JSON-serializable dictionaries."""

    return [entry.as_dict() for entry in (records or CORE_CARRIER_REGISTRY)]
