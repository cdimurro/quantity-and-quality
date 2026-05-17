from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from .adoption import ADOPTION_FIELDS, COMMON_NOTATION_EXAMPLES, STANDARD_INTEGRATION_POINTS
from .core import (
    EnergyReport,
    ReferenceContext,
    exergy_unit,
    format_energy_notation,
    parse_energy_notation,
    petela_exergy_factor,
    report_from_notation,
    solar_exergy_rate,
    thermal_exergy_factor_c,
)
from .records import (
    REPORT_SCHEMA_VERSION,
    annotate_records,
    load_records,
    validation_summary,
    write_annotated_records,
)
from .reference import filter_reference_examples, get_reference_example


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantity-quality",
        description="Adopt quantity-plus-Exergy-Factor energy reporting.",
    )
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
    thermal.add_argument("--sink-c", type=float, required=True)
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

    annotate = subparsers.add_parser("annotate", help="Annotate CSV/JSON records with fx and MWh_ex.")
    annotate.add_argument("input", help="Input .csv or .json file")
    annotate.add_argument("--output", "-o", default="", help="Optional output .csv or .json file")
    annotate.add_argument("--json", action="store_true", help="Emit JSON summary instead of text.")
    annotate.set_defaults(func=cmd_annotate)

    validate = subparsers.add_parser("validate", help="Validate CSV/JSON adoption records.")
    validate.add_argument("input", help="Input .csv or .json file")
    validate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    validate.set_defaults(func=cmd_validate)

    schema = subparsers.add_parser("schema", help="Show the minimum adoption fields.")
    schema.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    schema.set_defaults(func=cmd_schema)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args) or 0)


def cmd_report(args: argparse.Namespace) -> int:
    report = EnergyReport(
        quantity=args.quantity,
        unit=args.unit,
        exergy_factor=args.exergy_factor,
        label=args.label or None,
        context=_context_from_args(args),
    )
    _emit_report(report.as_dict(), args.json)
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    report = report_from_notation(args.notation)
    _emit_report(report.as_dict(), args.json)
    return 0


def cmd_thermal(args: argparse.Namespace) -> int:
    factor = thermal_exergy_factor_c(args.source_c, args.sink_c)
    report = EnergyReport(
        quantity=args.quantity,
        unit=args.unit,
        exergy_factor=factor,
        label=f"{args.source_c:g} C heat to {args.sink_c:g} C sink",
        context=ReferenceContext(
            reference=args.reference,
            boundary=args.boundary,
            operating_basis=(
                args.operating_basis
                or f"Carnot factor, source={args.source_c:g} C, sink={args.sink_c:g} C"
            ),
        ),
    )
    _emit_report(report.as_dict(), args.json)
    return 0


def cmd_solar(args: argparse.Namespace) -> int:
    reference_k = args.reference_c + 273.15
    factor = petela_exergy_factor(reference_k)
    report = EnergyReport(
        quantity=args.quantity,
        unit=args.unit,
        exergy_factor=factor,
        label=f"solar radiation at {args.reference_c:g} C reference",
        context=ReferenceContext(
            reference=args.reference,
            boundary=args.boundary,
            operating_basis=args.operating_basis or "Petela radiation factor",
        ),
    ).as_dict()
    if args.irradiance_w_m2 is not None and args.area_m2 is not None:
        report["solar_exergy_rate_w"] = solar_exergy_rate(
            args.irradiance_w_m2,
            args.area_m2,
            reference_k,
        )
    _emit_report(report, args.json)
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    record = get_reference_example(args.id)
    unit = record["quantity_unit"]
    factor = float(record["exergy_factor"])
    payload = dict(record)
    payload["notation"] = format_energy_notation(args.quantity, unit, factor)
    payload["accessible_exergy"] = args.quantity * factor
    payload["accessible_exergy_unit"] = exergy_unit(unit)
    if args.json:
        _emit_json(payload)
    else:
        print(f"{payload['id']}: {payload['name']}")
        print(f"report: {payload['notation']}")
        print(f"accessible exergy: {payload['accessible_exergy']:.6g} {payload['accessible_exergy_unit']}")
        print(f"reference: {payload['reference']}")
        print(f"basis: {payload['basis']}")
        print(f"use: {payload['adoption_note']}")
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
    records = annotate_records(load_records(Path(args.input)))
    summary = validation_summary(records)
    if args.output:
        write_annotated_records(records, Path(args.output))
        summary["output"] = args.output
    if args.json:
        _emit_json(summary)
    else:
        print(f"records: {summary['valid_records']} valid / {summary['total_records']} total")
        if args.output:
            print(f"wrote: {args.output}")
        for issue in summary["issues"]:
            print(f"row {issue['row']}: {issue['field']} - {issue['message']}")
    return 0 if summary["ok"] else 2


def cmd_validate(args: argparse.Namespace) -> int:
    summary = validation_summary(annotate_records(load_records(Path(args.input))))
    if args.json:
        _emit_json(summary)
    else:
        print(f"valid: {summary['ok']}")
        print(f"records: {summary['valid_records']} valid / {summary['total_records']} total")
        for issue in summary["issues"]:
            print(f"row {issue['row']}: {issue['field']} - {issue['message']}")
    return 0 if summary["ok"] else 2


def cmd_schema(args: argparse.Namespace) -> int:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "minimum_fields": ADOPTION_FIELDS,
        "integration_points": STANDARD_INTEGRATION_POINTS,
    }
    if args.json:
        _emit_json(payload)
    else:
        print(f"schema: {REPORT_SCHEMA_VERSION}")
        print("minimum fields:")
        for field in ADOPTION_FIELDS:
            print(f"  - {field}")
        print("integration points:")
        for point in STANDARD_INTEGRATION_POINTS:
            print(f"  - {point['standard']}: {point['adoption_path']}")
    return 0


def _add_context_args(
    parser: argparse.ArgumentParser,
    *,
    reference: str = "declared by reporter",
    boundary: str = "declared reporting boundary",
) -> None:
    parser.add_argument("--reference", default=reference)
    parser.add_argument("--boundary", default=boundary)
    parser.add_argument("--operating-basis", default="")


def _context_from_args(args: argparse.Namespace) -> ReferenceContext:
    return ReferenceContext(
        reference=args.reference,
        boundary=args.boundary,
        operating_basis=args.operating_basis or "provided Exergy Factor",
    )


def _emit_report(payload: dict, as_json: bool) -> None:
    if as_json:
        _emit_json({"schema_version": REPORT_SCHEMA_VERSION, "record": payload})
        return
    print(payload.get("label") or "energy report")
    print(f"report: {payload['notation']}")
    exergy = payload.get("accessible_exergy", payload.get("accessible_exergy_rate"))
    exergy_unit = payload.get("accessible_exergy_unit", payload.get("accessible_exergy_rate_unit"))
    print(f"accessible exergy: {exergy:.6g} {exergy_unit}")
    if "solar_exergy_rate_w" in payload:
        print(f"solar exergy rate: {payload['solar_exergy_rate_w']:.6g} W_ex")


def _emit_json(payload: object) -> None:
    print(json.dumps(payload, indent=2))
