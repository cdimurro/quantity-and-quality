from __future__ import annotations

import re
from typing import Tuple

JOULES_PER_MWH = 3.6e9
JOULES_PER_BTU_IT = 1055.05585262
MWH_PER_BTU_IT = JOULES_PER_BTU_IT / JOULES_PER_MWH
MWH_PER_US_THERM = 105_480_400.0 / JOULES_PER_MWH

ENERGY_TO_MWH = {
    "wh": 1e-6,
    "kwh": 1e-3,
    "mwh": 1.0,
    "gwh": 1e3,
    "twh": 1e6,
    "j": 1.0 / JOULES_PER_MWH,
    "kj": 1.0 / 3.6e6,
    "mj": 1.0 / 3600.0,
    "gj": 1.0 / 3.6,
    "tj": 1e3 / 3.6,
    "pj": 1e6 / 3.6,
    "ej": 1e9 / 3.6,
    # NIST International Table Btu and U.S. legal therm definitions. A U.S.
    # therm is not exactly 100,000 Btu_IT, so the two constants intentionally
    # differ by about 0.024 %.
    "btu": MWH_PER_BTU_IT,
    "mmbtu": 1_000_000.0 * MWH_PER_BTU_IT,
    "therm": MWH_PER_US_THERM,
    # Units that appear on real utility bills and building-management exports.
    # Without these a record parsed, produced a notation, and then had no
    # accessible_exergy_mwh at all — so the one column that makes rows comparable
    # was silently blank, which is the opposite of what the framework is for.
    "dekatherm": 10.0 * MWH_PER_US_THERM,
    "dth": 10.0 * MWH_PER_US_THERM,
    # Refrigeration ton-hour = 12,000 Btu. Spelled WITHOUT an underscore on
    # purpose: `split_unit` reads everything after the first underscore as a
    # carrier suffix, so `ton_hour` parses as the mass unit `ton` carrying a
    # `_hour` suffix, and the row then has no convertible energy at all.
    "tonhour": 12000.0 * MWH_PER_BTU_IT,
    "tonh": 12000.0 * MWH_PER_BTU_IT,
    "trh": 12000.0 * MWH_PER_BTU_IT,
}


# Units that measure VOLUME or MASS, not energy.
#
# An Exergy Factor is a ratio of work potential to ENERGY, so multiplying one by
# a volume is meaningless: `4100 gallons, fx = 1.060` reads like a result and is
# not one. These are named explicitly so the record can be refused with an
# explanation, rather than accepted into a notation that looks authoritative.
NON_ENERGY_UNITS = frozenset(
    {
        "gal",
        "gallon",
        "gallons",
        "l",
        "liter",
        "liters",
        "litre",
        "litres",
        "m3",
        "cubicmeter",
        "cubicmetre",
        "ft3",
        "cf",
        "scf",
        "ccf",
        "mcf",
        "mmcf",
        "bbl",
        "barrel",
        "barrels",
        "kg",
        "lb",
        "lbs",
        "pound",
        "pounds",
        "tonne",
        "tonnes",
        "shortton",
        "ton",
        "tons",
    }
)


# Fuel volumes whose UNIT NAMES THE FUEL, and so can be converted to energy
# through a published equivalent.
#
# A bare `gallons` still cannot: a gallon of what, at what heating value. But
# `scf(natural gas)` and `bbl(oil)` carry their fuel in the unit. The figures
# below are explicitly labelled statistical estimates: EIA's 2026 U.S. average
# heat contents for natural gas and crude oil, plus the separate nominal BOE
# convention. They are the same estimates exposed by the website.
#
# `basis` follows the paper, which recommends HHV as the default public fuel
# basis "because it is common in national energy statistics and keeps fx below
# unity for common combustion fuels", and requires any LHV denominator to be
# visible in the carrier suffix. Natural gas resolves to the HHV reference. The
# petroleum equivalent is paired with the crude reference the package actually
# ships, which is not an HHV figure — so the record says so rather than implying
# a basis it does not have.
# The package ships no natural-gas reference of its own, so gas volumes resolve
# to `methane-hhv` — the same approximation the carrier-phrase table already
# makes, and one the record states rather than hides.
# A volume alone never determines a fuel's exact energy content. These are
# explicitly versioned statistical estimates for convenience; calculated stream
# requests can always provide a measured heating value instead.
_EIA_2026_NATURAL_GAS_BTU_PER_SCF = 1036.0
_EIA_2026_CRUDE_OIL_MMBTU_PER_BBL = 5.689
_NOMINAL_BOE_MMBTU = 5.8

FUEL_VOLUME_UNITS = {
    "scf(natural gas)": (
        _EIA_2026_NATURAL_GAS_BTU_PER_SCF * MWH_PER_BTU_IT,
        "methane-hhv",
        "HHV",
        "1,036 Btu per scf (EIA 2026 estimated U.S. average)",
    ),
    "mcf(natural gas)": (
        1000.0 * _EIA_2026_NATURAL_GAS_BTU_PER_SCF * MWH_PER_BTU_IT,
        "methane-hhv",
        "HHV",
        "1.036 MMBtu per Mcf (EIA 2026 estimated U.S. average)",
    ),
    "mmcf(natural gas)": (
        1_000_000.0 * _EIA_2026_NATURAL_GAS_BTU_PER_SCF * MWH_PER_BTU_IT,
        "methane-hhv",
        "HHV",
        "1,036 MMBtu per MMcf (EIA 2026 estimated U.S. average)",
    ),
    # These abbreviations conventionally denote natural-gas billing volumes.
    # Keep the assumption explicit in the output rather than rejecting the units
    # after advertising them in the public changelog.
    "mcf": (
        1000.0 * _EIA_2026_NATURAL_GAS_BTU_PER_SCF * MWH_PER_BTU_IT,
        "methane-hhv",
        "HHV",
        "1.036 MMBtu per Mcf (EIA 2026 estimated U.S. average natural gas)",
    ),
    "mmcf": (
        1_000_000.0 * _EIA_2026_NATURAL_GAS_BTU_PER_SCF * MWH_PER_BTU_IT,
        "methane-hhv",
        "HHV",
        "1,036 MMBtu per MMcf (EIA 2026 estimated U.S. average natural gas)",
    ),
    "boe": (
        _NOMINAL_BOE_MMBTU * 1_000_000.0 * MWH_PER_BTU_IT,
        "crude-oil-approximate",
        "nominal BOE convention",
        "5.800 MMBtu per barrel of oil equivalent (nominal U.S. DOE convention)",
    ),
    "bbl(oil)": (
        _EIA_2026_CRUDE_OIL_MMBTU_PER_BBL * 1_000_000.0 * MWH_PER_BTU_IT,
        "crude-oil-approximate",
        "estimated gross heat content",
        "5.689 MMBtu per barrel (EIA 2026 estimated U.S. crude-oil average)",
    ),
}


def fuel_volume_conversion(unit: str):
    """Return (mwh_per_unit, reference_id, basis, note) when a unit names its fuel."""

    key = str(unit or "").strip().lower().replace("_", " ")
    key = re.sub(r"\s*\(\s*", "(", re.sub(r"\s*\)\s*", ")", key))
    entry = FUEL_VOLUME_UNITS.get(key)
    if entry is None:
        return None
    return entry


# Spellings that mean an existing unit. Normalising here keeps one source of
# truth: `therms` and `therm` must not disagree about whether a row is usable.
_UNIT_ALIASES = {
    "kwhs": "kwh",
    "mwhs": "mwh",
    "gwhs": "gwh",
    "twhs": "twh",
    "whs": "wh",
    "therms": "therm",
    "dekatherms": "dekatherm",
    "dths": "dth",
    "btus": "btu",
    "mmbtus": "mmbtu",
    "ton_hours": "tonhour",
    "ton_hour": "tonhour",
    "tonhours": "tonhour",
    "ton_hrs": "tonhour",
    "ton_hr": "tonhour",
    "tonhrs": "tonhour",
    "trhs": "trh",
    "joule": "j",
    "joules": "j",
    "kilojoules": "kj",
    "megajoules": "mj",
    "gigajoules": "gj",
    "kilowatthours": "kwh",
    "megawatthours": "mwh",
}


def canonical_energy_unit(unit: str) -> str:
    """Fold a written unit onto its table key: `therms` and `Ton-Hours` -> `therm`, `ton_hour`."""

    key = str(unit or "").strip().lower().replace(" ", "_").replace("-", "_")
    key = _UNIT_ALIASES.get(key, _UNIT_ALIASES.get(key.replace("_", "-"), key))
    if key in ENERGY_TO_MWH:
        return key
    # A trailing plural is the single most common reason a real column header
    # missed the table.
    if key.endswith("s") and key[:-1] in ENERGY_TO_MWH:
        return key[:-1]
    return key


def is_non_energy_unit(unit: str) -> bool:
    """True for volume and mass units, which an Exergy Factor cannot be applied to."""

    text = str(unit or "")
    # A known energy unit is never a volume, and this has to be checked FIRST:
    # a refrigeration ton-hour is energy, but splitting `ton_hour` on the
    # underscore leaves `ton`, which is a mass. That false positive rejected every
    # chilled-water row in a building export.
    if canonical_energy_unit(text) in ENERGY_TO_MWH:
        return False
    base = text.partition("_")[0].strip().lower().replace(" ", "").replace("-", "")
    return base in NON_ENERGY_UNITS


POWER_TO_MW = {
    "w": 1e-6,
    "kw": 1e-3,
    "mw": 1.0,
    "gw": 1e3,
}


def split_unit(unit: str) -> Tuple[str, str]:
    """Split `MWh_th` into (`MWh`, `_th`)."""

    if not unit:
        raise ValueError("unit is required")
    # Some real energy-unit spellings contain an underscore themselves. Resolve
    # those aliases before interpreting the first underscore as a carrier suffix:
    # `ton_hour` is a refrigeration energy unit, not a mass unit carrying `_hour`.
    normalized = str(unit).strip().lower().replace(" ", "_").replace("-", "_")
    whole = canonical_energy_unit(unit)
    if "_" in normalized and whole in ENERGY_TO_MWH:
        return whole, ""

    aliases = {**{key: key for key in ENERGY_TO_MWH}, **_UNIT_ALIASES}
    for alias in sorted(aliases, key=len, reverse=True):
        prefix = f"{alias}_"
        if normalized.startswith(prefix) and aliases[alias] in ENERGY_TO_MWH:
            return aliases[alias], normalized[len(alias) :]
    base, separator, suffix = unit.partition("_")
    return base, f"{separator}{suffix}" if separator else ""


def is_energy_unit(unit: str) -> bool:
    base, _ = split_unit(unit)
    return canonical_energy_unit(base) in ENERGY_TO_MWH


def is_power_unit(unit: str) -> bool:
    base, _ = split_unit(unit)
    return base.lower() in POWER_TO_MW


def convert_energy(value: float, from_unit: str, to_unit: str = "MWh") -> float:
    """Convert common energy units while ignoring carrier suffixes.

    Examples:
    - `kWh_th` to `MWh`
    - `MMBtu_HHV` to `MWh`
    """

    from_base, _ = split_unit(from_unit)
    to_base, _ = split_unit(to_unit)
    from_factor = ENERGY_TO_MWH.get(canonical_energy_unit(from_base))
    to_factor = ENERGY_TO_MWH.get(canonical_energy_unit(to_base))
    if from_factor is None:
        if is_non_energy_unit(from_base):
            raise ValueError(
                f"{from_unit} measures volume or mass, not energy. Convert it to an energy "
                f"quantity first (volume x heating value), then report that."
            )
        raise ValueError(f"unsupported energy unit: {from_unit}")
    if to_factor is None:
        raise ValueError(f"unsupported energy unit: {to_unit}")
    return float(value) * from_factor / to_factor


def convert_power(value: float, from_unit: str, to_unit: str = "MW") -> float:
    """Convert common power units while ignoring carrier suffixes."""

    from_base, _ = split_unit(from_unit)
    to_base, _ = split_unit(to_unit)
    from_factor = POWER_TO_MW.get(from_base.lower())
    to_factor = POWER_TO_MW.get(to_base.lower())
    if from_factor is None:
        raise ValueError(f"unsupported power unit: {from_unit}")
    if to_factor is None:
        raise ValueError(f"unsupported power unit: {to_unit}")
    return float(value) * from_factor / to_factor
