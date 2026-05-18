# Quantity and Quality

A lightweight Python library and CLI for reporting **energy quantity** together with **energy quality**.

Instead of writing:

```text
1 MWh
```

write:

```text
1 MWh, fx = 0.170
```

where `fx` is the **Exergy Factor**: accessible useful work potential per unit of energy.

For example:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

means that 1 MWh of 80 °C heat carries about:

```text
0.170 MWh_ex
```

of accessible work potential relative to a 20 °C reference sink.

This framework is designed for make the full thermodynamic energy picture visible for energy analysts, engineers, consultants, researchers, software teams, and workflows that need a simple way to add energy-quality reporting to existing energy data.

It does **not** replace detailed exergy analysis, process simulation, ISO 50001, IPMVP, LCA, cost accounting, or engineering judgment. It adds one useful quality field to existing energy records so electricity, fuels, heat, cooling, storage, and savings can be compared more honestly.

---

## What You Can Do With It

Use this framework to:

- calculate Exergy Factor for electricity, heat, cooling, fuels, and solar radiation
- convert ordinary energy records into quantity-plus-quality notation
- clean CSV, JSON, JSONL, Excel, DataFrame, SQL, stream, or URL records
- compare energy options using `MWh_ex`, `cost/MWh_ex`, and `CO2/MWh_ex`
- add auditable context such as reference sink, boundary, basis, assumptions, and warnings
- export canonical reference data for web calculators, dashboards, APIs, and reports

The package is designed to start simple: use reference defaults for screening, then replace them with site-specific values when accuracy matters.

---

## Install

From PyPI:

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

If the package is not yet published to PyPI, install directly from GitHub:

```bash
python -m pip install git+https://github.com/cdimurro/quantity-and-quality.git
```

---

## The Three Main Workflows

### 1. Calculate One Stream

Use this when you know the energy form and want a quick quantity-plus-quality record.

```bash
quantity-quality calc thermal --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
```

Example output:

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

---

### 2. Clean Existing Energy Records

Use this when you already have energy records in a file or data source.

```bash
quantity-quality clean examples/adoption_records.csv --output clean.csv
```

The cleaner accepts messy field names such as:

```text
energy_kwh
supply_temp_f
fuel_type
reference_id
fx
exergy_factor
```

It adds:

- notation
- accessible exergy
- normalized `MWh_ex` where possible
- reference context
- assumptions
- warnings
- validation issues

Example:

```python
import quantity_quality as qq

records = qq.clean_records([
    {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
    {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
    {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
])

for record in records:
    print(record["full_notation"], record["missing_context"])
```

---

### 3. Compare Energy Options

Use this when you want to compare fuels, heat, electricity, waste heat, cooling, storage, or project scenarios.

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

---

## Python API

```python
import quantity_quality as qq

record = qq.thermal(1, "MWh_th", source_c=80, sink_c=20)

print(record.full_notation)
# 1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]

print(record.accessible_exergy, record.accessible_exergy_unit)
# 0.169899... MWh_ex
```

Create a custom record:

```python
record = qq.report(1, "MWh", fx=0.73)

print(record.notation)
# 1 MWh, fx = 0.73
```

Use a bundled reference example:

```python
record = qq.lookup("heat-80c-standard", quantity=1.8)

print(record.full_notation)
# 1.8 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]
```

Compare scenario files:

```python
result = qq.compare_scenario_file("examples/process_heat_comparison.json")
print(qq.scenario_to_markdown(result))
```

---

## Core Formula

The reporting layer normalizes different energy carriers into one quality field:

```text
accessible exergy = energy quantity * Exergy Factor
```

or:

```text
X_A = E * fx
```

For power:

```text
accessible exergy rate = power * Exergy Factor
```

or:

```text
Xdot_A = P * fx
```

For heat, the default thermal Exergy Factor uses the Carnot factor:

```text
fx = 1 - T0 / Th
```

Temperatures are converted to kelvin internally. Public examples use:

```text
T0 = 20 C
```

unless another sink or reference condition is declared.

Fuel examples must declare their energy basis. HHV is recommended for broad public comparison because it avoids confusing `fx > 1` values for common fuels. LHV is supported when explicitly labeled.

---

## Why This Matters

One MWh of electricity, one MWh of 80 °C heat, one MWh of 40 °C heat, and one MWh of fuel are equal under first-law energy accounting.

They are not equal as useful work resources.

Examples with a 20 °C reference sink:

| Stream | Conventional Report | Quantity + Exergy Factor |
|---|---:|---:|
| Electricity | `1 MWh` | `1 MWh, fx = 1.000` |
| Heat at 150 °C | `1 MWh_th` | `1 MWh_th, fx = 0.307` |
| Heat at 80 °C | `1 MWh_th` | `1 MWh_th, fx = 0.170` |
| Heat at 40 °C | `1 MWh_th` | `1 MWh_th, fx = 0.064` |
| Methane, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.93` |
| Hydrogen, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.83` |

The Exergy Factor helps reveal:

- when high-grade resources are used for low-grade services
- when low-grade heat can be productively cascaded
- when heat pumps act as work-potential matching devices
- when fuels, electricity, heat, cooling, and storage are not directly comparable by MWh alone
- when savings should be reported as both avoided energy and avoided accessible exergy

---

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

---

## Reference Data

The package includes reference examples for:

- electricity
- mechanical work
- thermal streams
- cooling
- fuels
- solar radiation
- storage
- measurement and reporting use cases

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

Each reference example declares:

- boundary
- basis
- source
- confidence class
- carrier
- reference condition
- structured context such as temperatures or fuel basis where relevant

Reference examples are starting assumptions, not universal constants. Use them for screening, teaching, first-pass comparison, and software integration. Replace them with site-specific values when making project decisions.

---

## Website Data Export

The static `exergyfactor.com` calculator can consume reference data generated from this Python package:

```bash
quantity-quality export-web-data \
  --output ../exergy-factor/data/reference_examples.json \
  --js-output ../exergy-factor/data/reference_examples.js
```

The JavaScript bundle is synchronous and small, so the website calculator can load canonical values immediately without waiting for a runtime fetch.

This keeps the Python library and public calculator aligned around one source of truth.

---

## Reporting Notation

### Short notation

Use this when the reference convention is already known, the carrier is unambiguous, or the value is being used in a compact dashboard, invoice, spreadsheet, or chart.

```text
1 MWh, fx = 0.73
```

### Full notation

Use this for thermal streams, non-default references, technical reports, datasets, audits, and any case where another person needs to verify the value from the notation itself.

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

### Structured data

Use this in APIs, databases, telemetry, invoices, procurement data, and standards templates where records should be machine-readable.

```json
{
  "quantity": 1.0,
  "unit": "MWh_th",
  "exergy_factor": 0.170,
  "source_c": 80,
  "sink_c": 20,
  "reference": "20 C thermal sink",
  "boundary": "delivery point",
  "basis": "Carnot factor"
}
```

The practical standard is:

```text
quantity, fx = value
```

plus enough declared context to make the value interpretable.

---

## Supply-Demand Matching

The framework becomes most useful when both supply and demand are reported with Exergy Factor.

Supply:

```text
(P_s, fx_s)
```

Demand:

```text
(P_d, fx_d)
```

Good match:

```text
P_s ~= P_d
fx_s ~= fx_d
```

Wasteful match:

```text
fx_s >> fx_d
```

This means a high-exergy source is being used for a low-exergy service.

Insufficient match:

```text
fx_s < fx_d
```

This means the supply must be upgraded by a heat pump, compressor, reactor, electrolyzer, or another conversion process.

A simple mismatch index is:

```text
Delta_fx = fx_s - fx_d
```

For a matched energy quantity:

```text
X_mismatch = E_matched * max(0, fx_s - fx_d)
```

---

## Stream Quality vs. Process Efficiency

The framework keeps stream reporting separate from process performance.

Stream descriptor:

```text
(E, fx)
```

or:

```text
(P, fx)
```

Process descriptor:

```text
eta_x
Xdot_dest
```

where:

```text
eta_x = useful exergy output / accessible exergy input
Xdot_dest = T0 * Sdot_gen
```

A stream can have high `fx` and still be wasted in an irreversible device.

A stream can have low `fx` and still be valuable if it is well matched to a low-`fx` demand.

---

## Machine-Readable Input Patterns

The library accepts incomplete records immediately, computes what it can, and returns:

- capabilities
- missing context
- assumptions
- warnings
- validation issues

This lets records improve over time instead of forcing every user through a fixed checklist.

The simplest machine-readable record only needs:

```text
quantity or power
unit
fx or exergy_factor
```

For declared context, add:

```text
reference
boundary
basis
```

For thermal streams, include source temperature and reference sink temperature when possible:

```text
source_c
sink_c
```

For chemical carriers, declare the energy basis:

```text
HHV
LHV
tabulated chemical exergy
```

---

## Project Contents

```text
src/quantity_quality/                  Python package
data/reference_examples.json           Canonical reference examples
data/reference_examples.csv            Spreadsheet export
data/quantity_quality_record.schema.json
                                       JSON Schema for interoperable records
examples/adoption_records.csv          Cleaning example
examples/process_heat_comparison.json  Scenario comparison example
docs/adoption-cookbook.md              Practical adoption recipes
paper/                                 Framework paper
```

---

## Development

```bash
python -m pip install -e ".[all,dev]"
python -m pytest -q
python -m build
```

The package is typed:

```text
py.typed
```

and built as a pure Python wheel.

---

## Citation

If you use this framework, examples, or code, please cite:

```bibtex
@misc{dimurro2026quantityquality,
  title  = {Quantity and Quality: A Standard Reporting Framework for Energy Systems},
  author = {DiMurro, Christopher},
  year   = {2026},
  note   = {Independent Researcher, Exergy Lab}
}
```

After the arXiv version is available, replace this with the arXiv citation.

---

## License

MIT
