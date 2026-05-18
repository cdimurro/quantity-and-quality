# Energy Quantity and Quality

Instead of reporting:

```text
1 MWh
```

report:

```text
1 MWh, fx = 0.170
```

where `fx` is the **Exergy Factor**: accessible useful work potential per unit energy.

For example:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

means that 1 MWh of 80 C heat carries about 0.170 MWh_ex of accessible work potential relative to a 20 C reference sink.

This package is not a process simulator and does not replace detailed exergy analysis, ISO 50001, IPMVP, LCA, cost accounting, or engineering judgment. It gives existing energy quantity metrics one additional quality field so electricity, fuels, heat, cooling, storage, and savings can be compared honestly.

## Install

```bash
python -m pip install quantity-quality
```

For local development:

```bash
python -m pip install -e ".[all,dev]"
```

YAML scenario files require the optional scenario extra:

```bash
python -m pip install "quantity-quality[scenario]"
```

## The Three Main Workflows

### 1. Calculate One Stream

```bash
quantity-quality calc thermal --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
```

Output:

```text
80 C heat to 20 C sink
report: 1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]
accessible exergy: 0.169899 MWh_ex
```

Other common calculations:

```bash
quantity-quality calc electricity --quantity 1 --unit MWh
quantity-quality calc fuel --quantity 1 --fuel "natural gas" --basis HHV
quantity-quality calc cooling --quantity 1 --unit MWh_cooling --cold-service-c 7 --ambient-sink-c 30
quantity-quality calc custom --quantity 1 --unit MWh --fx 0.73
```

### 2. Clean Existing Energy Records

Use this when you already have CSV, JSON, JSONL, Excel, DataFrame, SQL, or stream records.

```bash
quantity-quality clean examples/adoption_records.csv --output clean.csv
```

The cleaner accepts messy field names such as `energy_kwh`, `supply_temp_f`, `fuel_type`, `reference_id`, and `fx`. It adds notation, accessible exergy, normalized MWh_ex where possible, context, assumptions, warnings, and validation issues.

### 3. Compare A Scenario

```bash
quantity-quality compare examples/process_heat_comparison.json
```

Example output:

```text
Option                Energy         fx       MWh_ex  Cost/MWh_ex  CO2/MWh_ex
--------------------  -------------  -------  ------  -----------  ----------
Natural gas HHV       10000 MWh_HHV  0.93     9300    34.4086      194.624
Hydrogen HHV          10000 MWh_HHV  0.83     8300    114.458      0
Electric resistance   10000 MWh      1        10000   70           0
Recovered 500 C heat  10000 MWh_th   0.61437  6143.7  19.5322      0
```

Markdown and JSON reports are also available:

```bash
quantity-quality compare examples/process_heat_comparison.json --format markdown --output report.md
quantity-quality compare examples/process_heat_comparison.json --format json
```

## Python API

```python
import quantity_quality as qq

record = qq.thermal(1, "MWh_th", source_c=80, sink_c=20)
print(record.full_notation)
# 1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]

print(record.accessible_exergy, record.accessible_exergy_unit)
# 0.169899... MWh_ex
```

Clean records from ordinary dictionaries:

```python
records = qq.clean_records([
    {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
    {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
    {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
])

for record in records:
    print(record["full_notation"], record["missing_context"])
```

Compare scenario files:

```python
result = qq.compare_scenario_file("examples/process_heat_comparison.json")
print(qq.scenario_to_markdown(result))
```

## Core Formula

The reporting layer normalizes different energy carriers into one field:

```text
accessible exergy = energy quantity * Exergy Factor
X_A = E * fx
```

For power:

```text
accessible exergy rate = power * Exergy Factor
Xdot_A = P * fx
```

Thermal examples use the Carnot factor:

```text
fx = 1 - T0 / Th
```

Temperatures are in kelvin internally. Public examples use `T0 = 20 C` unless another sink is declared.

Fuel examples must declare their energy basis. HHV is recommended for broad public comparison because it avoids confusing `fx > 1` values for common fuels. LHV is supported when explicitly labeled.

## Data Contract

The minimum direct record is:

```json
{
  "quantity": 1,
  "unit": "MWh",
  "exergy_factor": 0.73
}
```

For auditable records, add context:

```json
{
  "quantity": 1,
  "unit": "MWh_th",
  "exergy_factor": 0.170,
  "source_c": 80,
  "sink_c": 20,
  "reference": "20 C thermal sink",
  "boundary": "delivery point",
  "basis": "Carnot factor"
}
```

Bundled reference examples can be used with `reference_id`:

```json
{
  "quantity": 1,
  "unit": "MWh_th",
  "reference_id": "heat-80c-standard"
}
```

The JSON Schema is packaged and available at:

```text
data/quantity_quality_record.schema.json
```

CLI:

```bash
quantity-quality schema --json-schema
```

Python:

```python
schema = qq.load_record_schema()
```

## Reference Data

The package includes reference examples for electricity, thermal streams, cooling, fuels, solar radiation, storage, and measurement use cases.

```bash
quantity-quality list
quantity-quality list --category thermal
quantity-quality lookup heat-80c-standard
```

Reference data files:

```text
data/reference_examples.json
data/reference_examples.csv
```

Each reference example declares its boundary, basis, source, confidence class, and structured context such as temperatures or fuel basis where relevant.

## Website Data Export

The static `exergyfactor.com` calculator can consume reference data generated from this Python package:

```bash
quantity-quality export-web-data \
  --output ../exergy-factor/data/reference_examples.json \
  --js-output ../exergy-factor/data/reference_examples.js
```

The JavaScript bundle is synchronous and small, so the website calculator can load canonical values immediately without waiting for a runtime fetch.

## Project Contents

```text
src/quantity_quality/                 Python package
data/reference_examples.json          Canonical reference examples
data/reference_examples.csv           Spreadsheet export
data/quantity_quality_record.schema.json
                                      JSON Schema for interoperable records
examples/adoption_records.csv         Cleaning example
examples/process_heat_comparison.json Scenario comparison example
docs/adoption-cookbook.md             Practical adoption recipes
paper/                                Framework paper
```

## Development

```bash
python -m pip install -e ".[all,dev]"
python -m pytest -q
python -m build
```

The package is typed (`py.typed`) and built as a pure Python wheel.

## License

MIT
