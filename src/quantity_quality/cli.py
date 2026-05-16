from __future__ import annotations

import argparse
import json
from typing import Iterable, Optional

from .core import EnergyReport, ReferenceContext, thermal_exergy_factor_c
from .reference import filter_reference_examples, get_reference_example


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantity-quality",
        description="Report energy quantity together with Exergy Factor.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    thermal = subparsers.add_parser("thermal", help="Compute a thermal Exergy Factor.")
    thermal.add_argument("--source-c", type=float, required=True)
    thermal.add_argument("--sink-c", type=float, required=True)
    thermal.add_argument("--quantity", type=float, default=1.0)
    thermal.add_argument("--unit", default="MWh")
    thermal.add_argument("--reference", default="declared thermal sink")
    thermal.add_argument("--boundary", default="thermal reporting boundary")
    thermal.add_argument("--json", action="store_true", help="Emit JSON instead of text.")

    lookup = subparsers.add_parser("lookup", help="Show one reference example.")
    lookup.add_argument("id")
    lookup.add_argument("--json", action="store_true", help="Emit JSON instead of text.")

    list_cmd = subparsers.add_parser("list", help="List bundled reference examples.")
    list_cmd.add_argument("--category")
    list_cmd.add_argument("--text")
    list_cmd.add_argument("--json", action="store_true", help="Emit JSON instead of text.")

    return parser


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "thermal":
        factor = thermal_exergy_factor_c(args.source_c, args.sink_c)
        report = EnergyReport(
            quantity=args.quantity,
            unit=args.unit,
            exergy_factor=factor,
            label=f"{args.source_c:g} C heat to {args.sink_c:g} C sink",
            context=ReferenceContext(
                reference=args.reference,
                boundary=args.boundary,
                operating_basis=f"Carnot factor, source={args.source_c:g} C, sink={args.sink_c:g} C",
            ),
        )
        _emit(report.as_dict(), args.json)
        return

    if args.command == "lookup":
        _emit(get_reference_example(args.id), args.json)
        return

    if args.command == "list":
        records = filter_reference_examples(category=args.category, text=args.text)
        _emit(records, args.json)
        return

    parser.error(f"unknown command: {args.command}")


def _emit(payload: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    if isinstance(payload, list):
        for record in payload:
            print(f"{record['id']}: {record['name']} | f_X={record['exergy_factor']}")
        return

    if isinstance(payload, dict) and payload.get("type") == "energy":
        print(f"{payload['label']}")
        print(f"quantity: {payload['quantity']} {payload['unit']}")
        print(f"f_X: {payload['exergy_factor']:.6g}")
        print(f"accessible exergy: {payload['accessible_exergy']:.6g} {payload['accessible_exergy_unit']}")
        return

    if isinstance(payload, dict):
        print(f"{payload['id']}: {payload['name']}")
        print(f"category: {payload['category']}")
        print(f"basis: {payload['basis']}")
        print(f"f_X: {payload['exergy_factor']}")
        print(f"reference: {payload['reference']}")
        print(f"use: {payload['adoption_note']}")
        return

    print(payload)
