# Quantity and Quality

[![PyPI](https://img.shields.io/pypi/v/quantity-and-quality.svg)](https://pypi.org/project/quantity-and-quality/)
[![Python](https://img.shields.io/pypi/pyversions/quantity-and-quality.svg)](https://pypi.org/project/quantity-and-quality/)
[![CI](https://github.com/cdimurro/quantity-and-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/cdimurro/quantity-and-quality/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A small Python library and CLI for calculating and reporting the **energy
quantity**, **Exergy Factor**, and **accessible exergy** of individual energy
streams. It can also account for the **Applied Exergy** that reaches an end-use
task.

**[Try the calculator](https://exergyfactor.com)** ·
[Paper](paper/quantity-and-quality-standard-reporting-framework.pdf) ·
[Practical cookbook](docs/adoption-cookbook.md) ·
[Physical models](docs/physical-streams.md) ·
[Validation](docs/validation.md)

Conventional energy records usually provide only a quantity:

```text
1 MWh
```

Quantity and Quality adds the number that is usually missing:

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

Here `fx` is the Exergy Factor: accessible useful-work potential per unit of
energy. The example contains about `0.170 MWh_ex` relative to a 20 °C sink.

The thermodynamics are established. This project makes them easy to apply in a
calculator, spreadsheet, script, database, API, or AI-agent workflow.

## What It Does

- Calculates energy quantity, `fx`, and accessible exergy for electrical,
  mechanical, thermal, fluid, chemical, radiative, electromagnetic, nuclear,
  plasma, and separation streams.
- Calculates quantity from measurements such as power and time, torque and
  speed, mass and heating value, temperature change, fluid state, irradiance,
  field strength, or reaction extent.
- Handles biomass and bioenergy without inventing a universal factor for
  variable feedstocks.
- Reports friction, rolling resistance, and aerodynamic drag as mechanical work
  dissipated to heat and exergy destruction.
- Cleans existing CSV, JSON, JSONL, Excel, DataFrame, SQL, stream, and URL data.
- Keeps primary, secondary, final, and useful energy separate from Applied
  Exergy and from the resulting energy service.
- Uses the same JSON-shaped calculation contract from Python, the CLI, HTTP,
  and agent discovery.

The browser calculator stays intentionally simple. Advanced and auditable paths
live in the library, CLI, schemas, and optional API.

## Install

```bash
python -m pip install quantity-and-quality
```

The command is `quantity-quality`; the import is `quantity_quality`.

Optional integrations are installed only when needed:

```bash
python -m pip install "quantity-and-quality[scenario]"  # YAML scenarios
python -m pip install "quantity-and-quality[api]"       # HTTP API
python -m pip install "quantity-and-quality[fluids]"    # Real-fluid properties
```

## Quick Start

### Calculate a known stream

```bash
quantity-quality calc thermal \
  --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
```

```text
80 C heat to 20 C sink
report: 1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
accessible exergy: 0.169899 MWh_ex
```

The equivalent Python call is:

```python
import quantity_quality as qq

record = qq.thermal(1, "MWh_th", source_c=80, sink_c=20)
print(record.full_notation)
print(record.accessible_exergy, record.accessible_exergy_unit)
```

Other direct calculations include:

```bash
quantity-quality calc electricity --quantity 1 --unit MWh
quantity-quality calc fuel --quantity 1 --fuel "natural gas" --basis HHV
quantity-quality calc cooling --quantity 1 --unit MWh_cooling \
  --cold-service-c 7 --ambient-sink-c 30
quantity-quality calc custom --quantity 1 --unit MWh --fx 0.73
```

### Calculate from physical inputs

One request shape works from Python, the CLI, or HTTP:

```json
{
  "stream_type": "heat",
  "mass_flow_kg_s": 2.5,
  "duration_hours": 8,
  "specific_heat_kj_kg_k": 4.186,
  "source_c": 80,
  "return_c": 50,
  "sink_c": 20
}
```

```bash
quantity-quality calculate examples/stream-calculation.json --json
```

Packaged examples cover shaft work, steam condensation, biomass, drag,
electromagnetic fields, D–T reaction products, and plasma:

```bash
quantity-quality calculate examples/mechanical-shaft.json --json
quantity-quality calculate examples/steam-condensation.json --json
quantity-quality calculate examples/biomass-calculation.json --json
quantity-quality calculate examples/aerodynamic-drag.json --json
quantity-quality calculate examples/electromagnetic-field.json --json
quantity-quality calculate examples/dt-fusion-neutron.json --json
quantity-quality calculate examples/plasma-state.json --json
```

See the [physical-stream guide](docs/physical-streams.md) and the focused
[fields, plasma, and nuclear guide](docs/nuclear-plasma-electromagnetic.md) for
model assumptions and boundaries.

### Clean existing records

```bash
quantity-quality clean energy.csv --output energy_qq.csv
```

The cleaner recognizes common fields such as `energy_kwh`, `supply_temp_f`,
`fuel_type`, `fx`, and `exergy_factor`. It adds notation, accessible exergy,
reference context, assumptions, warnings, and validation issues.

```python
records = qq.clean_records(
    [
        {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
        {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
        {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
    ]
)
```

### Account for what reaches the task

Use a separate end-use account when multiple boundaries are known:

```bash
quantity-quality account examples/end-use-accounting.json --json
```

```text
primary energy -> secondary energy -> final energy -> useful energy -> energy service
primary exergy -> secondary exergy -> final exergy -> Applied Exergy
```

Applied Exergy is the exergy crossing the last device-to-task boundary. It is
not useful energy: useful energy can contain both exergy and anergy. Energy
services are the outcomes people want—such as a comfortable occupied home, a
cold beer, or passenger-miles—and use outcome units rather than energy units.

The library derives Applied Exergy from `useful.quantity × useful.fx`, from
`final exergy × end_use_exergy_efficiency`, or from a directly supplied value.
Independent paths must agree.

See the [dataset compatibility guide](docs/dataset-compatibility.md) for primary,
secondary, final, and useful data, including substitution-method records.

## The Model

For an energy quantity:

```text
X_A = E × fx
```

For an energy rate:

```text
Xdot_A = P × fx
```

For heat at a constant source temperature:

```text
fx = 1 - T0 / Th
```

For sensible heat cooling from `Ts` to `Tr` with constant heat capacity:

```text
fx = 1 - T0 ln(Ts/Tr) / (Ts - Tr)
```

Temperatures are evaluated in kelvin. Thermal records should declare their
reference temperature; fuels should declare HHV or LHV.

Exergy exists because a stream is distinguishable from a declared environment
or task boundary. A temperature, pressure, chemical, electrical, mechanical, or
radiative difference can support work. At equilibrium, the relevant difference
and exergy vanish. The library includes that evidence in each record's
`distinguishability` field; it does not apply a second factor because `fx`
already quantifies the work-bearing difference.

### A quantity comparison

Examples below use a 20 °C reference sink:

| Stream | Conventional record | Quantity + quality |
|---|---:|---:|
| Electricity | `1 MWh` | `1 MWh, fx = 1.0` |
| Heat at 150 °C | `1 MWh_th` | `1 MWh_th, fx = 0.307` |
| Heat at 80 °C | `1 MWh_th` | `1 MWh_th, fx = 0.170` |
| Heat at 40 °C | `1 MWh_th` | `1 MWh_th, fx = 0.064` |
| Methane, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.930` |
| Hydrogen, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.830` |

Equal energy quantities are not necessarily equal useful-work resources. This
library calculates and reports that difference; downstream tools can decide how
to use it.

## Interfaces for Software and Agents

Discover supported stream types and exact request schemas instead of guessing
field names:

```bash
quantity-quality capabilities --json
quantity-quality capabilities --json-schema
quantity-quality schema --json-schema
```

The optional HTTP service exposes the same deterministic calculations:

```bash
python -m pip install "quantity-and-quality[api]"
quantity-quality serve-api
```

```text
GET  /v1/capabilities
GET  /v1/calculate/schema
POST /v1/calculate
GET  /v1/accounting/schema
POST /v1/account
```

Open <http://127.0.0.1:8000/docs> for interactive API documentation. Invalid
requests return stable error codes and identify the field that needs attention.

The packaged schemas are:

```text
data/quantity_quality_record.schema.json
data/stream_calculation_request.schema.json
data/energy_accounting_request.schema.json
```

The [reference-data guide](data/README.md) defines fields, notation, precision,
verification, schemas, bundled examples, and the website export.

## Accuracy and Scope

The package starts with transparent reference defaults for screening, then lets
users replace them with site-specific measurements. It labels estimates,
retains model and source provenance, and rejects inputs outside a model's stated
domain rather than silently inventing a result.

Important boundaries include:

- Biomass and heterogeneous fuels have no universal factor; moisture,
  composition, ash, heating value, and basis matter.
- Friction and drag are losses. Their incoming mechanical work, residual heat
  exergy, and exergy destruction are reported separately.
- Nuclear reaction-product energy is not reactor heat or electricity. Neutrons,
  charged particles, neutrinos, photons, heat, and electrical output remain
  separate streams at their actual boundaries.
- Plasma's built-in model is an ideal classical inventory. Advanced
  distributions can supply independently evaluated mean energy and quality.
- Substitution-method primary energy is a counterfactual accounting quantity,
  not a physical stream at that magnitude, so it is not assigned physical
  exergy.

The permanent test suite covers exact identities, equation conformance,
domain checks, real public-data fixtures, package builds, and wheel installation
across supported Python versions. See [numerical validation](docs/validation.md)
for benchmarks, tolerances, data revisions, and the full live-data test.

## Documentation

| Guide | Use it for |
|---|---|
| [Adoption cookbook](docs/adoption-cookbook.md) | Browser, CLI, Python, HTTP, cleaning, and accounting recipes |
| [Reference data and contract](data/README.md) | Fields, schemas, notation, verification, presets, and web export |
| [Physical streams](docs/physical-streams.md) | Mechanical, electrical, fluid, biomass, radiation, separation, friction, and drag models |
| [Fields, plasma, and nuclear](docs/nuclear-plasma-electromagnetic.md) | Electromagnetic, radiation-entropy, reaction-product, and plasma boundaries |
| [Dataset compatibility](docs/dataset-compatibility.md) | Energy-balance stages, substitution accounting, and external datasets |
| [Numerical validation](docs/validation.md) | Equations, benchmarks, real-data fixtures, tolerances, and limits |
| [Canonical paper](paper/quantity-and-quality-standard-reporting-framework.pdf) | Framework, derivation, application, and evidence |
| [Contributing](CONTRIBUTING.md) | Development setup and contribution standards |

## Project Boundary

This repository is dedicated to calculating and reporting the exact quantity
and quality of energy streams. It does not model technologies, emissions,
health, or economics. [The Exergy Imperative](https://github.com/cdimurro/the-exergy-imperative)
uses stream-level thermodynamics for that wider downstream analysis.

[exergyfactor.com](https://exergyfactor.com) is the simple browser calculator;
this package supplies the deeper programmable and auditable calculation layer.

## Contributing, Citation, and License

Corrections to published numbers, sourced reference examples, documentation
improvements, and real-dataset adoption reports are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Machine-readable citation metadata is in [CITATION.cff](CITATION.cff). GitHub
also renders it through **Cite this repository** in the repository sidebar.

Released under the [MIT License](LICENSE).
