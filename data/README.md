# Reference Examples Database

This folder contains starter examples for reporting energy quantity together with Exergy Factor.

The records are intended for adoption, review, and extension. They are not a substitute for project-specific engineering, declared reference conditions, or detailed exergy balances.

Use these records directly with the CLI:

```bash
quantity-quality lookup heat-80c-standard
quantity-quality annotate examples/adoption_records.csv --output runtime/adoption_records_annotated.csv
```

## Files

- `reference_examples.json` - canonical data source.
- `reference_examples.csv` - spreadsheet-friendly export generated from the JSON file.
- `quantity_quality_record.schema.json` - JSON Schema for interoperable records.

## Field dictionary

- `id` - stable machine-readable identifier.
- `name` - human-readable example name.
- `category` - broad class such as `thermal`, `chemical`, `electrical`, `storage`, or `measurement`.
- `carrier` - carrier or stream type.
- `basis` - calculation convention for the Exergy Factor.
- `quantity_unit` - example reporting unit.
- `exergy_factor` - accessible exergy per unit energy or power.
- `factor_unit` - reported factor unit.
- `reference` - declared sink, basis, or reference convention.
- `boundary` - reporting boundary where the factor is intended to apply.
- `calculation` - concise calculation note.
- `adoption_note` - practical use note.
- `source` - origin of the example value.
- `source_c` - explicit thermal source temperature in C, when relevant.
- `sink_c` - explicit thermal sink/reference temperature in C, when relevant.
- `cold_service_c` - explicit cooling service temperature in C, when relevant.
- `ambient_sink_c` - explicit cooling heat-rejection temperature in C, when relevant.
- `basis_type` - machine-readable calculation class such as `thermal_carnot`, `cooling_service`, `chemical_exergy_factor`, or `work_equivalent`.
- `fuel_basis` - fuel denominator such as `HHV` or `LHV`, when relevant.
- `confidence` - use class such as `framework_convention`, `computed_reference`, `reference_default`, or `illustrative_reference`.

Rows in operational spreadsheets can use `reference_id` to copy a bundled example's `exergy_factor`, `reference`, `boundary`, and `basis` into an annotated output file.

## Contribution standard

New examples should declare:

1. The reporting boundary.
2. The reference sink or environment.
3. The carrier and energy basis.
4. The formula or table used.
5. Whether the value is standard, local, operational, or illustrative.
