# Nuclear, plasma, electromagnetic, and radiation streams

These models answer a narrow question: how much energy crosses or exists inside
a declared boundary, in what physical form, and how much of it is exergy at that
boundary? They do not simulate a reactor, plasma discharge, antenna, shielding
system, or end-use device.

Use the same JSON request with `calculate_stream()`, `quantity-quality
calculate`, or `POST /v1/calculate`. The browser calculator remains a simple
quantity-and-quality calculator.

## Electromagnetic fields

A linear, isotropic, nondispersive field inventory uses

```text
E = integral [epsilon |E|^2 / 2 + |B|^2 / (2 mu)] dV
```

The request can describe one uniform volume or a piecewise-uniform
`field_cells` array. A measured flux crossing a surface uses

```text
E = S_normal A dt
```

and the plane-wave convenience model uses an RMS electric-field amplitude,
`S = E_rms^2 / Z`. The explicit name `electric_field_rms_v_m` prevents the
factor-of-two error caused by confusing peak and RMS amplitude.

```json
{
  "stream_type": "electromagnetic_field",
  "electric_field_rms_v_m": 100,
  "wave_impedance_ohm": 376.730313412,
  "area_m2": 2,
  "duration_hours": 1,
  "boundary": "receiving aperture"
}
```

Field energy is work-equivalent (`fx = 1`) at the field-transfer boundary.
Antenna efficiency, absorption, dielectric loss, and conversion efficiency
belong downstream. Relative permittivity and permeability are valid only for a
linear, isotropic, nondispersive medium. Dispersive, lossy, nonlinear,
anisotropic, or hysteretic media must supply energy from a validated
constitutive model. NIST describes why electromagnetic energy density in
dispersive and dissipative media requires a more general treatment.

Incoherent photon radiation is `_rad`, not `_em`. Neutrons and charged reaction
products are particles, not electromagnetic radiation.

## Nuclear inventory and reaction products

Nuclear inventory and released reaction energy are different boundaries.

Inventory mode calculates a possible nuclear-energy quantity from a mass defect
or isotope count. It requires `accessible_fraction`; the library does not assume
fuel burnup, criticality, reactor design, or how much inventory can react.

Reaction mode calculates released energy from

```text
E = N_reactions Q
```

where `Q` may be supplied directly, calculated from matching rest-mass lists, or
provided by a named preset. Atomic and nuclear mass conventions must never be
mixed, so mass-list requests require a `mass_convention`. `reaction_amount_mol`
means moles of reaction events, not moles of either reactant.

The bundled `dt_fusion` preset represents the dominant D–T branch with a rounded
17.6 MeV Q-value partitioned into a 14.1 MeV neutron and 3.5 MeV alpha particle.
The partition sums exactly to the declared total:

```json
{
  "stream_type": "thermonuclear",
  "reaction_preset": "dt_fusion",
  "reaction_count": 1e20,
  "nuclear_channel": "neutron"
}
```

At the immediate reaction-product boundary, neutron and alpha kinetic energy is
ordered particle energy and has `fx = 1`. That does not mean a plant can turn it
all into electricity. Transport, escape, moderation, capture, deposition,
thermalization, and power conversion occur at later boundaries.

For a spatially uniform fusion interval, event count can be calculated from a
caller-supplied reactivity:

```text
N_reactions = n1 n2 <sigma v> V dt
```

The factor is one half for identical reactants. The request must identify
`reactivity_source`; the library does not silently choose a temperature,
cross-section fit, or distribution. The model assumes density, reactivity, and
reacting volume remain uniform and constant and does not model depletion.

Other reactions use `reaction_channels`. Fractions must sum to one and every
channel declares its own carrier and Exergy Factor. These are fractions of the
released energy, not reaction branching probabilities or particle-count
fractions. This accommodates fission, other fusion fuels, gamma emission,
neutrino losses, and imported nuclear-data results without pretending that all
product energy is heat or photons.

## Plasma state inventory

The dependency-free plasma model is an ideal-species state inventory. Each
species supplies a particle count or number density and either a temperature or
an externally calculated mean kinetic energy.

For a classical Maxwellian species,

```text
U_kinetic = f N k T / 2
X_thermal,V = f N k [(T - T0) - T0 ln(T/T0)] / 2
```

The second expression is constant-volume thermal availability relative to the
declared reference temperature. Bulk motion is added as kinetic work.
Ionization or excitation energy can be included, but requires an explicit
`internal_exergy_factor` because its recoverable work depends on composition and
the relaxation path.

```json
{
  "stream_type": "plasma",
  "volume_m3": 1,
  "reference_temperature_k": 293.15,
  "plasma_species": [
    {
      "name": "electron",
      "number_density_m3": 1e20,
      "temperature_ev": 1000
    },
    {
      "name": "deuteron",
      "number_density_m3": 1e20,
      "temperature_ev": 1000
    }
  ],
  "magnetic_flux_density_t": 0.01
}
```

Electron and ion temperatures remain separate. A uniform or cell-integrated
electromagnetic field may be added to the inventory without counting it as
particle thermal energy.

The classical path rejects a materially relativistic temperature. For a
relativistic, non-Maxwellian, degenerate, strongly coupled, or otherwise
non-ideal plasma, supply `mean_kinetic_energy_ev_per_particle` and a matching
`kinetic_exergy_factor` from an appropriate distribution model, or supply the
total plasma quantity and factor. Collective modes, sheaths, interaction
energy, chemical potential, trapped radiation, and fusion reactions are not
silently inferred.

## Thermal and nonthermal radiation

Blackbody radiation uses the Petela factor and includes ambient
counter-radiation through its declared source and reference temperatures.
Coherent radiation can be declared work-equivalent at its receiving boundary.

For an externally evaluated spectrum or measured net radiation transfer, supply
energy and entropy crossing the same boundary over the same interval:

```text
X = E - T0 S
```

```json
{
  "stream_type": "radiation",
  "quantity": 1,
  "unit": "kWh_rad",
  "radiation_model": "spectral_entropy",
  "radiation_entropy_j_k": 3600,
  "reference_temperature_k": 300
}
```

This entropy path accommodates non-blackbody thermonuclear photon spectra
without labeling neutron energy as radiation. The supplied energy and entropy
must describe the same net transfer; otherwise the calculated factor is not a
valid boundary property.

## Model and data sources

- [NIST 2022 CODATA constants](https://physics.nist.gov/cuu/Constants/index.html)
- [NIST electromagnetic energy density in dispersive and dissipative media](https://www.nist.gov/publications/electromagnetic-energy-density-dispersive-and-dissipative-media)
- [NRL Plasma Formulary](https://www.nrl.navy.mil/News-Media/Publications/NRL-PlasmaFormulary/)
- [IAEA Fusion Physics](https://www-pub.iaea.org/MTCD/Publications/PDF/Pub1562_web.pdf)
- [IAEA D–T product-energy reference](https://conferences.iaea.org/event/214/contributions/17398/)
- [IAEA nuclear data services](https://www-nds.iaea.org/)

The numerical constants are the 2022 CODATA values exposed by NIST. The D–T
preset intentionally uses the customary rounded 14.1 + 3.5 = 17.6 MeV product
accounting. Higher-precision reaction work should use a matching evaluated
mass/Q-value source and record its convention.
