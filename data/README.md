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

Rows in operational spreadsheets can use `reference_id` to copy a bundled example's `exergy_factor`, `reference`, `boundary`, and `basis` into an annotated output file.

## Contribution standard

New examples should declare:

1. The reporting boundary.
2. The reference sink or environment.
3. The carrier and energy basis.
4. The formula or table used.
5. Whether the value is standard, local, operational, or illustrative.
