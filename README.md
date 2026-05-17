# Quantity and Quality

Companion repository for the paper, **Quantity and Quality: A Standard Reporting Framework for Energy Systems**.

This repo is the public home for supplemental material, reference example database, and a Python library to assist with the reporting adoption of energy quantity with an additional quality factor attached to it.

## The new reporting notation

Stop reporting energy quantities as just one number where possible. This paper proposes the new standard notation should look like this:

```text
1 MWh, fX = 0.73
```

That means "one megawatt-hour of energy carrying 0.73 megawatt-hours of accessible work potential." The same pattern works for any scale or unit:

```text
1 kWh, fX = 0.73
12 GJ, fX = 0.41
4.2 MW, fX = 0.18
```

The scientific version from the paper is written like this:

```text
Energy quantity: (E, fX)
Power rate:      (P, fX)
```

`E` or `P` says how much energy is present or moving. `fX` says how much **accessible work potential** that energy carries at a declared reporting boundary.

## Why this matters in the real world

Energy decisions are made every day from spreadsheets, tariffs, meters, dashboards, audits, equipment specs, and policy reports that reduce energy to a single number. That single number is simple, but it hides important information about how valuable that number actually is. Adding fx shows difference between a high-grade resource that can do almost any energy job and a low-grade resource that can only satisfy a narrow service. The result is that projects can appear balanced in MWh while still wasting useful work potential.

The discovery here is a missing reporting layer. The world already knows how to meter energy quantity. What it has not had is a simple notation that makes energy quality visible everywhere energy quantity is already reported. `1 MWh, fX = 0.73` is meant to be easy enough for invoices, building dashboards, engineering reports, procurement specs, utility programs, academic papers, and machine-readable datasets.

This matters most where the energy transition is becoming multi-carrier: electricity, heat, hydrogen, methane, ammonia, batteries, thermal storage, district energy, compressed gases, industrial waste heat, and cooling all coexist in the same planning problem. A scalar MWh makes these resources look interchangeable. Exergy Factor shows whether a supply is well matched to the service it is being asked to perform.

For industry, this can reduce avoidable waste. It can show when high-grade electricity or fuel is being used for low-temperature heat without recovery, when waste heat is valuable enough to route into a nearby demand, when a heat pump is acting as a work-potential matching device, and when a storage asset's nameplate MWh overstates the service grade it can provide.

For institutions, this is deliberately compatible with existing practice. It can be layered into [ISO 50001 energy management](https://www.iso.org/iso-50001-energy-management.html), [IPMVP measurement and verification](https://evo-world.org/en/products-services-mainmenu-en/protocols/ipmvp), and [ISO 14040 life-cycle assessment](https://www.iso.org/standard/37456.html) as a supplemental field. The point is not to replace kWh, emissions, cost, or lifecycle inventory data. The point is to stop those systems from hiding thermodynamic quality.

## Common industry notation examples

These are examples for how the notation can appear in real reports. Exact values depend on the declared reference, boundary, and basis.

| Real-world Example | Notation | Use case |
|---|---|---|
| Grid electricity delivered | `1 MWh, fX = 1` | Utility bills, facility meters, procurement |
| PV electrical output | `1 MWh, fX = 1` | Solar output after conversion to electricity |
| Battery discharge | `1 MWh, fX = 1` | Storage dispatch and grid services |
| Motor shaft work | `1 MWh, fX = 1` | Industrial drives, pumps, compressors |
| Solar radiation resource | `1 MWh, fX = 0.931` | Solar resource quality before conversion losses |
| 40 C low-temperature heat | `1 MWh, fX = 0.064` | Space heating, data-center heat recovery |
| 60 C domestic hot water heat | `1 MWh, fX = 0.12` | Buildings, campuses, hotels, hospitals |
| 80 C district heat | `1 MWh, fX = 0.17` | District energy delivery and tariffs |
| 80 C district heat to 50 C return | `1 MWh, fX = 0.085` | Network operation using return-line sink |
| 90 C district heat to 50 C return | `1 MWh, fX = 0.11` | Campus and city heat networks |
| 150 C low-pressure steam | `1 MWh, fX = 0.307` | Process heat, food, pharma, paper, drying |
| 250 C process heat | `1 MWh, fX = 0.44` | Industrial heat recovery and electrification |
| 500 C high-temperature heat | `1 MWh, fX = 0.621` | Cement, metals, chemicals, high-grade heat |
| Methane / natural gas on LHV basis | `1 MWh, fX = 1.04` | Fuel inventories, gas procurement, boilers |
| Methane / natural gas on HHV basis | `1 MWh, fX = 0.93` | Gas bills and HHV-based fuel accounting |
| Hydrogen on LHV basis | `1 MWh, fX = 0.98` | Electrolyzers, refining, ammonia, fuel policy |
| Hydrogen on HHV basis | `1 MWh, fX = 0.83` | Hydrogen reporting with HHV denominator |
| 80 C hot-water thermal storage | `1 MWh, fX = 0.17` | Thermal storage and district energy |
| 150 C process-heat storage | `1 MWh, fX = 0.307` | Thermal oil, molten salt, industrial storage |
| 7 C cooling service vs 30 C ambient | `1 MWh, fX = 0.082` | Chilled water, refrigeration, district cooling |

## What is in this repository

- `data/reference_examples.json` and `data/reference_examples.csv` - starter reference examples for common energy carriers, heat grades, storage types, and reporting cases.
- `src/quantity_quality/` - a small Python library for computing and reporting records like `1 MWh, fX = 0.73`.
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
    reference="standard thermal sink",
    boundary="building heating loop",
    operating_basis="source and sink temperatures in C",
)

factor = thermal_exergy_factor_c(source_c=80, sink_c=20)
stream = EnergyReport(quantity=1.0, unit="MWh", exergy_factor=factor, context=context)

print(stream.accessible_exergy)
```

## Command-line examples

```bash
quantity-quality report --quantity 1 --unit MWh --fx 0.73
quantity-quality parse "1 MWh, fX = 0.73"
quantity-quality thermal --source-c 80 --sink-c 20 --quantity 1 --unit MWh
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

## Reporting fields

A minimum record should include:

- `quantity` or `power`
- `unit`
- `exergy_factor`
- `reference`
- `boundary`
- `operating_basis`

For chemical carriers, also declare the energy basis, such as `LHV`, `HHV`, or `chemical_exergy_table`.

## Adoption path for organizations

Start by adding `exergy_factor` to existing energy records. Do not redesign every meter, dashboard, or procurement system first. The fastest adoption path is to keep the existing `quantity` and `unit` fields, add `fX`, and attach the metadata needed to interpret it.

For a facility team, this can begin as a spreadsheet column beside kWh, therms, steam, chilled water, or fuel use. For a software team, it can begin as an additional field in telemetry, billing, ESG, LCA, or optimization data models. For a standards body, it can begin as a supplemental reporting attribute, not a replacement for existing energy accounting.

Recommended first pilots:

- District heating and cooling: publish MWh and MWh_ex by delivery temperature and return/sink condition.
- Industrial heat recovery: rank waste heat streams by `quantity, fX` rather than MWh alone.
- Hydrogen and fuel policy: require `LHV`, `HHV`, or chemical-exergy basis on every fuel record.
- Energy audits and M&V: report both avoided energy and avoided accessible exergy.
- Storage procurement: compare assets by service-grade MWh_ex, not nameplate MWh alone.

## License

Software, library source, and starter data are released under the MIT License unless otherwise noted. The paper remains attributable to Christopher DiMurro.
