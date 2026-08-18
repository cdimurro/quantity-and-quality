"""First-principles quantity and exergy calculations for physical streams.

The functions in this module deliberately return ordinary energy units.  They
do not hide a process efficiency inside a stream factor: mechanical and field
energy is work-equivalent at its transfer boundary, while fluid-state exergy is
always evaluated against an explicit environment.
"""

from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence

from .units import convert_energy

STANDARD_GRAVITY_M_S2 = 9.80665
SPEED_OF_LIGHT_M_S = 299_792_458.0
AVOGADRO_CONSTANT = 6.022_140_76e23
MOLAR_GAS_CONSTANT_J_MOL_K = 8.314_462_618_153_24
BOLTZMANN_CONSTANT_J_K = 1.380_649e-23
ELEMENTARY_CHARGE_C = 1.602_176_634e-19
ATOMIC_MASS_CONSTANT_KG = 1.660_539_068_92e-27
ELECTRON_MASS_KG = 9.109_383_713_9e-31
PROTON_MASS_KG = 1.672_621_925_95e-27
DEUTERON_MASS_KG = 3.343_583_776_8e-27
TRITON_MASS_KG = 5.007_356_751_2e-27
ALPHA_PARTICLE_MASS_KG = 6.644_657_345_0e-27
VACUUM_PERMITTIVITY_F_M = 8.854_187_818_8e-12
VACUUM_PERMEABILITY_H_M = 1.256_637_061_27e-6
VACUUM_IMPEDANCE_OHM = math.sqrt(VACUUM_PERMEABILITY_H_M / VACUUM_PERMITTIVITY_F_M)
PHYSICAL_CONSTANTS_SOURCE = "NIST 2022 CODATA recommended values"

PRESSURE_TO_PA = {
    "pa": 1.0,
    "kpa": 1_000.0,
    "mpa": 1_000_000.0,
    "bar": 100_000.0,
    "mbar": 100.0,
    "atm": 101_325.0,
    "psi": 6_894.757_293_168,
}


class PhysicalCalculationError(ValueError):
    """A stable error for invalid first-principles calculation inputs."""

    def __init__(self, code: str, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict:
        result = {"code": self.code, "message": str(self)}
        if self.field:
            result["field"] = self.field
        return result


def shaft_energy(
    torque_nm: float,
    rotational_speed_rpm: float,
    duration_hours: float,
    *,
    output_unit: str = "kWh_m",
) -> float:
    """Mechanical energy transferred by a shaft at constant torque and speed."""

    torque = _nonnegative(torque_nm, "torque_nm")
    speed = _nonnegative(rotational_speed_rpm, "rotational_speed_rpm")
    duration = _nonnegative(duration_hours, "duration_hours")
    radians_per_second = speed * 2.0 * math.pi / 60.0
    return _joules(torque * radians_per_second * duration * 3600.0, output_unit)


def kinetic_energy(
    mass_kg: float,
    velocity_m_s: float,
    *,
    reference_velocity_m_s: float = 0.0,
    output_unit: str = "kWh_m",
) -> float:
    """Translational kinetic-energy difference relative to a velocity datum."""

    mass = _nonnegative(mass_kg, "mass_kg")
    velocity = _nonnegative(velocity_m_s, "velocity_m_s")
    reference = _nonnegative(reference_velocity_m_s, "reference_velocity_m_s")
    if velocity < reference:
        raise PhysicalCalculationError(
            "invalid_reference",
            "velocity_m_s must be greater than or equal to reference_velocity_m_s",
            field="velocity_m_s",
        )
    return _joules(0.5 * mass * (velocity**2 - reference**2), output_unit)


def gravitational_potential_energy(
    mass_kg: float,
    height_difference_m: float,
    *,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
    output_unit: str = "kWh_m",
) -> float:
    """Gravitational potential-energy difference ``m g dz``."""

    mass = _nonnegative(mass_kg, "mass_kg")
    height = _nonnegative(height_difference_m, "height_difference_m")
    gravity = _positive(gravity_m_s2, "gravity_m_s2")
    return _joules(mass * gravity * height, output_unit)


def rotational_energy(
    moment_of_inertia_kg_m2: float,
    rotational_speed_rpm: float,
    *,
    reference_speed_rpm: float = 0.0,
    output_unit: str = "kWh_m",
) -> float:
    """Rotational kinetic-energy difference ``I (omega^2-omega0^2) / 2``."""

    inertia = _nonnegative(moment_of_inertia_kg_m2, "moment_of_inertia_kg_m2")
    speed = _nonnegative(rotational_speed_rpm, "rotational_speed_rpm")
    reference = _nonnegative(reference_speed_rpm, "reference_speed_rpm")
    if speed < reference:
        raise PhysicalCalculationError(
            "invalid_reference",
            "rotational_speed_rpm must be at least reference_speed_rpm",
            field="rotational_speed_rpm",
        )
    omega = speed * 2.0 * math.pi / 60.0
    omega0 = reference * 2.0 * math.pi / 60.0
    return _joules(0.5 * inertia * (omega**2 - omega0**2), output_unit)


def elastic_energy(
    spring_constant_n_m: float,
    displacement_m: float,
    *,
    reference_displacement_m: float = 0.0,
    output_unit: str = "kWh_m",
) -> float:
    """Linear-elastic energy difference ``k (x^2-x0^2) / 2``."""

    spring = _nonnegative(spring_constant_n_m, "spring_constant_n_m")
    displacement = _nonnegative(displacement_m, "displacement_m")
    reference = _nonnegative(reference_displacement_m, "reference_displacement_m")
    if displacement < reference:
        raise PhysicalCalculationError(
            "invalid_reference",
            "displacement_m must be at least reference_displacement_m",
            field="displacement_m",
        )
    return _joules(0.5 * spring * (displacement**2 - reference**2), output_unit)


def hydraulic_energy(
    pressure_difference: float,
    volume_m3: float,
    *,
    pressure_unit: str = "Pa",
    output_unit: str = "kWh_m",
) -> float:
    """Boundary work ``delta-p V`` for an effectively incompressible fluid."""

    pressure_pa = pressure_to_pa(pressure_difference, pressure_unit)
    volume = _nonnegative(volume_m3, "volume_m3")
    return _joules(pressure_pa * volume, output_unit)


def electrical_energy(
    voltage_v: float,
    current_a: float,
    duration_hours: float,
    *,
    phase: str = "dc",
    power_factor: float = 1.0,
    output_unit: str = "kWh_e",
) -> float:
    """Electrical energy from DC, single-phase AC, or balanced three-phase AC."""

    voltage = _nonnegative(voltage_v, "voltage_v")
    current = _nonnegative(current_a, "current_a")
    duration = _nonnegative(duration_hours, "duration_hours")
    factor = _finite(power_factor, "power_factor")
    if not 0.0 <= factor <= 1.0:
        raise PhysicalCalculationError(
            "invalid_value", "power_factor must be between 0 and 1", field="power_factor"
        )
    normalized_phase = str(phase).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_phase in {"dc", "single_phase", "single_phase_ac", "ac"}:
        phase_multiplier = 1.0
    elif normalized_phase in {"three_phase", "three_phase_ac", "3_phase", "3ph"}:
        phase_multiplier = math.sqrt(3.0)
    else:
        raise PhysicalCalculationError(
            "unsupported_mode",
            "phase must be dc, single_phase, or three_phase",
            field="phase",
        )
    if normalized_phase == "dc" and not math.isclose(factor, 1.0):
        raise PhysicalCalculationError(
            "invalid_value", "DC calculations require power_factor = 1", field="power_factor"
        )
    joules = phase_multiplier * voltage * current * factor * duration * 3600.0
    return _joules(joules, output_unit)


def capacitor_energy(
    capacitance_f: float,
    voltage_v: float,
    *,
    reference_voltage_v: float = 0.0,
    output_unit: str = "kWh_e",
) -> float:
    """Electrostatic energy difference ``C (V^2-V0^2) / 2``."""

    capacitance = _nonnegative(capacitance_f, "capacitance_f")
    voltage = _nonnegative(voltage_v, "voltage_v")
    reference = _nonnegative(reference_voltage_v, "reference_voltage_v")
    if voltage < reference:
        raise PhysicalCalculationError(
            "invalid_reference",
            "voltage_v must be at least reference_voltage_v",
            field="voltage_v",
        )
    return _joules(0.5 * capacitance * (voltage**2 - reference**2), output_unit)


def inductor_energy(
    inductance_h: float,
    current_a: float,
    *,
    reference_current_a: float = 0.0,
    output_unit: str = "kWh_e",
) -> float:
    """Magnetic-field energy difference ``L (I^2-I0^2) / 2``."""

    inductance = _nonnegative(inductance_h, "inductance_h")
    current = _nonnegative(current_a, "current_a")
    reference = _nonnegative(reference_current_a, "reference_current_a")
    if current < reference:
        raise PhysicalCalculationError(
            "invalid_reference",
            "current_a must be at least reference_current_a",
            field="current_a",
        )
    return _joules(0.5 * inductance * (current**2 - reference**2), output_unit)


def electromagnetic_field_energy(
    volume_m3: float,
    *,
    electric_field_v_m: float = 0.0,
    magnetic_flux_density_t: float = 0.0,
    reference_electric_field_v_m: float = 0.0,
    reference_magnetic_flux_density_t: float = 0.0,
    relative_permittivity: float = 1.0,
    relative_permeability: float = 1.0,
    output_unit: str = "kWh_em",
) -> float:
    """Stored field-energy difference in a linear, isotropic, nondispersive medium.

    The density is ``epsilon E^2/2 + B^2/(2 mu)``. Dispersive, nonlinear,
    anisotropic, hysteretic, or dissipative media require a supplied validated
    constitutive calculation rather than this model.
    """

    volume = _nonnegative(volume_m3, "volume_m3")
    electric = _nonnegative(electric_field_v_m, "electric_field_v_m")
    magnetic = _nonnegative(magnetic_flux_density_t, "magnetic_flux_density_t")
    electric0 = _nonnegative(reference_electric_field_v_m, "reference_electric_field_v_m")
    magnetic0 = _nonnegative(reference_magnetic_flux_density_t, "reference_magnetic_flux_density_t")
    epsilon_r = _positive(relative_permittivity, "relative_permittivity")
    mu_r = _positive(relative_permeability, "relative_permeability")
    density_j_m3 = 0.5 * VACUUM_PERMITTIVITY_F_M * epsilon_r * (electric**2 - electric0**2) + (
        magnetic**2 - magnetic0**2
    ) / (2.0 * VACUUM_PERMEABILITY_H_M * mu_r)
    tolerance = max(1e-18, abs(density_j_m3) * 1e-12)
    if density_j_m3 < -tolerance:
        raise PhysicalCalculationError(
            "state_below_reference",
            "the declared electromagnetic field contains less stored energy than the reference field",
        )
    return _joules(volume * max(0.0, density_j_m3), output_unit)


def electromagnetic_field_map_energy(
    cells: Sequence[Mapping[str, object]],
    *,
    output_unit: str = "kWh_em",
) -> float:
    """Integrate stored electromagnetic energy over piecewise-uniform cells."""

    if not cells:
        raise PhysicalCalculationError(
            "missing_input", "field_cells must contain at least one cell", field="field_cells"
        )
    total_j = 0.0
    for index, cell in enumerate(cells):
        try:
            total_j += electromagnetic_field_energy(
                cell["volume_m3"],
                electric_field_v_m=cell.get("electric_field_v_m", 0.0),
                magnetic_flux_density_t=cell.get("magnetic_flux_density_t", 0.0),
                reference_electric_field_v_m=cell.get("reference_electric_field_v_m", 0.0),
                reference_magnetic_flux_density_t=cell.get(
                    "reference_magnetic_flux_density_t", 0.0
                ),
                relative_permittivity=cell.get("relative_permittivity", 1.0),
                relative_permeability=cell.get("relative_permeability", 1.0),
                output_unit="J_em",
            )
        except (KeyError, TypeError) as exc:
            raise PhysicalCalculationError(
                "invalid_field_map",
                f"field_cells[{index}] must be an object containing volume_m3",
                field="field_cells",
            ) from exc
    return _joules(total_j, output_unit)


def poynting_flux_energy(
    power_flux_density_w_m2: float,
    area_m2: float,
    duration_hours: float,
    *,
    normal_or_capture_factor: float = 1.0,
    output_unit: str = "kWh_em",
) -> float:
    """Energy crossing a surface from measured normal Poynting flux."""

    flux = _nonnegative(power_flux_density_w_m2, "power_flux_density_w_m2")
    area = _nonnegative(area_m2, "area_m2")
    duration = _nonnegative(duration_hours, "duration_hours")
    factor = _fraction(normal_or_capture_factor, "normal_or_capture_factor")
    return _joules(flux * area * factor * duration * 3600.0, output_unit)


def plane_wave_energy(
    electric_field_rms_v_m: float,
    area_m2: float,
    duration_hours: float,
    *,
    wave_impedance_ohm: float = VACUUM_IMPEDANCE_OHM,
    normal_or_capture_factor: float = 1.0,
    output_unit: str = "kWh_em",
) -> float:
    """Energy in a uniform traveling wave from RMS electric-field amplitude."""

    electric_rms = _nonnegative(electric_field_rms_v_m, "electric_field_rms_v_m")
    impedance = _positive(wave_impedance_ohm, "wave_impedance_ohm")
    return poynting_flux_energy(
        electric_rms**2 / impedance,
        area_m2,
        duration_hours,
        normal_or_capture_factor=normal_or_capture_factor,
        output_unit=output_unit,
    )


def battery_energy(
    charge_ah: float,
    average_voltage_v: float,
    *,
    output_unit: str = "kWh_e",
) -> float:
    """Electrical energy from charge throughput and measured average terminal voltage."""

    charge = _nonnegative(charge_ah, "charge_ah")
    voltage = _nonnegative(average_voltage_v, "average_voltage_v")
    return _joules(charge * 3600.0 * voltage, output_unit)


def phase_change_energy(
    mass_kg: float,
    latent_heat_kj_kg: float,
    *,
    output_unit: str = "kWh_th",
) -> float:
    """Latent energy ``m L`` at a declared phase-change state."""

    mass = _nonnegative(mass_kg, "mass_kg")
    latent = _positive(latent_heat_kj_kg, "latent_heat_kj_kg")
    return _joules(mass * latent * 1000.0, output_unit)


def blackbody_radiation_exergy_factor(source_temperature_k: float, reference_k: float) -> float:
    """Petela factor for blackbody radiation at any declared source temperature."""

    source = _positive(source_temperature_k, "source_temperature_k")
    reference = _positive(reference_k, "reference_k")
    if reference > source:
        raise PhysicalCalculationError(
            "invalid_reference",
            "reference_k must not exceed source_temperature_k",
            field="reference_k",
        )
    if reference == source:
        return 0.0
    ratio = reference / source
    return 1.0 - (4.0 / 3.0) * ratio + (1.0 / 3.0) * ratio**4


def ideal_gas_physical_exergy(
    mass_kg: float,
    temperature_k: float,
    pressure_pa: float,
    *,
    reference_temperature_k: float = 293.15,
    reference_pressure_pa: float = 101_325.0,
    cp_j_kg_k: float = 1005.0,
    gas_constant_j_kg_k: float = 287.05,
    velocity_m_s: float = 0.0,
    reference_velocity_m_s: float = 0.0,
    height_difference_m: float = 0.0,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
    output_unit: str = "kWh_m",
) -> float:
    """Physical exergy of a constant-cp ideal gas relative to ``T0,p0``.

    The returned quantity is reversible work potential, so it is reported as a
    mechanical work-equivalent quantity rather than pretending that ``delta-p V``
    describes a compressible gas inventory.
    """

    mass = _nonnegative(mass_kg, "mass_kg")
    temperature = _positive(temperature_k, "temperature_k")
    pressure = _positive(pressure_pa, "pressure_pa")
    t0 = _positive(reference_temperature_k, "reference_temperature_k")
    p0 = _positive(reference_pressure_pa, "reference_pressure_pa")
    cp = _positive(cp_j_kg_k, "cp_j_kg_k")
    gas_constant = _positive(gas_constant_j_kg_k, "gas_constant_j_kg_k")
    velocity = _nonnegative(velocity_m_s, "velocity_m_s")
    v0 = _nonnegative(reference_velocity_m_s, "reference_velocity_m_s")
    height = _finite(height_difference_m, "height_difference_m")
    gravity = _positive(gravity_m_s2, "gravity_m_s2")
    specific = (
        cp * ((temperature - t0) - t0 * math.log(temperature / t0))
        + gas_constant * t0 * math.log(pressure / p0)
        + 0.5 * (velocity**2 - v0**2)
        + gravity * height
    )
    if specific < -1e-9:
        raise PhysicalCalculationError(
            "state_below_reference",
            "the declared ideal-gas state has negative source exergy relative to the reference",
        )
    return _joules(mass * max(0.0, specific), output_unit)


def physical_exergy_from_properties(
    mass_kg: float,
    enthalpy_kj_kg: float,
    entropy_kj_kg_k: float,
    reference_enthalpy_kj_kg: float,
    reference_entropy_kj_kg_k: float,
    reference_temperature_k: float,
    *,
    velocity_m_s: float = 0.0,
    reference_velocity_m_s: float = 0.0,
    height_difference_m: float = 0.0,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
    output_unit: str = "kWh_m",
) -> float:
    """Physical flow exergy from externally supplied ``h`` and ``s`` values."""

    mass = _nonnegative(mass_kg, "mass_kg")
    enthalpy = _finite(enthalpy_kj_kg, "enthalpy_kj_kg")
    entropy = _finite(entropy_kj_kg_k, "entropy_kj_kg_k")
    h0 = _finite(reference_enthalpy_kj_kg, "reference_enthalpy_kj_kg")
    s0 = _finite(reference_entropy_kj_kg_k, "reference_entropy_kj_kg_k")
    t0 = _positive(reference_temperature_k, "reference_temperature_k")
    velocity = _nonnegative(velocity_m_s, "velocity_m_s")
    v0 = _nonnegative(reference_velocity_m_s, "reference_velocity_m_s")
    height = _finite(height_difference_m, "height_difference_m")
    gravity = _positive(gravity_m_s2, "gravity_m_s2")
    specific_kj_kg = (enthalpy - h0) - t0 * (entropy - s0)
    specific_j_kg = specific_kj_kg * 1000.0 + 0.5 * (velocity**2 - v0**2) + gravity * height
    if specific_j_kg < -1e-6:
        raise PhysicalCalculationError(
            "state_below_reference",
            "the supplied state properties give negative physical exergy relative to the reference",
        )
    return _joules(mass * max(0.0, specific_j_kg), output_unit)


def fluid_physical_exergy(
    fluid: str,
    mass_kg: float,
    *,
    temperature_c: Optional[float] = None,
    pressure_pa: Optional[float] = None,
    vapor_quality: Optional[float] = None,
    reference_temperature_c: float = 20.0,
    reference_pressure_pa: float = 101_325.0,
    velocity_m_s: float = 0.0,
    reference_velocity_m_s: float = 0.0,
    height_difference_m: float = 0.0,
    output_unit: str = "kWh_m",
) -> dict:
    """Physical exergy from a CoolProp state, with backend provenance returned.

    CoolProp is optional so the dependency-free reporting interface stays light.
    Install ``quantity-and-quality[fluids]`` to enable this path.
    """

    try:
        import CoolProp  # type: ignore
        from CoolProp.CoolProp import PropsSI  # type: ignore
    except ImportError as exc:
        raise PhysicalCalculationError(
            "missing_optional_dependency",
            "fluid-state calculations require: pip install quantity-and-quality[fluids]",
            field="fluid",
        ) from exc

    name = str(fluid).strip()
    if not name:
        raise PhysicalCalculationError("missing_input", "fluid is required", field="fluid")
    inputs = _coolprop_inputs(temperature_c, pressure_pa, vapor_quality)
    try:
        enthalpy = float(PropsSI("Hmass", *inputs, name)) / 1000.0
        entropy = float(PropsSI("Smass", *inputs, name)) / 1000.0
        h0 = (
            float(
                PropsSI(
                    "Hmass",
                    "T",
                    _c_to_k(reference_temperature_c, "reference_temperature_c"),
                    "P",
                    _positive(reference_pressure_pa, "reference_pressure_pa"),
                    name,
                )
            )
            / 1000.0
        )
        s0 = (
            float(
                PropsSI(
                    "Smass",
                    "T",
                    _c_to_k(reference_temperature_c, "reference_temperature_c"),
                    "P",
                    _positive(reference_pressure_pa, "reference_pressure_pa"),
                    name,
                )
            )
            / 1000.0
        )
    except Exception as exc:
        raise PhysicalCalculationError(
            "invalid_fluid_state",
            f"CoolProp could not evaluate the declared {name} state: {exc}",
            field="fluid",
        ) from exc
    quantity = physical_exergy_from_properties(
        mass_kg,
        enthalpy,
        entropy,
        h0,
        s0,
        reference_temperature_c + 273.15,
        velocity_m_s=velocity_m_s,
        reference_velocity_m_s=reference_velocity_m_s,
        height_difference_m=height_difference_m,
        output_unit=output_unit,
    )
    return {
        "quantity": quantity,
        "unit": output_unit,
        "exergy_factor": 1.0,
        "fluid": name,
        "enthalpy_kj_kg": enthalpy,
        "entropy_kj_kg_k": entropy,
        "reference_enthalpy_kj_kg": h0,
        "reference_entropy_kj_kg_k": s0,
        "reference_temperature_c": reference_temperature_c,
        "reference_pressure_pa": reference_pressure_pa,
        "property_backend": "CoolProp",
        "property_backend_version": str(CoolProp.__version__),
        "energy_basis": "reversible physical work potential relative to the declared environment",
    }


def fluid_state_change_exergy(
    fluid: str,
    mass_kg: float,
    *,
    inlet_temperature_c: Optional[float] = None,
    inlet_pressure_pa: Optional[float] = None,
    inlet_vapor_quality: Optional[float] = None,
    outlet_temperature_c: Optional[float] = None,
    outlet_pressure_pa: Optional[float] = None,
    outlet_vapor_quality: Optional[float] = None,
    reference_temperature_c: float = 20.0,
    reference_pressure_pa: float = 101_325.0,
    output_unit: str = "kWh",
) -> dict:
    """Energy and physical-exergy decrease between two CoolProp fluid states."""

    inlet = fluid_physical_exergy(
        fluid,
        mass_kg,
        temperature_c=inlet_temperature_c,
        pressure_pa=inlet_pressure_pa,
        vapor_quality=inlet_vapor_quality,
        reference_temperature_c=reference_temperature_c,
        reference_pressure_pa=reference_pressure_pa,
        output_unit=output_unit,
    )
    outlet = fluid_physical_exergy(
        fluid,
        mass_kg,
        temperature_c=outlet_temperature_c,
        pressure_pa=outlet_pressure_pa,
        vapor_quality=outlet_vapor_quality,
        reference_temperature_c=reference_temperature_c,
        reference_pressure_pa=reference_pressure_pa,
        output_unit=output_unit,
    )
    exergy_change = inlet["quantity"] - outlet["quantity"]
    tolerance = max(1e-12, abs(inlet["quantity"]) * 1e-12)
    if exergy_change < -tolerance:
        raise PhysicalCalculationError(
            "invalid_state_order",
            "outlet physical exergy exceeds inlet physical exergy; reverse the states or model the required input",
            field="outlet_temperature_c",
        )
    exergy_change = max(0.0, exergy_change)
    enthalpy_change_kj = mass_kg * (inlet["enthalpy_kj_kg"] - outlet["enthalpy_kj_kg"])
    enthalpy_change = convert_energy(enthalpy_change_kj, "kJ", output_unit)
    return {
        "physical_exergy_change": exergy_change,
        "enthalpy_change": enthalpy_change,
        "unit": output_unit,
        "inlet": {
            "enthalpy_kj_kg": inlet["enthalpy_kj_kg"],
            "entropy_kj_kg_k": inlet["entropy_kj_kg_k"],
        },
        "outlet": {
            "enthalpy_kj_kg": outlet["enthalpy_kj_kg"],
            "entropy_kj_kg_k": outlet["entropy_kj_kg_k"],
        },
        "property_backend": inlet["property_backend"],
        "property_backend_version": inlet["property_backend_version"],
        "reference_temperature_c": reference_temperature_c,
        "reference_pressure_pa": reference_pressure_pa,
    }


def ideal_mixture_separation_energy(
    amount_mol: float,
    mole_fractions: Sequence[float],
    temperature_k: float,
    *,
    output_unit: str = "kWh_m",
) -> float:
    """Minimum reversible work to separate an ideal-gas mixture into pure species."""

    amount = _nonnegative(amount_mol, "amount_mol")
    temperature = _positive(temperature_k, "temperature_k")
    fractions = [_nonnegative(value, "mole_fractions") for value in mole_fractions]
    if len(fractions) < 2:
        raise PhysicalCalculationError(
            "invalid_composition",
            "at least two mole fractions are required",
            field="mole_fractions",
        )
    total = sum(fractions)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise PhysicalCalculationError(
            "invalid_composition", "mole_fractions must sum to 1", field="mole_fractions"
        )
    mixing_sum = sum(value * math.log(value) for value in fractions if value > 0.0)
    joules = -amount * MOLAR_GAS_CONSTANT_J_MOL_K * temperature * mixing_sum
    return _joules(joules, output_unit)


def humid_air_physical_exergy(
    dry_air_mass_kg: float,
    temperature_k: float,
    pressure_pa: float,
    humidity_ratio: float,
    *,
    reference_temperature_k: float = 293.15,
    reference_pressure_pa: float = 101_325.0,
    reference_humidity_ratio: float = 0.007261,
    dry_air_cp_j_kg_k: float = 1006.0,
    water_vapor_cp_j_kg_k: float = 1860.0,
    dry_air_gas_constant_j_kg_k: float = 287.055,
    output_unit: str = "kWh_m",
) -> float:
    """Total ideal-mixture flow exergy of humid air per Wepfer's model.

    Humidity ratios are kg water vapor per kg dry air.  The model contains the
    thermal, pressure, and composition difference from the declared ambient
    state, so humidity is not treated as an unexplained correction factor.
    """

    mass = _nonnegative(dry_air_mass_kg, "dry_air_mass_kg")
    temperature = _positive(temperature_k, "temperature_k")
    pressure = _positive(pressure_pa, "pressure_pa")
    humidity = _nonnegative(humidity_ratio, "humidity_ratio")
    t0 = _positive(reference_temperature_k, "reference_temperature_k")
    p0 = _positive(reference_pressure_pa, "reference_pressure_pa")
    humidity0 = _positive(reference_humidity_ratio, "reference_humidity_ratio")
    cp_air = _positive(dry_air_cp_j_kg_k, "dry_air_cp_j_kg_k")
    cp_vapor = _positive(water_vapor_cp_j_kg_k, "water_vapor_cp_j_kg_k")
    gas_constant = _positive(dry_air_gas_constant_j_kg_k, "dry_air_gas_constant_j_kg_k")
    molal_humidity = 1.6078 * humidity
    molal_humidity0 = 1.6078 * humidity0
    thermal = (
        (cp_air + humidity * cp_vapor) * t0 * (temperature / t0 - 1.0 - math.log(temperature / t0))
    )
    pressure_term = (1.0 + molal_humidity) * gas_constant * t0 * math.log(pressure / p0)
    composition = (1.0 + molal_humidity) * math.log(
        (1.0 + molal_humidity0) / (1.0 + molal_humidity)
    )
    if molal_humidity > 0.0:
        composition += molal_humidity * math.log(molal_humidity / molal_humidity0)
    specific = thermal + pressure_term + gas_constant * t0 * composition
    if specific < -1e-6:
        raise PhysicalCalculationError(
            "state_below_reference",
            "the humid-air source state has negative flow exergy relative to the declared reference",
        )
    return _joules(mass * max(0.0, specific), output_unit)


def humid_air_humidity_ratio(
    temperature_c: float,
    pressure_pa: float,
    relative_humidity: float,
) -> dict:
    """Humidity ratio from a CoolProp psychrometric state with provenance."""

    try:
        import CoolProp  # type: ignore
        from CoolProp.HumidAirProp import HAPropsSI  # type: ignore
    except ImportError as exc:
        raise PhysicalCalculationError(
            "missing_optional_dependency",
            "relative-humidity calculations require: pip install quantity-and-quality[fluids]",
        ) from exc
    temperature_k = _c_to_k(temperature_c, "temperature_c")
    pressure = _positive(pressure_pa, "pressure_pa")
    relative = _finite(relative_humidity, "relative_humidity")
    if not 0.0 <= relative <= 1.0:
        raise PhysicalCalculationError(
            "invalid_value",
            "relative_humidity must be a fraction between 0 and 1",
            field="relative_humidity",
        )
    try:
        ratio = float(HAPropsSI("W", "T", temperature_k, "P", pressure, "R", relative))
    except Exception as exc:
        raise PhysicalCalculationError(
            "invalid_humid_air_state",
            f"CoolProp could not evaluate the declared humid-air state: {exc}",
        ) from exc
    return {
        "humidity_ratio": ratio,
        "property_backend": "CoolProp humid air",
        "property_backend_version": str(CoolProp.__version__),
    }


def chemical_mixture_properties(components: Sequence[Mapping[str, object]]) -> dict:
    """Energy basis and chemical exergy of a mass-fraction mixture.

    Component heating values and chemical exergies must be supplied in matching
    MJ/kg units.  This avoids inventing accuracy for heterogeneous fuels such as
    biomass, waste, biogas, and commodity natural-gas blends.
    """

    if not components:
        raise PhysicalCalculationError(
            "missing_input", "components must contain at least one component", field="components"
        )
    mass_fraction_sum = 0.0
    heating_value = 0.0
    chemical_exergy = 0.0
    normalized = []
    for index, component in enumerate(components):
        try:
            fraction = _nonnegative(
                component["mass_fraction"], f"components[{index}].mass_fraction"
            )
            hv = _nonnegative(
                component["heating_value_mj_kg"],
                f"components[{index}].heating_value_mj_kg",
            )
            exergy = _nonnegative(
                component["chemical_exergy_mj_kg"],
                f"components[{index}].chemical_exergy_mj_kg",
            )
        except KeyError as exc:
            raise PhysicalCalculationError(
                "missing_input",
                f"components[{index}] requires mass_fraction, heating_value_mj_kg, and chemical_exergy_mj_kg",
                field="components",
            ) from exc
        mass_fraction_sum += fraction
        heating_value += fraction * hv
        chemical_exergy += fraction * exergy
        normalized.append(
            {
                "name": str(component.get("name", f"component-{index + 1}")),
                "mass_fraction": fraction,
                "heating_value_mj_kg": hv,
                "chemical_exergy_mj_kg": exergy,
            }
        )
    if not math.isclose(mass_fraction_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise PhysicalCalculationError(
            "invalid_composition", "component mass fractions must sum to 1", field="components"
        )
    if heating_value <= 0.0:
        raise PhysicalCalculationError(
            "invalid_composition", "mixture heating value must be positive", field="components"
        )
    return {
        "heating_value_mj_kg": heating_value,
        "chemical_exergy_mj_kg": chemical_exergy,
        "exergy_factor": chemical_exergy / heating_value,
        "components": normalized,
        "mixing_model": "mass-weighted supplied component properties; mixing exergy excluded",
    }


def radiation_exergy_from_energy_entropy(
    energy: float,
    energy_unit: str,
    entropy_j_k: float,
    reference_temperature_k: float,
    *,
    output_unit: str = "kWh_ex",
) -> dict:
    """Exergy of a declared net radiation transfer from its energy and entropy.

    The caller must provide energy and entropy crossing the same boundary over
    the same interval. For a net transfer, ``X = E - T0 S``. A blackbody source
    and environment should use the Petela model instead, which includes ambient
    counter-radiation explicitly.
    """

    energy_j = convert_energy(_positive(energy, "energy"), energy_unit, "J")
    entropy = _nonnegative(entropy_j_k, "entropy_j_k")
    reference = _positive(reference_temperature_k, "reference_temperature_k")
    exergy_j = energy_j - reference * entropy
    tolerance = max(1e-9, energy_j * 1e-12)
    if exergy_j < -tolerance:
        raise PhysicalCalculationError(
            "invalid_radiation_entropy",
            "T0 times radiation entropy exceeds the declared net radiation energy",
            field="entropy_j_k",
        )
    if exergy_j > energy_j + tolerance:
        raise PhysicalCalculationError(
            "invalid_radiation_entropy",
            "declared radiation entropy would make exergy exceed net radiation energy",
            field="entropy_j_k",
        )
    exergy_j = min(energy_j, max(0.0, exergy_j))
    return {
        "energy": convert_energy(energy_j, "J", output_unit.replace("_ex", "")),
        "exergy": convert_energy(exergy_j, "J", output_unit),
        "exergy_factor": exergy_j / energy_j,
        "entropy_j_k": entropy,
        "reference_temperature_k": reference,
    }


def nuclear_reaction_q_value_mev(
    reactant_atomic_masses_u: Sequence[float],
    product_atomic_masses_u: Sequence[float],
) -> float:
    """Reaction Q-value from matching atomic or nuclear rest-mass conventions."""

    if not reactant_atomic_masses_u or not product_atomic_masses_u:
        raise PhysicalCalculationError(
            "missing_input",
            "reactant_atomic_masses_u and product_atomic_masses_u must be non-empty",
        )
    reactants = sum(
        _positive(value, "reactant_atomic_masses_u") for value in reactant_atomic_masses_u
    )
    products = sum(_positive(value, "product_atomic_masses_u") for value in product_atomic_masses_u)
    mass_defect_u = reactants - products
    if mass_defect_u <= 0.0:
        raise PhysicalCalculationError(
            "non_exoergic_reaction",
            "reactant rest mass must exceed product rest mass for positive released energy",
        )
    joules = mass_defect_u * ATOMIC_MASS_CONSTANT_KG * SPEED_OF_LIGHT_M_S**2
    return joules / (1.0e6 * ELEMENTARY_CHARGE_C)


def nuclear_reaction_energy(
    reaction_count: float,
    q_value_mev: float,
    *,
    output_unit: str = "MWh_nuclear",
) -> float:
    """Released reaction energy from event count and Q-value."""

    reactions = _nonnegative(reaction_count, "reaction_count")
    q_value = _positive(q_value_mev, "q_value_mev")
    joules = reactions * q_value * 1.0e6 * ELEMENTARY_CHARGE_C
    return _joules(joules, output_unit)


def fusion_reaction_count(
    reactant_1_number_density_m3: float,
    reactant_2_number_density_m3: float,
    reactivity_m3_s: float,
    volume_m3: float,
    duration_seconds: float,
    *,
    identical_reactants: bool = False,
) -> float:
    """Fusion-event count from densities and supplied Maxwellian-averaged reactivity."""

    density_1 = _nonnegative(reactant_1_number_density_m3, "reactant_1_number_density_m3")
    density_2 = _nonnegative(reactant_2_number_density_m3, "reactant_2_number_density_m3")
    reactivity = _nonnegative(reactivity_m3_s, "reactivity_m3_s")
    volume = _nonnegative(volume_m3, "volume_m3")
    duration = _nonnegative(duration_seconds, "duration_seconds")
    if identical_reactants and not math.isclose(density_1, density_2, rel_tol=1e-12, abs_tol=0.0):
        raise PhysicalCalculationError(
            "inconsistent_reactants",
            "identical_reactants requires equal reactant number densities; use one species density for both inputs",
            field="identical_reactants",
        )
    symmetry = 0.5 if identical_reactants else 1.0
    return symmetry * density_1 * density_2 * reactivity * volume * duration


def plasma_species_energy(
    species: Sequence[Mapping[str, object]],
    volume_m3: float,
    *,
    reference_temperature_k: float = 293.15,
    output_unit: str = "kWh_plasma",
) -> dict:
    """Energy and constrained exergy of ideal plasma species.

    Maxwellian species use the classical translational energy ``f N k T / 2``
    and constant-volume availability relative to ``T0``. A supplied mean kinetic
    energy path accommodates non-Maxwellian or relativistic distributions but
    requires a matching exergy factor. Ionization/excitation energy similarly
    requires a caller-supplied factor because its recoverable work depends on the
    reference composition and relaxation path.
    """

    if not species:
        raise PhysicalCalculationError(
            "missing_input",
            "plasma_species must contain at least one species",
            field="plasma_species",
        )
    volume = _positive(volume_m3, "volume_m3")
    reference = _positive(reference_temperature_k, "reference_temperature_k")
    total_energy_j = 0.0
    total_exergy_j = 0.0
    components = []
    warnings = []
    for index, component in enumerate(species):
        if not isinstance(component, Mapping):
            raise PhysicalCalculationError(
                "invalid_plasma_species",
                f"plasma_species[{index}] must be an object",
                field="plasma_species",
            )
        name = str(component.get("name", f"species-{index + 1}"))
        has_count = component.get("particle_count") is not None
        has_density = component.get("number_density_m3") is not None
        if has_count == has_density:
            raise PhysicalCalculationError(
                "conflicting_inputs",
                f"plasma_species[{index}] requires exactly one of particle_count or number_density_m3",
                field="plasma_species",
            )
        count = (
            _nonnegative(component["particle_count"], f"plasma_species[{index}].particle_count")
            if has_count
            else _nonnegative(
                component["number_density_m3"],
                f"plasma_species[{index}].number_density_m3",
            )
            * volume
        )
        has_temperature = (
            component.get("temperature_k") is not None
            or component.get("temperature_ev") is not None
        )
        has_mean_energy = component.get("mean_kinetic_energy_ev_per_particle") is not None
        if has_temperature == has_mean_energy:
            raise PhysicalCalculationError(
                "conflicting_inputs",
                f"plasma_species[{index}] requires a temperature or mean_kinetic_energy_ev_per_particle, but not both",
                field="plasma_species",
            )
        if (
            component.get("temperature_k") is not None
            and component.get("temperature_ev") is not None
        ):
            raise PhysicalCalculationError(
                "conflicting_inputs",
                f"plasma_species[{index}] cannot provide both temperature_k and temperature_ev",
                field="plasma_species",
            )

        distribution = "supplied_mean_kinetic_energy"
        if has_temperature:
            if component.get("kinetic_exergy_factor") is not None:
                raise PhysicalCalculationError(
                    "conflicting_inputs",
                    f"plasma_species[{index}] kinetic_exergy_factor is only valid with a supplied mean kinetic energy",
                    field="plasma_species",
                )
            temperature = (
                _positive(component["temperature_k"], f"plasma_species[{index}].temperature_k")
                if component.get("temperature_k") is not None
                else _positive(
                    component["temperature_ev"],
                    f"plasma_species[{index}].temperature_ev",
                )
                * ELEMENTARY_CHARGE_C
                / BOLTZMANN_CONSTANT_J_K
            )
            degrees = _positive(
                component.get("degrees_of_freedom", 3.0),
                f"plasma_species[{index}].degrees_of_freedom",
            )
            thermal_j = 0.5 * degrees * count * BOLTZMANN_CONSTANT_J_K * temperature
            thermal_exergy_j = (
                0.5
                * degrees
                * count
                * BOLTZMANN_CONSTANT_J_K
                * ((temperature - reference) - reference * math.log(temperature / reference))
            )
            distribution = "classical_maxwellian"
            particle_mass = _plasma_particle_mass(component, name)
            if particle_mass is not None:
                relativistic_ratio = (
                    BOLTZMANN_CONSTANT_J_K * temperature / (particle_mass * SPEED_OF_LIGHT_M_S**2)
                )
                if relativistic_ratio >= 0.1:
                    raise PhysicalCalculationError(
                        "relativistic_plasma",
                        f"plasma_species[{index}] is outside the nonrelativistic Maxwellian model; supply mean_kinetic_energy_ev_per_particle and kinetic_exergy_factor from a relativistic distribution model",
                        field="plasma_species",
                    )
                if relativistic_ratio >= 0.01:
                    warnings.append(
                        f"{name}: relativistic corrections may be material; use a supplied distribution mean for precision work"
                    )
        else:
            mean_ev = _nonnegative(
                component["mean_kinetic_energy_ev_per_particle"],
                f"plasma_species[{index}].mean_kinetic_energy_ev_per_particle",
            )
            thermal_j = count * mean_ev * ELEMENTARY_CHARGE_C
            if component.get("kinetic_exergy_factor") is None:
                raise PhysicalCalculationError(
                    "missing_input",
                    f"plasma_species[{index}] requires kinetic_exergy_factor with a supplied mean kinetic energy",
                    field="plasma_species",
                )
            thermal_factor = _nonnegative(
                component["kinetic_exergy_factor"],
                f"plasma_species[{index}].kinetic_exergy_factor",
            )
            thermal_exergy_j = thermal_j * thermal_factor

        particle_mass = _plasma_particle_mass(component, name)
        velocity = _nonnegative(
            component.get("bulk_velocity_m_s", 0.0),
            f"plasma_species[{index}].bulk_velocity_m_s",
        )
        reference_velocity = _nonnegative(
            component.get("reference_bulk_velocity_m_s", 0.0),
            f"plasma_species[{index}].reference_bulk_velocity_m_s",
        )
        if velocity < reference_velocity:
            raise PhysicalCalculationError(
                "invalid_reference",
                f"plasma_species[{index}] bulk velocity must not be below its reference velocity",
                field="plasma_species",
            )
        if velocity and particle_mass is None:
            raise PhysicalCalculationError(
                "missing_input",
                f"plasma_species[{index}] requires particle_mass_kg for bulk kinetic energy",
                field="plasma_species",
            )
        if particle_mass is not None:
            speed_ratio = velocity / SPEED_OF_LIGHT_M_S
            if speed_ratio >= 0.1:
                raise PhysicalCalculationError(
                    "relativistic_plasma",
                    f"plasma_species[{index}] bulk motion is outside the nonrelativistic kinetic-energy model",
                    field="plasma_species",
                )
            if speed_ratio >= 0.03:
                warnings.append(
                    f"{name}: relativistic corrections may be material for the declared bulk velocity"
                )
        bulk_j = (
            0.5 * count * particle_mass * (velocity**2 - reference_velocity**2)
            if particle_mass is not None
            else 0.0
        )
        internal_ev = _nonnegative(
            component.get("internal_energy_ev_per_particle", 0.0),
            f"plasma_species[{index}].internal_energy_ev_per_particle",
        )
        internal_j = count * internal_ev * ELEMENTARY_CHARGE_C
        if internal_j and component.get("internal_exergy_factor") is None:
            raise PhysicalCalculationError(
                "missing_input",
                f"plasma_species[{index}] requires internal_exergy_factor for ionization/excitation energy",
                field="plasma_species",
            )
        internal_factor = _nonnegative(
            component.get("internal_exergy_factor", 0.0),
            f"plasma_species[{index}].internal_exergy_factor",
        )
        charge_state = (
            _finite(component["charge_state"], f"plasma_species[{index}].charge_state")
            if component.get("charge_state") is not None
            else None
        )
        species_energy_j = thermal_j + bulk_j + internal_j
        species_exergy_j = thermal_exergy_j + bulk_j + internal_j * internal_factor
        total_energy_j += species_energy_j
        total_exergy_j += species_exergy_j
        components.append(
            {
                "name": name,
                "particle_count": count,
                "distribution_model": distribution,
                "thermal_or_random_energy_j": thermal_j,
                "thermal_or_random_exergy_j": thermal_exergy_j,
                "bulk_kinetic_energy_j": bulk_j,
                "internal_energy_j": internal_j,
                "internal_exergy_j": internal_j * internal_factor,
                "charge_state": charge_state,
                "particle_mass_kg": particle_mass,
            }
        )
    factor = 0.0 if total_energy_j == 0.0 else total_exergy_j / total_energy_j
    return {
        "energy": _joules(total_energy_j, output_unit),
        "exergy": _joules(total_exergy_j, output_unit),
        "exergy_factor": factor,
        "energy_j": total_energy_j,
        "exergy_j": total_exergy_j,
        "reference_temperature_k": reference,
        "volume_m3": volume,
        "species": components,
        "warnings": warnings,
        "model": "ideal species; classical Maxwellian or supplied distribution mean",
    }


def nuclear_mass_energy(
    mass_defect_kg: float,
    *,
    output_unit: str = "MWh_fission",
) -> float:
    """Reaction energy from a measured or modeled mass defect, ``delta-m c^2``."""

    mass = _nonnegative(mass_defect_kg, "mass_defect_kg")
    return _joules(mass * SPEED_OF_LIGHT_M_S**2, output_unit)


def fission_reaction_energy(
    isotope_mass_kg: float,
    atomic_mass_g_mol: float,
    energy_per_fission_mev: float,
    *,
    fissioned_fraction: float = 1.0,
    output_unit: str = "MWh_fission",
) -> float:
    """Nuclear reaction energy from isotope inventory and energy per fission."""

    mass = _nonnegative(isotope_mass_kg, "isotope_mass_kg")
    molar_mass = _positive(atomic_mass_g_mol, "atomic_mass_g_mol")
    energy_mev = _positive(energy_per_fission_mev, "energy_per_fission_mev")
    fraction = _finite(fissioned_fraction, "fissioned_fraction")
    if not 0.0 <= fraction <= 1.0:
        raise PhysicalCalculationError(
            "invalid_value",
            "fissioned_fraction must be between 0 and 1",
            field="fissioned_fraction",
        )
    moles = mass * 1000.0 / molar_mass
    reactions = moles * AVOGADRO_CONSTANT * fraction
    joules_per_reaction = energy_mev * 1.0e6 * 1.602_176_634e-19
    return _joules(reactions * joules_per_reaction, output_unit)


def friction_loss_energy(
    friction_force_n: float,
    distance_m: float,
    *,
    output_unit: str = "kWh_m",
) -> float:
    """Mechanical work removed by a measured resisting force."""

    force = _nonnegative(friction_force_n, "friction_force_n")
    distance = _nonnegative(distance_m, "distance_m")
    return _joules(force * distance, output_unit)


def rolling_friction_loss_energy(
    coefficient_of_rolling_resistance: float,
    normal_force_n: float,
    distance_m: float,
    *,
    output_unit: str = "kWh_m",
) -> float:
    """Rolling-resistance loss ``Crr N d`` under constant conditions."""

    coefficient = _nonnegative(
        coefficient_of_rolling_resistance, "coefficient_of_rolling_resistance"
    )
    normal = _nonnegative(normal_force_n, "normal_force_n")
    distance = _nonnegative(distance_m, "distance_m")
    return _joules(coefficient * normal * distance, output_unit)


def aerodynamic_drag_loss_energy(
    fluid_density_kg_m3: float,
    drag_coefficient: float,
    frontal_area_m2: float,
    relative_speed_m_s: float,
    *,
    distance_m: Optional[float] = None,
    duration_hours: Optional[float] = None,
    output_unit: str = "kWh_m",
) -> float:
    """Work against steady quadratic drag ``0.5 rho Cd A v^2``."""

    density = _nonnegative(fluid_density_kg_m3, "fluid_density_kg_m3")
    coefficient = _nonnegative(drag_coefficient, "drag_coefficient")
    area = _nonnegative(frontal_area_m2, "frontal_area_m2")
    speed = _nonnegative(relative_speed_m_s, "relative_speed_m_s")
    if (distance_m is None) == (duration_hours is None):
        raise PhysicalCalculationError(
            "conflicting_inputs",
            "provide exactly one of distance_m or duration_hours",
        )
    if distance_m is not None:
        distance = _nonnegative(distance_m, "distance_m")
    else:
        duration = _nonnegative(duration_hours, "duration_hours")
        distance = speed * duration * 3600.0
    force = 0.5 * density * coefficient * area * speed**2
    return _joules(force * distance, output_unit)


def pressure_to_pa(value: float, unit: str = "Pa") -> float:
    pressure = _nonnegative(value, "pressure")
    key = str(unit).strip().lower().replace(" ", "")
    try:
        return pressure * PRESSURE_TO_PA[key]
    except KeyError as exc:
        known = ", ".join(sorted(PRESSURE_TO_PA))
        raise PhysicalCalculationError(
            "unsupported_unit",
            f"unsupported pressure unit: {unit}. Supported units: {known}",
            field="pressure_unit",
        ) from exc


def _plasma_particle_mass(component: Mapping[str, object], name: str) -> Optional[float]:
    if component.get("particle_mass_kg") is not None:
        return _positive(component["particle_mass_kg"], "particle_mass_kg")
    key = name.strip().lower().replace("_", " ")
    known = {
        "electron": ELECTRON_MASS_KG,
        "electrons": ELECTRON_MASS_KG,
        "e": ELECTRON_MASS_KG,
        "e-": ELECTRON_MASS_KG,
        "e−": ELECTRON_MASS_KG,
        "proton": PROTON_MASS_KG,
        "protons": PROTON_MASS_KG,
        "hydrogen ion": PROTON_MASS_KG,
        "h+": PROTON_MASS_KG,
        "deuteron": DEUTERON_MASS_KG,
        "deuterium ion": DEUTERON_MASS_KG,
        "triton": TRITON_MASS_KG,
        "tritium ion": TRITON_MASS_KG,
        "alpha": ALPHA_PARTICLE_MASS_KG,
        "alpha particle": ALPHA_PARTICLE_MASS_KG,
        "helium 4 ion": ALPHA_PARTICLE_MASS_KG,
    }
    return known.get(key)


def _coolprop_inputs(
    temperature_c: Optional[float],
    pressure_pa: Optional[float],
    vapor_quality: Optional[float],
) -> tuple:
    supplied = sum(value is not None for value in (temperature_c, pressure_pa, vapor_quality))
    if supplied != 2:
        raise PhysicalCalculationError(
            "invalid_fluid_state",
            "fluid state requires exactly two of temperature_c, pressure_pa, and vapor_quality",
        )
    if vapor_quality is not None:
        quality = _finite(vapor_quality, "vapor_quality")
        if not 0.0 <= quality <= 1.0:
            raise PhysicalCalculationError(
                "invalid_value", "vapor_quality must be between 0 and 1", field="vapor_quality"
            )
        if temperature_c is not None:
            return ("T", _c_to_k(temperature_c, "temperature_c"), "Q", quality)
        return ("P", _positive(pressure_pa, "pressure_pa"), "Q", quality)
    return (
        "T",
        _c_to_k(temperature_c, "temperature_c"),
        "P",
        _positive(pressure_pa, "pressure_pa"),
    )


def _joules(value: float, output_unit: str) -> float:
    return convert_energy(value, "J", output_unit)


def _c_to_k(value: object, field: str) -> float:
    temperature = _finite(value, field) + 273.15
    if temperature <= 0.0:
        raise PhysicalCalculationError(
            "invalid_temperature", f"{field} must be above absolute zero", field=field
        )
    return temperature


def _finite(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PhysicalCalculationError(
            "invalid_number", f"{field} must be a finite number", field=field
        ) from exc
    if not math.isfinite(number):
        raise PhysicalCalculationError(
            "invalid_number", f"{field} must be a finite number", field=field
        )
    return number


def _nonnegative(value: object, field: str) -> float:
    number = _finite(value, field)
    if number < 0.0:
        raise PhysicalCalculationError("invalid_value", f"{field} must be nonnegative", field=field)
    return number


def _fraction(value: object, field: str) -> float:
    number = _nonnegative(value, field)
    if number > 1.0:
        raise PhysicalCalculationError(
            "invalid_value", f"{field} must be between 0 and 1", field=field
        )
    return number


def _positive(value: object, field: str) -> float:
    number = _finite(value, field)
    if number <= 0.0:
        raise PhysicalCalculationError("invalid_value", f"{field} must be positive", field=field)
    return number
