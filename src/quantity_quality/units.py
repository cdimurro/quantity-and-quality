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
}


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
    return base.lower() in ENERGY_TO_MWH


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
    from_factor = ENERGY_TO_MWH.get(from_base.lower())
    to_factor = ENERGY_TO_MWH.get(to_base.lower())
    if from_factor is None:
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
