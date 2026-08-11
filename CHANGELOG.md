# Changelog

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
