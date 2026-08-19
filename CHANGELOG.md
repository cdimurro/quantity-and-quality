# Changelog

## 0.13.0 - 2026-08-18 - Cross-product conformance and web contracts

### Added

- A versioned, schema-validated conformance contract for shared thermal,
  cooling, sensible-heat, Petela, accessible-exergy, weighted-factor, and
  notation behavior across both Python packages and the browser calculator.
- Public contract and reference-data loaders with SHA-256 fingerprints.
- Web exports now include source package version, reference-data hash, and
  conformance-contract hash, and can emit the canonical contract for consumers.

### Safety and accuracy

- Both 20 °C and 25 °C Petela cases declare the reference environment
  explicitly, preventing user-facing defaults from becoming silent numerical
  disagreements.
- Valid cases, tolerances, invalid-input behavior, notation, schema structure,
  reference-data revision, and record count are enforced in CI.

## 0.12.0 - Fields, plasma, and nuclear reactions

### Added

- Electromagnetic field inventories for uniform and cell-integrated linear
  fields, measured normal Poynting flux, and RMS plane waves.
- Nuclear reaction accounting from mass defect, Q-value and event count, molar
  reaction extent, matching rest-mass lists, or sourced fusion reactivity.
- A D–T fusion preset that conserves its declared 17.6 MeV total while keeping
  14.1 MeV neutron and 3.5 MeV alpha product streams distinct.
- Ideal-species plasma inventories with separate species temperatures or
  supplied distribution means, bulk motion, ionization/excitation energy, and
  optional electromagnetic field energy.
- Radiation availability from co-boundary energy and entropy for externally
  evaluated non-blackbody spectra.
- Carrier tokens for electromagnetic fields, nuclear totals, neutrons, charged
  particles, neutrinos, and plasma, plus packaged examples and a focused model
  guide.

### Safety and accuracy

- Reaction-product energy is not mislabeled as reactor heat, electricity, or
  photon radiation. Downstream transport, deposition, and conversion remain
  separate boundaries.
- Density/reactivity fusion calculations require provenance for the supplied
  `<sigma v>`. Rest-mass Q-value calculations require an explicit convention so
  atomic and nuclear masses are not mixed.
- Relativistic plasma temperatures are rejected by the classical Maxwellian
  path. Non-Maxwellian and higher-fidelity models can supply independently
  evaluated mean energy and quality without hard-coding a speculative model.
- The stream request schema is 1.2, the carrier registry is 0.3, and Python,
  CLI, HTTP, and agent discovery expose the same contracts.

## 0.11.0 - Physical energy forms

### Added

- First-principles quantity calculators for shaft, kinetic, gravitational,
  rotational, elastic, hydraulic, electrical-field, battery-throughput, and
  phase-change energy.
- Physical flow exergy from supplied enthalpy and entropy, a transparent ideal-
  gas approximation, or an optional version-recorded CoolProp backend for
  steam, refrigerants, cryogens, compressed gases, and other supported fluids.
- State-to-state fluid accounting that can report enthalpy change as energy and
  physical-exergy change as its quality, without treating pressure alone as a
  complete thermodynamic state.
- Humid-air physical and composition exergy relative to a declared ambient
  state, including an optional relative-humidity conversion path.
- First-class `biomass` and `bioenergy` requests. Variable fuels require a
  measured chemical-exergy ratio, complete supplied component properties, or
  an explicitly sourced factor; dry-basis moisture adjustments are labeled.
- Generic blackbody and work-equivalent radiation, ideal-mixture separation,
  and nuclear mass-defect or fission-inventory calculations. Nuclear inventory
  requires an explicit accessible fraction.
- Friction, rolling resistance, and aerodynamic-drag loss models. They report
  mechanical work lost, residual heat exergy, and exergy destroyed separately.
- Agent-discoverable request fields and examples for every new model, a physical
  stream guide, and optional `fluids` installation extra.

### Changed

- Carrier registry 0.2 adds radiative, cooling, biomass, biogas, syngas,
  alcohol-fuel, and ammonia unit families.
- Radiation is distinct from the solar convenience model, and fluid-state
  distinguishability includes thermal, pressure, and composition differences.
- The unified calculation schema is version 1.1 and supports the new physical
  forms through the same Python, CLI, HTTP, and agent-native contract.

### Safety and accuracy

- Friction and air resistance are modeled as process losses rather than new
  energy forms. At ambient dissipation temperature their energy remains heat,
  their residual heat exergy is zero, and the incoming mechanical exergy is
  destroyed.
- Heterogeneous bioenergy receives no universal default factor. Non-ideal
  chemical mixing and variable-speed or variable-force losses must use a more
  appropriate property model or interval integration.

## 0.10.0 - Distinguishability and Applied Exergy

### Added

- Every stream record now exposes the physical distinguishability represented by
  its Exergy Factor, including source/reference states and gradients when known.
  Distinguishability is evidence for `fx`, not a second multiplier.
- `account_energy_chain()` keeps primary, secondary, final, and useful energy
  alongside their physical exergy stages, then identifies Applied Exergy at the
  last device-to-task boundary.
- Optional secondary energy/exergy now represents transformed transportable
  carriers between primary conversion and final delivery.
- Energy-only statistical stages can omit `fx`; source dataset and variable
  provenance are retained without inventing exergy.
- Primary-energy conventions distinguish direct, physical-energy-content,
  total-energy-supply, and substitution methods. Counterfactual substitution
  values are accepted but cannot be converted to physical exergy.
- Energy services are separate outcome records with non-energy units such as
  `passenger_mile`, `occupied_comfort_hour`, or `cold_beer_served`.
- Applied Exergy can be derived from useful energy and useful-stage `fx`, from
  final exergy and end-use exergy efficiency, or supplied directly. Independent
  paths are reconciled and inconsistent single-input balances are rejected.
- `quantity-quality account`, `POST /v1/account`, `GET /v1/accounting/schema`,
  and a packaged JSON Schema expose the same accounting contract to users and
  agents.
- Pinned numerical benchmarks from NIST, IAPWS-IF97, EIA, XAI4HEAT, and the
  OWID Energy dataset, plus a read-only full public-data validation command.

### Changed

- Equal source/reference temperatures now return `fx = 0`, making the
  indistinguishable equilibrium state explicit.
- The canonical paper now defines distinguishability, Applied Exergy, the
  primary-secondary-final-useful crosswalk, and the separation between energy
  and societal services.
- Fuel-volume shortcuts now use explicitly versioned EIA 2026 U.S.-average
  estimates (1,036 Btu/scf natural gas and 5.689 MMBtu/bbl crude oil), carry an
  `estimated_reference` quality flag, and warn that a measured heating value is
  required for a meter-specific result. `boe` remains a separate nominal 5.8
  MMBtu convention.

### Fixed

- Replaced sparse saturated-steam-table interpolation—which differed from
  IAPWS-IF97 by as much as 1.31 °C—with the explicit IF97 region-4 equation.
- Compound refrigeration-unit aliases such as `ton_hour` and `ton_hrs` now
  normalize as energy rather than being mistaken for mass.
- Known volume and mass units are rejected even when an explicit `fx` is
  supplied, preventing dimensionally invalid output such as `gallons_ex`.
- Scientific notation now round-trips through the public notation parser, with
  verification tolerance based on the printed exponent and precision.
- Solar and inverse-temperature helpers reject non-finite or physically invalid
  reference states, and `_ex` validation no longer accepts unrelated suffixes
  such as `_extra`.
- The XAI4HEAT sensitivity analysis now excludes reversed or ambient-
  indistinguishable stream states. This corrects valid-interval counts without
  materially changing the delivery-weighted portfolio factors.

## 0.9.0 - Focused stream calculation

### Added

- `calculate_stream()` accepts one JSON-shaped request from Python, the CLI, the
  HTTP API, or an AI agent and returns energy quantity, Exergy Factor, and
  accessible exergy through the existing record contract.
- Physical-input quantity paths for power × time, sensible heat
  (`m cp (Ts - Tr)`), fuel mass or volume × heating value, and solar irradiance
  × area × time.
- Fuel quality can use either a bundled factor or a declared chemical-exergy to
  HHV/LHV ratio.
- `quantity-quality calculate`, `quantity-quality capabilities`,
  `POST /v1/calculate`, and `GET /v1/capabilities` expose the same calculation
  and discovery surface.
- Machine-readable calculation errors, quantity method identifiers, original
  calculation inputs, and stream types.
- Reproducible integrated sensible-heat notation with supply, return, and
  reference temperatures.

### Changed

- Product documentation now focuses on calculating and reporting individual
  streams. Technology, process, emissions, health, and economic analysis is
  explicitly delegated to The Exergy Imperative.
- Return temperature is distinct from the reference environment throughout the
  parser and cleaner, allowing the integrated sensible-heat calculation to be
  represented correctly.

## 0.8.1 - Release stabilization

### Fixed

- Full thermal, cooling, and fuel notation now round-trips through the high-level
  API and cleaner without losing temperatures or basis metadata.
- Tiny nonzero energy quantities no longer format as zero, and bare `Mcf` and
  `MMcf` natural-gas billing units now follow the documented conversion.
- Blank and non-finite spreadsheet values become row-level validation issues.
  Pressure is only interpreted through the saturated-steam table when the row
  explicitly describes steam, a boiler, or condensate.
- Invalid domain inputs to calculation endpoints return structured client errors
  instead of HTTP 500 responses.
- Power records preserve `power`, `accessible_exergy_rate`, and rate units.
- Scenario grade mismatch is calculated over matched supply and demand energy.
- Fuel lookups retain HHV/LHV basis, and capability metadata no longer labels
  solar or chemical records self-verifying when notation verification cannot
  reproduce them.

### Changed

- Split chemical `energy_basis` labels from numeric `energy_basis_value` values
  and aligned the input/output JSON Schema with all supported record shapes.
- API-key requests require terms acceptance, are rate-limited per email, roll
  back when delivery fails, and can be revoked. SQLite connections are closed.
- URL cleaning now permits only HTTP(S), rejects embedded credentials, and has
  configurable time and response-size limits.
- The 40-page proposed-framework paper is canonical. Its source, analysis
  scripts, generated tables, and figures are included for reproducibility.
- Development checks now include Ruff, coverage, generated-data synchronization,
  schema validation, distribution inspection, and isolated wheel smoke tests.

## 0.8.0 - Fuel volumes that name their fuel

The website converted `scf(natural gas)`, `Mcf`, `MMcf`, `bbl(oil)` and `boe` to
energy; the library refused them. The same record was usable in one place and
rejected in the other.

### Added

- **Fuel-volume units convert when the unit names the fuel**, through the
  standard statistical equivalents — 1,000 Btu per scf, 5.80 MMBtu per barrel —
  producing the same numbers the website produces. 1 bbl(oil) becomes 1.6994 MWh
  and 1.8014 MWh_ex on both.
- Every conversion records what it used and on what basis. The paper's
  enforcement mechanism is that a chemical token is incomplete when its basis and
  reference table are not recoverable, so the assumption names the equivalent and
  the basis rather than leaving them implied.

Basis follows the paper, which recommends HHV as the default public fuel basis
"because it is common in national energy statistics and keeps fx below unity for
common combustion fuels". Gas volumes resolve to the HHV reference. The petroleum
equivalent is paired with the crude reference this package actually ships, which
is not an HHV figure, and the record says so instead of implying a basis it does
not have.

A bare `gallons`, `litres` or `kg` is still refused: a gallon of what, at what
heating value.

### Known gap

The paper's Carrier Registry lists `MWh_HHV_diesel`, `MWh_HHV_gasoline`,
`MWh_HHV_crude` and `MWh_HHV_coal`, and recommends HHV as the default. This
package ships only LHV values for those four — 1.06, 1.07, 1.06 and 1.05 — every
one above unity, which is the outcome the paper says an HHV basis avoids. Adding
the HHV factors needs chemical-exergy values from a cited table; they are not
invented here.

## 0.7.0 - Made usable on a real spreadsheet

A representative facility export — Site / Meter / Month / Usage / Units / Notes,
with therms, ton-hours, MMBtu and gallons in it — produced **zero** usable
records out of eight. It now produces six, and the two it refuses it refuses for
good reasons.

### Fixed

- **The reporter's own columns are kept.** The CSV writer excluded the source
  record, so Site, Meter, Month and Notes vanished and results could not be
  joined back to the data they came from. Output is now the original columns
  first and unchanged, then the essential few. `--detailed` restores the full
  set. A reporter's own `fx` column keeps its name; the computed one becomes
  `qq_fx`.
- **Ordinary words are understood.** "Main electric", "Natural gas boiler",
  "Chilled water" and similar are read from values and column headers and mapped
  to the bundled reference examples, which already held the answers. Every match
  is recorded as a presumptive assumption naming the text it matched, and
  anything stated explicitly always wins.
- **A temperature written in prose is read.** `exhaust ~340F`, `44F supply`,
  `delivered at 80 C`. A unit letter must be a whole word, so `845000 kWh` is
  never read as 845000 K.
- **Steam pressure becomes a delivery temperature.** `supply 165 psig` resolves
  through a saturation table to 189 C. Saturated steam is assumed and the record
  says so.
- **Real utility units convert.** therms (plural), dekatherms, ton-hours and
  their spellings reach a comparable `MWh_ex`. Previously `therm` worked and
  `therms` silently produced nothing, which is worse than refusing.
- **Volumes are never given an Exergy Factor.** Gallons, litres, ccf, barrels and
  masses are refused with instructions, because a factor is work potential per
  unit *energy*: `4100 gallons, fx = 1.060` reads like a result and is not one.
- **Cooling read from prose gets an ambient.** A service temperature alone left
  the row unanswerable on a missing ambient.
- The "not enough information" message now names what a person actually has — a
  temperature, a fuel and basis, a reference id — instead of four internal field
  names, one of which was the number they came for.

### Changed

- **An exact Exergy Factor is no longer padded.** Electricity reads `fx = 1.0`,
  not `fx = 1.000`: it is 1 by definition, not 1 measured to three decimals.
  Computed factors still keep their trailing zeros (`0.170`, `0.730`), which is
  what states the precision being claimed.

## 0.6.0 - The Full Operational Notation

The paper defines a completely specified stream declaration as
`1 MWh, fx = 0.170 [Th = 80°C, T0 = 20°C]`, and its value is that the recipient
can re-derive the factor in one step. Three things had to be true for that to
hold, and none of them were.

- **The Exergy Factor is now a fixed-width field.** `0.170`, not `0.17`; `1.000`,
  not `1`. The trailing digits state the precision being claimed, and without
  them the published figure did not look like the value a reader recomputes
  (`1 - 293.15/353.15 = 0.16990 -> 0.170`). The quantity is unchanged: the paper
  writes `1 MWh`, not `1.000 MWh`. **This changes printed notation strings.**
- **The full declaration now parses.** `parse_energy_notation` rejected the
  bracket outright, so the library emitted a canonical form it could not read
  back. Both forms now round-trip. `°C` is accepted but not required, and a
  bracket temperature may state `K` or `F` explicitly. `ParsedNotation` gained
  `source_c`, `sink_c`, `cold_service_c`, `energy_basis`, and
  `is_fully_specified`.
- **Added `verify_notation()` and `quantity-quality verify`.** These re-derive a
  record's factor from its own bracket and report agreement — the property the
  notation exists for, previously implemented nowhere. The CLI exits non-zero on
  a verifiable mismatch so it can gate a pipeline. A record with no bracket is
  reported as *not verifiable*, which is not the same as wrong.

## 0.5.0 - Third Draft Alignment

- **Distribution renamed to `quantity-and-quality`**, matching the repository
  name. Install with `pip install quantity-and-quality`. The command stays
  `quantity-quality` and the import stays `quantity_quality`, so existing scripts
  and CLI usage are unaffected — only the install name changes.
- Added a formal Carrier Registry API with core third-draft suffixes, including `MWh_solar`, `MWh_fission`, and carrier-specific chemical tokens such as `MWh_HHV_CH4`, `MWh_HHV_NG`, and `MWh_HHV_H2`.
- Added Fidelity Tier definitions, tier inference, and conformance issue reporting for F0 through F4 records.
- Added diagnostics for Exergy Capital Efficiency, second-law efficiency, Exergy Loss Angle, inverse angle mapping, Loss Angle Velocity, and F3 weighted factors.
- Added F3 thermal interval helpers for synchronized dynamic temperature records.
- Added an optional deterministic FastAPI service with calculation endpoints, API key request/delivery support, and CLI server startup.
- Updated fuel notation defaults, reference examples, schema fields, CLI registry/tier commands, README examples, and tests to match the third draft.

## 0.4.0 - Launch Readiness

- Added `calc`, `clean`, and `compare` CLI workflows for first-time users.
- Added scenario comparison for JSON files, with optional YAML support through `quantity-quality[scenario]`.
- Added Markdown and JSON scenario report output.
- Added a packaged JSON Schema for interoperable Quantity + Quality records.
- Added structured reference metadata for basis type, confidence, fuel basis, and explicit temperatures.
- Added static website export data so web presets can be generated from the Python reference database.
- Added adoption cookbook examples for audits, district energy, fuels, and scenario comparison.
- Added CI and PyPI publishing workflow templates.

## 0.3.0

- Added messy-record cleanup for CSV, JSON, JSONL, Excel, DataFrames, SQL, streams, and URLs.
- Added readiness metadata with capabilities, missing context, assumptions, and warnings.
- Added bundled reference examples and web export groundwork.
