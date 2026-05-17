from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Union

from .core import (
    EnergyReport,
    chemical_exergy_factor,
    cooling_exergy_factor_c,
    parse_energy_notation,
    petela_exergy_factor,
    thermal_exergy_factor_c,
)
from .model import QuantityQualityRecord
from .reference import extract_temperature_context, get_reference_example
from .units import convert_energy, convert_power, is_energy_unit, is_power_unit


DEFAULT_SINK_C = 20.0

FUEL_FACTORS = {
    "methane": {"HHV": 0.93, "LHV": 1.04},
    "natural_gas": {"HHV": 0.93, "LHV": 1.04},
    "hydrogen": {"HHV": 0.83, "LHV": 0.98},
}


def report(
    quantity: float,
    unit: str,
    fx: Optional[float] = None,
    *,
    exergy_factor: Optional[float] = None,
    reference: str = "",
    boundary: str = "",
    basis: str = "",
    label: Optional[str] = None,
    method: str = "supplied",
) -> QuantityQualityRecord:
    """Create the simplest possible Quantity + Quality record.

    This is the adoption entry point: provide a quantity, a unit, and `fx`.
    Context can be added later for auditability.
    """

    factor = _resolve_factor(fx, exergy_factor)
    warnings = _context_warnings(unit=unit, reference=reference, boundary=boundary, basis=basis)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=reference,
        boundary=boundary,
        basis=basis,
        method=method,
        label=label,
        warnings=tuple(warnings),
    )


def from_notation(text: str, **context: object) -> QuantityQualityRecord:
    """Parse `1 MWh, fx = 0.73` into a high-level record."""

    parsed = parse_energy_notation(text)
    return report(parsed.quantity, parsed.unit, parsed.exergy_factor, **context)


def thermal(
    quantity: float = 1.0,
    unit: str = "MWh_th",
    *,
    source_c: float,
    sink_c: Optional[float] = None,
    reference: str = "",
    boundary: str = "thermal stream",
    basis: str = "",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create a self-verifying thermal stream record.

    If `sink_c` is omitted, the paper default `T0 = 20 C` is used.
    """

    assumptions = []
    if sink_c is None:
        sink_c = DEFAULT_SINK_C
        assumptions.append("default reference sink assumed: T0 = 20 C")
    factor = thermal_exergy_factor_c(source_c, sink_c)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=reference or f"T0 = {sink_c:g} C",
        boundary=boundary,
        basis=basis or f"Carnot factor, source={source_c:g} C, sink={sink_c:g} C",
        method="thermal",
        label=label or f"{source_c:g} C heat to {sink_c:g} C sink",
        source_c=source_c,
        sink_c=sink_c,
        assumptions=tuple(assumptions),
    )


def electricity(
    quantity: float = 1.0,
    unit: str = "MWh",
    *,
    boundary: str = "electrical delivery boundary",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create an electricity record using the standard work-quality convention `fx = 1`."""

    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=1.0,
        reference="electrical work boundary",
        boundary=boundary,
        basis="electrical work potential per unit delivered electricity",
        method="electricity",
        label=label or "electricity",
    )


def cooling(
    quantity: float = 1.0,
    unit: str = "MWh_cooling",
    *,
    cold_service_c: float,
    ambient_sink_c: float,
    boundary: str = "cooling service boundary",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create a cooling-service record."""

    factor = cooling_exergy_factor_c(cold_service_c, ambient_sink_c)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=f"T0 = {ambient_sink_c:g} C",
        boundary=boundary,
        basis=(
            "minimum work potential per unit cooling service, "
            f"cold={cold_service_c:g} C, ambient={ambient_sink_c:g} C"
        ),
        method="cooling",
        label=label or f"{cold_service_c:g} C cooling against {ambient_sink_c:g} C ambient",
        cold_service_c=cold_service_c,
        ambient_sink_c=ambient_sink_c,
    )


def solar(
    quantity: float = 1.0,
    unit: str = "MWh_solar",
    *,
    reference_c: float = DEFAULT_SINK_C,
    reference: str = "",
    boundary: str = "solar resource boundary",
    basis: str = "",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create a solar radiation record using the Petela radiation factor."""

    factor = petela_exergy_factor(reference_c + 273.15)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=reference or f"T0 = {reference_c:g} C",
        boundary=boundary,
        basis=basis or "Petela radiation factor",
        method="solar",
        label=label or f"solar radiation at {reference_c:g} C reference",
        sink_c=reference_c,
    )


def chemical(
    quantity: float,
    unit: str,
    *,
    chemical_exergy: float,
    energy_basis: float,
    basis_label: str = "declared energy basis",
    boundary: str = "fuel inventory or fuel-flow meter",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create a chemical energy record from chemical exergy and an energy denominator."""

    factor = chemical_exergy_factor(chemical_exergy, energy_basis)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=basis_label,
        boundary=boundary,
        basis="chemical exergy divided by declared energy basis",
        method="chemical",
        label=label or "chemical energy",
        energy_basis=basis_label,
        metadata={"chemical_exergy": chemical_exergy, "energy_basis": energy_basis},
    )


def fuel(
    quantity: float,
    fuel: str,
    *,
    basis: str = "HHV",
    unit: Optional[str] = None,
    boundary: str = "fuel inventory or fuel-flow meter",
) -> QuantityQualityRecord:
    """Create a common fuel record with a bundled Exergy Factor preset."""

    fuel_key = fuel.lower().replace(" ", "_").replace("-", "_")
    basis_key = basis.upper()
    try:
        factor = FUEL_FACTORS[fuel_key][basis_key]
    except KeyError as exc:
        known = ", ".join(sorted(FUEL_FACTORS))
        raise ValueError(f"unknown fuel/basis preset: {fuel} {basis}. Known fuels: {known}") from exc
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit or f"MWh_{basis_key}",
        exergy_factor=factor,
        reference=f"declared {basis_key} energy basis",
        boundary=boundary,
        basis=f"chemical exergy divided by {basis_key}",
        method="fuel",
        label=f"{fuel_key.replace('_', ' ')} on {basis_key} basis",
        fuel=fuel_key,
        energy_basis=basis_key,
    )


def lookup(
    reference_id: str,
    *,
    quantity: float = 1.0,
    unit: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create a record from the bundled reference-example database."""

    example = get_reference_example(reference_id)
    temperatures = extract_temperature_context(example)
    return QuantityQualityRecord(
        quantity=quantity,
        unit=unit or str(example["quantity_unit"]),
        exergy_factor=float(example["exergy_factor"]),
        reference=str(example.get("reference", "")),
        boundary=str(example.get("boundary", "")),
        basis=str(example.get("basis", "")),
        method="reference",
        label=str(example.get("name", reference_id)),
        source_c=temperatures.get("source_c"),
        sink_c=temperatures.get("sink_c"),
        cold_service_c=temperatures.get("cold_service_c"),
        ambient_sink_c=temperatures.get("ambient_sink_c"),
        reference_id=reference_id,
        metadata={
            "category": example.get("category", ""),
            "carrier": example.get("carrier", ""),
            "calculation": example.get("calculation", ""),
            "adoption_note": example.get("adoption_note", ""),
            "source": example.get("source", ""),
        },
    )


def source_temperature_for_fx_c(fx: float, *, sink_c: float = DEFAULT_SINK_C) -> float:
    """Return the thermal source temperature implied by `fx` and a sink."""

    factor = float(fx)
    if factor < 0 or factor >= 1:
        raise ValueError("thermal fx must be greater than or equal to 0 and less than 1")
    sink_k = float(sink_c) + 273.15
    return sink_k / (1.0 - factor) - 273.15


def annotate_file(input_path: Union[str, Path], *, output: Optional[Union[str, Path]] = None) -> dict:
    """Annotate CSV/JSON energy records with notation, fx, context, and warnings."""

    from .clean import clean_file

    return clean_file(input_path, output=output)


RecordLike = Union[QuantityQualityRecord, EnergyReport, Mapping[str, object]]


def compare(records: Iterable[RecordLike], *, sort: bool = True) -> List[dict]:
    """Return comparison rows with raw and normalized accessible exergy when possible."""

    rows = [_comparison_row(_coerce_record(record)) for record in records]
    if sort:
        rows.sort(key=lambda row: row.get("sort_value", float("-inf")), reverse=True)
    for row in rows:
        row.pop("sort_value", None)
    return rows


def _comparison_row(record: QuantityQualityRecord) -> dict:
    row = {
        "label": record.label or record.notation,
        "notation": record.full_notation,
        "quantity": record.quantity,
        "unit": record.unit,
        "fx": record.fx,
        "accessible_exergy": record.accessible_exergy,
        "accessible_exergy_unit": record.accessible_exergy_unit,
        "capabilities": list(record.capabilities),
        "missing_context": list(record.missing_context),
        "warnings": list(record.warnings),
    }
    if is_energy_unit(record.unit):
        row["accessible_exergy_mwh"] = convert_energy(
            record.accessible_exergy,
            record.accessible_exergy_unit,
            "MWh",
        )
        row["sort_value"] = row["accessible_exergy_mwh"]
    elif is_power_unit(record.unit):
        row["accessible_exergy_mw"] = convert_power(
            record.accessible_exergy,
            record.accessible_exergy_unit,
            "MW",
        )
        row["sort_value"] = row["accessible_exergy_mw"]
    else:
        row["sort_value"] = record.accessible_exergy
        row["warnings"].append("unit could not be normalized for comparison")
    return row


def _coerce_record(record: RecordLike) -> QuantityQualityRecord:
    if isinstance(record, QuantityQualityRecord):
        return record
    if isinstance(record, EnergyReport):
        return QuantityQualityRecord(
            quantity=record.quantity,
            unit=record.unit,
            exergy_factor=record.exergy_factor,
            reference=record.context.reference,
            boundary=record.context.boundary,
            basis=record.context.operating_basis,
            method="energy_report",
            label=record.label,
        )
    if isinstance(record, Mapping):
        quantity = record.get("quantity", record.get("power"))
        factor = record.get("exergy_factor", record.get("fx"))
        unit = record.get("unit")
        if quantity is None or factor is None or unit is None:
            raise ValueError("mapping records must include quantity, unit, and exergy_factor/fx")
        return QuantityQualityRecord(
            quantity=float(quantity),
            unit=str(unit),
            exergy_factor=float(factor),
            reference=str(record.get("reference", "")),
            boundary=str(record.get("boundary", "")),
            basis=str(record.get("basis", record.get("operating_basis", ""))),
            method=str(record.get("method", "mapping")),
            label=str(record.get("label", "")) or None,
        )
    raise TypeError(f"unsupported record type: {type(record)!r}")


def _resolve_factor(fx: Optional[float], exergy_factor: Optional[float]) -> float:
    if fx is None and exergy_factor is None:
        raise ValueError("fx or exergy_factor is required")
    if fx is not None and exergy_factor is not None and float(fx) != float(exergy_factor):
        raise ValueError("fx and exergy_factor disagree")
    return float(exergy_factor if exergy_factor is not None else fx)


def _context_warnings(*, unit: str, reference: str, boundary: str, basis: str) -> List[str]:
    return []
