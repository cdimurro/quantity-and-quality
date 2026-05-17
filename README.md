# Energy Quantity and Quality

Companion repository for **Quantity and Quality: A Standard Reporting Framework for Energy Systems**.

Energy systems usually report only quantity:

```text
1 MWh
```

This repository supports a simple second-law reporting extension:

```text
1 MWh, fx = 0.170
```

where `fx` is the **Exergy Factor**: accessible useful work potential per unit energy.

For a fully specified thermal stream:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

This means:

```text
energy quantity    = 1 MWh_th
Exergy Factor      = 0.170 MWh_ex / MWh
accessible exergy  = 0.170 MWh_ex
source temperature = 80 C
reference sink     = 20 C
```

The goal is not to replace kWh, MWh, Btu, cost, emissions, ISO 50001, IPMVP, life-cycle assessment, or detailed exergy analysis. The goal is to add one quality field that makes useful work potential visible.

---

## Core idea

Do not report energy quantities using just one number.

Report:

```text
quantity + Exergy Factor
```

Scientific notation:

```text
Energy quantity: (E, fx)
Power rate:      (P, fx)
```

where:

```text
E  = accumulated energy quantity
P  = power rate
fx = accessible exergy per unit energy or power
```

The accessible exergy is:

```text
X_A = fx * E
```

For power:

```text
Xdot_A = fx * P
```

Example:

```text
100 MWh, fx = 0.17
```

means:

```text
accessible exergy = 17 MWh_ex
```

---

## Why this matters

One MWh of electricity, one MWh of 80 C heat, one MWh of 40 C heat, and one MWh of fuel are all equal under first-law energy accounting.

They are not equal as useful work resources.

Examples with a 20 C reference sink:

| Stream | Conventional report | Quantity + Exergy Factor |
|---|---:|---:|
| Electricity | `1 MWh` | `1 MWh, fx = 1.000` |
| Heat at 150 C | `1 MWh_th` | `1 MWh_th, fx = 0.307` |
| Heat at 80 C | `1 MWh_th` | `1 MWh_th, fx = 0.170` |
| Heat at 40 C | `1 MWh_th` | `1 MWh_th, fx = 0.064` |
| Methane, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.93` |
| Hydrogen, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.83` |

The Exergy Factor makes visible when high-grade resources are being used for low-grade services, when low-grade heat can be productively cascaded, and when technologies such as heat pumps act as work-potential matching devices.

---

## Quickstart

Install locally:

```bash
python -m pip install -e .
```

Run a thermal example:

```bash
quantity-quality thermal --source-c 80 --sink-c 20 --quantity 1 --unit MWh_th
```

Expected result:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
accessible_exergy = 0.170 MWh_ex
```

Check:

```text
fx = 1 - 293.15 / 353.15 = 0.170
```

---

## Python example

```python
import quantity_quality as qq

record = qq.report(1, "MWh", fx=0.73)
print(record.notation)
# 1 MWh, fx = 0.73

heat = qq.thermal(2.738, "kWh_th", source_c=541)
print(heat.full_notation)
# 2.738 kWh_th, fx = 0.64 [Th = 541 C, T0 = 20 C]

district_heat = qq.lookup("heat-80c-standard", quantity=1.8)
print(district_heat.full_notation)
# 1.8 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]
```

The library can also clean messy real-world data without forcing every user through a fixed checklist:

```python
messy_records = [
    {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
    {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
    {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
]

clean = qq.clean_records(messy_records)
for record in clean:
    print(record["full_notation"], record["missing_context"])
```

If source field names are unusual, provide a mapping:

```python
record = qq.clean_record(
    {"asset": "Kiln exhaust", "measured_energy": 2.738, "supply_temp_f": 1005.8},
    mapping={
        "label": "asset",
        "quantity": "measured_energy",
        "unit": "kWh_th",
        "source_f": "supply_temp_f",
    },
)
```

The cleanup API accepts records from dictionaries, lists, CSV, JSON, JSONL/NDJSON, DataFrames, SQL query results, streams, URLs, and Excel files when optional data dependencies are installed:

```python
qq.clean_file("energy.csv")
qq.clean_file("meter_events.jsonl")
qq.clean_dataframe(df)
qq.clean_sql(connection, "select * from meter_readings")
qq.clean_stream(sensor_events)
```

---

## Command-line examples

```bash
quantity-quality report --quantity 1 --unit MWh --fx 0.73
quantity-quality parse "1 MWh, fx = 0.73"
quantity-quality thermal --source-c 80 --sink-c 20 --quantity 1 --unit MWh_th
quantity-quality solar --quantity 1 --unit MWh_solar
quantity-quality lookup heat-80c-standard
quantity-quality list --category thermal
quantity-quality examples
quantity-quality annotate examples/adoption_records.csv --output runtime/adoption_records_annotated.csv
quantity-quality annotate meter_events.jsonl --output meter_events_clean.jsonl
quantity-quality annotate messy.csv --mapping '{"quantity":"Measured Energy","unit":"kWh_th","source_f":"Supply Temp F"}'
quantity-quality validate examples/adoption_records.csv
```

Emit JSON:

```bash
quantity-quality report --quantity 1 --unit MWh --fx 0.73 --json
quantity-quality schema --json
```

---

## Reporting notation

### Tier 1: short notation

Use this when the reference convention is already known, the carrier is unambiguous, or the value is being used in a compact dashboard, invoice, spreadsheet, or chart.

```text
1 MWh, fx = 0.73
```

### Tier 2: full notation

Use this for thermal streams, non-default references, technical reports, datasets, audits, and any case where another person needs to verify the value from the notation itself.

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

### Tier 3: structured data

Use this in APIs, databases, telemetry, invoices, procurement data, and standards templates where records should be machine-readable.

```json
{
  "energy_mwh": 1.0,
  "unit": "MWh_th",
  "exergy_factor": 0.170,
  "source_temperature_c": 80,
  "reference_sink_temperature_c": 20,
  "reference": "T0 = 20 C",
  "boundary": "delivery point",
  "operating_basis": "Carnot factor"
}
```

The proposed standard should not require four numeric fields for every record. Four numeric fields are useful for many thermal records, but electricity needs a boundary, not source and sink temperatures. Fuels need an energy basis such as HHV, LHV, or tabulated chemical exergy. Pressure and mass-flow cases need their own carrier metadata.

The practical standard is therefore:

```text
quantity, fx = value
```

plus enough declared context to make the value interpretable.

---

## Reference conditions

Exergy is not absolute energy. Exergy is useful work potential relative to a reference sink, environment, service, boundary, and feasible conversion path.

The same quantity of energy can have zero exergy relative to one reference environment and positive exergy relative to another.

For public thermal examples in this repository, use:

```text
T0 = 20 C = 293.15 K
p0 = 101.325 kPa when pressure matters
```

This default is useful because it keeps examples simple and makes common heat cases easy to compare.

`20 C` should be treated as a default reference point, not a hidden universal truth. If your application has a different reference sink temperature, specify it directly:

```text
1 MWh_th, fx = 0.150 [Th = 80 C, T0 = 25 C]
```

For chemical fuels, the more important default is usually the energy basis. The paper recommends HHV as the default fuel basis for broad operational reporting because it avoids `fx > 1` for common fuels, while still allowing LHV when explicitly labeled.

---

## Carrier-specific potentials

Different energy carriers naturally have different potential units. The framework normalizes them into the same Exergy Factor.

| Carrier | Potential | Unit | Exergy flow |
|---|---:|---:|---:|
| Electric charge | voltage difference | `J/C = V` | `Xdot = I * Delta V` |
| Entropy | temperature difference | `K` | `Xdot = Sdot * (Th - Tc)` |
| Mole amount | chemical potential difference | `J/mol` | `Xdot = sum(ndot_i * Delta mu_i)` |
| Volume | pressure difference | `J/m3 = Pa` | `Xdot = Vdot * Delta p` |
| Mass | specific work potential | `J/kg` | `Xdot = mdot * Delta psi` |

The common structure is:

```text
exergy flow = carrier current * accessible potential difference
```

or:

```text
Xdot_A = Cdot * DeltaPhi_A
```

The reporting layer then normalizes the result:

```text
fx = X_A / E
```

or:

```text
fx = Xdot_A / P
```

---

## Thermal streams

For heat, entropy is the natural carrier.

Thermal Exergy Factor:

```text
fx = 1 - T0 / Th
```

Temperatures must be in kelvin.

Example:

```text
Th = 80 C = 353.15 K
T0 = 20 C = 293.15 K

fx = 1 - 293.15 / 353.15 = 0.170
```

Report:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

Meaning:

```text
accessible exergy = 0.170 MWh_ex
```

---

## Chemical carriers

Chemical streams must declare their energy basis.

Recommended public reporting basis:

```text
HHV
```

Accepted when explicitly labeled:

```text
LHV
chemical exergy table
Gibbs free energy of reaction
process-specific denominator
```

Illustrative values:

| Fuel | Basis | Example notation | Note |
|---|---:|---:|---|
| Methane | HHV | `1 MWh_HHV, fx = 0.93` | Recommended public basis |
| Methane | LHV | `1 MWh_LHV, fx = 1.04` | Can exceed 1 because denominator changes |
| Hydrogen | HHV | `1 MWh_HHV, fx = 0.83` | Recommended public basis |
| Hydrogen | LHV | `1 MWh_LHV, fx = 0.98` | Explicitly label basis |

`fx > 1` on an LHV basis is not a physics violation. It means the denominator is a selected accounting basis, not a full energy inventory.

---

## Supply-demand matching

The framework becomes most useful when both supply and demand are reported with Exergy Factor.

Supply:

```text
(Ps, fx_s)
```

Demand:

```text
(Pd, fx_d)
```

Good match:

```text
Ps ~= Pd
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

## Stream factor vs. process efficiency

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

## Example notations

Values are rounded engineering examples. Thermal examples use `T0 = 20 C` unless noted.

| Use case | Notation | Reference or basis |
|---|---|---|
| Grid electricity delivered | `845 kWh, fx = 1.000` | electrical delivery boundary |
| Battery discharge | `2.4 MWh, fx = 1.000` | electrical output boundary |
| Motor shaft work | `12.5 GJ, fx = 1.000` | shaft-work boundary |
| 40 C low-temperature heat | `35000 Btu_th, fx = 0.064` | `Th = 40 C, T0 = 20 C` |
| 80 C district heat | `1.8 MWh_th, fx = 0.170` | `Th = 80 C, T0 = 20 C` |
| 150 C process heat | `12 GJ_th, fx = 0.307` | `Th = 150 C, T0 = 20 C` |
| 500 C industrial heat | `22 MMBtu_th, fx = 0.621` | `Th = 500 C, T0 = 20 C` |
| Methane or natural gas | `850 MMBtu_HHV, fx = 0.93` | HHV basis |
| Methane or natural gas | `249 MWh_LHV, fx = 1.04` | LHV basis, explicitly labeled |
| Hydrogen | `6.8 MWh_HHV, fx = 0.83` | HHV basis |
| Hydrogen | `6.8 MWh_LHV, fx = 0.98` | LHV basis, explicitly labeled |
| Thermal storage at 80 C | `14 MWh_th, fx = 0.170` | storage discharge, `T0 = 20 C` |
| Cooling service | `900 kWh_cooling, fx = 0.082` | cold service 7 C, ambient sink 30 C |
| Power rate example | `4.2 MW, fx = 0.18` | declared service boundary |

For the full reference table, see:

```text
data/reference_examples.json
data/reference_examples.csv
```

---

## What is in this repository

```text
data/reference_examples.json      Starter reference examples for software use
data/reference_examples.csv       Starter reference examples for spreadsheets
src/quantity_quality/             Python package
examples/quickstart.py            Direct adoption example
examples/adoption_records.csv     Example input records
paper/                            Paper PDF and supporting files
```

The starter database includes common thermal, electrical, chemical, storage, and reporting examples with fields for:

```text
quantity_unit
exergy_factor
reference
boundary
basis
adoption_note
```

---

## Machine-readable input patterns

The library accepts incomplete records immediately, computes what it can, and returns `capabilities`, `missing_context`, `assumptions`, and `warnings` so records can improve over time.

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
basis or operating_basis
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

## Adoption path

Start by adding `exergy_factor` to existing energy records.

Do not redesign every meter, dashboard, tariff, procurement system, or reporting standard first.

For a facility team, this can begin as a spreadsheet column beside kWh, therms, steam, chilled water, or fuel use.

For a software team, it can begin as an additional field in telemetry, billing, ESG, life-cycle assessment, or optimization data models.

For a standards body, it can begin as a supplemental reporting attribute, not a replacement for existing energy accounting.

Recommended first pilots:

| Domain | First pilot |
|---|---|
| District heating and cooling | Publish MWh and MWh_ex by delivery temperature and return or sink condition |
| Industrial heat recovery | Rank waste heat streams by `quantity, fx` rather than MWh alone |
| Hydrogen and fuel policy | Require `HHV`, `LHV`, or chemical-exergy basis on every fuel record |
| Energy audits and M&V | Report both avoided energy and avoided accessible exergy |
| Storage procurement | Compare assets by service-grade MWh_ex, not nameplate MWh alone |

---

## Scope and limitations

This repository does not replace:

```text
detailed exergy analysis
plant simulation
ISO 50001
IPMVP
life-cycle assessment
engineering judgment
```

It provides a lightweight reporting layer:

```text
(E, fx)
```

or:

```text
(P, fx)
```

The Exergy Factor depends on the declared reference, boundary, carrier, and energy basis.

For thermal streams, declare source and sink temperatures when possible.

For chemical carriers, declare HHV, LHV, or tabulated chemical exergy basis.

For dynamic systems, `fx` can be time-varying:

```text
fx(t)
```

and aggregated over an interval using an energy-weighted average.

---

## Project status

Early reference implementation.

Current focus:

```text
stable notation
reference example database
simple thermal, solar, and fuel examples
CLI and Python reporting helpers
```

Planned:

```text
validation tests for all reference examples
additional carrier modules
district heating examples
measurement and verification templates
arXiv-linked paper release
```

---

## Citation

If you use this framework, examples, or code, please cite:

```bibtex
@misc{dimurro2026quantityquality,
  title  = {Quantity and Quality: A Two-Number Reporting Framework for Multi-Carrier Energy Systems},
  author = {DiMurro, Christopher},
  year   = {2026},
  note   = {Independent Researcher, Exergy Lab}
}
```

After the arXiv version is available, replace this with the arXiv citation.

---

## License

Software, library source, and starter data are released under the MIT License unless otherwise noted.

The paper remains attributable to Christopher DiMurro.
