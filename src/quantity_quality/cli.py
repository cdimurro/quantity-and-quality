from __future__ import annotations

import argparse
import json
import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Iterable, Optional

from .adoption import ADOPTION_FIELDS, COMMON_NOTATION_EXAMPLES, INPUT_PATTERNS, STANDARD_INTEGRATION_POINTS
from .api import (
    cooling as build_cooling,
    electricity as build_electricity,
    fuel as build_fuel,
    from_notation as build_from_notation,
    lookup as build_lookup,
    report as build_report,
    solar as build_solar,
    thermal as build_thermal,
)
from .clean import clean_file
from .core import solar_exergy_rate
from .records import REPORT_SCHEMA_VERSION
from .reference import filter_reference_examples
from .scenario import compare_scenario_file, scenario_to_markdown, scenario_to_table
from .schema import load_record_schema
from .web_export import write_web_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantity-quality",
        description="Adopt quantity-plus-Exergy-Factor energy reporting.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Create one report: 1 MWh, fx = 0.73.")
    report.add_argument("--quantity", type=float, required=True)
    report.add_argument("--unit", required=True)
    report.add_argument("--fx", "--exergy-factor", dest="exergy_factor", type=float, required=True)
    _add_context_args(report)
    report.add_argument("--label", default="")
    report.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    report.set_defaults(func=cmd_report)

    parse = subparsers.add_parser("parse", help="Parse notation like '1 MWh, fx = 0.73'.")
    parse.add_argument("notation")
    parse.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parse.set_defaults(func=cmd_parse)

    thermal = subparsers.add_parser("thermal", help="Compute a thermal Exergy Factor.")
    thermal.add_argument("--source-c", type=float, required=True)
    thermal.add_argument("--sink-c", type=float, default=None, help="Reference sink in C; defaults to 20 C.")
    thermal.add_argument("--quantity", type=float, default=1.0)
    thermal.add_argument("--unit", default="MWh_th")
    _add_context_args(thermal)
    thermal.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    thermal.set_defaults(func=cmd_thermal)

    solar = subparsers.add_parser("solar", help="Compute solar radiation fx and optional exergy rate.")
    solar.add_argument("--quantity", type=float, default=1.0)
    solar.add_argument("--unit", default="MWh_solar")
    solar.add_argument("--reference-c", type=float, default=20.0)
    solar.add_argument("--irradiance-w-m2", type=float, default=None)
    solar.add_argument("--area-m2", type=float, default=None)
    _add_context_args(solar, reference="20 C reference environment", boundary="solar resource boundary")
    solar.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    solar.set_defaults(func=cmd_solar)

    calc = subparsers.add_parser("calc", help="Calculate common Quantity + Quality records.")
    calc_subparsers = calc.add_subparsers(dest="calc_command", required=True)

    calc_custom = calc_subparsers.add_parser("custom", help="Calculate from quantity, unit, and fx.")
    calc_custom.add_argument("--quantity", type=float, required=True)
    calc_custom.add_argument("--unit", required=True)
    calc_custom.add_argument("--fx", "--exergy-factor", dest="exergy_factor", type=float, required=True)
    _add_context_args(calc_custom)
    calc_custom.add_argument("--label", default="")
    calc_custom.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_custom.set_defaults(func=cmd_report)

    calc_thermal = calc_subparsers.add_parser("thermal", help="Calculate thermal Exergy Factor.")
    calc_thermal.add_argument("--source-c", type=float, required=True)
    calc_thermal.add_argument("--sink-c", type=float, default=None, help="Reference sink in C; defaults to 20 C.")
    calc_thermal.add_argument("--quantity", type=float, default=1.0)
    calc_thermal.add_argument("--unit", default="MWh_th")
    _add_context_args(calc_thermal)
    calc_thermal.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_thermal.set_defaults(func=cmd_thermal)

    calc_cooling = calc_subparsers.add_parser("cooling", help="Calculate cooling service Exergy Factor.")
    calc_cooling.add_argument("--cold-service-c", type=float, required=True)
    calc_cooling.add_argument("--ambient-sink-c", type=float, required=True)
    calc_cooling.add_argument("--quantity", type=float, default=1.0)
    calc_cooling.add_argument("--unit", default="MWh_cooling")
    calc_cooling.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_cooling.set_defaults(func=cmd_calc_cooling)

    calc_electricity = calc_subparsers.add_parser("electricity", help="Calculate delivered electricity at fx = 1.")
    calc_electricity.add_argument("--quantity", type=float, default=1.0)
    calc_electricity.add_argument("--unit", default="MWh")
    calc_electricity.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_electricity.set_defaults(func=cmd_calc_electricity)

    calc_fuel = calc_subparsers.add_parser("fuel", help="Calculate a bundled fuel preset.")
    calc_fuel.add_argument("--fuel", required=True)
    calc_fuel.add_argument("--basis", default="HHV")
    calc_fuel.add_argument("--quantity", type=float, default=1.0)
    calc_fuel.add_argument("--unit", default="")
    calc_fuel.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_fuel.set_defaults(func=cmd_calc_fuel)

    calc_reference = calc_subparsers.add_parser("reference", help="Calculate from a bundled reference id.")
    calc_reference.add_argument("id")
    calc_reference.add_argument("--quantity", type=float, default=1.0)
    calc_reference.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    calc_reference.set_defaults(func=cmd_lookup)

    lookup = subparsers.add_parser("lookup", help="Show one reference example.")
    lookup.add_argument("id")
    lookup.add_argument("--quantity", type=float, default=1.0)
    lookup.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    lookup.set_defaults(func=cmd_lookup)

    list_cmd = subparsers.add_parser("list", help="List bundled reference examples.")
    list_cmd.add_argument("--category")
    list_cmd.add_argument("--text")
    list_cmd.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    list_cmd.set_defaults(func=cmd_list)

    examples = subparsers.add_parser("examples", help="Show common industry notation examples.")
    examples.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    examples.set_defaults(func=cmd_examples)

    annotate = subparsers.add_parser("annotate", help="Clean messy energy records into Quantity + Quality records.")
    _add_clean_args(annotate)
    annotate.set_defaults(func=cmd_annotate)

    clean = subparsers.add_parser("clean", help="Alias for annotate: clean messy energy records.")
    _add_clean_args(clean)
    clean.set_defaults(func=cmd_annotate)

    compare_cmd = subparsers.add_parser("compare", help="Compare a scenario JSON/YAML file.")
    compare_cmd.add_argument("scenario", help="Scenario .json, .yaml, or .yml file")
    compare_cmd.add_argument("--format", choices=("table", "json", "markdown"), default="table")
    compare_cmd.add_argument("--output", "-o", default="", help="Optional output file for JSON or Markdown.")
    compare_cmd.set_defaults(func=cmd_compare)

    validate = subparsers.add_parser("validate", help="Validate/preview messy energy records.")
    validate.add_argument("input", help="Input .csv, .json, .jsonl, .ndjson, .xlsx, or .xls file")
    validate.add_argument("--mapping", default="", help="JSON object or path mapping standard fields to source fields.")
    validate.add_argument("--defaults", default="", help="JSON object or path with default field values.")
    validate.add_argument("--default-sink-c", type=float, default=20.0)
    validate.add_argument("--no-default-sink", action="store_true", help="Do not assume T0 = 20 C for thermal records.")
    validate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    validate.set_defaults(func=cmd_validate)

    schema = subparsers.add_parser("schema", help="Show the minimum adoption fields.")
    schema.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    schema.add_argument("--json-schema", action="store_true", help="Emit the record JSON Schema.")
    schema.set_defaults(func=cmd_schema)

    export_web = subparsers.add_parser("export-web-data", help="Export static website reference data.")
    export_web.add_argument("--output", "-o", required=True, help="Output JSON file for website reference data.")
    export_web.add_argument(
        "--js-output",
        default="",
        help="Optional synchronous browser data bundle loaded before script.js.",
    )
    export_web.set_defaults(func=cmd_export_web_data)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args) or 0)


def cmd_report(args: argparse.Namespace) -> int:
    record = build_report(
        args.quantity,
        args.unit,
        fx=args.exergy_factor,
        label=args.label or None,
        reference=args.reference,
        boundary=args.boundary,
        basis=args.operating_basis,
    )
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    record = build_from_notation(args.notation)
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_thermal(args: argparse.Namespace) -> int:
    record = build_thermal(
        quantity=args.quantity,
        unit=args.unit,
        source_c=args.source_c,
        sink_c=args.sink_c,
        reference=args.reference,
        boundary=args.boundary or "thermal stream",
        basis=args.operating_basis,
    )
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_solar(args: argparse.Namespace) -> int:
    reference_k = args.reference_c + 273.15
    report = build_solar(
        quantity=args.quantity,
        unit=args.unit,
        reference_c=args.reference_c,
        reference=args.reference,
        boundary=args.boundary or "solar resource boundary",
        basis=args.operating_basis,
    ).as_dict()
    if args.irradiance_w_m2 is not None and args.area_m2 is not None:
        report["solar_exergy_rate_w"] = solar_exergy_rate(
            args.irradiance_w_m2,
            args.area_m2,
            reference_k,
        )
    _emit_report(report, args.json)
    return 0


def cmd_calc_cooling(args: argparse.Namespace) -> int:
    record = build_cooling(
        quantity=args.quantity,
        unit=args.unit,
        cold_service_c=args.cold_service_c,
        ambient_sink_c=args.ambient_sink_c,
    )
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_calc_electricity(args: argparse.Namespace) -> int:
    record = build_electricity(quantity=args.quantity, unit=args.unit)
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_calc_fuel(args: argparse.Namespace) -> int:
    record = build_fuel(
        args.quantity,
        args.fuel,
        basis=args.basis,
        unit=args.unit or None,
    )
    _emit_report(record.as_dict(), args.json)
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    record = build_lookup(args.id, quantity=args.quantity)
    payload = record.as_dict()
    if args.json:
        _emit_json(payload)
    else:
        print(payload.get("label", args.id))
        print(f"report: {payload['full_notation']}")
        print(f"accessible exergy: {payload['accessible_exergy']:.6g} {payload['accessible_exergy_unit']}")
        capabilities = ", ".join(payload.get("capabilities", []))
        if capabilities:
            print(f"capabilities: {capabilities}")
        missing = ", ".join(payload.get("missing_context", []))
        if missing:
            print(f"missing context: {missing}")
        print(f"reference: {payload['reference']}")
        print(f"basis: {payload['basis']}")
        adoption_note = payload.get("metadata", {}).get("adoption_note", "")
        if adoption_note:
            print(f"use: {adoption_note}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    records = filter_reference_examples(category=args.category, text=args.text)
    if args.json:
        _emit_json({"schema_version": REPORT_SCHEMA_VERSION, "records": records})
    else:
        for record in records:
            print(f"{record['id']}: {record['name']} | fx={record['exergy_factor']}")
    return 0


def cmd_examples(args: argparse.Namespace) -> int:
    if args.json:
        _emit_json({"schema_version": REPORT_SCHEMA_VERSION, "records": COMMON_NOTATION_EXAMPLES})
    else:
        for record in COMMON_NOTATION_EXAMPLES:
            print(f"{record['notation']:28}  {record['name']}  ({record['where_used']})")
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
    summary = clean_file(
        args.input,
        output=args.output or None,
        mapping=_load_json_arg(args.mapping),
        defaults=_load_json_arg(args.defaults),
        assume_default_sink=not args.no_default_sink,
        default_sink_c=args.default_sink_c,
    )
    if args.json:
        _emit_json(summary)
    else:
        print(f"records: {summary['clean_records']} clean / {summary['total_records']} total")
        print(f"needs attention: {summary['records_needing_attention']}")
        if args.output:
            print(f"wrote: {args.output}")
        for issue in summary["issues"]:
            print(f"row {issue['row']}: {issue['field']} - {issue['message']}")
    return 0 if summary["ok"] else 2


def cmd_validate(args: argparse.Namespace) -> int:
    summary = clean_file(
        args.input,
        mapping=_load_json_arg(args.mapping),
        defaults=_load_json_arg(args.defaults),
        assume_default_sink=not args.no_default_sink,
        default_sink_c=args.default_sink_c,
    )
    if args.json:
        _emit_json(summary)
    else:
        print(f"valid: {summary['ok']}")
        print(f"records: {summary['clean_records']} clean / {summary['total_records']} total")
        print(f"needs attention: {summary['records_needing_attention']}")
        for issue in summary["issues"]:
            print(f"row {issue['row']}: {issue['field']} - {issue['message']}")
    return 0 if summary["ok"] else 2


def cmd_compare(args: argparse.Namespace) -> int:
    result = compare_scenario_file(args.scenario)
    if args.format == "json":
        text = json.dumps(result, indent=2) + "\n"
    elif args.format == "markdown":
        text = scenario_to_markdown(result)
    else:
        text = scenario_to_table(result) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote: {args.output}")
    else:
        print(text, end="")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    if args.json_schema:
        _emit_json(load_record_schema())
        return 0
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "recommended_fields": ADOPTION_FIELDS,
        "input_patterns": INPUT_PATTERNS,
        "integration_points": STANDARD_INTEGRATION_POINTS,
    }
    if args.json:
        _emit_json(payload)
    else:
        print(f"schema: {REPORT_SCHEMA_VERSION}")
        print("input patterns:")
        for name, fields in INPUT_PATTERNS.items():
            print(f"  - {name}: {', '.join(fields)}")
        print("recommended interoperable fields:")
        for field in ADOPTION_FIELDS:
            print(f"  - {field}")
        print("integration points:")
        for point in STANDARD_INTEGRATION_POINTS:
            print(f"  - {point['standard']}: {point['adoption_path']}")
    return 0


def cmd_export_web_data(args: argparse.Namespace) -> int:
    payload = write_web_data(args.output, js_output=args.js_output or None)
    print(f"wrote: {args.output}")
    if args.js_output:
        print(f"wrote: {args.js_output}")
    print(f"schema: {payload['schema_version']}")
    print(f"presets: {len(payload['presets'])}")
    return 0


def _add_context_args(
    parser: argparse.ArgumentParser,
    *,
    reference: str = "",
    boundary: str = "",
) -> None:
    parser.add_argument("--reference", default=reference)
    parser.add_argument("--boundary", default=boundary)
    parser.add_argument("--operating-basis", default="")


def _add_clean_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", help="Input .csv, .json, .jsonl, .ndjson, .xlsx, or .xls file")
    parser.add_argument("--output", "-o", default="", help="Optional output .csv, .json, .jsonl, or .ndjson file")
    parser.add_argument("--mapping", default="", help="JSON object or path mapping standard fields to source fields.")
    parser.add_argument("--defaults", default="", help="JSON object or path with default field values.")
    parser.add_argument("--default-sink-c", type=float, default=20.0)
    parser.add_argument("--no-default-sink", action="store_true", help="Do not assume T0 = 20 C for thermal records.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary instead of text.")


def _emit_report(payload: dict, as_json: bool) -> None:
    if as_json:
        _emit_json({"schema_version": REPORT_SCHEMA_VERSION, "record": payload})
        return
    print(payload.get("label") or "energy report")
    print(f"report: {payload.get('full_notation') or payload['notation']}")
    exergy = payload.get("accessible_exergy", payload.get("accessible_exergy_rate"))
    exergy_unit = payload.get("accessible_exergy_unit", payload.get("accessible_exergy_rate_unit"))
    print(f"accessible exergy: {exergy:.6g} {exergy_unit}")
    capabilities = ", ".join(payload.get("capabilities", []))
    if capabilities:
        print(f"capabilities: {capabilities}")
    missing = ", ".join(payload.get("missing_context", []))
    if missing:
        print(f"missing context: {missing}")
    for assumption in payload.get("assumptions", []):
        print(f"assumption: {assumption}")
    for warning in payload.get("warnings", []):
        print(f"warning: {warning}")
    if "solar_exergy_rate_w" in payload:
        print(f"solar exergy rate: {payload['solar_exergy_rate_w']:.6g} W_ex")


def _emit_json(payload: object) -> None:
    print(json.dumps(payload, indent=2))


def _load_json_arg(value: str) -> Optional[dict]:
    if not value:
        return None
    path = Path(value)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(value)
    if not isinstance(data, dict):
        raise ValueError("mapping/defaults must be a JSON object")
    return data


def _package_version() -> str:
    try:
        return version("quantity-quality")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject.exists():
            match = re.search(r'^version = "([^"]+)"', pyproject.read_text(encoding="utf-8"), flags=re.MULTILINE)
            if match:
                return match.group(1)
        return "0.0.0+local"
