from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "reference_examples.json"
CSV_PATH = ROOT / "data" / "reference_examples.csv"
PACKAGE_DATA_PATH = ROOT / "src" / "quantity_quality" / "data" / "reference_examples.json"
SCHEMA_PATH = ROOT / "data" / "quantity_quality_record.schema.json"
PACKAGE_SCHEMA_PATH = (
    ROOT / "src" / "quantity_quality" / "data" / "quantity_quality_record.schema.json"
)
STREAM_SCHEMA_PATH = ROOT / "data" / "stream_calculation_request.schema.json"
PACKAGE_STREAM_SCHEMA_PATH = (
    ROOT / "src" / "quantity_quality" / "data" / "stream_calculation_request.schema.json"
)
ACCOUNTING_SCHEMA_PATH = ROOT / "data" / "energy_accounting_request.schema.json"
PACKAGE_ACCOUNTING_SCHEMA_PATH = (
    ROOT / "src" / "quantity_quality" / "data" / "energy_accounting_request.schema.json"
)
CONFORMANCE_PATH = ROOT / "data" / "conformance_contract_v1.json"
PACKAGE_CONFORMANCE_PATH = (
    ROOT / "src" / "quantity_quality" / "data" / "conformance_contract_v1.json"
)
CONFORMANCE_SCHEMA_PATH = ROOT / "data" / "conformance_contract_v1.schema.json"
PACKAGE_CONFORMANCE_SCHEMA_PATH = (
    ROOT / "src" / "quantity_quality" / "data" / "conformance_contract_v1.schema.json"
)


def _csv_text(records: list[dict], fields: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _matches(path: Path, expected: str) -> bool:
    return path.exists() and path.read_text(encoding="utf-8") == expected


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize generated reference data and the packaged schema."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated files are stale without modifying them",
    )
    args = parser.parse_args(argv)

    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not records:
        raise SystemExit("reference_examples.json is empty")

    fields = []
    for record in records:
        for field in record.keys():
            if field not in fields:
                fields.append(field)
    csv_text = _csv_text(records, fields)
    package_data_text = json.dumps(records, indent=2) + "\n"
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else None
    stream_schema_text = (
        STREAM_SCHEMA_PATH.read_text(encoding="utf-8") if STREAM_SCHEMA_PATH.exists() else None
    )
    accounting_schema_text = (
        ACCOUNTING_SCHEMA_PATH.read_text(encoding="utf-8")
        if ACCOUNTING_SCHEMA_PATH.exists()
        else None
    )
    conformance = json.loads(CONFORMANCE_PATH.read_text(encoding="utf-8"))
    reference_hash = hashlib.sha256(
        DATA_PATH.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    if conformance["reference_data"]["sha256"] != reference_hash:
        raise SystemExit(
            f"conformance contract reference-data hash is stale: expected {reference_hash}"
        )
    if conformance["reference_data"]["record_count"] != len(records):
        raise SystemExit("conformance contract reference-data record count is stale")
    conformance_text = json.dumps(conformance, indent=2) + "\n"
    conformance_schema_text = CONFORMANCE_SCHEMA_PATH.read_text(encoding="utf-8")

    expected = {
        CSV_PATH: csv_text,
        PACKAGE_DATA_PATH: package_data_text,
        PACKAGE_CONFORMANCE_PATH: conformance_text,
        PACKAGE_CONFORMANCE_SCHEMA_PATH: conformance_schema_text,
    }
    if schema_text is not None:
        expected[PACKAGE_SCHEMA_PATH] = schema_text
    if stream_schema_text is not None:
        expected[PACKAGE_STREAM_SCHEMA_PATH] = stream_schema_text
    if accounting_schema_text is not None:
        expected[PACKAGE_ACCOUNTING_SCHEMA_PATH] = accounting_schema_text

    if args.check:
        stale = [
            path.relative_to(ROOT) for path, text in expected.items() if not _matches(path, text)
        ]
        if stale:
            names = ", ".join(str(path) for path in stale)
            raise SystemExit(f"generated files are stale: {names}")
        print("reference data and packaged schema are synchronized")
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSV_PATH.write_text(csv_text, encoding="utf-8")
    PACKAGE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACKAGE_DATA_PATH.write_text(package_data_text, encoding="utf-8")
    PACKAGE_CONFORMANCE_PATH.write_text(conformance_text, encoding="utf-8")
    PACKAGE_CONFORMANCE_SCHEMA_PATH.write_text(conformance_schema_text, encoding="utf-8")

    if schema_text is not None:
        PACKAGE_SCHEMA_PATH.write_text(schema_text, encoding="utf-8")
    if stream_schema_text is not None:
        PACKAGE_STREAM_SCHEMA_PATH.write_text(stream_schema_text, encoding="utf-8")
    if accounting_schema_text is not None:
        PACKAGE_ACCOUNTING_SCHEMA_PATH.write_text(accounting_schema_text, encoding="utf-8")

    print(f"wrote {CSV_PATH.relative_to(ROOT)}")
    print(f"wrote {PACKAGE_DATA_PATH.relative_to(ROOT)}")
    print(f"wrote {PACKAGE_CONFORMANCE_PATH.relative_to(ROOT)}")
    print(f"wrote {PACKAGE_CONFORMANCE_SCHEMA_PATH.relative_to(ROOT)}")
    if SCHEMA_PATH.exists():
        print(f"wrote {PACKAGE_SCHEMA_PATH.relative_to(ROOT)}")
    if STREAM_SCHEMA_PATH.exists():
        print(f"wrote {PACKAGE_STREAM_SCHEMA_PATH.relative_to(ROOT)}")
    if ACCOUNTING_SCHEMA_PATH.exists():
        print(f"wrote {PACKAGE_ACCOUNTING_SCHEMA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
