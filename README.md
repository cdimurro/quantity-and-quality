# Quantity and Quality

[![PyPI](https://img.shields.io/pypi/v/quantity-and-quality.svg)](https://pypi.org/project/quantity-and-quality/)
[![Python](https://img.shields.io/pypi/pyversions/quantity-and-quality.svg)](https://pypi.org/project/quantity-and-quality/)
[![CI](https://github.com/cdimurro/quantity-and-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/cdimurro/quantity-and-quality/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/cdimurro/quantity-and-quality/blob/main/LICENSE)

A small Python library and CLI for calculating and reporting the **energy quantity**, **Exergy Factor**, and **accessible exergy** of individual energy streams, with optional end-use accounting through **Applied Exergy**.

**[Try it in your browser](https://exergyfactor.com)** ·
[Paper](https://github.com/cdimurro/quantity-and-quality/blob/main/paper/quantity-and-quality-standard-reporting-framework.pdf) ·
[Adoption cookbook](https://github.com/cdimurro/quantity-and-quality/blob/main/docs/adoption-cookbook.md) ·
[Physical streams](https://github.com/cdimurro/quantity-and-quality/blob/main/docs/physical-streams.md) ·
[Fields, plasma, and nuclear](https://github.com/cdimurro/quantity-and-quality/blob/main/docs/nuclear-plasma-electromagnetic.md) ·
[Dataset compatibility](https://github.com/cdimurro/quantity-and-quality/blob/main/docs/dataset-compatibility.md) ·
[Numerical validation](https://github.com/cdimurro/quantity-and-quality/blob/main/docs/validation.md) ·
[Changelog](https://github.com/cdimurro/quantity-and-quality/blob/main/CHANGELOG.md)

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

The thermodynamics are well understood. The missing piece is a simple way to put them into everyday energy records. This package calculates the number, states the physical difference that makes work possible, and makes the result easy to carry into a spreadsheet, API, database, or report.

The calculator remains focused on one stream: `Q`, `fx`, and `X = Q × fx`. The library can also place calculated streams at primary, secondary, final, and useful boundaries and identify the Applied Exergy that reaches the task. It does not model technologies, emissions, health, or economics; use [The Exergy Imperative](https://github.com/cdimurro/the-exergy-imperative) for that downstream analysis.

---

## What You Can Do With It

Use this framework to:

- calculate quantity and Exergy Factor for electrical, electromagnetic,
  mechanical, hydraulic, thermal, fluid-state, humid-air, chemical, radiative,
  separation, nuclear, and plasma streams
- calculate quantity from measured physical inputs, including shaft torque,
  motion, pressure, phase change, voltage and current, fuel composition, and
  irradiance
- model biomass and bioenergy without assuming that variable moisture,
  composition, and heating value have one universal factor
- account for friction, rolling resistance, and aerodynamic drag as mechanical
  work dissipated to heat and exergy destruction
- convert ordinary energy records into quantity-plus-quality notation
- clean CSV, JSON, JSONL, Excel, DataFrame, SQL, stream, or URL records
- add auditable context such as reference sink, boundary, basis, assumptions, and warnings
- expose the thermodynamic distinguishability behind `fx` without inventing a second factor
- keep primary, secondary, final, and useful energy distinct from Applied Exergy and the resulting energy service
- use one JSON-shaped request from Python, the CLI, HTTP, or an AI agent

The package is designed to start simple: use reference defaults for screening, then replace them with site-specific values when accuracy matters. Estimated fuel-volume conversions are labeled and warn when a measured heating value is needed; see [numerical validation](docs/validation.md).

---

## Install

From PyPI:

```bash
python -m pip install quantity-and-quality
```

The installed command is `quantity-quality` (no "and"), and the import name is
`quantity_quality`.

For local development:

```bash
python -m pip install -e ".[all,dev]"
```

YAML scenario files require the optional scenario extra, the HTTP API requires
the `api` extra, and real-fluid properties require the `fluids` extra:

```bash
python -m pip install "quantity-and-quality[scenario]"
python -m pip install "quantity-and-quality[api]"
python -m pip install "quantity-and-quality[fluids]"
```

To install the unreleased development version directly from GitHub:

```bash
python -m pip install git+https://github.com/cdimurro/quantity-and-quality.git
```

---

## The Four Main Workflows

### 1. Calculate One Stream

Use this when you know the energy form and want a quick quantity-plus-quality record.

```bash
quantity-quality calc thermal --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
```

Example output:

```text
80 C heat to 20 C sink
report: 1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
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

records = qq.clean_records(
    [
        {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
        {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
        {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
    ]
)

for record in records:
    print(record["full_notation"], record["missing_context"])
```

---

### 3. Calculate From Physical Inputs

Use the same JSON request from Python, the CLI, or the HTTP API. This example calculates both the sensible heat quantity and its integrated Exergy Factor:

```bash
quantity-quality calculate examples/stream-calculation.json --json
```

The request contains ordinary measured values:

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

Discover all accepted request shapes programmatically:

```bash
quantity-quality capabilities --json
quantity-quality capabilities --json-schema
```

The same entry point covers forms that are often omitted from ordinary energy
calculators:

```bash
quantity-quality calculate examples/mechanical-shaft.json --json
quantity-quality calculate examples/steam-condensation.json --json
quantity-quality calculate examples/biomass-calculation.json --json
quantity-quality calculate examples/aerodynamic-drag.json --json
quantity-quality calculate examples/electromagnetic-field.json --json
quantity-quality calculate examples/dt-fusion-neutron.json --json
quantity-quality calculate examples/plasma-state.json --json
```

The browser calculator stays intentionally simple. These advanced, auditable
paths live in the library, CLI, schema, and API; see the [physical-stream
guide](docs/physical-streams.md). Nuclear reaction products, plasma state
inventories, electromagnetic fields, and non-blackbody radiation are documented
in the [fields, plasma, and nuclear guide](docs/nuclear-plasma-electromagnetic.md).

---

### 4. Account For What Reaches The Task

Use the optional account when you have more than one boundary. It keeps each
physical and societal quantity distinct:

```text
primary energy -> secondary energy -> final energy -> useful energy -> energy service
primary exergy -> secondary exergy -> final exergy -> Applied Exergy
```

Secondary energy is the optional transformed, transportable carrier boundary:
electricity at generator output, refined fuel leaving a refinery, or district
heat entering a network. It can be omitted when a dataset does not report that
boundary separately.

Applied Exergy is the exergy crossing the last device-to-task boundary. It is
not useful energy: useful energy can still contain both exergy and anergy.
Energy services are the outcomes people want—such as a cold beer, an occupied
home kept comfortable, or passenger-miles—and use outcome units rather than
joules or watt-hours.

```bash
quantity-quality account examples/end-use-accounting.json --json
```

The library derives Applied Exergy from `useful.quantity × useful.fx`, from
`final exergy × end_use_exergy_efficiency`, or accepts a directly measured or
independently calculated value. When more than one path is supplied, they must
agree.

Energy-only datasets are accepted without `fx`; the library preserves their
quantity and provenance and leaves exergy unreported. Set `accounting_method` to
`physical_energy_content`, `total_energy_supply`, `direct`, or `substitution`.
Substitution-method values are counterfactual fossil-input equivalents, so the
library will not multiply them by a physical Exergy Factor. See the
[dataset compatibility guide](docs/dataset-compatibility.md).

---

## Python API

```python
import quantity_quality as qq

record = qq.thermal(1, "MWh_th", source_c=80, sink_c=20)

print(record.full_notation)
# 1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]

print(record.accessible_exergy, record.accessible_exergy_unit)
# 0.169899... MWh_ex
```

Calculate from the measurements you have:

```python
result = qq.calculate_stream(
    {
        "stream_type": "electricity",
        "power": 100,
        "power_unit": "kW",
        "duration_hours": 8,
    }
)

print(result.full_notation)
# 800 kWh_e, fx = 1.0
```

Account across end-use boundaries:

```python
account = qq.account_energy_chain(
    {
        "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
        "useful": {
            "quantity": 3,
            "unit": "MWh_th",
            "fx": 0.064,
            "source_c": 40,
            "sink_c": 20,
        },
        "service": {
            "name": "Warm home",
            "quantity": 720,
            "unit": "occupied_comfort_hour",
        },
    }
)

print(account.applied_exergy_mwh)
# 0.192 MWh_ex
```

Create a custom record:

```python
record = qq.report(1, "MWh", fx=0.73)

print(record.notation)
# 1 MWh, fx = 0.730
```

### HTTP API

The optional FastAPI service exposes the same deterministic calculations and an
OpenAPI document:

```bash
python -m pip install "quantity-and-quality[api]"
quantity-quality serve-api
```

Open <http://127.0.0.1:8000/docs> for interactive documentation. Use
`GET /v1/capabilities` to discover supported inputs and `POST /v1/calculate` to
calculate a stream. The request schema is also available at
`GET /v1/calculate/schema`. End-use accounts use `POST /v1/account`, with the
request schema at `GET /v1/accounting/schema`. Set `QQ_API_REQUIRE_KEY=1` for
authenticated deployments. API-key requests require explicit terms acceptance,
are limited per email, and keys can be revoked with `POST /v1/api-keys/revoke`.

Production deployments should provide TLS, a persistent backed-up database,
working SMTP delivery, proxy-level IP rate limits, logging, monitoring, and an
explicit `QQ_API_CORS_ORIGINS` list.

Use a bundled reference example:

```python
record = qq.lookup("heat-80c-standard", quantity=1.8)

print(record.full_notation)
# 1.8 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
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

For a sensible-heat stream cooling from supply to return temperature, use the
integrated constant-heat-capacity helper:

```python
fx = qq.sensible_heat_exergy_factor_c(supply_c=80, return_c=50, sink_c=20)
```

This evaluates `1 - T0 * ln(Ts/Tr) / (Ts - Tr)` in kelvin and matches the F3
sensitivity method in the canonical paper.

Temperatures are converted to kelvin internally. Public examples use:

```text
T0 = 20 C
```

unless another sink or reference condition is declared.

Fuel examples must declare their energy basis. HHV is recommended for broad public comparison because it avoids confusing `fx > 1` values for common fuels. LHV is supported when explicitly labeled.

### Distinguishability

Exergy exists because a stream is thermodynamically distinguishable from a
declared environment or task boundary. A temperature, pressure, chemical,
electrical, mechanical, or radiative difference can support work; at equilibrium
the relevant difference and exergy vanish.

The library reports that evidence in `record.distinguishability`. It does not
apply a second "distinguishability factor": `fx` already quantifies the
work-bearing difference.

### Applied Exergy

For a declared end-use chain:

```text
X_primary = E_primary * fx_primary
X_secondary = E_secondary * fx_secondary
X_final   = E_final   * fx_final
X_applied = E_useful  * fx_useful
          = X_final * end-use exergy efficiency
```

`X_applied` is called *useful exergy* or *useful work* in societal exergy
literature. This project uses **Applied Exergy** to make the application boundary
explicit and to prevent confusion with useful energy.

Useful energy need not be lower than final energy—for example, a heat pump can
deliver several units of useful heat per unit of final electricity. Applied
Exergy, however, cannot exceed final exergy in the single-input chain represented
by this account.

The substitution method is separate from thermodynamics. It rescales some
non-fossil electricity into a hypothetical fossil-input equivalent for
statistical comparison. Such a value can be retained as primary-energy data,
but it is not a physical stream at that magnitude and is not used to calculate
primary exergy. Our World in Data has announced a transition of its headline
primary-energy treatment, while its pinned public energy-data snapshot at commit
`7e387a1` still labels renewable-consumption fields as substitution-method data.
Datasets and releases can therefore differ, so the convention must be read from
the source metadata and declared on every imported stage.

Terminology follows the [IEA definitions of useful energy and energy
services](https://www.iea.org/glossary) and the established
[primary-final-useful energy and exergy
chain](https://doi.org/10.1088/2753-3751/ad4e39). The interpretation of exergy
as thermodynamic distinguishability from the environment is documented in
[Masini and Ayres' exergy-accounting
chapter](https://web.mit.edu/2.813/www/readings/MasiniAyres.pdf). "Applied
Exergy" is this project's explicit name for useful-stage exergy at the
device-to-task boundary.

---

## Why This Matters

One MWh of electricity, one MWh of 80 °C heat, one MWh of 40 °C heat, and one MWh of fuel are equal under first-law energy accounting.

They are not equal as useful work resources.

Examples with a 20 °C reference sink:

| Stream | Conventional Report | Quantity + Exergy Factor |
|---|---:|---:|
| Electricity | `1 MWh` | `1 MWh, fx = 1.0` |
| Heat at 150 °C | `1 MWh_th` | `1 MWh_th, fx = 0.307` |
| Heat at 80 °C | `1 MWh_th` | `1 MWh_th, fx = 0.170` |
| Heat at 40 °C | `1 MWh_th` | `1 MWh_th, fx = 0.064` |
| Methane, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.930` |
| Hydrogen, HHV basis | `1 MWh_HHV` | `1 MWh_HHV, fx = 0.830` |

The Exergy Factor supplies the quality number that conventional energy accounting leaves out. This package calculates and reports that number; downstream tools can decide how to use it.

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

For a chemical calculation, keep the denominator label separate from its numeric
value:

```json
{
  "quantity": 1,
  "unit": "MWh_HHV_CH4",
  "chemical_exergy": 55.5,
  "energy_basis": "HHV",
  "energy_basis_value": 50.0
}
```

Power records use `power` and return `accessible_exergy_rate` rather than silently
changing a rate into an energy quantity.

The JSON Schema is packaged and available at:

```text
data/quantity_quality_record.schema.json
data/stream_calculation_request.schema.json
data/energy_accounting_request.schema.json
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
- fuels, including chemical defaults for selected conventional carriers
- biomass and bioenergy carrier units (composition-specific quality must be
  supplied rather than guessed)
- solar and other radiation
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

Mechanical motion, fluid states, humid air, separation, nuclear inventory, and
dissipative losses are calculated from request inputs rather than represented by
fixed reference factors.

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

A **computed** Exergy Factor keeps its trailing zeros: `0.170`, not `0.17`, and
`0.730`, not `0.73`. Those digits state the precision being claimed, and they
make the published figure look like the value a reader recomputes.

An **exact** factor is not padded. Electricity is 1 by definition, not 1 measured
to three decimals, so it reads `fx = 1.0`. The quantity is never padded either —
`1 MWh`, not `1.000 MWh`.

### Short notation

Use this when the reference convention is already known, the carrier is unambiguous, or the value is being used in a compact dashboard, invoice, spreadsheet, or chart.

```text
1 MWh, fx = 1.0
```

A short-form record is not verifiable from itself. That is a legitimate choice
for electricity, where `fx = 1.0` regardless of the sink — but it is a choice,
and the reader should be able to tell that it was made.

### Full notation

Use this for thermal streams, non-default references, technical reports, datasets, audits, and any case where another person needs to verify the value from the notation itself.

```text
1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]
```

**This is the point of the notation.** The bracket declares the source and
reference temperatures, so whoever receives the record can re-derive the factor
themselves — in one division, without trusting the sender or this library:

```text
fx = 1 - T0/Th = 1 - 293.15/353.15 = 0.170
```

From the shell, on any record — including ones this package did not produce:

```bash
quantity-quality verify "1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]"
# 1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]
#   fx = 1 - T0/Th = 1 - 293.15/353.15 = 0.170  [OK]
```

It exits non-zero when a verifiable record disagrees with its own bracket, so it
can gate a pipeline: a report whose stated factors no longer match the
temperatures printed beside them fails the build instead of being published.
A record with no bracket exits zero — it has not been contradicted.

From Python:

```python
>>> import quantity_quality as qq
>>> print(qq.verify_notation("1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]"))
fx = 1 - T0/Th = 1 - 293.15/353.15 = 0.170  [OK]

>>> check = qq.verify_notation("1 MWh_th, fx = 0.900 [Th = 80 C, T0 = 20 C]")
>>> check.agrees, round(check.difference, 3)
(False, 0.73)
```

A record with no declaration bracket is reported as **not verifiable**, which is
not the same as wrong — nothing has been contradicted, there is simply nothing to
check against.

The bracket also round-trips, so a record can be read back out of a report,
a CSV cell, or an email:

```python
>>> parsed = qq.parse_energy_notation("1 MWh, fx = 0.170 [Th = 80°C, T0 = 20°C]")
>>> parsed.source_c, parsed.sink_c, parsed.is_fully_specified
(80.0, 20.0, True)
```

`°C` is accepted but never required, and a bracket temperature may state `K` or
`F` explicitly — `[Th = 353.15 K, T0 = 293.15 K]` parses to the same record. The
canonical written form stays ASCII so the notation survives a spreadsheet, a
plain-text log, and an email without an encoding step.

Cooling services declare their own bracket and verify against the service
equation:

```text
1 MWh_cooling, fx = 0.082 [Tcold = 7 C, T0 = 30 C]
fx = T0/Tcold - 1 = 303.15/280.15 - 1 = 0.082
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
data/stream_calculation_request.schema.json
                                       JSON Schema for stream calculation inputs
data/energy_accounting_request.schema.json
                                       JSON Schema for end-use accounting inputs
examples/adoption_records.csv          Cleaning example
examples/stream-calculation.json       Physical-input stream request
examples/electromagnetic-field.json    Field-transfer request
examples/dt-fusion-neutron.json        D-T reaction-product request
examples/plasma-state.json             Ideal-species plasma inventory
examples/end-use-accounting.json       Applied Exergy accounting request
examples/owid-substitution-accounting.json  Historical statistical-method example
docs/adoption-cookbook.md              Practical adoption recipes
docs/nuclear-plasma-electromagnetic.md Advanced physical-model boundaries
paper/                                 Framework paper
```

---

## Development

```bash
python -m pip install -e ".[all,dev]"
python scripts/sync_reference_data.py --check
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=quantity_quality
python -m build
python -m twine check dist/*
```

For the pinned all-row XAI4HEAT and OWID numerical pass:

```bash
python scripts/validate_real_data.py
```

The required source revisions and expected hashes are documented in the
[numerical validation guide](docs/validation.md).

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
  title  = {Quantity and Quality: A Proposed Exergy-Factor Reporting Framework for Energy Systems},
  author = {DiMurro, Christopher},
  year   = {2026},
  note   = {Independent Researcher, Exergy Lab}
}
```

Machine-readable citation metadata is in
[`CITATION.cff`](https://github.com/cdimurro/quantity-and-quality/blob/main/CITATION.cff). GitHub
renders a formatted citation from it via the **Cite this repository** button in
the repository sidebar.

---

## Contributing

Issues and pull requests are welcome, particularly:

- **Reference examples** for carriers or processes not yet covered, with a
  stated boundary, basis, and source. New examples belong in
  `data/reference_examples.json` and should come with a test.
- **Corrections to any published number.** If a reference value here is wrong,
  that is the most valuable issue you can file — please include the working, not
  just the corrected value.
- **Adoption reports**: what broke when you pointed this at a real dataset.

Before opening a pull request:

```bash
python -m pip install -e ".[all,dev]"
python -m pytest -q
```

See the full
[contribution guide](https://github.com/cdimurro/quantity-and-quality/blob/main/CONTRIBUTING.md)
and [security policy](https://github.com/cdimurro/quantity-and-quality/blob/main/SECURITY.md).
CI runs formatting, lint, synchronization, schema, test, coverage, and package
checks on Python 3.9 through 3.14.

---

## Related

| | |
|---|---|
| **[exergyfactor.com](https://exergyfactor.com)** | Browser calculator built on this package's reference data. No install required. |
| **[cdimurro/exergy-factor](https://github.com/cdimurro/exergy-factor)** | Source for that site. |
| **[The Exergy Imperative](https://github.com/cdimurro/the-exergy-imperative)** | Uses stream-level thermodynamics for process, technology, emissions, health, and economic analysis. |

---

## License

[MIT](https://github.com/cdimurro/quantity-and-quality/blob/main/LICENSE) © 2026 Christopher DiMurro
