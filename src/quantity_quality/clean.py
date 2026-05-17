from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence, Union
from urllib.request import urlopen

from .core import parse_energy_notation
from .records import annotate_record
from .units import is_energy_unit, is_power_unit, split_unit


RecordMapping = Mapping[str, Union[str, int, float, Callable[[Mapping[str, Any]], Any], None]]


FIELD_ALIASES = {
    "label": (
        "label",
        "name",
        "asset",
        "asset_name",
        "meter",
        "meter_name",
        "stream",
        "stream_name",
        "description",
    ),
    "quantity": (
        "quantity",
        "energy",
        "energy_quantity",
        "amount",
        "value",
        "usage",
        "consumption",
        "reading",
        "delivered_energy",
        "energy_delivered",
    ),
    "power": ("power", "demand", "load", "rate", "power_rate"),
    "unit": ("unit", "units", "uom", "energy_unit", "power_unit", "measurement_unit"),
    "fx": (
        "fx",
        "f_x",
        "fX",
        "exergy_factor",
        "quality_factor",
        "quality",
        "quality_ratio",
        "exergy_ratio",
    ),
    "notation": ("notation", "qq_notation", "quantity_quality_notation"),
    "reference_id": ("reference_id", "example_id", "preset", "reference_example", "qq_reference"),
    "reference": ("reference", "reference_environment", "reference_sink", "sink_reference"),
    "boundary": ("boundary", "reporting_boundary", "meter_boundary", "measurement_boundary"),
    "basis": ("basis", "operating_basis", "method", "calculation_basis"),
    "source_c": (
        "source_c",
        "source_temp_c",
        "source_temperature_c",
        "supply_temp_c",
        "supply_temperature_c",
        "hot_temp_c",
        "hot_temperature_c",
        "th_c",
        "t_h_c",
    ),
    "source_f": (
        "source_f",
        "source_temp_f",
        "source_temperature_f",
        "supply_temp_f",
        "supply_temperature_f",
        "hot_temp_f",
        "hot_temperature_f",
        "th_f",
        "t_h_f",
    ),
    "source_k": (
        "source_k",
        "source_temp_k",
        "source_temperature_k",
        "supply_temp_k",
        "supply_temperature_k",
        "hot_temp_k",
        "hot_temperature_k",
        "th_k",
        "t_h_k",
    ),
    "sink_c": (
        "sink_c",
        "sink_temp_c",
        "sink_temperature_c",
        "reference_c",
        "reference_temp_c",
        "reference_temperature_c",
        "ambient_c",
        "ambient_temp_c",
        "return_c",
        "return_temp_c",
        "return_temperature_c",
        "t0_c",
        "t_0_c",
    ),
    "sink_f": (
        "sink_f",
        "sink_temp_f",
        "sink_temperature_f",
        "reference_f",
        "reference_temp_f",
        "ambient_f",
        "ambient_temp_f",
        "return_f",
        "return_temp_f",
        "t0_f",
        "t_0_f",
    ),
    "sink_k": (
        "sink_k",
        "sink_temp_k",
        "sink_temperature_k",
        "reference_k",
        "reference_temp_k",
        "ambient_k",
        "ambient_temp_k",
        "return_k",
        "return_temp_k",
        "t0_k",
        "t_0_k",
    ),
    "cold_service_c": ("cold_service_c", "cold_c", "chilled_water_c", "cooling_temp_c", "tcold_c"),
    "ambient_sink_c": ("ambient_sink_c", "heat_rejection_c", "rejection_temp_c", "cooling_sink_c"),
    "chemical_exergy": ("chemical_exergy", "chemical_exergy_value", "exergy_content"),
    "energy_basis": ("energy_basis", "fuel_basis", "basis_value", "hhv_lhv", "heating_value_basis"),
    "fuel": ("fuel", "fuel_type", "carrier", "energy_carrier"),
}


UNIT_HINTS = {
    "wh": "Wh",
    "kwh": "kWh",
    "mwh": "MWh",
    "gwh": "GWh",
    "j": "J",
    "kj": "kJ",
    "mj": "MJ",
    "gj": "GJ",
    "tj": "TJ",
    "pj": "PJ",
    "ej": "EJ",
    "btu": "Btu",
    "mmbtu": "MMBtu",
    "therm": "therm",
    "w": "W",
    "kw": "kW",
    "mw": "MW",
    "gw": "GW",
}


FUEL_REFERENCE_IDS = {
    ("methane", "HHV"): "methane-hhv",
    ("methane", "LHV"): "methane-lhv",
    ("natural_gas", "HHV"): "methane-hhv",
    ("natural_gas", "LHV"): "methane-lhv",
    ("natural gas", "HHV"): "methane-hhv",
    ("natural gas", "LHV"): "methane-lhv",
    ("hydrogen", "HHV"): "hydrogen-hhv",
    ("hydrogen", "LHV"): "hydrogen-lhv",
}


def clean_record(
    raw: Mapping[str, Any],
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    assume_default_sink: bool = True,
    default_sink_c: float = 20.0,
) -> dict:
    """Clean one messy energy record into Quantity + Quality output fields."""

    normalized = normalize_record(
        raw,
        mapping=mapping,
        defaults=defaults,
        assume_default_sink=assume_default_sink,
        default_sink_c=default_sink_c,
    )
    annotated = annotate_record(normalized)
    payload = annotated.record
    payload["source"] = dict(raw)
    if annotated.issues:
        payload["issues"] = [issue.as_dict() for issue in annotated.issues]
    return payload


def clean_records(
    records: Iterable[Mapping[str, Any]],
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    assume_default_sink: bool = True,
    default_sink_c: float = 20.0,
) -> list[dict]:
    """Clean a sequence of mapping records."""

    return [
        clean_record(
            record,
            mapping=mapping,
            defaults=defaults,
            assume_default_sink=assume_default_sink,
            default_sink_c=default_sink_c,
        )
        for record in records
    ]


def clean_stream(
    records: Iterable[Mapping[str, Any]],
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    assume_default_sink: bool = True,
    default_sink_c: float = 20.0,
) -> Iterator[dict]:
    """Yield cleaned records from any iterable of raw records."""

    for record in records:
        yield clean_record(
            record,
            mapping=mapping,
            defaults=defaults,
            assume_default_sink=assume_default_sink,
            default_sink_c=default_sink_c,
        )


def clean_file(
    input_path: Union[str, Path],
    *,
    output: Optional[Union[str, Path]] = None,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    file_format: Optional[str] = None,
    assume_default_sink: bool = True,
    default_sink_c: float = 20.0,
) -> dict:
    """Clean records from CSV, JSON, JSONL/NDJSON, or Excel files."""

    records = load_any(input_path, file_format=file_format)
    cleaned = clean_records(
        records,
        mapping=mapping,
        defaults=defaults,
        assume_default_sink=assume_default_sink,
        default_sink_c=default_sink_c,
    )
    summary = clean_summary(cleaned)
    summary["records"] = cleaned
    if output is not None:
        write_clean_records(cleaned, output)
        summary["output"] = str(output)
    return summary


def clean_url(
    url: str,
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    file_format: Optional[str] = None,
) -> dict:
    """Load and clean CSV, JSON, or JSONL data from a URL."""

    with urlopen(url) as response:
        content = response.read().decode("utf-8")
        content_type = response.headers.get("content-type", "")
    fmt = file_format or _format_from_name(url, content_type=content_type)
    records = _loads_records(content, fmt)
    cleaned = clean_records(records, mapping=mapping, defaults=defaults)
    summary = clean_summary(cleaned)
    summary["records"] = cleaned
    summary["source_url"] = url
    return summary


def clean_dataframe(
    dataframe: Any,
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    return_dataframe: bool = False,
) -> Any:
    """Clean a pandas-like DataFrame.

    If `return_dataframe=True`, pandas must be installed.
    """

    records = dataframe.to_dict(orient="records")
    cleaned = clean_records(records, mapping=mapping, defaults=defaults)
    if not return_dataframe:
        return cleaned
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise ImportError("return_dataframe=True requires pandas") from exc
    return pd.DataFrame(cleaned)


def clean_sql(
    connection: Any,
    query: str,
    *,
    params: Optional[Union[Sequence[Any], Mapping[str, Any]]] = None,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
) -> list[dict]:
    """Clean rows returned by a DB-API compatible SQL connection."""

    cursor = connection.execute(query, params or ())
    columns = [column[0] for column in cursor.description]
    records = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return clean_records(records, mapping=mapping, defaults=defaults)


def load_any(input_path: Union[str, Path], *, file_format: Optional[str] = None) -> list[dict]:
    path = Path(input_path)
    fmt = (file_format or path.suffix.lstrip(".")).lower()
    if fmt == "csv":
        return load_csv(path)
    if fmt == "json":
        return load_json(path)
    if fmt in {"jsonl", "ndjson"}:
        return load_jsonl(path)
    if fmt in {"xlsx", "xls"}:
        return load_excel(path)
    raise ValueError("supported input formats are .csv, .json, .jsonl, .ndjson, .xlsx, and .xls")


def load_csv(path: Union[str, Path]) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_json(path: Union[str, Path]) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _json_to_records(data)


def load_jsonl(path: Union[str, Path]) -> list[dict]:
    records = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        value = json.loads(stripped)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL line {line_number} must be an object")
        records.append(value)
    return records


def load_excel(path: Union[str, Path], *, sheet_name: Union[str, int] = 0) -> list[dict]:
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise ImportError("Excel input requires pandas with an Excel engine such as openpyxl") from exc
    return pd.read_excel(path, sheet_name=sheet_name).to_dict(orient="records")


def write_clean_records(records: Sequence[Mapping[str, Any]], output_path: Union[str, Path]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps({"records": list(records)}, indent=2) + "\n", encoding="utf-8")
        return
    if suffix in {".jsonl", ".ndjson"}:
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return
    if suffix == ".csv":
        _write_csv(records, path)
        return
    raise ValueError("supported output formats are .csv, .json, .jsonl, and .ndjson")


def clean_summary(records: Sequence[Mapping[str, Any]]) -> dict:
    invalid = [record for record in records if record.get("issues")]
    attention = [record for record in records if record.get("needs_attention")]
    return {
        "ok": not invalid,
        "total_records": len(records),
        "clean_records": len(records) - len(invalid),
        "records_needing_attention": len(attention),
        "invalid_records": len(invalid),
        "issues": [
            {"row": index + 1, **issue}
            for index, record in enumerate(records)
            for issue in record.get("issues", [])
        ],
    }


def normalize_record(
    raw: Mapping[str, Any],
    *,
    mapping: Optional[RecordMapping] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    assume_default_sink: bool = True,
    default_sink_c: float = 20.0,
) -> dict:
    """Normalize messy field names and units into the internal adoption schema."""

    source = dict(raw)
    normalized: dict[str, Any] = {}
    warnings: list[str] = []
    assumptions: list[str] = []

    if defaults:
        normalized.update(defaults)

    _apply_mapping(source, normalized, mapping or {}, warnings)
    _apply_aliases(source, normalized)
    _parse_notation(normalized)
    _infer_quantity_and_unit_from_keys(source, normalized, warnings)
    _normalize_units(normalized)
    _convert_temperatures(normalized, warnings)
    _infer_carrier_from_context(normalized, warnings)
    _normalize_fx(normalized, source, warnings)
    _apply_fuel_reference(normalized)

    if assume_default_sink and normalized.get("source_c") not in (None, "") and normalized.get("sink_c") in (None, ""):
        normalized["sink_c"] = default_sink_c
        assumptions.append(f"default reference sink assumed: T0 = {default_sink_c:g} C")

    if warnings:
        normalized["_warnings"] = [*normalized.get("_warnings", []), *warnings]
    if assumptions:
        normalized["_assumptions"] = [*normalized.get("_assumptions", []), *assumptions]
    return normalized


def _parse_notation(normalized: dict[str, Any]) -> None:
    notation = normalized.get("notation")
    if notation in (None, ""):
        return
    parsed = parse_energy_notation(str(notation))
    normalized.setdefault("quantity", parsed.quantity)
    normalized.setdefault("unit", parsed.unit)
    normalized.setdefault("fx", parsed.exergy_factor)


def _apply_mapping(
    source: Mapping[str, Any],
    normalized: dict[str, Any],
    mapping: RecordMapping,
    warnings: list[str],
) -> None:
    for target, spec in mapping.items():
        canonical = _canonical_field(target)
        if callable(spec):
            value = spec(source)
        elif isinstance(spec, str):
            found, value = _lookup_path(source, spec)
            if not found:
                value = spec
        else:
            value = spec
        _assign_value(normalized, canonical, value, warnings)


def _apply_aliases(source: Mapping[str, Any], normalized: dict[str, Any]) -> None:
    lookup = {_normalize_key(key): value for key, value in source.items()}
    for canonical, aliases in FIELD_ALIASES.items():
        if canonical in normalized and normalized[canonical] not in (None, ""):
            continue
        for alias in aliases:
            value = lookup.get(_normalize_key(alias))
            if value not in (None, ""):
                normalized[canonical] = value
                break


def _infer_quantity_and_unit_from_keys(
    source: Mapping[str, Any],
    normalized: dict[str, Any],
    warnings: list[str],
) -> None:
    if normalized.get("quantity") not in (None, "") and normalized.get("power") not in (None, ""):
        return
    for key, value in source.items():
        if value in (None, ""):
            continue
        unit = _unit_from_key(key)
        if not unit:
            continue
        try:
            float(value)
        except (TypeError, ValueError):
            continue
        if is_power_unit(unit):
            if normalized.get("power") in (None, ""):
                normalized["power"] = value
                normalized.setdefault("unit", unit)
                warnings.append(f"inferred power and unit from field '{key}'")
        else:
            if normalized.get("quantity") in (None, ""):
                normalized["quantity"] = value
                normalized.setdefault("unit", _carrier_unit_from_key(key, unit))
                warnings.append(f"inferred quantity and unit from field '{key}'")


def _normalize_units(normalized: dict[str, Any]) -> None:
    unit = normalized.get("unit")
    if unit in (None, ""):
        return
    normalized["unit"] = _canonical_unit(str(unit))


def _convert_temperatures(normalized: dict[str, Any], warnings: list[str]) -> None:
    conversions = (
        ("source_f", "source_c", lambda value: (value - 32.0) * 5.0 / 9.0),
        ("source_k", "source_c", lambda value: value - 273.15),
        ("sink_f", "sink_c", lambda value: (value - 32.0) * 5.0 / 9.0),
        ("sink_k", "sink_c", lambda value: value - 273.15),
    )
    for source_field, target_field, converter in conversions:
        if normalized.get(target_field) not in (None, "") or normalized.get(source_field) in (None, ""):
            continue
        value = _as_float(normalized[source_field])
        if value is None:
            continue
        normalized[target_field] = converter(value)
        warnings.append(f"converted {source_field} to {target_field}")


def _infer_carrier_from_context(normalized: dict[str, Any], warnings: list[str]) -> None:
    unit = normalized.get("unit")
    if unit in (None, ""):
        return
    base, suffix = split_unit(str(unit))
    if suffix:
        return
    if normalized.get("source_c") not in (None, "") and is_energy_unit(base):
        normalized["unit"] = f"{base}_th"
        warnings.append("inferred thermal carrier from source temperature")
    elif normalized.get("cold_service_c") not in (None, "") and is_energy_unit(base):
        normalized["unit"] = f"{base}_cooling"
        warnings.append("inferred cooling carrier from cold service temperature")


def _normalize_fx(normalized: dict[str, Any], source: Mapping[str, Any], warnings: list[str]) -> None:
    if normalized.get("fx") in (None, ""):
        return
    factor = _as_float(normalized["fx"])
    if factor is None:
        return
    key_text = " ".join(str(key).lower() for key in source.keys())
    if factor > 1.0 and factor <= 100.0 and ("percent" in key_text or "pct" in key_text or "%" in key_text):
        normalized["fx"] = factor / 100.0
        warnings.append("converted percentage quality factor to fractional fx")


def _apply_fuel_reference(normalized: dict[str, Any]) -> None:
    if normalized.get("reference_id") not in (None, ""):
        return
    fuel = normalized.get("fuel")
    basis = normalized.get("energy_basis") or normalized.get("basis")
    if fuel in (None, "") or basis in (None, ""):
        return
    fuel_key = str(fuel).lower().strip().replace("-", "_")
    basis_key = str(basis).upper().strip()
    reference_id = FUEL_REFERENCE_IDS.get((fuel_key, basis_key))
    if reference_id:
        normalized["reference_id"] = reference_id


def _assign_value(normalized: dict[str, Any], field_name: str, value: Any, warnings: list[str]) -> None:
    if field_name in {"source_f", "source_k", "sink_f", "sink_k"}:
        normalized[field_name] = value
        return
    if field_name == "source_f":
        normalized["source_f"] = value
        return
    normalized[field_name] = value
    if field_name == "unit":
        normalized[field_name] = _canonical_unit(str(value))


def _canonical_field(field_name: str) -> str:
    normalized = _normalize_key(field_name)
    for canonical, aliases in FIELD_ALIASES.items():
        if normalized == _normalize_key(canonical) or normalized in {_normalize_key(alias) for alias in aliases}:
            return canonical
    return normalized


def _canonical_unit(unit: str) -> str:
    cleaned = unit.strip().replace(" ", "_").replace("-", "_")
    base, suffix = split_unit(cleaned)
    key = _normalize_key(base)
    canonical = UNIT_HINTS.get(key, base)
    return f"{canonical}{suffix}"


def _unit_from_key(key: str) -> str:
    normalized = _normalize_key(key)
    parts = normalized.split("_")
    for index, part in enumerate(parts):
        if part in UNIT_HINTS:
            unit = UNIT_HINTS[part]
            suffix = ""
            remainder = parts[index + 1 :]
            if "th" in remainder or "thermal" in parts or "heat" in parts:
                suffix = "_th"
            elif "hhv" in remainder:
                suffix = "_HHV"
            elif "lhv" in remainder:
                suffix = "_LHV"
            elif "solar" in parts:
                suffix = "_solar"
            elif "cooling" in parts or "chilled" in parts:
                suffix = "_cooling"
            return f"{unit}{suffix}"
    return ""


def _carrier_unit_from_key(key: str, unit: str) -> str:
    normalized = _normalize_key(key)
    if "_" in unit:
        return unit
    if "heat" in normalized or "thermal" in normalized or "steam" in normalized:
        return f"{unit}_th"
    if "cooling" in normalized or "chilled" in normalized:
        return f"{unit}_cooling"
    if "solar" in normalized:
        return f"{unit}_solar"
    if "hhv" in normalized:
        return f"{unit}_HHV"
    if "lhv" in normalized:
        return f"{unit}_LHV"
    return unit


def _lookup_path(source: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    if path in source:
        return True, source[path]
    current: Any = source
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_to_records(data: Any) -> list[dict]:
    if isinstance(data, dict):
        if isinstance(data.get("records"), list):
            return list(data["records"])
        if isinstance(data.get("data"), list):
            return list(data["data"])
        if isinstance(data.get("items"), list):
            return list(data["items"])
        return [data]
    if isinstance(data, list):
        return list(data)
    raise ValueError("JSON input must be an object, a list, or {'records': [...]}")


def _loads_records(content: str, fmt: str) -> list[dict]:
    if fmt == "csv":
        return [dict(row) for row in csv.DictReader(content.splitlines())]
    if fmt == "json":
        return _json_to_records(json.loads(content))
    if fmt in {"jsonl", "ndjson"}:
        return [json.loads(line) for line in content.splitlines() if line.strip()]
    raise ValueError(f"unsupported URL input format: {fmt}")


def _format_from_name(name: str, *, content_type: str = "") -> str:
    suffix = Path(name.split("?", 1)[0]).suffix.lstrip(".").lower()
    if suffix:
        return suffix
    if "jsonl" in content_type or "ndjson" in content_type:
        return "jsonl"
    if "json" in content_type:
        return "json"
    if "csv" in content_type:
        return "csv"
    raise ValueError("could not infer input format")


def _write_csv(records: Sequence[Mapping[str, Any]], path: Path) -> None:
    preferred = [
        "label",
        "quantity",
        "unit",
        "fx",
        "notation",
        "full_notation",
        "accessible_exergy",
        "accessible_exergy_unit",
        "accessible_exergy_mwh",
        "reference",
        "boundary",
        "basis",
        "capabilities",
        "missing_context",
        "assumptions",
        "warnings",
    ]
    fields = list(preferred)
    for record in records:
        for key in record.keys():
            if key not in fields and key not in {"source", "readiness", "metadata"}:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(_csv_ready(record, fields))


def _csv_ready(record: Mapping[str, Any], fields: Sequence[str]) -> dict:
    row = {field: record.get(field, "") for field in fields}
    for field, value in list(row.items()):
        if isinstance(value, list):
            row[field] = "; ".join(str(item) for item in value)
        elif isinstance(value, dict):
            row[field] = json.dumps(value, sort_keys=True)
    return row
