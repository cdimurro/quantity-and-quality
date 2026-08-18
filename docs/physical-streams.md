# Physical stream calculations

The calculator uses a small number of physical models rather than creating a
different thermodynamic rule for every technology. Wind, water in motion,
shafts, vehicles, and flywheels are mechanical. Steam, compressed air,
refrigerants, geothermal fluids, and cryogens are fluid states. Biomass,
biogas, batteries, and synthetic fuels are chemical internally and are reported
at the carrier that crosses the selected boundary.

Every request can be sent unchanged to `calculate_stream()`,
`quantity-quality calculate`, or `POST /v1/calculate`.

## Mechanical and electrical work

Mechanical modes are:

- shaft: `torque_nm`, `rotational_speed_rpm`, and `duration_hours`;
- kinetic: mass and velocity relative to an explicit velocity datum;
- gravitational: mass and height difference;
- rotational: moment of inertia and rotational speed;
- elastic: spring constant and displacement; and
- hydraulic: pressure difference and liquid volume or volume flow.

The equations are respectively `tau omega dt`, `m(v²-v0²)/2`, `mg dz`,
`I(omega²-omega0²)/2`, `k(x²-x0²)/2`, and `delta-p V`. The last expression is
for effectively incompressible hydraulic work. It is not used for compressed
gas inventories.

Electrical quantity can be supplied directly, calculated from power and time,
or calculated from voltage and current. DC and single-phase AC use `V I`; a
balanced three-phase system uses `sqrt(3) V_line I_line PF`. Capacitor,
inductor, and battery-throughput paths use `CV²/2`, `LI²/2`, and measured
average terminal voltage times ampere-hours.

Mechanical and electrical work have `fx = 1` at their work-transfer boundary.
Conversion losses belong to the process that produced or consumed the work.

```json
{
  "stream_type": "mechanical",
  "mechanical_mode": "shaft",
  "torque_nm": 500,
  "rotational_speed_rpm": 1800,
  "duration_hours": 2
}
```

## Fluids, steam, refrigerants, and compressed gases

The specific physical flow exergy of a nonreacting fluid is

```text
x = (h - h0) - T0 (s - s0) + (v² - v0²)/2 + g(z-z0)
```

The dependency-free path accepts supplied enthalpy and entropy. This allows
licensed or site-standard property systems, including NIST REFPROP, to provide
the properties without coupling their license to this package.

The optional fluid backend provides water, steam, air, refrigerants, brines,
cryogens, pure fluids, and supported mixtures through CoolProp:

```bash
python -m pip install "quantity-and-quality[fluids]"
```

Every result records the backend and exact version. A single state is reported
as reversible physical work potential in a mechanical work-equivalent unit. A
two-state request can instead report the inlet-to-outlet enthalpy decrease as
the energy quantity and the physical-exergy decrease as its quality:

```json
{
  "stream_type": "fluid",
  "fluid": "Water",
  "mass": 1000,
  "inlet_pressure_pa": 1000000,
  "inlet_vapor_quality": 1,
  "outlet_pressure_pa": 1000000,
  "outlet_vapor_quality": 0,
  "reported_energy_basis": "enthalpy_change",
  "reference_temperature_c": 20,
  "reference_pressure_pa": 101325
}
```

Pressure alone does not define a steam state. Supply temperature and pressure,
pressure and vapor quality, or temperature and vapor quality. Generic latent
heat is also available when measured mass, latent heat, and phase-change
temperature are already known. Do not use `m cp delta-T` across a phase change.

The `ideal_gas` model is a transparent constant-heat-capacity approximation for
screening compressed-gas states. Use the fluid backend or supplied measured
properties when real-gas effects matter.

## Humid air

Humid air uses the Wepfer ideal-mixture expression, including temperature,
pressure, and water-vapor composition relative to an explicitly declared
ambient humidity state. Humidity ratios can be supplied directly. Relative
humidity is converted with the optional CoolProp humid-air backend.

The result is physical and composition work potential per kg of dry air. It can
represent the state burden behind heating, cooling, humidification, drying, and
dehumidification without pretending that relative humidity is itself an energy
unit.

## Biomass, bioenergy, and chemical mixtures

Biomass and bioenergy are supported, but they deliberately have no universal
factor. Wood, crop residue, municipal waste, biogas, syngas, and blended liquid
biofuels vary with moisture, ash, composition, and measurement basis.

A defensible request supplies one of:

- measured heating value plus chemical exergy and matching denominator;
- a mass-fraction component analysis with heating value and chemical exergy for
  every component; or
- an explicitly sourced `fx`.

```json
{
  "stream_type": "biomass",
  "mass": 1000,
  "mass_unit": "kg",
  "heating_value": 18,
  "heating_value_unit": "MJ/kg",
  "basis": "LHV",
  "chemical_exergy": 19,
  "energy_basis_value": 18,
  "quality_basis_unit": "MJ/kg as received",
  "feedstock_class": "declared biomass feedstock",
  "property_source": "caller-supplied matching-basis analysis"
}
```

`chemical_exergy` and `energy_basis_value` must use the same unit and material
basis. `feedstock_class`, moisture, ash, and the property source are retained as
metadata when supplied. Once biomass has been converted, report its output by
the form crossing the boundary—for example, electricity, heat, shaft work, or
biogas—rather than continuing to call every downstream stream "bioenergy."

Dry-basis heating values can be applied to calculated dry matter with
`moisture_fraction`, but the result warns that measured as-received heating
value is preferred. Component-weighted mixtures explicitly warn that non-ideal
mixing exergy is excluded.

## Radiation, electromagnetic fields, plasma, and nuclear energy

Generic blackbody radiation uses the Petela factor with a declared source and
reference temperature. Coherent or otherwise work-equivalent radiation can be
declared at its delivery boundary. Externally evaluated radiation energy and
entropy can use `X = E - T0 S`. Solar remains a separate convenient alias with
the solar-source model.

Stored electromagnetic fields can be integrated over uniform volumes or a cell
map. Transmitted field energy can use measured normal Poynting flux or an RMS
plane-wave electric field. These are `_em` streams; incoherent photons are
`_rad`, while neutrons and charged particles retain particle carriers.

Ideal-gas separation uses the reversible Gibbs mixing work
`-n R T sum(y_i ln y_i)`. Non-ideal solutions, seawater, and reactive separation
should supply a validated Gibbs/free-energy result from the appropriate
property model.

Nuclear inventory quantity can be calculated from a mass defect or from isotope
mass, atomic mass, energy per fission, and fissioned fraction. The calculator
never assumes how much inventory is accessible: `accessible_fraction` is
required. Reaction mode instead calculates released energy from a Q-value and
event count, partitions it into named product channels, and supports a sourced
fusion-reactivity input. The bundled D–T preset keeps its 14.1 MeV neutron and
3.5 MeV alpha products separate.

Plasma inventory accepts separate species counts and temperatures, bulk motion,
supplied ionization/excitation energy, and optional electromagnetic field
energy. Its built-in path is deliberately limited to ideal classical species;
advanced distributions can supply their independently evaluated mean energy and
factor.

See the focused [nuclear, plasma, electromagnetic, and radiation
guide](nuclear-plasma-electromagnetic.md) for equations, examples, provenance
requirements, and model limits. Reactor heat and generated electricity are
reported separately at their actual thermal or electrical boundaries.

## Friction and air resistance

Friction and drag are losses, not energy forms. The calculator supports:

- measured resisting force times distance;
- rolling resistance `Crr N d`; and
- steady quadratic drag `rho Cd A v² d / 2`.

The resulting mechanical work is treated as dissipated heat. The output reports
the residual heat exergy at the declared dissipation temperature and the
destroyed exergy separately. If dissipation occurs at the reference temperature,
the heat remains energy but has `fx = 0`, and all incoming mechanical exergy is
destroyed.

These models assume constant conditions. For changing speed, force, pressure,
or temperature, calculate interval records and sum their energy and exergy.

## Accuracy and provenance

Calculated constants, reference states, property model, backend version,
assumptions, and warnings travel with each record. Exactness is always relative
to the declared model and inputs. A highly accurate equation of state cannot
repair an incorrect pressure basis, unknown composition, unmeasured moisture,
or a boundary that mixes input energy with output energy.

Authoritative property references include the
[IAPWS Industrial Formulation 1997](https://www.iapws.org/relguide/IF97-Rev.pdf),
[NIST REFPROP](https://www.nist.gov/srd/refprop), and the open-source
[CoolProp property library](https://coolprop.org/). Field, plasma, radiation,
and nuclear models use [NIST CODATA](https://physics.nist.gov/cuu/Constants/),
the [NRL Plasma Formulary](https://www.nrl.navy.mil/News-Media/Publications/NRL-PlasmaFormulary/),
and [IAEA Fusion Physics](https://www-pub.iaea.org/MTCD/Publications/PDF/Pub1562_web.pdf).
