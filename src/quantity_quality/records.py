from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence

from .core import (
    chemical_exergy_factor,
    cooling_exergy_factor_c,
    thermal_exergy_factor_c,
)
from .model import QuantityQualityRecord
from .reference import extract_temperature_context, get_reference_example


REPORT_SCHEMA_VERSION = "quantity_quality_report_v1"


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str

    def as_dict(self) -> dict:
        return {"field": self.field, "message": self.message}


@dataclass(frozen=True)
class AnnotatedRecord:
    source: dict
    record: dict
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "ok": self.ok,
            "source": self.source,
            "record": self.record,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def annotate_record(raw: Mapping[str, object]) -> AnnotatedRecord:
    """Normalize one adoption record and compute notation + accessible exergy.

    Supported inputs:
    - quantity, unit, exergy_factor
    - quantity, unit, fx
    - quantity, unit, reference_id
    - quantity, unit, source_c, sink_c
    - quantity, unit, chemical_exergy, energy_basis
    """

    source = dict(raw)
    issues: List[ValidationIssue] = []

    quantity = _optional_number(source, "quantity", issues)
    if quantity is None:
        quantity = _optional_number(source, "power", issues)
    if quantity is None:
        issues.append(ValidationIssue("quantity", "quantity or power is required"))
    unit = _string(source, "unit", issues)

    factor, reference_record, method = _factor_from_record(source, issues)

    reference_temperatures = extract_temperature_context(reference_record or {})
    source_c = _optional_number(source, "source_c", issues)
    sink_c = _optional_number(source, "sink_c", issues)
    cold_service_c = _optional_number(source, "cold_service_c", issues)
    ambient_sink_c = _optional_number(source, "ambient_sink_c", issues)
    if source_c is None:
        source_c = reference_temperatures.get("source_c")
    if sink_c is None:
        sink_c = reference_temperatures.get("sink_c")
    if cold_service_c is None:
        cold_service_c = reference_temperatures.get("cold_service_c")
    if ambient_sink_c is None:
        ambient_sink_c = reference_temperatures.get("ambient_sink_c")

    record = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "quantity": quantity,
        "unit": unit,
        "exergy_factor": factor,
        "reference": str(source.get("reference", "") or (reference_record or {}).get("reference", "")),
        "boundary": str(source.get("boundary", "") or (reference_record or {}).get("boundary", "")),
        "operating_basis": str(
            source.get("operating_basis", source.get("basis", ""))
            or (reference_record or {}).get("basis", "")
        ),
    }
    if factor is not None:
        _apply_method_defaults(record, method, source_c, sink_c, cold_service_c, ambient_sink_c)

    if quantity is not None and unit and factor is not None:
        warnings = list(source.get("_warnings", []) or [])
        assumptions = list(source.get("_assumptions", []) or [])
        if "_th" in unit.lower() and source_c is None and sink_c is None and not reference_record:
            warnings.append("thermal record is usable but not self-verifying without source_c and sink_c")
        qq_record = QuantityQualityRecord(
            quantity=quantity,
            unit=unit,
            exergy_factor=factor,
            reference=record["reference"],
            boundary=record["boundary"],
            basis=record["operating_basis"],
            method=method,
            label=str(source.get("label", "")) or None,
            source_c=source_c,
            sink_c=sink_c,
            cold_service_c=cold_service_c,
            ambient_sink_c=ambient_sink_c,
            fuel=str(source.get("fuel", "")) or None,
            energy_basis=str(source.get("energy_basis", "")) or None,
            reference_id=str(source.get("reference_id", "")) or None,
            assumptions=tuple(assumptions),
            warnings=tuple(warnings),
            metadata={
                "reference_source": (reference_record or {}).get("source", ""),
                "calculation": (reference_record or {}).get("calculation", ""),
            },
        )
        record.update(qq_record.as_dict())
        record["schema_version"] = REPORT_SCHEMA_VERSION
    else:
        record["notation"] = ""
        record["full_notation"] = ""
        record["accessible_exergy"] = None
        record["accessible_exergy_unit"] = ""
        record["capabilities"] = []
        record["missing_context"] = []
        record["readiness"] = {
            "capabilities": [],
            "missing_context": [],
            "assumptions": [],
            "warnings": [],
        }
        record["needs_attention"] = True
        record["warnings"] = []
        record["assumptions"] = []

    return AnnotatedRecord(source=source, record=record, issues=issues)


def _apply_method_defaults(
    record: dict,
    method: str,
    source_c: Optional[float],
    sink_c: Optional[float],
    cold_service_c: Optional[float],
    ambient_sink_c: Optional[float],
) -> None:
    if method == "thermal" and source_c is not None and sink_c is not None:
        record["reference"] = record["reference"] or f"T0 = {sink_c:g} C"
        record["boundary"] = record["boundary"] or "thermal stream"
        record["operating_basis"] = (
            record["operating_basis"] or f"Carnot factor, source={source_c:g} C, sink={sink_c:g} C"
        )
    if method == "cooling" and cold_service_c is not None and ambient_sink_c is not None:
        record["reference"] = record["reference"] or f"T0 = {ambient_sink_c:g} C"
        record["boundary"] = record["boundary"] or "cooling service boundary"
        record["operating_basis"] = (
            record["operating_basis"]
            or f"minimum work potential, cold={cold_service_c:g} C, ambient={ambient_sink_c:g} C"
        )
    if method == "chemical":
        record["boundary"] = record["boundary"] or "fuel inventory or fuel-flow meter"
        record["operating_basis"] = record["operating_basis"] or "chemical exergy divided by declared energy basis"


def annotate_records(records: Iterable[Mapping[str, object]]) -> List[AnnotatedRecord]:
    return [annotate_record(record) for record in records]


def load_records(path: Path) -> List[dict]:
    """Load CSV or JSON adoption records."""

    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                return list(data["records"])
            return [data]
        if isinstance(data, list):
            return list(data)
        raise ValueError("JSON input must be an object, a list, or {'records': [...]}")
    raise ValueError("input must be .csv or .json")


def write_annotated_records(records: Sequence[AnnotatedRecord], path: Path) -> None:
    """Write annotated records to CSV or JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "records": [record.as_dict() for record in records],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return
    if path.suffix.lower() == ".csv":
        fields = [
            "schema_version",
            "quantity",
            "unit",
            "exergy_factor",
            "fx",
            "notation",
            "accessible_exergy",
            "accessible_exergy_unit",
            "full_notation",
            "accessible_exergy_mwh",
            "accessible_exergy_mw",
            "reference",
            "boundary",
            "operating_basis",
            "basis",
            "needs_attention",
            "method",
            "capabilities",
            "missing_context",
            "source_c",
            "sink_c",
            "cold_service_c",
            "ambient_sink_c",
            "reference_id",
            "warnings",
            "assumptions",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(_csv_record(record.record, fields) for record in records)
        return
    raise ValueError("output must be .csv or .json")


def validation_summary(records: Sequence[AnnotatedRecord]) -> dict:
    invalid = [record for record in records if not record.ok]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "ok": not invalid,
        "total_records": len(records),
        "valid_records": len(records) - len(invalid),
        "invalid_records": len(invalid),
        "issues": [
            {"row": index + 1, **issue.as_dict()}
            for index, record in enumerate(records)
            for issue in record.issues
        ],
    }


def _csv_record(record: Mapping[str, object], fields: Sequence[str]) -> dict:
    row = {field: record.get(field, "") for field in fields}
    for field in ("warnings", "assumptions", "capabilities", "missing_context"):
        if isinstance(row.get(field), list):
            row[field] = "; ".join(str(value) for value in row[field])
    return row


def _factor_from_record(
    source: Mapping[str, object],
    issues: List[ValidationIssue],
) -> tuple[Optional[float], Optional[dict], str]:
    explicit = _first_present(source, ("exergy_factor", "fx", "f_x"))
    if explicit is not None:
        try:
            factor = float(explicit)
        except (TypeError, ValueError):
            issues.append(ValidationIssue("exergy_factor", "must be numeric"))
            return None, None, "supplied"
        if factor < 0:
            issues.append(ValidationIssue("exergy_factor", "must be nonnegative"))
            return None, None, "supplied"
        return factor, None, "supplied"

    reference_id = source.get("reference_id")
    if reference_id:
        try:
            reference_record = get_reference_example(str(reference_id))
            return float(reference_record["exergy_factor"]), reference_record, "reference"
        except KeyError:
            issues.append(ValidationIssue("reference_id", f"unknown reference id: {reference_id}"))
            return None, None, "reference"

    if _has_any(source, ("source_c", "sink_c")):
        source_c = _temperature_number(source, "source_c", issues)
        sink_c = _temperature_number(source, "sink_c", issues)
        if source_c is not None and sink_c is not None:
            try:
                return thermal_exergy_factor_c(source_c, sink_c), None, "thermal"
            except ValueError as exc:
                issues.append(ValidationIssue("source_c/sink_c", str(exc)))
        return None, None, "thermal"

    if _has_any(source, ("cold_service_c", "ambient_sink_c")):
        cold_service_c = _temperature_number(source, "cold_service_c", issues)
        ambient_sink_c = _temperature_number(source, "ambient_sink_c", issues)
        if cold_service_c is not None and ambient_sink_c is not None:
            try:
                return cooling_exergy_factor_c(cold_service_c, ambient_sink_c), None, "cooling"
            except ValueError as exc:
                issues.append(ValidationIssue("cold_service_c/ambient_sink_c", str(exc)))
        return None, None, "cooling"

    if _has_any(source, ("chemical_exergy", "energy_basis")):
        chemical = _number(source, "chemical_exergy", issues)
        basis = _number(source, "energy_basis", issues)
        if chemical is not None and basis is not None:
            try:
                return chemical_exergy_factor(chemical, basis), None, "chemical"
            except ValueError as exc:
                issues.append(ValidationIssue("chemical_exergy/energy_basis", str(exc)))
        return None, None, "chemical"

    issues.append(
        ValidationIssue(
            "exergy_factor",
            "provide exergy_factor/fx, reference_id, source_c+sink_c, or chemical_exergy+energy_basis",
        )
    )
    return None, None, "unknown"


def _first_present(source: Mapping[str, object], keys: Sequence[str]) -> Optional[object]:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def _has_any(source: Mapping[str, object], keys: Sequence[str]) -> bool:
    return any(source.get(key) not in (None, "") for key in keys)


def _number(source: Mapping[str, object], field_name: str, issues: List[ValidationIssue]) -> Optional[float]:
    value = source.get(field_name)
    if value in (None, ""):
        issues.append(ValidationIssue(field_name, "is required"))
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        issues.append(ValidationIssue(field_name, "must be numeric"))
        return None
    if numeric < 0:
        issues.append(ValidationIssue(field_name, "must be nonnegative"))
        return None
    return numeric


def _temperature_number(
    source: Mapping[str, object],
    field_name: str,
    issues: List[ValidationIssue],
) -> Optional[float]:
    value = source.get(field_name)
    if value in (None, ""):
        issues.append(ValidationIssue(field_name, "is required"))
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        issues.append(ValidationIssue(field_name, "must be numeric"))
        return None


def _optional_number(
    source: Mapping[str, object],
    field_name: str,
    issues: List[ValidationIssue],
) -> Optional[float]:
    value = source.get(field_name)
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        issues.append(ValidationIssue(field_name, "must be numeric"))
        return None
    if numeric < 0:
        issues.append(ValidationIssue(field_name, "must be nonnegative"))
        return None
    return numeric


def _string(source: Mapping[str, object], field_name: str, issues: List[ValidationIssue]) -> str:
    value = source.get(field_name)
    if value in (None, ""):
        issues.append(ValidationIssue(field_name, "is required"))
        return ""
    return str(value)
