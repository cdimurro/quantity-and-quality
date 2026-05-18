from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from .api import (
    chemical,
    cooling,
    electricity,
    from_notation,
    fuel,
    lookup,
    report,
    thermal,
)
from .model import QuantityQualityRecord
from .units import convert_energy, is_energy_unit


SCENARIO_SCHEMA_VERSION = "quantity_quality_scenario_v1"


def load_scenario(path: Union[str, Path]) -> dict:
    """Load a scenario comparison from JSON or YAML."""

    scenario_path = Path(path)
    text = scenario_path.read_text(encoding="utf-8")
    suffix = scenario_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ImportError("YAML scenarios require the 'scenario' extra: pip install quantity-quality[scenario]") from exc
        data = yaml.safe_load(text)
    else:
        raise ValueError("scenario files must be .json, .yaml, or .yml")
    if not isinstance(data, dict):
        raise ValueError("scenario file must contain an object")
    return data


def compare_scenario(scenario: Mapping[str, Any]) -> dict:
    """Compare scenario options by energy quantity and accessible exergy."""

    options = scenario.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError("scenario requires a non-empty options list")

    demand_record = None
    if isinstance(scenario.get("demand"), Mapping):
        demand_record = record_from_mapping(scenario["demand"])

    rows = [
        _scenario_row(option, demand_record=demand_record)
        for option in options
        if isinstance(option, Mapping)
    ]
    if len(rows) != len(options):
        raise ValueError("each scenario option must be an object")

    return {
        "schema_version": SCENARIO_SCHEMA_VERSION,
        "name": str(scenario.get("name", "scenario")),
        "demand": demand_record.as_dict() if demand_record is not None else None,
        "rows": rows,
    }


def compare_scenario_file(path: Union[str, Path]) -> dict:
    """Load and compare a scenario file."""

    return compare_scenario(load_scenario(path))


def record_from_mapping(source: Mapping[str, Any]) -> QuantityQualityRecord:
    """Create a QuantityQualityRecord from a scenario option or demand mapping."""

    quantity = float(source.get("quantity", source.get("energy", 1.0)))
    unit = str(source.get("unit", "MWh"))
    label = _label(source)

    notation = source.get("notation")
    if notation:
        return from_notation(str(notation), label=label)

    reference_id = source.get("reference_id") or source.get("preset")
    if reference_id:
        record = lookup(str(reference_id), quantity=quantity, unit=unit if source.get("unit") else None)
        return _replace_label(record, label)

    kind = str(source.get("type", source.get("method", ""))).lower().strip()
    if kind == "electricity":
        return electricity(quantity, unit, label=label)
    if kind == "fuel" or source.get("fuel"):
        record = fuel(
            quantity,
            str(source.get("fuel", "natural gas")),
            basis=str(source.get("energy_basis", source.get("basis", "HHV"))),
            unit=unit if source.get("unit") else None,
        )
        return _replace_label(record, label)
    if source.get("source_c") is not None:
        return thermal(
            quantity,
            unit,
            source_c=float(source["source_c"]),
            sink_c=float(source.get("sink_c", 20.0)),
            label=label,
        )
    if source.get("cold_service_c") is not None:
        return cooling(
            quantity,
            unit,
            cold_service_c=float(source["cold_service_c"]),
            ambient_sink_c=float(source.get("ambient_sink_c", 20.0)),
            label=label,
        )
    if source.get("chemical_exergy") is not None:
        return chemical(
            quantity,
            unit,
            chemical_exergy=float(source["chemical_exergy"]),
            energy_basis=float(source["energy_basis"]),
            basis_label=str(source.get("basis_label", "declared energy basis")),
            label=label,
        )

    factor = source.get("exergy_factor", source.get("fx"))
    if factor is not None:
        return report(
            quantity,
            unit,
            fx=float(factor),
            reference=str(source.get("reference", "")),
            boundary=str(source.get("boundary", "")),
            basis=str(source.get("basis", "")),
            label=label,
        )

    raise ValueError(f"scenario record '{label}' needs reference_id, type, temperatures, fuel, notation, or fx")


def scenario_to_markdown(result: Mapping[str, Any]) -> str:
    """Render a scenario comparison as a Markdown table."""

    rows = result.get("rows", [])
    lines = [
        f"# {result.get('name', 'Scenario')}",
        "",
        "| Option | Energy | fx | MWh_ex | Unavailable | Cost/MWh | Cost/MWh_ex | CO2/MWh | CO2/MWh_ex |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {label} | {energy} | {fx} | {mwh_ex} | {unavailable} | {cost} | {cost_ex} | {co2} | {co2_ex} |".format(
                label=row["label"],
                energy=f"{_fmt(row['quantity'])} {row['unit']}",
                fx=_fmt(row["fx"]),
                mwh_ex=_fmt(row.get("accessible_exergy_mwh")),
                unavailable=_fmt(row.get("unavailable_energy")),
                cost=_fmt(row.get("cost_per_mwh")),
                cost_ex=_fmt(row.get("cost_per_mwh_ex")),
                co2=_fmt(row.get("co2_kg_per_mwh")),
                co2_ex=_fmt(row.get("co2_kg_per_mwh_ex")),
            )
        )
    return "\n".join(lines) + "\n"


def scenario_to_table(result: Mapping[str, Any]) -> str:
    """Render a compact fixed-width scenario table for the CLI."""

    rows = result.get("rows", [])
    headings = ("Option", "Energy", "fx", "MWh_ex", "Cost/MWh_ex", "CO2/MWh_ex")
    rendered = [
        (
            str(row["label"]),
            f"{_fmt(row['quantity'])} {row['unit']}",
            _fmt(row["fx"]),
            _fmt(row.get("accessible_exergy_mwh")),
            _fmt(row.get("cost_per_mwh_ex")),
            _fmt(row.get("co2_kg_per_mwh_ex")),
        )
        for row in rows
    ]
    widths = [
        max(len(headings[index]), *(len(row[index]) for row in rendered))
        for index in range(len(headings))
    ]
    lines = [_format_table_row(headings, widths), _format_table_row(tuple("-" * width for width in widths), widths)]
    lines.extend(_format_table_row(row, widths) for row in rendered)
    return "\n".join(lines)


def _scenario_row(option: Mapping[str, Any], *, demand_record: Optional[QuantityQualityRecord]) -> dict:
    record = record_from_mapping(option)
    row = record.as_dict()
    row["id"] = str(option.get("id", option.get("reference_id", row.get("label", ""))))
    row["label"] = _label(option) or row.get("label", row["id"])
    row["fx"] = record.fx
    if is_energy_unit(record.unit):
        row["energy_mwh"] = convert_energy(record.quantity, record.unit, "MWh")
    if record.accessible_exergy_mwh is not None:
        row["accessible_exergy_mwh"] = record.accessible_exergy_mwh
    if 0 <= record.fx <= 1:
        row["unavailable_energy"] = record.quantity * (1.0 - record.fx)
        row["unavailable_energy_unit"] = record.unit
    if record.fx > 0:
        if option.get("cost_per_mwh") is not None:
            row["cost_per_mwh"] = float(option["cost_per_mwh"])
            row["cost_per_mwh_ex"] = float(option["cost_per_mwh"]) / record.fx
        if option.get("co2_kg_per_mwh") is not None:
            row["co2_kg_per_mwh"] = float(option["co2_kg_per_mwh"])
            row["co2_kg_per_mwh_ex"] = float(option["co2_kg_per_mwh"]) / record.fx
    if demand_record is not None and row.get("energy_mwh") is not None:
        row["demand_fx"] = demand_record.fx
        row["grade_mismatch_mwh_ex"] = row["energy_mwh"] * max(0.0, record.fx - demand_record.fx)
        row["grade_shortfall_mwh_ex"] = row["energy_mwh"] * max(0.0, demand_record.fx - record.fx)
    return row


def _replace_label(record: QuantityQualityRecord, label: str) -> QuantityQualityRecord:
    if not label:
        return record
    return QuantityQualityRecord(
        quantity=record.quantity,
        unit=record.unit,
        exergy_factor=record.exergy_factor,
        reference=record.reference,
        boundary=record.boundary,
        basis=record.basis,
        method=record.method,
        label=label,
        source_c=record.source_c,
        sink_c=record.sink_c,
        cold_service_c=record.cold_service_c,
        ambient_sink_c=record.ambient_sink_c,
        fuel=record.fuel,
        energy_basis=record.energy_basis,
        reference_id=record.reference_id,
        assumptions=record.assumptions,
        warnings=record.warnings,
        metadata=record.metadata,
    )


def _label(source: Mapping[str, Any]) -> str:
    return str(source.get("label", source.get("name", source.get("id", ""))) or "")


def _fmt(value: object) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.6g}"


def _format_table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(values))
