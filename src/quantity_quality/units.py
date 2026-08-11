from __future__ import annotations

from typing import Tuple


ENERGY_TO_MWH = {
    "wh": 1e-6,
    "kwh": 1e-3,
    "mwh": 1.0,
    "gwh": 1e3,
    "j": 1.0 / 3.6e9,
    "kj": 1.0 / 3.6e6,
    "mj": 1.0 / 3600.0,
    "gj": 1.0 / 3.6,
    "tj": 1e3 / 3.6,
    "pj": 1e6 / 3.6,
    "ej": 1e9 / 3.6,
    "btu": 0.0002930710701722222 / 1000.0,
    "mmbtu": 0.2930710701722222,
    "therm": 0.02930011111111111,
    # Units that appear on real utility bills and building-management exports.
    # Without these a record parsed, produced a notation, and then had no
    # accessible_exergy_mwh at all — so the one column that makes rows comparable
    # was silently blank, which is the opposite of what the framework is for.
    "dekatherm": 0.2930011111111111,       # 10 therms
    "dth": 0.2930011111111111,
    # Refrigeration ton-hour = 12,000 Btu. Spelled WITHOUT an underscore on
    # purpose: `split_unit` reads everything after the first underscore as a
    # carrier suffix, so `ton_hour` parses as the mass unit `ton` carrying a
    # `_hour` suffix, and the row then has no convertible energy at all.
    "tonhour": 12000.0 * 0.0002930710701722222 / 1000.0,
    "tonh": 12000.0 * 0.0002930710701722222 / 1000.0,
    "trh": 12000.0 * 0.0002930710701722222 / 1000.0,
}


# Units that measure VOLUME or MASS, not energy.
#
# An Exergy Factor is a ratio of work potential to ENERGY, so multiplying one by
# a volume is meaningless: `4100 gallons, fx = 1.060` reads like a result and is
# not one. These are named explicitly so the record can be refused with an
# explanation, rather than accepted into a notation that looks authoritative.
NON_ENERGY_UNITS = frozenset({
    "gal", "gallon", "gallons", "l", "liter", "liters", "litre", "litres",
    "m3", "cubicmeter", "cubicmetre", "ft3", "cf", "scf", "ccf", "mcf", "mmcf",
    "bbl", "barrel", "barrels", "kg", "lb", "lbs", "pound", "pounds",
    "tonne", "tonnes", "shortton", "ton", "tons",
})


# Spellings that mean an existing unit. Normalising here keeps one source of
# truth: `therms` and `therm` must not disagree about whether a row is usable.
_UNIT_ALIASES = {
    "kwhs": "kwh", "mwhs": "mwh", "gwhs": "gwh", "whs": "wh",
    "therms": "therm", "dekatherms": "dekatherm", "dths": "dth",
    "btus": "btu", "mmbtus": "mmbtu",
    "ton_hours": "tonhour", "ton_hour": "tonhour", "tonhours": "tonhour",
    "ton_hrs": "tonhour", "ton_hr": "tonhour", "tonhrs": "tonhour", "trhs": "trh",
    "joule": "j", "joules": "j", "kilojoules": "kj", "megajoules": "mj",
    "gigajoules": "gj", "kilowatthours": "kwh", "megawatthours": "mwh",
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
