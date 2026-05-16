from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence

from .core import (
    accessible_exergy,
    chemical_exergy_factor,
    exergy_unit,
    format_energy_notation,
    thermal_exergy_factor_c,
)
from .reference import get_reference_example


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

    factor, reference_record = _factor_from_record(source, issues)

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

    if quantity is not None and unit and factor is not None:
        record["notation"] = format_energy_notation(quantity, unit, factor)
        record["accessible_exergy"] = accessible_exergy(quantity, factor)
        record["accessible_exergy_unit"] = exergy_unit(unit)
    else:
        record["notation"] = ""
        record["accessible_exergy"] = None
        record["accessible_exergy_unit"] = ""

    return AnnotatedRecord(source=source, record=record, issues=issues)


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
        rows = [record.record for record in records]
        fields = [
            "schema_version",
            "quantity",
            "unit",
            "exergy_factor",
            "notation",
            "accessible_exergy",
            "accessible_exergy_unit",
            "reference",
            "boundary",
            "operating_basis",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
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


def _factor_from_record(
    source: Mapping[str, object],
    issues: List[ValidationIssue],
) -> tuple[Optional[float], Optional[dict]]:
    explicit = _first_present(source, ("exergy_factor", "fx", "f_x"))
    if explicit is not None:
        try:
            factor = float(explicit)
        except (TypeError, ValueError):
            issues.append(ValidationIssue("exergy_factor", "must be numeric"))
            return None, None
        if factor < 0:
            issues.append(ValidationIssue("exergy_factor", "must be nonnegative"))
            return None, None
        return factor, None

    reference_id = source.get("reference_id")
    if reference_id:
        try:
            reference_record = get_reference_example(str(reference_id))
            return float(reference_record["exergy_factor"]), reference_record
        except KeyError:
            issues.append(ValidationIssue("reference_id", f"unknown reference id: {reference_id}"))
            return None, None

    if _has_any(source, ("source_c", "sink_c")):
        source_c = _number(source, "source_c", issues)
        sink_c = _number(source, "sink_c", issues)
        if source_c is not None and sink_c is not None:
            try:
                return thermal_exergy_factor_c(source_c, sink_c), None
            except ValueError as exc:
                issues.append(ValidationIssue("source_c/sink_c", str(exc)))
        return None, None

    if _has_any(source, ("chemical_exergy", "energy_basis")):
        chemical = _number(source, "chemical_exergy", issues)
        basis = _number(source, "energy_basis", issues)
        if chemical is not None and basis is not None:
            try:
                return chemical_exergy_factor(chemical, basis), None
            except ValueError as exc:
                issues.append(ValidationIssue("chemical_exergy/energy_basis", str(exc)))
        return None, None

    issues.append(
        ValidationIssue(
            "exergy_factor",
            "provide exergy_factor/fx, reference_id, source_c+sink_c, or chemical_exergy+energy_basis",
        )
    )
    return None, None


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
