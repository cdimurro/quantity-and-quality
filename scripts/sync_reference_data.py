from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "reference_examples.json"
CSV_PATH = ROOT / "data" / "reference_examples.csv"
PACKAGE_DATA_PATH = ROOT / "src" / "quantity_quality" / "data" / "reference_examples.json"
SCHEMA_PATH = ROOT / "data" / "quantity_quality_record.schema.json"
PACKAGE_SCHEMA_PATH = ROOT / "src" / "quantity_quality" / "data" / "quantity_quality_record.schema.json"


def main() -> None:
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not records:
        raise SystemExit("reference_examples.json is empty")

    fields = []
    for record in records:
        for field in record.keys():
            if field not in fields:
                fields.append(field)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    PACKAGE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACKAGE_DATA_PATH.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    if SCHEMA_PATH.exists():
        PACKAGE_SCHEMA_PATH.write_text(SCHEMA_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"wrote {CSV_PATH.relative_to(ROOT)}")
    print(f"wrote {PACKAGE_DATA_PATH.relative_to(ROOT)}")
    if SCHEMA_PATH.exists():
        print(f"wrote {PACKAGE_SCHEMA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
