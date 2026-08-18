# Numerical validation

The project treats numerical correctness as a release requirement. Validation is
split into exact identities, equation conformance, public-data regression tests,
and explicitly labeled estimates.

## What is validated

- Every supported energy unit is round-tripped through MWh. SI and customary
  unit benchmarks use the NIST definitions for the watt-hour, International
  Table Btu, and U.S. legal therm.
- Carnot, cooling, integrated sensible-heat, Petela, chemical-ratio, weighted
  factor, quantity, and end-use accounting paths are checked against independent
  equations and domain constraints.
- Mechanical, electrical-field, phase-change, ideal-gas, ideal-mixture,
  nuclear-reaction, friction, rolling-resistance, and aerodynamic-drag paths are
  checked directly against their defining SI equations. One thousand seeded
  random mass/velocity/height cases guard the kinetic and gravitational paths.
- Electromagnetic stored-field energy is checked independently against
  `epsilon E²/2 + B²/(2 mu)`, while Poynting and RMS plane-wave cases guard the
  surface/time and amplitude conventions.
- D–T event energy, mass-derived Q-value, reaction-rate integration, and
  neutron-plus-alpha conservation are independently checked in SI units. Tests
  also ensure neutron energy cannot silently become photon radiation.
- Ideal plasma species are checked against `f N k T/2`, constant-volume
  availability, bulk energy, internal-state inputs, and optional field energy.
  Unsupported relativistic inputs and incomplete distribution models must fail
  rather than return an approximate number.
- A 10 bar saturated-steam condensation case is checked three ways: CoolProp
  enthalpy/entropy properties, the independent `delta-h - T0 delta-s` exergy
  balance, and the Carnot factor at saturation. Refrigerant, cryogenic nitrogen,
  compressed-air, and humid-air states exercise the same property contract.
- Saturated-steam pressure inference uses the explicit IAPWS-IF97 region-4
  equation. Six pinned points from 0.5 bar through the critical pressure are
  regression-tested to `1e-10` °C. A separate dense comparison against an
  independent IF97 implementation found a maximum absolute difference below
  `5e-11` °C.
- Four pinned XAI4HEAT rows are part of the ordinary test suite. The full live
  validator checks all 51,592 processed district-heating intervals at commit
  `fc7ee9a`, compares the library with independently evaluated equations, and
  checks portfolio factors and valid-interval counts.
- Three real 2024 rows from the OWID Energy dataset—United States, Germany, and
  World—verify TWh normalization, electricity exergy, source provenance, and the
  rule that substitution-method primary energy is not converted into physical
  exergy.

The pinned values, source commits, URLs, and SHA-256 hashes are in
[`tests/fixtures/real_world_benchmarks.json`](../tests/fixtures/real_world_benchmarks.json).
CI uses this small immutable fixture and does not depend on live network access.

## Run the permanent suite

```bash
python -m pytest -q
```

## Run the full public-data validation

Clone the exact source revisions into the ignored runtime directory:

```bash
git clone https://github.com/xai4heat/xai4heat runtime/external/xai4heat
git -C runtime/external/xai4heat checkout fc7ee9ada9e2be658914c5b41e572c00e624ad1e

git clone https://github.com/owid/energy-data runtime/external/owid-energy-data
git -C runtime/external/owid-energy-data checkout 7e387a16f70a510e433f8aac7efeac6faa1e5059

python scripts/validate_real_data.py
```

The command is read-only. It fails if a commit, source-file hash, row value,
validity count, or calculation result differs from the pinned benchmark.

## Exact calculations versus estimates

The following paths are deterministic calculations from the caller's declared
inputs:

- power × duration
- mass × declared heating value
- volume × declared heating value
- mass × declared heat capacity × temperature difference
- irradiance × area × duration
- Exergy Factor equations and energy/exergy accounting

The new physical example regressions include:

| Request | Energy quantity | Exergy Factor | Accessible exergy |
|---|---:|---:|---:|
| 500 N m shaft, 1,800 rpm, 2 h | 188.495559 kWh_m | 1 | 188.495559 kWh_ex |
| 1,000 kg saturated steam, 10 bar, vapor to liquid | 559.609315 kWh_th | 0.352909765 | 197.491592 kWh_ex |
| 1,000 kg biomass, 18 MJ/kg LHV, 19 MJ/kg chemical exergy | 5 MWh_LHV_biomass | 1.055555556 | 5.277777778 MWh_ex |
| Constant quadratic drag in the packaged example | 0.701822917 kWh_th | 0 at ambient | 0 kWh_ex residual heat |
| 100 V/m RMS vacuum plane wave, 2 m², 1 h | 0.053088375 kWh_em | 1 | 0.053088375 kWh_ex |
| 10²⁰ D–T reactions, total products | 78.328635 kWh_nuclear | 1 | 78.328635 kWh_ex |
| 10²⁰ D–T reactions, neutron channel | 62.751918 kWh_neutron | 1 | 62.751918 kWh_ex |

The steam values above are a regression for CoolProp 8.0.0 and are accompanied
by backend/version metadata. Later compatible backend releases may make small
property refinements; the equation-level balance remains the release criterion.
For licensed or organization-standard property data, callers can bypass the
optional backend and supply enthalpy and entropy from REFPROP or another
validated property system.

A fuel volume without a measured heating value cannot produce an exact energy
quantity because fuel composition varies. Convenience inputs such as
`scf(natural gas)` and `bbl(oil)` therefore use pinned EIA 2026 U.S.-average
estimates. Their records carry `data_quality_flag="estimated_reference"`, an
assumption, and a warning asking for a measured HHV or LHV. The nominal `boe`
conversion is similarly identified as a convention. These fallback values must
not be presented as meter-specific measurements.

Bundled fuel Exergy Factors are rounded public reference defaults. Use the
declared `chemical_exergy` and `energy_basis_value` path when composition-specific
accuracy is required.

Biomass and other heterogeneous fuels receive no bundled universal factor.
Their heating value and chemical exergy must use the same moisture, ash,
composition, and HHV/LHV basis. The request can retain feedstock class, moisture,
ash, property source, and basis unit. A dry-matter shortcut is labeled and warns
that it is not a measured as-received value.

Friction and aerodynamic drag are deterministic only for the declared constant
force or steady-flow conditions. They are reported as incoming mechanical work
lost, residual exergy in the dissipated heat, and exergy destruction. Changing
speed, density, force, or temperature requires interval integration.

Electromagnetic material models are exact only inside their declared linear,
isotropic, nondispersive domain. Fusion reactivity is caller-supplied and
sourced because it depends on the reactant distribution and nuclear data.
Plasma's built-in Maxwellian inventory excludes collective, degeneracy,
strong-coupling, sheath, and transport effects; use externally evaluated
species or total-state inputs when those effects are material.

## Authoritative numerical sources

- [NIST Guide to the SI conversion factors](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9)
- [IAPWS Industrial Formulation 1997](https://www.iapws.org/relguide/IF97-Rev.pdf)
- [IAPWS-95 water and steam formulation](https://www.iapws.org/relguide/IAPWS-95.html)
- [NIST REFPROP](https://www.nist.gov/srd/refprop)
- [CoolProp documentation](https://coolprop.org/)
- [EIA energy conversion calculators](https://www.eia.gov/energyexplained/units-and-calculators/energy-conversion-calculators.php)
- [XAI4HEAT public repository](https://github.com/xai4heat/xai4heat)
- [OWID Energy dataset](https://github.com/owid/energy-data)
- [NIST 2022 CODATA constants](https://physics.nist.gov/cuu/Constants/)
- [NRL Plasma Formulary](https://www.nrl.navy.mil/News-Media/Publications/NRL-PlasmaFormulary/)
- [IAEA Fusion Physics](https://www-pub.iaea.org/MTCD/Publications/PDF/Pub1562_web.pdf)

No finite test suite can prove correctness for every possible future input.
Release confidence comes from keeping the physical domain narrow, rejecting
invalid states, labeling estimates, pinning public evidence, and making every
equation and assumption inspectable.
