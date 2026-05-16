from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Optional, Tuple, Union


Number = Union[int, float]


@dataclass(frozen=True)
class ReferenceContext:
    """Metadata that makes an Exergy Factor interpretable."""

    reference: str
    boundary: str
    operating_basis: str
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class EnergyReport:
    """A quantity-plus-quality record for accumulated energy."""

    quantity: float
    unit: str
    exergy_factor: float
    context: ReferenceContext
    label: Optional[str] = None

    def __post_init__(self) -> None:
        _require_nonnegative(self.quantity, "quantity")
        _require_valid_factor(self.exergy_factor)
        if not self.unit:
            raise ValueError("unit is required")

    @property
    def accessible_exergy(self) -> float:
        return accessible_exergy(self.quantity, self.exergy_factor)

    @property
    def accessible_exergy_unit(self) -> str:
        return f"{self.unit}_ex"

    def as_dict(self) -> dict:
        return {
            "type": "energy",
            "label": self.label,
            "quantity": self.quantity,
            "unit": self.unit,
            "exergy_factor": self.exergy_factor,
            "accessible_exergy": self.accessible_exergy,
            "accessible_exergy_unit": self.accessible_exergy_unit,
            "context": self.context.as_dict(),
        }


@dataclass(frozen=True)
class PowerReport:
    """A quantity-plus-quality record for an energy or work rate."""

    power: float
    unit: str
    exergy_factor: float
    context: ReferenceContext
    label: Optional[str] = None

    def __post_init__(self) -> None:
        _require_nonnegative(self.power, "power")
        _require_valid_factor(self.exergy_factor)
        if not self.unit:
            raise ValueError("unit is required")

    @property
    def accessible_exergy_rate(self) -> float:
        return accessible_exergy(self.power, self.exergy_factor)

    @property
    def accessible_exergy_rate_unit(self) -> str:
        return f"{self.unit}_ex"

    def as_dict(self) -> dict:
        return {
            "type": "power",
            "label": self.label,
            "power": self.power,
            "unit": self.unit,
            "exergy_factor": self.exergy_factor,
            "accessible_exergy_rate": self.accessible_exergy_rate,
            "accessible_exergy_rate_unit": self.accessible_exergy_rate_unit,
            "context": self.context.as_dict(),
        }


def accessible_exergy(quantity_or_power: Number, exergy_factor: Number) -> float:
    """Return accessible exergy for an energy quantity or power rate."""

    quantity = float(quantity_or_power)
    factor = float(exergy_factor)
    _require_nonnegative(quantity, "quantity_or_power")
    _require_valid_factor(factor)
    return quantity * factor


def thermal_exergy_factor(source_k: Number, sink_k: Number) -> float:
    """Carnot Exergy Factor for heat from a source to a sink, both in kelvin."""

    source = float(source_k)
    sink = float(sink_k)
    if not math.isfinite(source) or not math.isfinite(sink):
        raise ValueError("temperatures must be finite")
    if source <= 0 or sink <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if source <= sink:
        raise ValueError("source temperature must be greater than sink temperature")
    return 1.0 - sink / source


def thermal_exergy_factor_c(source_c: Number, sink_c: Number) -> float:
    """Carnot Exergy Factor for heat from a source to a sink, both in C."""

    return thermal_exergy_factor(float(source_c) + 273.15, float(sink_c) + 273.15)


def cooling_exergy_factor_c(cold_service_c: Number, ambient_sink_c: Number) -> float:
    """Minimum work potential per unit cooling for a cold service below ambient.

    This uses f_X = T_ambient / T_cold - 1. Treat it as a service-demand factor,
    not as a heat-source factor.
    """

    cold = float(cold_service_c) + 273.15
    ambient = float(ambient_sink_c) + 273.15
    if not math.isfinite(cold) or not math.isfinite(ambient):
        raise ValueError("temperatures must be finite")
    if cold <= 0 or ambient <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if ambient <= cold:
        raise ValueError("ambient sink must be warmer than the cold service")
    return ambient / cold - 1.0


def chemical_exergy_factor(chemical_exergy: Number, energy_basis: Number) -> float:
    """Return chemical Exergy Factor as chemical exergy divided by the declared energy basis."""

    exergy = float(chemical_exergy)
    basis = float(energy_basis)
    _require_positive(exergy, "chemical_exergy")
    _require_positive(basis, "energy_basis")
    return exergy / basis


WeightedInput = Union[
    EnergyReport,
    PowerReport,
    Mapping[str, Number],
    Tuple[Number, Number],
]


def weighted_exergy_factor(records: Iterable[WeightedInput]) -> float:
    """Energy-weighted or power-weighted average Exergy Factor.

    Each record may be an EnergyReport, PowerReport, mapping with
    `quantity` or `power` plus `exergy_factor`, or a `(quantity, factor)` tuple.
    """

    total_quantity = 0.0
    total_exergy = 0.0

    for record in records:
        quantity, factor = _quantity_and_factor(record)
        _require_nonnegative(quantity, "quantity")
        _require_valid_factor(factor)
        total_quantity += quantity
        total_exergy += quantity * factor

    if total_quantity <= 0:
        raise ValueError("at least one record with positive quantity or power is required")
    return total_exergy / total_quantity


def _quantity_and_factor(record: WeightedInput) -> Tuple[float, float]:
    if isinstance(record, EnergyReport):
        return record.quantity, record.exergy_factor
    if isinstance(record, PowerReport):
        return record.power, record.exergy_factor
    if isinstance(record, Mapping):
        if "quantity" in record:
            quantity = record["quantity"]
        elif "power" in record:
            quantity = record["power"]
        else:
            raise ValueError("mapping records must include quantity or power")
        return float(quantity), float(record["exergy_factor"])

    quantity, factor = record
    return float(quantity), float(factor)


def _require_nonnegative(value: Number, name: str) -> None:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")


def _require_positive(value: Number, name: str) -> None:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def _require_valid_factor(value: Number) -> None:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("exergy_factor must be a finite nonnegative number")

