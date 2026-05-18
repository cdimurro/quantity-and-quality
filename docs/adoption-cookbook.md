# Quantity + Quality Adoption Cookbook

This cookbook shows low-friction ways to add Exergy Factor reporting to existing energy records.

## 1. Add One Column To Existing Data

Start with the records you already have:

```csv
asset,energy_kwh,reference_id
Grid meter,845,electricity-delivered
District heat loop,1800,heat-80c-standard
```

Clean and annotate them:

```bash
quantity-quality clean energy.csv --output energy_qq.csv
```

The output adds `fx`, `full_notation`, `accessible_exergy`, context, assumptions, and warnings.

## 2. Calculate One Known Stream

Use `calc` when you know what kind of stream you are reporting.

```bash
quantity-quality calc thermal --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
quantity-quality calc fuel --quantity 1 --fuel "natural gas" --basis HHV
quantity-quality calc electricity --quantity 1 --unit MWh
```

## 3. Compare Options

Use a scenario file when comparing alternatives.

```bash
quantity-quality compare examples/process_heat_comparison.json
quantity-quality compare examples/process_heat_comparison.json --format markdown --output report.md
```

The comparison table includes energy quantity, `fx`, accessible exergy, unavailable energy where meaningful, and cost or CO2 normalized by `MWh_ex` when those inputs are supplied.

## 4. Energy Audits And M&V

For efficiency projects, report avoided energy and avoided accessible exergy side by side:

```json
{
  "quantity": 100,
  "unit": "MWh",
  "reference_id": "electricity-delivered",
  "label": "avoided electricity"
}
```

Low-temperature heat savings should not be treated as equivalent to electricity savings:

```json
{
  "quantity": 100,
  "unit": "MWh_th",
  "reference_id": "heat-40c-standard",
  "label": "avoided 40 C heat"
}
```

## 5. District Heating And Cooling

For district systems, prefer actual delivery and return or rejection conditions when available:

```json
{
  "quantity": 1800,
  "unit": "MWh_th",
  "source_c": 80,
  "sink_c": 50,
  "label": "80 C district heat to 50 C return"
}
```

If those temperatures are not available, use a reference id and let the output show what context is assumed.

## 6. Fuels And Hydrogen

Always declare the basis:

```bash
quantity-quality calc fuel --fuel hydrogen --basis HHV --quantity 6.8 --unit MWh_HHV
quantity-quality calc fuel --fuel hydrogen --basis LHV --quantity 6.8 --unit MWh_LHV
```

LHV factors can exceed 1 for some fuels because the denominator is a selected accounting basis. Use HHV for broad public comparisons unless your workflow explicitly requires LHV.

## 7. Software Integration

For APIs and databases, validate records against:

```text
data/quantity_quality_record.schema.json
```

The minimum direct-record pattern is:

```json
{
  "quantity": 1,
  "unit": "MWh",
  "exergy_factor": 0.73
}
```

For auditable records, add `reference`, `boundary`, and `basis`, or use a bundled `reference_id`.
