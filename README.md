# Energy Quantity and Quality

Companion repository for **Quantity and Quality: A Standard Reporting Framework for Energy Systems**.

This repo contains supplemental examples, a reference database, and a small Python library for adopting a simple idea:

```text
Do not report energy quantity alone.
Report quantity plus Exergy Factor.
```

## Core notation

The everyday notation is:

```text
1 MWh, fx = 0.73
```

This means one megawatt-hour of energy carrying 0.73 megawatt-hours of accessible work potential at the declared reporting boundary.

The same pattern works across energy quantities and power rates:

```text
2.738 kWh, fx = 0.64
850 MMBtu, fx = 0.93
0.018 EJ, fx = 0.17
4.2 MW, fx = 0.18
```

The scientific form from the paper is:

```text
Energy quantity: (E, fx)
Power rate:      (P, fx)
```

`E` or `P` says how much energy is present or moving. `fx` says how much accessible work potential that energy carries per unit energy or power.

## Why reference conditions matter

Exergy is not absolute energy. Exergy is useful work potential relative to a reference environment, sink, service, boundary, and allowed conversion path.
The same quantity of energy can simulatneously have zero Exergy relative to one reference environment but positive Exergy relative to another.

That means this short notation:

```text
2.738 kWh, fx = 0.64
```

is easy to read, but not fully self-verifying by itself. For a thermal stream, the same `fx` depends on the source temperature and the reference sink temperature. With a 20 C sink, `fx = 0.64` corresponds to roughly 541 C heat:

```text
2.738 kWh_th, fx = 0.64 [Th = 541 C, T0 = 20 C]
```

With a different sink temperature, the same source would have a different `fx`. This is not a problem with the framework. It is the thermodynamics: useful work potential fundamentally exists because there is an accessible gradient relative to a reference.

## Recommended reporting rule

Use a three-tier rule:

**Tier 1: short notation for adoption**

Use this when the reference convention is already known, when the carrier is unambiguous, or when the value is being used in a compact dashboard, invoice, spreadsheet, or chart.

```text
1 MWh, fx = 0.73
```

**Tier 2: full notation for verification**

Use this for thermal streams, non-default references, technical reports, standards work, datasets, audits, and any case where another person needs to be able verify the exact value from the notation itself.

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

**Tier 3: structured data for systems**

Use this in APIs, databases, telemetry, invoices, procurement data, and standards templates where every application that should be machine-readable.

```json
{"energy_mwh": 1.0, "fx": 0.170, "T_h_C": 80, "T_0_C": 20}
```

The standard should not require four numbers for every record. That would make adoption harder and would not fit every carrier. Four numeric fields are right for many thermal records, but electricity needs a boundary, not a source and sink temperature. Fuels need an energy basis such as HHV, LHV, or chemical exergy table. Solar radiation needs a radiation reference convention. Pressure and mass-flow cases need their own carrier metadata.

The practical standard is therefore:

```text
quantity, fx = value
```

plus enough declared context to make the value interpretable.

## Default sink recommendation

For public thermal examples in this repository, use:

```text
T0 = 20 C = 293.15 K
p0 = 101.325 kPa when pressure matters
```

That default is useful because it keeps examples simple and makes common heat cases easy to compare. It also aligns with the previous literature on exergy.

`20 C` should be treated as a default reference point, not a hidden universal truth. If you specific application has a different environment sink temperature, which is likely, you have two options:

```text
1. Set the reference sink temperature to 20 C and then calculate the Exergy Potential Different (EPD) to your specific environment sink temperature and adjust the final value.
2. Specify your exact reference sink temeprature in the notation itself: 1 MWh_th, fx = 0.15 [Th = 80 C, T0 = 25 C]
```

For chemical fuels, the more important default is usually the energy basis. The revised paper recommends HHV as the default fuel basis for broad operational reporting because it avoids `fx > 1` for common fuels, while still allowing LHV when explicitly labeled.

## Why this matters

Energy accounting usually tells us how much energy moved. It often does not tell us what that energy could still do.

One MWh of electricity, one MWh of 80 C heat, one MWh of 40 C heat, and one MWh of fuel are all equal under first-law quantity accounting. They are not equal as useful work resources. Exergy Factor makes that difference visible without replacing the units people already use.

This matters for district energy, industrial heat recovery, building electrification, hydrogen policy, fuel comparison, storage valuation, life-cycle assessment, measurement and verification, and energy-market design. It helps show when high-grade resources are being used for low-grade services, when low-grade heat can be productively cascaded, and when a technology such as a heat pump is acting as a work-potential matching device.

The goal is not to replace kWh, MWh, GJ, Btu, cost, emissions, or existing standards. The goal is to add one quality field that prevents those systems from hiding thermodynamic value.

## Example notations

These examples show the flexibility of the framework. Values are rounded engineering examples; thermal values declare the source and reference sink when needed.

| Use case | Notation | Reference or basis |
|---|---|---|
| Grid electricity delivered | `845 kWh, fx = 1` | electrical delivery boundary |
| Battery discharge | `2.4 MWh, fx = 1` | electrical output boundary |
| Motor shaft work | `12.5 GJ, fx = 1` | shaft-work boundary |
| Solar radiation resource | `5.2 MWh_solar, fx = 0.932` | Petela factor, T0 = 20 C |
| 40 C low-temperature heat | `35000 Btu_th, fx = 0.064` | Th = 40 C, T0 = 20 C |
| 60 C domestic hot water | `500 kWh_th, fx = 0.120` | Th = 60 C, T0 = 20 C |
| 80 C district heat | `1.8 MWh_th, fx = 0.170` | Th = 80 C, T0 = 20 C |
| 80 C heat to return line | `1 MWh_th, fx = 0.085` | Th = 80 C, T0 = 50 C return |
| 150 C process steam | `12 GJ_th, fx = 0.307` | Th = 150 C, T0 = 20 C |
| 250 C process heat | `0.004 EJ_th, fx = 0.440` | Th = 250 C, T0 = 20 C |
| High-temperature heat example | `2.738 kWh_th, fx = 0.640` | Th about 541 C, T0 = 20 C |
| 500 C industrial heat | `22 MMBtu_th, fx = 0.621` | Th = 500 C, T0 = 20 C |
| Methane / natural gas | `850 MMBtu_HHV, fx = 0.93` | HHV basis |
| Methane / natural gas | `249 MWh_LHV, fx = 1.04` | LHV basis, explicitly labeled |
| Hydrogen | `6.8 MWh_HHV, fx = 0.83` | HHV basis |
| Hydrogen | `6.8 MWh_LHV, fx = 0.98` | LHV basis, explicitly labeled |
| Thermal storage at 80 C | `14 MWh_th, fx = 0.170` | storage discharge, T0 = 20 C |
| Thermal storage at 150 C | `3.5 MWh_th, fx = 0.307` | storage discharge, T0 = 20 C |
| Cooling service | `900 kWh_cooling, fx = 0.082` | cold service 7 C, ambient sink 30 C |
| Power rate example | `4.2 MW, fx = 0.18` | power rate, declared service boundary |

## What is in this repository

- `data/reference_examples.json` and `data/reference_examples.csv` - starter reference examples for common energy carriers, heat grades, storage types, and reporting cases.
- `src/quantity_quality/` - a small Python library for computing and reporting records like `1 MWh, fx = 0.73`.
- `examples/quickstart.py` - a direct adoption example.
- `paper/quantity-and-quality-standard-reporting-framework.pdf` - the source paper PDF.

## Reference examples database

The starter database is meant to make adoption easier. It includes common thermal, electrical, chemical, storage, and measurement examples with fields for:

- `quantity_unit`
- `exergy_factor`
- `reference`
- `boundary`
- `basis`
- `adoption_note`

Use the JSON file for software integration and the CSV file for spreadsheets:

```text
data/reference_examples.json
data/reference_examples.csv
```

## Install the Python library locally

```bash
python -m pip install -e .
```

Then:

```python
from quantity_quality import EnergyReport, ReferenceContext, thermal_exergy_factor_c

context = ReferenceContext(
    reference="T0 = 20 C",
    boundary="building heating loop",
    operating_basis="Carnot factor from source and sink temperatures",
)

factor = thermal_exergy_factor_c(source_c=80, sink_c=20)
stream = EnergyReport(quantity=1.0, unit="MWh_th", exergy_factor=factor, context=context)

print(stream.as_dict())
```

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
quantity-quality validate examples/adoption_records.csv
```

The CLI is intentionally simple and offline. It can emit human-readable output for quick use or JSON for software integration:

```bash
quantity-quality report --quantity 1 --unit MWh --fx 0.73 --json
quantity-quality schema --json
```

## Minimum reporting fields

A minimum machine-readable record should include:

- `quantity` or `power`
- `unit`
- `exergy_factor`
- `reference`
- `boundary`
- `operating_basis`

For thermal streams, include source temperature and reference sink temperature when possible. For chemical carriers, declare the energy basis: `HHV`, `LHV`, or tabulated chemical exergy.

## Adoption path

Start by adding `exergy_factor` to existing energy records. Do not redesign every meter, dashboard, tariff, or procurement system first.

For a facility team, this can begin as a spreadsheet column beside kWh, therms, steam, chilled water, or fuel use. For a software team, it can begin as an additional field in telemetry, billing, ESG, life-cycle assessment, or optimization data models. For a standards body, it can begin as a supplemental reporting attribute, not a replacement for existing energy accounting.

Recommended first pilots:

- District heating and cooling: publish MWh and MWh_ex by delivery temperature and return or sink condition.
- Industrial heat recovery: rank waste heat streams by `quantity, fx` rather than MWh alone.
- Hydrogen and fuel policy: require `HHV`, `LHV`, or chemical-exergy basis on every fuel record.
- Energy audits and M&V: report both avoided energy and avoided accessible exergy.
- Storage procurement: compare assets by service-grade MWh_ex, not nameplate MWh alone.

## License

Software, library source, and starter data are released under the MIT License unless otherwise noted. The paper remains attributable to Christopher DiMurro.
