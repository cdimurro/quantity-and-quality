"""Focused calculation of energy quantity, Exergy Factor, and accessible exergy.

The public request is deliberately JSON-shaped. The same dictionary can be used
from Python, the CLI, the HTTP API, or an AI agent without translating between
four different interfaces.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Mapping, Optional, Tuple

from .accounting import accounting_capabilities
from .api import FUEL_SYMBOLS, chemical, cooling, electricity, fuel, report, solar, thermal
from .core import exergy_unit, sensible_heat_exergy_factor_c, thermal_exergy_factor_c
from .distinguishability import distinguishability_capabilities
from .model import QuantityQualityRecord
from .physical import (
    PHYSICAL_CONSTANTS_SOURCE,
    PhysicalCalculationError,
    aerodynamic_drag_loss_energy,
    battery_energy,
    blackbody_radiation_exergy_factor,
    capacitor_energy,
    chemical_mixture_properties,
    elastic_energy,
    electrical_energy,
    electromagnetic_field_energy,
    electromagnetic_field_map_energy,
    fission_reaction_energy,
    fluid_physical_exergy,
    fluid_state_change_exergy,
    friction_loss_energy,
    fusion_reaction_count,
    gravitational_potential_energy,
    humid_air_humidity_ratio,
    humid_air_physical_exergy,
    hydraulic_energy,
    ideal_gas_physical_exergy,
    ideal_mixture_separation_energy,
    inductor_energy,
    kinetic_energy,
    nuclear_mass_energy,
    nuclear_reaction_energy,
    nuclear_reaction_q_value_mev,
    phase_change_energy,
    physical_exergy_from_properties,
    plane_wave_energy,
    plasma_species_energy,
    poynting_flux_energy,
    pressure_to_pa,
    radiation_exergy_from_energy_entropy,
    rolling_friction_loss_energy,
    rotational_energy,
    shaft_energy,
)
from .units import (
    ENERGY_TO_MWH,
    MWH_PER_BTU_IT,
    POWER_TO_MW,
    convert_energy,
    convert_power,
    fuel_volume_conversion,
    is_energy_unit,
)

STREAM_CALCULATION_SCHEMA_VERSION = "1.2"

_MASS_TO_KG = {
    "g": 0.001,
    "kg": 1.0,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "metricton": 1000.0,
    "shortton": 907.18474,
}

_SPECIFIC_ENERGY_TO_MWH_PER_KG = {
    "j/kg": 1.0 / 3.6e9,
    "kj/kg": 1.0 / 3.6e6,
    "mj/kg": 1.0 / 3600.0,
    "gj/kg": 1.0 / 3.6,
    "wh/kg": 1.0e-6,
    "kwh/kg": 1.0e-3,
    "mwh/kg": 1.0,
    "mwh/tonne": 1.0e-3,
    "mwh/metricton": 1.0e-3,
    "btu/lb": MWH_PER_BTU_IT / 0.45359237,
    "kwh/lb": 1.0e-3 / 0.45359237,
}

_VOLUME_TO_M3 = {
    "l": 0.001,
    "liter": 0.001,
    "liters": 0.001,
    "litre": 0.001,
    "litres": 0.001,
    "m3": 1.0,
    "ft3": 0.028316846592,
    "scf": 0.028316846592,
    "gal": 0.003785411784,
    "gallon": 0.003785411784,
    "gallons": 0.003785411784,
}

_ENERGY_DENSITY_TO_MWH_PER_M3 = {
    "j/m3": 1.0 / 3.6e9,
    "kj/m3": 1.0 / 3.6e6,
    "mj/m3": 1.0 / 3600.0,
    "gj/m3": 1.0 / 3.6,
    "wh/m3": 1.0e-6,
    "kwh/m3": 1.0e-3,
    "mwh/m3": 1.0,
    "kwh/l": 1.0,
    "mj/l": 1.0 / 3.6,
    "btu/scf": MWH_PER_BTU_IT / 0.028316846592,
    "btu/ft3": MWH_PER_BTU_IT / 0.028316846592,
    "btu/gal": MWH_PER_BTU_IT / 0.003785411784,
}

_POWER_ENERGY_UNITS = {
    "w": "Wh",
    "kw": "kWh",
    "mw": "MWh",
    "gw": "GWh",
}

_NUCLEAR_REACTION_PRESETS = {
    "dt_fusion": {
        "name": "deuterium-tritium fusion",
        "q_value_mev": 17.6,
        "mass_convention": "IAEA dominant D-T branch rounded product energies",
        "reaction_data_source": "IAEA D-T dominant branch: 14.1 MeV neutron and 3.5 MeV alpha",
        "channels": (
            {
                "name": "neutron",
                "carrier": "neutron",
                "fraction": 14.1 / 17.6,
                "exergy_factor": 1.0,
            },
            {
                "name": "alpha",
                "carrier": "charged_particle",
                "fraction": 3.5 / 17.6,
                "exergy_factor": 1.0,
            },
        ),
    }
}

_STREAM_ALIASES = {
    "electric": "electricity",
    "electrical": "electricity",
    "thermal": "heat",
    "heating": "heat",
    "chemical": "fuel",
    "biomass": "fuel",
    "bioenergy": "fuel",
    "shaft": "mechanical",
    "hydraulic": "mechanical",
    "pressure": "fluid",
    "compressed_air": "fluid",
    "fission": "nuclear",
    "friction": "dissipation",
    "drag": "dissipation",
    "electromagnetic": "electromagnetic_field",
    "em_field": "electromagnetic_field",
    "field": "electromagnetic_field",
    "fusion": "nuclear",
    "thermonuclear": "nuclear",
}

_REQUEST_FIELDS = {
    "stream_type",
    "quantity",
    "unit",
    "power",
    "power_unit",
    "duration_hours",
    "output_unit",
    "source_c",
    "return_c",
    "sink_c",
    "cold_service_c",
    "ambient_sink_c",
    "mass",
    "mass_unit",
    "mass_flow_kg_s",
    "volume",
    "volume_unit",
    "specific_heat_kj_kg_k",
    "heating_value",
    "heating_value_unit",
    "chemical_exergy",
    "energy_basis_value",
    "irradiance_w_m2",
    "area_m2",
    "reference_c",
    "fuel",
    "basis",
    "fx",
    "exergy_factor",
    "reference",
    "boundary",
    "operating_basis",
    "label",
    # Electrical measurement and field-energy paths.
    "voltage_v",
    "current_a",
    "electrical_phase",
    "power_factor",
    "capacitance_f",
    "reference_voltage_v",
    "inductance_h",
    "reference_current_a",
    "charge_ah",
    "average_voltage_v",
    # Distributed electromagnetic fields and energy flux.
    "field_model",
    "volume_m3",
    "electric_field_v_m",
    "magnetic_flux_density_t",
    "reference_electric_field_v_m",
    "reference_magnetic_flux_density_t",
    "relative_permittivity",
    "relative_permeability",
    "field_cells",
    "power_flux_density_w_m2",
    "normal_or_capture_factor",
    "electric_field_rms_v_m",
    "wave_impedance_ohm",
    # Mechanical and hydraulic paths.
    "mechanical_mode",
    "torque_nm",
    "rotational_speed_rpm",
    "reference_speed_rpm",
    "moment_of_inertia_kg_m2",
    "velocity_m_s",
    "reference_velocity_m_s",
    "height_difference_m",
    "gravity_m_s2",
    "spring_constant_n_m",
    "displacement_m",
    "reference_displacement_m",
    "pressure_difference",
    "pressure_unit",
    "volume_flow_m3_s",
    # Latent heat, fluid states, and property provenance.
    "latent_heat_kj_kg",
    "phase_change_c",
    "fluid",
    "temperature_c",
    "temperature_k",
    "pressure_pa",
    "pressure",
    "reference_temperature_c",
    "reference_temperature_k",
    "reference_pressure_pa",
    "vapor_quality",
    "inlet_temperature_c",
    "inlet_pressure_pa",
    "inlet_vapor_quality",
    "outlet_temperature_c",
    "outlet_pressure_pa",
    "outlet_vapor_quality",
    "reported_energy_basis",
    "enthalpy_kj_kg",
    "entropy_kj_kg_k",
    "reference_enthalpy_kj_kg",
    "reference_entropy_kj_kg_k",
    "cp_j_kg_k",
    "gas_constant_j_kg_k",
    "property_model",
    "dry_air_mass_kg",
    "humidity_ratio",
    "reference_humidity_ratio",
    "relative_humidity",
    "reference_relative_humidity",
    "dry_air_cp_j_kg_k",
    "water_vapor_cp_j_kg_k",
    "dry_air_gas_constant_j_kg_k",
    # Radiation, mixtures, separation, and nuclear inventory.
    "source_temperature_c",
    "source_temperature_k",
    "radiation_model",
    "radiation_entropy_j_k",
    "components",
    "moisture_fraction",
    "ash_fraction",
    "heating_value_basis",
    "feedstock_class",
    "quality_basis_unit",
    "property_source",
    "composition_source",
    "amount_mol",
    "mole_fractions",
    "mass_defect_kg",
    "isotope_mass_kg",
    "atomic_mass_g_mol",
    "energy_per_fission_mev",
    "fissioned_fraction",
    "accessible_fraction",
    "nuclear_mode",
    "reaction_preset",
    "q_value_mev",
    "reaction_count",
    "reaction_amount_mol",
    "reactant_atomic_masses_u",
    "product_atomic_masses_u",
    "reactant_1_number_density_m3",
    "reactant_2_number_density_m3",
    "reactivity_m3_s",
    "duration_seconds",
    "identical_reactants",
    "reaction_channels",
    "nuclear_channel",
    "reactivity_source",
    "mass_convention",
    # Plasma state inventory.
    "plasma_model",
    "plasma_species",
    # Friction and aerodynamic dissipation.
    "loss_model",
    "friction_force_n",
    "distance_m",
    "coefficient_of_rolling_resistance",
    "normal_force_n",
    "fluid_density_kg_m3",
    "drag_coefficient",
    "frontal_area_m2",
    "relative_speed_m_s",
    "dissipation_c",
}


class StreamCalculationError(ValueError):
    """A stable, machine-readable error raised for an invalid stream request."""

    def __init__(self, code: str, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict:
        payload = {"code": self.code, "message": str(self)}
        if self.field:
            payload["field"] = self.field
        return payload


def energy_from_power(
    power: float,
    duration_hours: float,
    *,
    power_unit: str = "kW",
    output_unit: str = "kWh",
) -> float:
    """Return energy from average power multiplied by elapsed hours."""

    power_value = _finite_nonnegative(power, "power")
    duration = _finite_nonnegative(duration_hours, "duration_hours")
    energy_mwh = convert_power(power_value, power_unit, "MW") * duration
    return convert_energy(energy_mwh, "MWh", output_unit)


def sensible_heat_energy(
    mass: float,
    specific_heat_kj_kg_k: float,
    supply_c: float,
    return_c: float,
    *,
    mass_unit: str = "kg",
    output_unit: str = "kWh_th",
) -> float:
    """Return sensible heat ``m cp (Ts - Tr)`` in the requested energy unit."""

    mass_kg = _mass_kg(mass, mass_unit)
    cp = _finite_positive(specific_heat_kj_kg_k, "specific_heat_kj_kg_k")
    supply = _finite_number(supply_c, "supply_c")
    return_temperature = _finite_number(return_c, "return_c")
    if supply <= return_temperature:
        raise StreamCalculationError(
            "invalid_temperature_order",
            "supply_c must be greater than return_c",
            field="supply_c",
        )
    energy_kj = mass_kg * cp * (supply - return_temperature)
    return convert_energy(energy_kj, "kJ", output_unit)


def solar_energy(
    irradiance_w_m2: float,
    area_m2: float,
    duration_hours: float,
    *,
    output_unit: str = "kWh_solar",
) -> float:
    """Return incident solar energy from irradiance, area, and elapsed hours."""

    irradiance = _finite_nonnegative(irradiance_w_m2, "irradiance_w_m2")
    area = _finite_nonnegative(area_m2, "area_m2")
    duration = _finite_nonnegative(duration_hours, "duration_hours")
    energy_kwh = irradiance * area * duration / 1000.0
    return convert_energy(energy_kwh, "kWh", output_unit)


def energy_from_mass(
    mass: float,
    heating_value: float,
    *,
    mass_unit: str = "kg",
    heating_value_unit: str = "MJ/kg",
    output_unit: str = "MWh",
) -> float:
    """Return fuel energy from mass multiplied by a declared heating value."""

    mass_kg = _mass_kg(mass, mass_unit)
    value = _finite_positive(heating_value, "heating_value")
    key = _specific_energy_key(heating_value_unit)
    factor = _SPECIFIC_ENERGY_TO_MWH_PER_KG.get(key)
    if factor is None:
        known = ", ".join(sorted(_SPECIFIC_ENERGY_TO_MWH_PER_KG))
        raise StreamCalculationError(
            "unsupported_unit",
            f"unsupported heating_value_unit: {heating_value_unit}. Supported units: {known}",
            field="heating_value_unit",
        )
    energy_mwh = mass_kg * value * factor
    return convert_energy(energy_mwh, "MWh", output_unit)


def energy_from_volume(
    volume: float,
    heating_value: float,
    *,
    volume_unit: str = "m3",
    heating_value_unit: str = "MJ/m3",
    output_unit: str = "MWh",
) -> float:
    """Return fuel energy from volume multiplied by a declared heating value."""

    volume_m3 = _volume_m3(volume, volume_unit)
    value = _finite_positive(heating_value, "heating_value")
    key = _specific_energy_key(heating_value_unit)
    factor = _ENERGY_DENSITY_TO_MWH_PER_M3.get(key)
    if factor is None:
        known = ", ".join(sorted(_ENERGY_DENSITY_TO_MWH_PER_M3))
        raise StreamCalculationError(
            "unsupported_unit",
            f"unsupported heating_value_unit: {heating_value_unit}. Supported units: {known}",
            field="heating_value_unit",
        )
    energy_mwh = volume_m3 * value * factor
    return convert_energy(energy_mwh, "MWh", output_unit)


def calculate_stream(request: Mapping[str, object]) -> QuantityQualityRecord:
    """Calculate one stream from a JSON-shaped request.

    Every result contains energy quantity, Exergy Factor, accessible exergy, the
    quantity method, the quality method, and the inputs used to obtain them.
    """

    if not isinstance(request, Mapping):
        raise StreamCalculationError("invalid_request", "request must be an object")
    data = {str(key): value for key, value in request.items() if value is not None}
    unknown = sorted(set(data) - _REQUEST_FIELDS)
    if unknown:
        raise StreamCalculationError(
            "unknown_input",
            f"unknown input field: {unknown[0]}",
            field=unknown[0],
        )
    raw_type = str(data.get("stream_type", "")).strip().lower().replace("-", "_")
    stream_type = _STREAM_ALIASES.get(raw_type, raw_type)
    if raw_type in {"biomass", "bioenergy"} and "fuel" not in data:
        data = {**data, "fuel": "biomass"}
    if raw_type in {"fusion", "thermonuclear"} and "nuclear_mode" not in data:
        data = {**data, "nuclear_mode": "reaction"}
    supported_types = {
        "electricity",
        "mechanical",
        "electromagnetic_field",
        "heat",
        "cooling",
        "fluid",
        "humid_air",
        "fuel",
        "solar",
        "radiation",
        "separation",
        "nuclear",
        "plasma",
        "dissipation",
        "custom",
    }
    if stream_type not in supported_types:
        raise StreamCalculationError(
            "unsupported_stream_type",
            f"unsupported stream_type: {stream_type}. Supported types: "
            + ", ".join(sorted(supported_types)),
            field="stream_type",
        )

    if stream_type == "electricity":
        record, quantity_method = _electricity_stream(data)
    elif stream_type == "mechanical":
        record, quantity_method = _mechanical_stream(data)
    elif stream_type == "electromagnetic_field":
        record, quantity_method = _electromagnetic_stream(data)
    elif stream_type == "heat":
        record, quantity_method = _heat_stream(data)
    elif stream_type == "cooling":
        quantity, unit, quantity_method = _common_quantity(data, suffix="_cooling")
        record = cooling(
            quantity=quantity,
            unit=unit,
            cold_service_c=_required_number(data, "cold_service_c"),
            ambient_sink_c=_required_number(data, "ambient_sink_c"),
            label=_label(data),
        )
    elif stream_type == "solar":
        record, quantity_method = _solar_stream(data)
    elif stream_type == "radiation":
        record, quantity_method = _radiation_stream(data)
    elif stream_type == "fluid":
        record, quantity_method = _fluid_stream(data)
    elif stream_type == "humid_air":
        record, quantity_method = _humid_air_stream(data)
    elif stream_type == "fuel":
        record, quantity_method = _fuel_stream(data)
    elif stream_type == "separation":
        record, quantity_method = _separation_stream(data)
    elif stream_type == "nuclear":
        record, quantity_method = _nuclear_stream(data)
    elif stream_type == "plasma":
        record, quantity_method = _plasma_stream(data)
    elif stream_type == "dissipation":
        record, quantity_method = _dissipation_stream(data)
    else:
        quantity, unit, quantity_method = _common_quantity(data, suffix="")
        factor = data.get("fx", data.get("exergy_factor"))
        if factor is None:
            raise StreamCalculationError(
                "missing_input", "custom streams require fx or exergy_factor", field="fx"
            )
        record = report(
            quantity,
            unit,
            fx=_finite_nonnegative(factor, "fx"),
            reference=str(data.get("reference", "")),
            boundary=str(data.get("boundary", "")),
            basis=str(data.get("operating_basis", data.get("basis", ""))),
            label=_label(data),
        )

    return replace(
        record,
        stream_type=stream_type,
        quantity_method_id=quantity_method,
        calculation_inputs=dict(data),
    )


def stream_capabilities() -> dict:
    """Return the supported request shapes for clients and AI agents."""

    return {
        "schema_version": STREAM_CALCULATION_SCHEMA_VERSION,
        "request_schema": (
            "https://raw.githubusercontent.com/cdimurro/quantity-and-quality/"
            "main/data/stream_calculation_request.schema.json"
        ),
        "model_guide": (
            "https://github.com/cdimurro/quantity-and-quality/blob/"
            "main/docs/nuclear-plasma-electromagnetic.md"
        ),
        "purpose": "Calculate energy quantity, Exergy Factor, and accessible exergy for one stream.",
        "stream_type_aliases": {
            "biomass": "fuel (biomass at its chemical-carrier boundary)",
            "bioenergy": "fuel (report derived heat, electricity, or motion by its delivered form)",
            "compressed_air": "fluid",
            "hydraulic": "mechanical",
            "shaft": "mechanical",
            "friction": "dissipation",
            "drag": "dissipation",
            "electromagnetic": "electromagnetic_field",
            "em_field": "electromagnetic_field",
            "fusion": "nuclear reaction",
            "thermonuclear": "nuclear reaction",
        },
        "distinguishability": distinguishability_capabilities(),
        "end_use_accounting": accounting_capabilities(),
        "common_quantity_inputs": [
            {"all_of": ["quantity", "unit"]},
            {"all_of": ["power", "power_unit", "duration_hours"]},
        ],
        "units": {
            "energy": sorted(ENERGY_TO_MWH),
            "power": sorted(POWER_TO_MW),
            "mass": sorted(_MASS_TO_KG),
            "heating_value": sorted(_SPECIFIC_ENERGY_TO_MWH_PER_KG),
            "volume": sorted(_VOLUME_TO_M3),
            "energy_density": sorted(_ENERGY_DENSITY_TO_MWH_PER_M3),
            "pressure": ["Pa", "kPa", "MPa", "bar", "mbar", "atm", "psi"],
            "temperature": ["C"],
            "duration": ["hours"],
        },
        "stream_types": {
            "electricity": {
                "quality_inputs": [],
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                    {"all_of": ["voltage_v", "current_a", "duration_hours"]},
                    {"all_of": ["capacitance_f", "voltage_v"]},
                    {"all_of": ["inductance_h", "current_a"]},
                    {"all_of": ["charge_ah", "average_voltage_v"]},
                ],
                "example": {
                    "stream_type": "electricity",
                    "power": 100,
                    "power_unit": "kW",
                    "duration_hours": 8,
                },
            },
            "mechanical": {
                "quality_inputs": [],
                "defaults": {"fx": 1.0},
                "modes": {
                    "shaft": ["torque_nm", "rotational_speed_rpm", "duration_hours"],
                    "rotational": ["moment_of_inertia_kg_m2", "rotational_speed_rpm"],
                    "kinetic": ["mass", "velocity_m_s"],
                    "gravitational": ["mass", "height_difference_m"],
                    "elastic": ["spring_constant_n_m", "displacement_m"],
                    "hydraulic": ["pressure_difference", "volume"],
                },
                "example": {
                    "stream_type": "mechanical",
                    "mechanical_mode": "shaft",
                    "torque_nm": 500,
                    "rotational_speed_rpm": 1800,
                    "duration_hours": 2,
                },
            },
            "electromagnetic_field": {
                "quality_inputs": [],
                "defaults": {"fx": 1.0},
                "models": [
                    "stored_field",
                    "field_map",
                    "poynting_flux",
                    "plane_wave",
                    "supplied_field_energy",
                ],
                "example": {
                    "stream_type": "electromagnetic_field",
                    "volume_m3": 2,
                    "electric_field_v_m": 1000,
                    "magnetic_flux_density_t": 0.01,
                },
            },
            "heat": {
                "quality_inputs": ["source_c"],
                "defaults": {"sink_c": 20.0},
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                    {
                        "all_of": [
                            "mass",
                            "specific_heat_kj_kg_k",
                            "source_c",
                            "return_c",
                        ],
                        "defaults": {"mass_unit": "kg"},
                    },
                    {
                        "all_of": [
                            "mass_flow_kg_s",
                            "duration_hours",
                            "specific_heat_kj_kg_k",
                            "source_c",
                            "return_c",
                        ]
                    },
                    {"all_of": ["mass", "latent_heat_kj_kg", "phase_change_c"]},
                ],
                "example": {
                    "stream_type": "heat",
                    "quantity": 1,
                    "unit": "MWh_th",
                    "source_c": 80,
                    "sink_c": 20,
                },
            },
            "fluid": {
                "quality_inputs": ["reference_temperature_c", "reference_pressure_pa"],
                "property_models": ["coolprop", "ideal_gas", "supplied_properties"],
                "quantity_inputs": [
                    {"all_of": ["mass", "fluid", "temperature_c", "pressure_pa"]},
                    {"all_of": ["mass", "fluid", "pressure_pa", "vapor_quality"]},
                    {
                        "all_of": [
                            "mass",
                            "enthalpy_kj_kg",
                            "entropy_kj_kg_k",
                            "reference_enthalpy_kj_kg",
                            "reference_entropy_kj_kg_k",
                        ]
                    },
                ],
                "example": {
                    "stream_type": "fluid",
                    "fluid": "Air",
                    "mass": 100,
                    "temperature_c": 40,
                    "pressure_pa": 700000,
                    "reference_temperature_c": 20,
                    "reference_pressure_pa": 101325,
                },
            },
            "humid_air": {
                "quality_inputs": [
                    "temperature and pressure",
                    "humidity_ratio or relative_humidity",
                    "reference humidity state",
                ],
                "example": {
                    "stream_type": "humid_air",
                    "dry_air_mass_kg": 1000,
                    "temperature_c": 30,
                    "pressure_pa": 101325,
                    "relative_humidity": 0.6,
                    "reference_temperature_c": 20,
                    "reference_relative_humidity": 0.5,
                },
            },
            "cooling": {
                "quality_inputs": ["cold_service_c", "ambient_sink_c"],
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                ],
                "example": {
                    "stream_type": "cooling",
                    "quantity": 1,
                    "unit": "MWh_cooling",
                    "cold_service_c": 7,
                    "ambient_sink_c": 30,
                },
            },
            "fuel": {
                "quality_inputs": [],
                "defaults": {"fuel": "natural gas", "basis": "HHV"},
                "quality_alternative": {"all_of": ["chemical_exergy", "energy_basis_value"]},
                "heterogeneous_carriers": {
                    "examples": ["biomass", "biogas", "syngas", "waste fuel"],
                    "require_one_of": [
                        ["chemical_exergy", "energy_basis_value"],
                        ["components"],
                        ["fx"],
                    ],
                },
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                    {
                        "all_of": ["mass", "heating_value"],
                        "defaults": {"mass_unit": "kg", "heating_value_unit": "MJ/kg"},
                    },
                    {
                        "all_of": ["volume", "heating_value"],
                        "defaults": {"volume_unit": "m3", "heating_value_unit": "MJ/m3"},
                    },
                ],
                "example": {
                    "stream_type": "fuel",
                    "mass": 100,
                    "mass_unit": "kg",
                    "heating_value": 50,
                    "heating_value_unit": "MJ/kg",
                    "fuel": "natural gas",
                    "basis": "LHV",
                },
            },
            "solar": {
                "quality_inputs": [],
                "defaults": {"reference_c": 20.0},
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                    {"all_of": ["irradiance_w_m2", "area_m2", "duration_hours"]},
                ],
                "example": {
                    "stream_type": "solar",
                    "irradiance_w_m2": 800,
                    "area_m2": 50,
                    "duration_hours": 6,
                },
            },
            "radiation": {
                "quality_inputs": ["radiation_model"],
                "models": [
                    "blackbody",
                    "spectral_entropy",
                    "coherent",
                    "work_equivalent",
                ],
                "example": {
                    "stream_type": "radiation",
                    "quantity": 1,
                    "unit": "MWh_rad",
                    "radiation_model": "blackbody",
                    "source_temperature_c": 900,
                    "reference_c": 20,
                },
            },
            "separation": {
                "quality_inputs": ["temperature_k", "mole_fractions"],
                "example": {
                    "stream_type": "separation",
                    "amount_mol": 1000,
                    "mole_fractions": [0.21, 0.79],
                    "temperature_k": 298.15,
                },
            },
            "nuclear": {
                "modes": ["inventory", "reaction"],
                "inventory_quality_inputs": ["accessible_fraction"],
                "reaction_quality_inputs": [
                    "reaction_preset",
                    "reaction_channels with channel exergy factors",
                    "or total-stream fx",
                ],
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["mass_defect_kg"]},
                    {
                        "all_of": [
                            "isotope_mass_kg",
                            "atomic_mass_g_mol",
                            "energy_per_fission_mev",
                        ]
                    },
                    {"all_of": ["reaction_count", "q_value_mev"]},
                    {"all_of": ["reaction_amount_mol", "q_value_mev"]},
                    {
                        "all_of": [
                            "reaction_count",
                            "reactant_atomic_masses_u",
                            "product_atomic_masses_u",
                            "mass_convention",
                        ]
                    },
                    {
                        "all_of": [
                            "reactant_1_number_density_m3",
                            "reactant_2_number_density_m3",
                            "reactivity_m3_s",
                            "reactivity_source",
                            "volume_m3",
                            "duration_seconds or duration_hours",
                            "q_value_mev or reaction_preset",
                        ]
                    },
                ],
                "example": {
                    "stream_type": "nuclear",
                    "nuclear_mode": "reaction",
                    "reaction_preset": "dt_fusion",
                    "reaction_count": 1e20,
                },
            },
            "plasma": {
                "quality_inputs": [
                    "reference_temperature",
                    "species temperature or supplied distribution mean and factor",
                    "internal-state exergy factor when ionization/excitation energy is included",
                ],
                "models": ["ideal_species", "supplied quantity and fx"],
                "example": {
                    "stream_type": "plasma",
                    "volume_m3": 1,
                    "plasma_species": [
                        {
                            "name": "electron",
                            "number_density_m3": 1e20,
                            "temperature_ev": 1000,
                        },
                        {
                            "name": "deuteron",
                            "number_density_m3": 1e20,
                            "temperature_ev": 1000,
                        },
                    ],
                },
            },
            "dissipation": {
                "quality_inputs": ["dissipation_c", "sink_c"],
                "models": ["friction_force", "rolling_resistance", "aerodynamic_drag"],
                "example": {
                    "stream_type": "dissipation",
                    "loss_model": "aerodynamic_drag",
                    "fluid_density_kg_m3": 1.225,
                    "drag_coefficient": 0.3,
                    "frontal_area_m2": 2.2,
                    "relative_speed_m_s": 25,
                    "distance_m": 10000,
                },
            },
            "custom": {
                "quality_inputs": ["fx or exergy_factor"],
                "quantity_inputs": [
                    {"all_of": ["quantity", "unit"]},
                    {"all_of": ["power", "power_unit", "duration_hours"]},
                ],
                "example": {
                    "stream_type": "custom",
                    "quantity": 1,
                    "unit": "MWh",
                    "fx": 0.73,
                },
            },
        },
    }


def _electricity_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    measurement_paths = {
        "current": "current_a" in data or ("voltage_v" in data and "duration_hours" in data),
        "capacitor": "capacitance_f" in data,
        "inductor": "inductance_h" in data,
        "battery": "charge_ah" in data or "average_voltage_v" in data,
    }
    active = [name for name, present in measurement_paths.items() if present]
    if active and ("quantity" in data or "power" in data):
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide one electrical measurement path, quantity, or power and duration",
        )
    if len(active) > 1:
        raise StreamCalculationError(
            "conflicting_inputs", "provide only one electrical measurement path"
        )
    output_unit = str(data.get("output_unit", "kWh_e"))
    if not active:
        quantity, unit, method = _common_quantity(data, suffix="_e")
    elif active[0] == "current":
        quantity = _physical_call(
            electrical_energy,
            _required_number(data, "voltage_v", nonnegative=True),
            _required_number(data, "current_a", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            phase=str(data.get("electrical_phase", "dc")),
            power_factor=_optional_number(data, "power_factor", 1.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_e")
        method = "quantity.electricity.voltage_current_duration.v1"
    elif active[0] == "capacitor":
        quantity = _physical_call(
            capacitor_energy,
            _required_number(data, "capacitance_f", nonnegative=True),
            _required_number(data, "voltage_v", nonnegative=True),
            reference_voltage_v=_optional_number(data, "reference_voltage_v", 0.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_e")
        method = "quantity.electricity.capacitor.v1"
    elif active[0] == "inductor":
        quantity = _physical_call(
            inductor_energy,
            _required_number(data, "inductance_h", nonnegative=True),
            _required_number(data, "current_a", nonnegative=True),
            reference_current_a=_optional_number(data, "reference_current_a", 0.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_e")
        method = "quantity.electricity.inductor.v1"
    else:
        quantity = _physical_call(
            battery_energy,
            _required_number(data, "charge_ah", nonnegative=True),
            _required_number(data, "average_voltage_v", nonnegative=True),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_e")
        method = "quantity.electricity.charge_average_voltage.v1"
    record = electricity(
        quantity=quantity,
        unit=unit,
        boundary=str(data.get("boundary", "electrical delivery boundary")),
        label=_label(data),
    )
    return replace(record, method_id="electricity.work_equivalent.v1"), method


def _electromagnetic_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    direct = "quantity" in data or "power" in data
    candidates = {
        "field_map": "field_cells" in data,
        "stored_field": any(
            key in data for key in ("electric_field_v_m", "magnetic_flux_density_t")
        ),
        "poynting_flux": "power_flux_density_w_m2" in data,
        "plane_wave": "electric_field_rms_v_m" in data,
    }
    active = [name for name, present in candidates.items() if present]
    if direct and active:
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide supplied energy or exactly one electromagnetic field model",
        )
    if not direct and len(active) != 1:
        raise StreamCalculationError(
            "ambiguous_inputs",
            "provide exactly one of field_cells, stored E/B fields, measured Poynting flux, or plane-wave RMS field",
            field="field_model",
        )
    output_unit = str(data.get("output_unit", "kWh_em"))
    metadata: dict[str, object] = {}
    if direct:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_em")
        model = "supplied_field_energy"
    elif active[0] == "field_map":
        cells = data["field_cells"]
        if not isinstance(cells, list):
            raise StreamCalculationError(
                "invalid_field_map", "field_cells must be an array", field="field_cells"
            )
        quantity = _physical_call(electromagnetic_field_map_energy, cells, output_unit=output_unit)
        unit = _carrier_unit(output_unit, "_em")
        quantity_method = "quantity.electromagnetic.field_map_volume_integral.v1"
        model = "field_map"
        metadata["cell_count"] = len(cells)
    elif active[0] == "stored_field":
        quantity = _physical_call(
            electromagnetic_field_energy,
            _required_number(data, "volume_m3", nonnegative=True),
            electric_field_v_m=_optional_number(data, "electric_field_v_m", 0.0),
            magnetic_flux_density_t=_optional_number(data, "magnetic_flux_density_t", 0.0),
            reference_electric_field_v_m=_optional_number(
                data, "reference_electric_field_v_m", 0.0
            ),
            reference_magnetic_flux_density_t=_optional_number(
                data, "reference_magnetic_flux_density_t", 0.0
            ),
            relative_permittivity=_optional_number(data, "relative_permittivity", 1.0),
            relative_permeability=_optional_number(data, "relative_permeability", 1.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_em")
        quantity_method = "quantity.electromagnetic.linear_field_volume.v1"
        model = "stored_field"
        metadata.update(
            {
                "volume_m3": data["volume_m3"],
                "electric_field_v_m": data.get("electric_field_v_m", 0.0),
                "magnetic_flux_density_t": data.get("magnetic_flux_density_t", 0.0),
                "relative_permittivity": data.get("relative_permittivity", 1.0),
                "relative_permeability": data.get("relative_permeability", 1.0),
            }
        )
    elif active[0] == "poynting_flux":
        quantity = _physical_call(
            poynting_flux_energy,
            _required_number(data, "power_flux_density_w_m2", nonnegative=True),
            _required_number(data, "area_m2", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            normal_or_capture_factor=_optional_number(data, "normal_or_capture_factor", 1.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_em")
        quantity_method = "quantity.electromagnetic.poynting_flux_surface_time.v1"
        model = "poynting_flux"
    else:
        quantity = _physical_call(
            plane_wave_energy,
            _required_number(data, "electric_field_rms_v_m", nonnegative=True),
            _required_number(data, "area_m2", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            wave_impedance_ohm=_optional_number(data, "wave_impedance_ohm", 376.730313412),
            normal_or_capture_factor=_optional_number(data, "normal_or_capture_factor", 1.0),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_em")
        quantity_method = "quantity.electromagnetic.plane_wave_rms.v1"
        model = "plane_wave"
    declared_model = str(data.get("field_model", "")).strip().lower().replace("-", "_")
    if declared_model and declared_model != model:
        raise StreamCalculationError(
            "conflicting_inputs",
            f"field_model={declared_model} conflicts with the inferred {model} input path",
            field="field_model",
        )
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=1.0,
        reference="declared zero or reference electromagnetic field",
        boundary=str(data.get("boundary", "electromagnetic field-transfer boundary")),
        basis=(
            "work-equivalent electromagnetic field energy; material conversion losses are excluded"
        ),
        method="electromagnetic",
        method_id=f"electromagnetic.{model}.work_equivalent.v1",
        tier="F2",
        label=_label(data) or f"{model.replace('_', ' ')} electromagnetic energy",
        metadata={
            "field_model": model,
            "material_model": "linear isotropic nondispersive"
            if model in {"stored_field", "field_map"}
            else None,
            "constants_source": PHYSICAL_CONSTANTS_SOURCE if not direct else None,
            **metadata,
        },
    )
    return record, quantity_method


def _mechanical_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    if "quantity" in data or "power" in data:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_m")
        mode = "supplied_work"
    else:
        mode = str(data.get("mechanical_mode", "")).strip().lower().replace("-", "_")
        candidates = {
            "shaft": "torque_nm" in data,
            "rotational": "moment_of_inertia_kg_m2" in data,
            "kinetic": "velocity_m_s" in data and ("mass" in data or "mass_flow_kg_s" in data),
            "gravitational": "height_difference_m" in data
            and ("mass" in data or "mass_flow_kg_s" in data),
            "elastic": "spring_constant_n_m" in data or "displacement_m" in data,
            "hydraulic": "pressure_difference" in data,
        }
        inferred = [name for name, present in candidates.items() if present]
        if not mode:
            if len(inferred) != 1:
                raise StreamCalculationError(
                    "ambiguous_inputs",
                    "mechanical_mode is required when the inputs do not identify exactly one model",
                    field="mechanical_mode",
                )
            mode = inferred[0]
        if mode not in candidates:
            raise StreamCalculationError(
                "unsupported_mode",
                "mechanical_mode must be shaft, rotational, kinetic, gravitational, elastic, or hydraulic",
                field="mechanical_mode",
            )
        output_unit = str(data.get("output_unit", "kWh_m"))
        if mode == "shaft":
            quantity = _physical_call(
                shaft_energy,
                _required_number(data, "torque_nm", nonnegative=True),
                _required_number(data, "rotational_speed_rpm", nonnegative=True),
                _required_number(data, "duration_hours", nonnegative=True),
                output_unit=output_unit,
            )
        elif mode == "rotational":
            quantity = _physical_call(
                rotational_energy,
                _required_number(data, "moment_of_inertia_kg_m2", nonnegative=True),
                _required_number(data, "rotational_speed_rpm", nonnegative=True),
                reference_speed_rpm=_optional_number(data, "reference_speed_rpm", 0.0),
                output_unit=output_unit,
            )
        elif mode == "kinetic":
            quantity = _physical_call(
                kinetic_energy,
                _total_mass_kg(data),
                _required_number(data, "velocity_m_s", nonnegative=True),
                reference_velocity_m_s=_optional_number(data, "reference_velocity_m_s", 0.0),
                output_unit=output_unit,
            )
        elif mode == "gravitational":
            quantity = _physical_call(
                gravitational_potential_energy,
                _total_mass_kg(data),
                _required_number(data, "height_difference_m", nonnegative=True),
                gravity_m_s2=_optional_number(data, "gravity_m_s2", 9.80665),
                output_unit=output_unit,
            )
        elif mode == "elastic":
            quantity = _physical_call(
                elastic_energy,
                _required_number(data, "spring_constant_n_m", nonnegative=True),
                _required_number(data, "displacement_m", nonnegative=True),
                reference_displacement_m=_optional_number(data, "reference_displacement_m", 0.0),
                output_unit=output_unit,
            )
        else:
            if "volume" in data:
                volume_m3 = _volume_m3(data["volume"], str(data.get("volume_unit", "m3")))
            else:
                flow = _required_number(data, "volume_flow_m3_s", nonnegative=True)
                duration = _required_number(data, "duration_hours", nonnegative=True)
                volume_m3 = flow * duration * 3600.0
            quantity = _physical_call(
                hydraulic_energy,
                _required_number(data, "pressure_difference", nonnegative=True),
                volume_m3,
                pressure_unit=str(data.get("pressure_unit", "Pa")),
                output_unit=output_unit,
            )
        unit = _carrier_unit(output_unit, "_m")
        quantity_method = f"quantity.mechanical.{mode}.v1"
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=1.0,
        reference="declared mechanical datum and work-transfer boundary",
        boundary=str(data.get("boundary", "mechanical work-transfer boundary")),
        basis=f"{mode.replace('_', ' ')} work is work-equivalent at the declared boundary",
        method="mechanical",
        method_id="mechanical.work_equivalent.v1",
        tier="F2",
        label=_label(data) or f"{mode.replace('_', ' ')} mechanical energy",
        metadata={"mechanical_mode": mode},
    )
    return record, quantity_method


def _heat_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    has_latent = "latent_heat_kj_kg" in data or "phase_change_c" in data
    if has_latent:
        source_c = _required_number(data, "phase_change_c")
    else:
        source_c = _required_number(data, "source_c")
    sink_c = _optional_number(data, "sink_c", 20.0)
    return_c = _optional_number(data, "return_c", None)

    if has_latent:
        if any(key in data for key in ("quantity", "power", "specific_heat_kj_kg_k", "return_c")):
            raise StreamCalculationError(
                "conflicting_inputs",
                "a generic phase-change request uses mass, latent_heat_kj_kg, and phase_change_c; "
                "use a fluid-state request for combined sensible and latent paths",
            )
        output_unit = str(data.get("output_unit", "kWh_th"))
        quantity = _physical_call(
            phase_change_energy,
            _total_mass_kg(data),
            _required_number(data, "latent_heat_kj_kg", positive=True),
            output_unit=output_unit,
        )
        record = thermal(
            quantity=quantity,
            unit=_carrier_unit(output_unit, "_th"),
            source_c=source_c,
            sink_c=sink_c,
            boundary=str(data.get("boundary", "phase-change heat-transfer boundary")),
            basis=(
                f"latent heat at {source_c:g} C with supplied latent heat "
                f"{float(data['latent_heat_kj_kg']):g} kJ/kg"
            ),
            label=_label(data) or f"phase change at {source_c:g} C",
        )
        return replace(record, method_id="thermal.phase_change.constant_temperature.v1"), (
            "quantity.thermal.mass_latent_heat.v1"
        )

    has_mass = "mass" in data or "mass_flow_kg_s" in data
    if has_mass:
        if "quantity" in data or "power" in data:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide mass or mass flow, quantity, or power and duration; use only one quantity path",
            )
        if return_c is None:
            raise StreamCalculationError(
                "missing_input",
                "return_c is required when calculating sensible heat",
                field="return_c",
            )
        if "mass" in data and "mass_flow_kg_s" in data:
            raise StreamCalculationError(
                "conflicting_inputs", "provide mass or mass_flow_kg_s, not both", field="mass"
            )
        if "mass" in data:
            mass = _required_number(data, "mass", nonnegative=True)
            mass_unit = str(data.get("mass_unit", "kg"))
        else:
            flow = _required_number(data, "mass_flow_kg_s", nonnegative=True)
            duration = _required_number(data, "duration_hours", nonnegative=True)
            mass = flow * duration * 3600.0
            mass_unit = "kg"
        output_unit = str(data.get("output_unit", "MWh_th"))
        quantity = sensible_heat_energy(
            mass,
            _required_number(data, "specific_heat_kj_kg_k", positive=True),
            source_c,
            return_c,
            mass_unit=mass_unit,
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_th")
        quantity_method = "quantity.sensible_heat.mass_cp_delta_t.v1"
    else:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_th")

    if return_c is None:
        record = thermal(
            quantity=quantity,
            unit=unit,
            source_c=source_c,
            sink_c=sink_c,
            label=_label(data),
        )
        return record, quantity_method

    factor = sensible_heat_exergy_factor_c(source_c, return_c, sink_c)
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=f"T0 = {sink_c:g} C",
        boundary=str(data.get("boundary", "sensible heat stream")),
        basis=(
            "integrated sensible-heat factor, "
            f"supply={source_c:g} C, return={return_c:g} C, sink={sink_c:g} C"
        ),
        method="thermal",
        method_id="thermal.sensible.integrated.v1",
        tier="F2",
        label=_label(data) or f"{source_c:g} C to {return_c:g} C sensible heat",
        source_c=source_c,
        return_c=return_c,
        sink_c=sink_c,
    )
    return record, quantity_method


def _solar_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    if "irradiance_w_m2" in data or "area_m2" in data:
        if "quantity" in data or "power" in data:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide irradiance and area, quantity, or power and duration; use only one quantity path",
            )
        output_unit = str(data.get("output_unit", "kWh_solar"))
        quantity = solar_energy(
            _required_number(data, "irradiance_w_m2", nonnegative=True),
            _required_number(data, "area_m2", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_solar")
        quantity_method = "quantity.solar.irradiance_area_duration.v1"
    else:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_solar")
    reference_c = _optional_number(data, "reference_c", 20.0)
    assert reference_c is not None
    record = solar(
        quantity=quantity,
        unit=unit,
        reference_c=reference_c,
        label=_label(data),
    )
    return record, quantity_method


def _radiation_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    if "irradiance_w_m2" in data or "area_m2" in data:
        if "quantity" in data or "power" in data:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide irradiance and area, quantity, or power and duration; use one path",
            )
        output_unit = str(data.get("output_unit", "kWh_rad"))
        quantity = solar_energy(
            _required_number(data, "irradiance_w_m2", nonnegative=True),
            _required_number(data, "area_m2", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            output_unit=output_unit,
        )
        unit = _carrier_unit(output_unit, "_rad")
        quantity_method = "quantity.radiation.irradiance_area_duration.v1"
    else:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_rad")
    model = str(data.get("radiation_model", "blackbody")).strip().lower()
    if "reference_temperature_k" in data and "reference_c" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide reference_temperature_k or reference_c, not both",
            field="reference_temperature_k",
        )
    if model not in {"spectral_entropy", "measured_entropy"} and "radiation_entropy_j_k" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "radiation_entropy_j_k requires the spectral_entropy or measured_entropy model",
            field="radiation_entropy_j_k",
        )
    if model == "blackbody":
        if "source_temperature_k" in data and "source_temperature_c" in data:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide source_temperature_k or source_temperature_c, not both",
                field="source_temperature_k",
            )
        if "source_temperature_k" in data:
            source_k = _required_number(data, "source_temperature_k", positive=True)
        else:
            source_k = _required_number(data, "source_temperature_c") + 273.15
        if "reference_temperature_k" in data:
            reference_k = _required_number(data, "reference_temperature_k", positive=True)
        else:
            reference_k = _optional_number(data, "reference_c", 20.0) + 273.15
        factor = _physical_call(blackbody_radiation_exergy_factor, source_k, reference_k)
        source_c = source_k - 273.15
        reference_c = reference_k - 273.15
        basis = "Petela blackbody-radiation factor"
        method_id = "radiation.petela.blackbody.v1"
    elif model in {"spectral_entropy", "measured_entropy"}:
        if "reference_temperature_k" in data:
            reference_k = _required_number(data, "reference_temperature_k", positive=True)
        else:
            reference_k = _optional_number(data, "reference_c", 20.0) + 273.15
        entropy_result = _physical_call(
            radiation_exergy_from_energy_entropy,
            quantity,
            unit,
            _required_number(data, "radiation_entropy_j_k", nonnegative=True),
            reference_k,
            output_unit=exergy_unit(unit),
        )
        factor = entropy_result["exergy_factor"]
        source_c = None
        reference_c = reference_k - 273.15
        basis = "net radiation availability from co-boundary energy and entropy transfer"
        method_id = "radiation.energy_entropy.availability.v1"
    elif model in {"work_equivalent", "coherent"}:
        factor = 1.0
        source_c = None
        reference_c = (
            _required_number(data, "reference_temperature_k", positive=True) - 273.15
            if "reference_temperature_k" in data
            else _optional_number(data, "reference_c", 20.0)
        )
        basis = "declared coherent/work-equivalent radiation at the delivery boundary"
        method_id = "radiation.work_equivalent.declared.v1"
    else:
        raise StreamCalculationError(
            "unsupported_mode",
            "radiation_model must be blackbody, spectral_entropy, coherent, or work_equivalent",
            field="radiation_model",
        )
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference=f"T0 = {reference_c:g} C",
        boundary=str(data.get("boundary", "radiation receiving boundary")),
        basis=basis,
        method="radiation",
        method_id=method_id,
        tier="F2",
        label=_label(data) or f"{model.replace('_', ' ')} radiation",
        source_c=source_c,
        sink_c=reference_c,
        metadata={
            "radiation_model": model,
            **(
                {"radiation_entropy_j_k": data["radiation_entropy_j_k"]}
                if "radiation_entropy_j_k" in data
                else {}
            ),
        },
    )
    return record, quantity_method


def _fluid_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    mass_kg = _total_mass_kg(data)
    has_state_change = any(key.startswith(("inlet_", "outlet_")) for key in data)
    if has_state_change:
        output_unit = str(data.get("output_unit", "kWh"))
        reference_c = _optional_number(data, "reference_temperature_c", 20.0)
        reference_pressure = _optional_number(data, "reference_pressure_pa", 101_325.0)
        result = _physical_call(
            fluid_state_change_exergy,
            str(data.get("fluid", "Water")),
            mass_kg,
            inlet_temperature_c=_optional_number(data, "inlet_temperature_c", None),
            inlet_pressure_pa=_optional_number(data, "inlet_pressure_pa", None),
            inlet_vapor_quality=_optional_number(data, "inlet_vapor_quality", None),
            outlet_temperature_c=_optional_number(data, "outlet_temperature_c", None),
            outlet_pressure_pa=_optional_number(data, "outlet_pressure_pa", None),
            outlet_vapor_quality=_optional_number(data, "outlet_vapor_quality", None),
            reference_temperature_c=reference_c,
            reference_pressure_pa=reference_pressure,
            output_unit=output_unit,
        )
        selected_basis = str(data.get("reported_energy_basis", "auto")).lower()
        if selected_basis == "auto":
            selected_basis = (
                "enthalpy_change" if result["enthalpy_change"] > 0.0 else "physical_exergy"
            )
        if selected_basis == "enthalpy_change":
            if result["enthalpy_change"] <= 0.0:
                raise StreamCalculationError(
                    "invalid_energy_basis",
                    "enthalpy_change is not positive for these states; use physical_exergy basis",
                    field="reported_energy_basis",
                )
            quantity = result["enthalpy_change"]
            unit = _carrier_unit(output_unit, "_th")
            factor = result["physical_exergy_change"] / quantity
            basis_text = "state-to-state enthalpy decrease with physical-exergy decrease as quality"
        elif selected_basis == "physical_exergy":
            quantity = result["physical_exergy_change"]
            unit = _carrier_unit(output_unit, "_m")
            factor = 0.0 if quantity == 0.0 else 1.0
            basis_text = "state-to-state decrease in reversible physical work potential"
        else:
            raise StreamCalculationError(
                "unsupported_mode",
                "reported_energy_basis must be auto, enthalpy_change, or physical_exergy",
                field="reported_energy_basis",
            )
        fluid_name = str(data.get("fluid", "Water"))
        record = QuantityQualityRecord(
            quantity=quantity,
            unit=unit,
            exergy_factor=factor,
            reference=f"T0 = {reference_c:g} C, p0 = {reference_pressure:g} Pa",
            boundary=str(data.get("boundary", "fluid inlet-to-outlet boundary")),
            basis=basis_text,
            method="fluid",
            method_id="fluid.state_change.coolprop.v1",
            tier="F2",
            label=_label(data) or f"{fluid_name} state change",
            sink_c=reference_c,
            metadata={**result, "fluid": fluid_name, "reported_energy_basis": selected_basis},
        )
        return record, "quantity.fluid.state_change.coolprop.v1"

    output_unit = str(data.get("output_unit", "kWh_m"))
    model = str(data.get("property_model", "")).strip().lower().replace("-", "_")
    if not model:
        if "enthalpy_kj_kg" in data or "entropy_kj_kg_k" in data:
            model = "supplied_properties"
        elif "cp_j_kg_k" in data or "gas_constant_j_kg_k" in data:
            model = "ideal_gas"
        else:
            model = "coolprop"
    reference_c = _optional_number(data, "reference_temperature_c", 20.0)
    reference_pressure = _optional_number(data, "reference_pressure_pa", 101_325.0)
    if model in {"supplied", "supplied_properties", "refprop"}:
        quantity = _physical_call(
            physical_exergy_from_properties,
            mass_kg,
            _required_number(data, "enthalpy_kj_kg"),
            _required_number(data, "entropy_kj_kg_k"),
            _required_number(data, "reference_enthalpy_kj_kg"),
            _required_number(data, "reference_entropy_kj_kg_k"),
            reference_c + 273.15,
            velocity_m_s=_optional_number(data, "velocity_m_s", 0.0),
            reference_velocity_m_s=_optional_number(data, "reference_velocity_m_s", 0.0),
            height_difference_m=_optional_number(data, "height_difference_m", 0.0),
            gravity_m_s2=_optional_number(data, "gravity_m_s2", 9.80665),
            output_unit=output_unit,
        )
        metadata = {
            "property_backend": str(data.get("property_model", "supplied properties")),
            "enthalpy_kj_kg": data["enthalpy_kj_kg"],
            "entropy_kj_kg_k": data["entropy_kj_kg_k"],
            "reference_enthalpy_kj_kg": data["reference_enthalpy_kj_kg"],
            "reference_entropy_kj_kg_k": data["reference_entropy_kj_kg_k"],
        }
        quantity_method = "quantity.fluid.physical_exergy.supplied_properties.v1"
    elif model in {"ideal", "ideal_gas"}:
        temperature_k = _temperature_k(data, "temperature")
        pressure_pa = _pressure_pa(data, "pressure")
        quantity = _physical_call(
            ideal_gas_physical_exergy,
            mass_kg,
            temperature_k,
            pressure_pa,
            reference_temperature_k=reference_c + 273.15,
            reference_pressure_pa=reference_pressure,
            cp_j_kg_k=_optional_number(data, "cp_j_kg_k", 1005.0),
            gas_constant_j_kg_k=_optional_number(data, "gas_constant_j_kg_k", 287.05),
            velocity_m_s=_optional_number(data, "velocity_m_s", 0.0),
            reference_velocity_m_s=_optional_number(data, "reference_velocity_m_s", 0.0),
            height_difference_m=_optional_number(data, "height_difference_m", 0.0),
            gravity_m_s2=_optional_number(data, "gravity_m_s2", 9.80665),
            output_unit=output_unit,
        )
        metadata = {
            "property_backend": "constant-cp ideal gas",
            "temperature_k": temperature_k,
            "pressure_pa": pressure_pa,
            "cp_j_kg_k": _optional_number(data, "cp_j_kg_k", 1005.0),
            "gas_constant_j_kg_k": _optional_number(data, "gas_constant_j_kg_k", 287.05),
        }
        quantity_method = "quantity.fluid.physical_exergy.ideal_gas.v1"
    elif model == "coolprop":
        result = _physical_call(
            fluid_physical_exergy,
            str(data.get("fluid", "Air")),
            mass_kg,
            temperature_c=_optional_number(data, "temperature_c", None),
            pressure_pa=_optional_number(data, "pressure_pa", None),
            vapor_quality=_optional_number(data, "vapor_quality", None),
            reference_temperature_c=reference_c,
            reference_pressure_pa=reference_pressure,
            velocity_m_s=_optional_number(data, "velocity_m_s", 0.0),
            reference_velocity_m_s=_optional_number(data, "reference_velocity_m_s", 0.0),
            height_difference_m=_optional_number(data, "height_difference_m", 0.0),
            output_unit=output_unit,
        )
        quantity = result["quantity"]
        metadata = {key: value for key, value in result.items() if key not in {"quantity", "unit"}}
        quantity_method = "quantity.fluid.physical_exergy.coolprop.v1"
    else:
        raise StreamCalculationError(
            "unsupported_mode",
            "property_model must be supplied_properties, ideal_gas, or coolprop",
            field="property_model",
        )
    factor = 0.0 if quantity == 0.0 else 1.0
    fluid_name = str(data.get("fluid", "declared fluid"))
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=_carrier_unit(output_unit, "_m"),
        exergy_factor=factor,
        reference=f"T0 = {reference_c:g} C, p0 = {reference_pressure:g} Pa",
        boundary=str(data.get("boundary", "fluid-state work-potential boundary")),
        basis="reversible physical work potential relative to the declared environment",
        method="fluid",
        method_id=f"fluid.physical_exergy.{model}.v1",
        tier="F2",
        label=_label(data) or f"{fluid_name} physical exergy",
        sink_c=reference_c,
        metadata={"fluid": fluid_name, "property_model": model, **metadata},
    )
    return record, quantity_method


def _humid_air_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    dry_air_mass = _required_number(data, "dry_air_mass_kg", nonnegative=True)
    temperature_k = _temperature_k(data, "temperature")
    pressure_pa = _pressure_pa(data, "pressure")
    reference_c = _optional_number(data, "reference_temperature_c", 20.0)
    reference_pressure = _optional_number(data, "reference_pressure_pa", 101_325.0)
    backend_metadata = {}
    if "humidity_ratio" in data:
        humidity_ratio = _required_number(data, "humidity_ratio", nonnegative=True)
    else:
        state = _physical_call(
            humid_air_humidity_ratio,
            temperature_k - 273.15,
            pressure_pa,
            _required_number(data, "relative_humidity", nonnegative=True),
        )
        humidity_ratio = state["humidity_ratio"]
        backend_metadata.update(state)
    if "reference_humidity_ratio" in data:
        reference_humidity = _required_number(data, "reference_humidity_ratio", positive=True)
    else:
        reference_state = _physical_call(
            humid_air_humidity_ratio,
            reference_c,
            reference_pressure,
            _optional_number(data, "reference_relative_humidity", 0.5),
        )
        reference_humidity = reference_state["humidity_ratio"]
        backend_metadata.update(
            {
                "property_backend": reference_state["property_backend"],
                "property_backend_version": reference_state["property_backend_version"],
            }
        )
    output_unit = str(data.get("output_unit", "kWh_m"))
    quantity = _physical_call(
        humid_air_physical_exergy,
        dry_air_mass,
        temperature_k,
        pressure_pa,
        humidity_ratio,
        reference_temperature_k=reference_c + 273.15,
        reference_pressure_pa=reference_pressure,
        reference_humidity_ratio=reference_humidity,
        dry_air_cp_j_kg_k=_optional_number(data, "dry_air_cp_j_kg_k", 1006.0),
        water_vapor_cp_j_kg_k=_optional_number(data, "water_vapor_cp_j_kg_k", 1860.0),
        dry_air_gas_constant_j_kg_k=_optional_number(data, "dry_air_gas_constant_j_kg_k", 287.055),
        output_unit=output_unit,
    )
    factor = 0.0 if quantity == 0.0 else 1.0
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=_carrier_unit(output_unit, "_m"),
        exergy_factor=factor,
        reference=(
            f"T0 = {reference_c:g} C, p0 = {reference_pressure:g} Pa, "
            f"humidity ratio 0 = {reference_humidity:.8g} kg/kg dry air"
        ),
        boundary=str(data.get("boundary", "humid-air state boundary")),
        basis="Wepfer ideal-mixture humid-air flow exergy per kg dry air",
        method="humid_air",
        method_id="humid_air.wepfer.total_flow_exergy.v1",
        tier="F2",
        label=_label(data) or "humid-air physical and composition exergy",
        sink_c=reference_c,
        metadata={
            "dry_air_mass_kg": dry_air_mass,
            "temperature_k": temperature_k,
            "pressure_pa": pressure_pa,
            "humidity_ratio": humidity_ratio,
            "reference_humidity_ratio": reference_humidity,
            **backend_metadata,
        },
    )
    return record, "quantity.humid_air.wepfer_state_exergy.v1"


def _separation_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    output_unit = str(data.get("output_unit", "kWh_m"))
    quantity = _physical_call(
        ideal_mixture_separation_energy,
        _required_number(data, "amount_mol", nonnegative=True),
        _number_sequence(data, "mole_fractions"),
        _temperature_k(data, "temperature"),
        output_unit=output_unit,
    )
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=_carrier_unit(output_unit, "_m"),
        exergy_factor=1.0,
        reference="unmixed pure components at the declared temperature and pressure",
        boundary=str(data.get("boundary", "ideal separation task boundary")),
        basis="minimum reversible work of ideal-gas separation",
        method="separation",
        method_id="separation.ideal_gas.minimum_work.v1",
        tier="F2",
        label=_label(data) or "minimum ideal-mixture separation work",
        metadata={"mole_fractions": list(_number_sequence(data, "mole_fractions"))},
    )
    return record, "quantity.separation.ideal_mixture.v1"


def _plasma_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    if "plasma_species" not in data:
        ignored_model_fields = [
            field
            for field in (
                "plasma_model",
                "field_model",
                "field_cells",
                "electric_field_v_m",
                "magnetic_flux_density_t",
            )
            if field in data
        ]
        if ignored_model_fields:
            raise StreamCalculationError(
                "conflicting_inputs",
                "plasma model or field inputs require plasma_species; a supplied total uses quantity and fx only",
                field=ignored_model_fields[0],
            )
        quantity, unit, quantity_method = _common_quantity(data, suffix="_plasma")
        factor_value = data.get("fx", data.get("exergy_factor"))
        if factor_value is None:
            raise StreamCalculationError(
                "missing_quality",
                "a supplied plasma energy quantity requires fx or exergy_factor; provide plasma_species for a calculated ideal-species state",
                field="fx",
            )
        record = QuantityQualityRecord(
            quantity=quantity,
            unit=unit,
            exergy_factor=_finite_nonnegative(factor_value, "fx"),
            reference=str(data.get("reference", "declared plasma reference environment")),
            boundary=str(data.get("boundary", "plasma inventory boundary")),
            basis=str(
                data.get(
                    "operating_basis",
                    "caller-supplied plasma energy and Exergy Factor",
                )
            ),
            method="plasma",
            method_id="plasma.supplied_state_factor.v1",
            tier="F2",
            label=_label(data) or "supplied plasma state",
        )
        return record, quantity_method

    if "quantity" in data or "power" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide plasma_species or a supplied quantity, not both",
            field="plasma_species",
        )
    species = data["plasma_species"]
    if not isinstance(species, list):
        raise StreamCalculationError(
            "invalid_plasma_species", "plasma_species must be an array", field="plasma_species"
        )
    model = str(data.get("plasma_model", "ideal_species")).strip().lower().replace("-", "_")
    if model not in {"ideal_species", "ideal_maxwellian"}:
        raise StreamCalculationError(
            "unsupported_mode",
            "plasma_model must be ideal_species; advanced distributions use supplied mean species energy",
            field="plasma_model",
        )
    if "reference_temperature_k" in data and "reference_temperature_c" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide reference_temperature_k or reference_temperature_c, not both",
            field="reference_temperature_k",
        )
    if "reference_temperature_k" in data:
        reference_k = _required_number(data, "reference_temperature_k", positive=True)
    else:
        reference_k = _optional_number(data, "reference_temperature_c", 20.0) + 273.15
    output_unit = str(data.get("output_unit", "kWh_plasma"))
    result = _physical_call(
        plasma_species_energy,
        species,
        _required_number(data, "volume_m3", positive=True),
        reference_temperature_k=reference_k,
        output_unit=output_unit,
    )
    field_energy = 0.0
    field_model = None
    has_field_map = "field_cells" in data
    has_uniform_field = any(
        key in data for key in ("electric_field_v_m", "magnetic_flux_density_t")
    )
    if has_field_map and has_uniform_field:
        raise StreamCalculationError(
            "conflicting_inputs",
            "plasma field energy accepts field_cells or one uniform E/B field, not both",
            field="field_cells",
        )
    if has_field_map:
        cells = data["field_cells"]
        if not isinstance(cells, list):
            raise StreamCalculationError(
                "invalid_field_map", "field_cells must be an array", field="field_cells"
            )
        field_energy = _physical_call(
            electromagnetic_field_map_energy, cells, output_unit=output_unit
        )
        field_model = "field_map"
    elif has_uniform_field:
        field_energy = _physical_call(
            electromagnetic_field_energy,
            _required_number(data, "volume_m3", positive=True),
            electric_field_v_m=_optional_number(data, "electric_field_v_m", 0.0),
            magnetic_flux_density_t=_optional_number(data, "magnetic_flux_density_t", 0.0),
            reference_electric_field_v_m=_optional_number(
                data, "reference_electric_field_v_m", 0.0
            ),
            reference_magnetic_flux_density_t=_optional_number(
                data, "reference_magnetic_flux_density_t", 0.0
            ),
            relative_permittivity=_optional_number(data, "relative_permittivity", 1.0),
            relative_permeability=_optional_number(data, "relative_permeability", 1.0),
            output_unit=output_unit,
        )
        field_model = "stored_field"
    declared_field_model = str(data.get("field_model", "")).strip().lower().replace("-", "_")
    if declared_field_model:
        if field_model is None:
            raise StreamCalculationError(
                "missing_input",
                "field_model requires matching plasma field inputs",
                field="field_model",
            )
        if declared_field_model != field_model:
            raise StreamCalculationError(
                "conflicting_inputs",
                f"field_model={declared_field_model} conflicts with the inferred {field_model} input path",
                field="field_model",
            )
    quantity = result["energy"] + field_energy
    accessible = result["exergy"] + field_energy
    factor = 0.0 if quantity == 0.0 else accessible / quantity
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=_carrier_unit(output_unit, "_plasma"),
        exergy_factor=factor,
        reference=f"same declared species and particle counts at T0 = {reference_k:g} K with zero/reference bulk and field states",
        boundary=str(data.get("boundary", "plasma state inventory boundary")),
        basis=(
            "ideal-species plasma energy with constant-volume thermal availability, bulk kinetic work, supplied internal-state quality, and optional field energy"
        ),
        method="plasma",
        method_id="plasma.ideal_species.state_inventory.v1",
        tier="F2",
        label=_label(data) or "ideal-species plasma state",
        sink_c=reference_k - 273.15,
        assumptions=(
            "species interactions, collective modes, sheath energy, and trapped radiation are excluded unless represented in supplied inputs",
        ),
        warnings=tuple(str(value) for value in result["warnings"]),
        metadata={
            **result,
            "field_energy": field_energy,
            "field_energy_unit": _carrier_unit(output_unit, "_em"),
            "field_model": field_model,
            "composition_constraint": "same species and particle counts at the reference state",
            "constants_source": PHYSICAL_CONSTANTS_SOURCE,
        },
    )
    return record, "quantity.plasma.ideal_species_inventory.v1"


def _nuclear_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    mode = str(data.get("nuclear_mode", "")).strip().lower().replace("-", "_")
    reaction_fields = {
        "reaction_preset",
        "q_value_mev",
        "reaction_count",
        "reaction_amount_mol",
        "reactant_atomic_masses_u",
        "product_atomic_masses_u",
        "reactant_1_number_density_m3",
        "reactant_2_number_density_m3",
        "reactivity_m3_s",
        "reaction_channels",
        "nuclear_channel",
    }
    if not mode:
        mode = "reaction" if any(field in data for field in reaction_fields) else "inventory"
    if mode == "reaction":
        return _nuclear_reaction_stream(data)
    if mode != "inventory":
        raise StreamCalculationError(
            "unsupported_mode",
            "nuclear_mode must be inventory or reaction",
            field="nuclear_mode",
        )
    if "quantity" in data or "power" in data:
        quantity, unit, quantity_method = _common_quantity(data, suffix="_fission")
    else:
        output_unit = str(data.get("output_unit", "MWh_fission"))
        if "mass_defect_kg" in data:
            quantity = _physical_call(
                nuclear_mass_energy,
                _required_number(data, "mass_defect_kg", nonnegative=True),
                output_unit=output_unit,
            )
            quantity_method = "quantity.nuclear.mass_defect.v1"
        else:
            quantity = _physical_call(
                fission_reaction_energy,
                _required_number(data, "isotope_mass_kg", nonnegative=True),
                _required_number(data, "atomic_mass_g_mol", positive=True),
                _required_number(data, "energy_per_fission_mev", positive=True),
                fissioned_fraction=_optional_number(data, "fissioned_fraction", 1.0),
                output_unit=output_unit,
            )
            quantity_method = "quantity.nuclear.isotope_fission_count.v1"
        unit = _carrier_unit(output_unit, "_fission")
    factor_value = data.get("accessible_fraction", data.get("fx", data.get("exergy_factor")))
    if factor_value is None:
        raise StreamCalculationError(
            "missing_input",
            "nuclear inventory requires accessible_fraction (or fx); reactor heat and electricity should be reported at their own boundaries",
            field="accessible_fraction",
        )
    factor = _finite_nonnegative(factor_value, "accessible_fraction")
    if factor > 1.0:
        raise StreamCalculationError(
            "out_of_range", "accessible_fraction must not exceed 1", field="accessible_fraction"
        )
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference="declared nuclear reaction and accessible fuel-cycle boundary",
        boundary=str(data.get("boundary", "nuclear fuel inventory")),
        basis="nuclear reaction energy multiplied by declared accessible fraction",
        method="fission",
        method_id="fission.inventory.accessible_fraction.v1",
        tier="F2",
        label=_label(data) or "nuclear fission energy inventory",
        metadata={
            "accessible_fraction": factor,
            "fissioned_fraction": data.get("fissioned_fraction"),
            "energy_per_fission_mev": data.get("energy_per_fission_mev"),
        },
    )
    return record, quantity_method


def _nuclear_reaction_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    if "accessible_fraction" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "accessible_fraction belongs to a nuclear inventory; reaction-product energy must be partitioned by physical output channel",
            field="accessible_fraction",
        )
    preset_key = str(data.get("reaction_preset", "")).strip().lower().replace("-", "_")
    preset = None
    if preset_key:
        try:
            preset = _NUCLEAR_REACTION_PRESETS[preset_key]
        except KeyError as exc:
            raise StreamCalculationError(
                "unsupported_reaction",
                f"unknown reaction_preset: {preset_key}. Supported presets: {', '.join(sorted(_NUCLEAR_REACTION_PRESETS))}",
                field="reaction_preset",
            ) from exc
    if preset is not None and any(
        key in data
        for key in ("q_value_mev", "reactant_atomic_masses_u", "product_atomic_masses_u")
    ):
        raise StreamCalculationError(
            "conflicting_inputs",
            "reaction_preset supplies its Q-value; do not also provide q_value_mev or atomic masses",
            field="reaction_preset",
        )
    if (
        preset is None
        and "q_value_mev" in data
        and any(key in data for key in ("reactant_atomic_masses_u", "product_atomic_masses_u"))
    ):
        raise StreamCalculationError(
            "conflicting_inputs",
            "provide q_value_mev or matching atomic-mass arrays, not both",
            field="q_value_mev",
        )
    if (preset is not None or "reaction_channels" in data) and any(
        key in data for key in ("fx", "exergy_factor")
    ):
        raise StreamCalculationError(
            "conflicting_inputs",
            "product channels determine reaction quality; do not also provide a total-stream factor",
            field="fx",
        )

    output_unit = str(data.get("output_unit", "MWh_nuclear"))
    reaction_count = None
    if "mass_defect_kg" in data:
        if any(
            field in data
            for field in (
                "reaction_count",
                "reaction_amount_mol",
                "reactant_1_number_density_m3",
                "reactant_2_number_density_m3",
                "reactivity_m3_s",
                "duration_seconds",
                "duration_hours",
                "q_value_mev",
                "reactant_atomic_masses_u",
                "product_atomic_masses_u",
            )
        ):
            raise StreamCalculationError(
                "conflicting_inputs",
                "mass_defect_kg directly supplies total reaction energy and cannot be combined with event-count or Q-value inputs",
                field="mass_defect_kg",
            )
        total_quantity = _physical_call(
            nuclear_mass_energy,
            _required_number(data, "mass_defect_kg", nonnegative=True),
            output_unit=output_unit,
        )
        q_value = float(preset["q_value_mev"]) if preset is not None else None
        quantity_method = "quantity.nuclear.reaction_mass_defect.v1"
    else:
        if preset is not None:
            q_value = float(preset["q_value_mev"])
        elif "q_value_mev" in data:
            q_value = _required_number(data, "q_value_mev", positive=True)
        elif "reactant_atomic_masses_u" in data or "product_atomic_masses_u" in data:
            mass_convention = str(data.get("mass_convention", "")).strip()
            if not mass_convention:
                raise StreamCalculationError(
                    "missing_provenance",
                    "atomic-mass Q-value inputs require mass_convention so atomic and nuclear masses are not mixed",
                    field="mass_convention",
                )
            q_value = _physical_call(
                nuclear_reaction_q_value_mev,
                _number_sequence(data, "reactant_atomic_masses_u", positive=True),
                _number_sequence(data, "product_atomic_masses_u", positive=True),
            )
        else:
            raise StreamCalculationError(
                "missing_input",
                "reaction mode requires reaction_preset, q_value_mev, matching atomic-mass arrays, or mass_defect_kg",
                field="q_value_mev",
            )
        count_paths = [
            "reaction_count" in data,
            "reaction_amount_mol" in data,
            any(
                key in data
                for key in (
                    "reactant_1_number_density_m3",
                    "reactant_2_number_density_m3",
                    "reactivity_m3_s",
                )
            ),
        ]
        if sum(count_paths) != 1:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide exactly one reaction-count path: reaction_count, reaction_amount_mol, or density/reactivity/volume/duration",
                field="reaction_count",
            )
        if count_paths[0]:
            reaction_count = _required_number(data, "reaction_count", nonnegative=True)
            quantity_method = "quantity.nuclear.reaction_count_q_value.v1"
        elif count_paths[1]:
            reaction_count = (
                _required_number(data, "reaction_amount_mol", nonnegative=True) * 6.022_140_76e23
            )
            quantity_method = "quantity.nuclear.reaction_extent_q_value.v1"
        else:
            reactivity_source = str(data.get("reactivity_source", "")).strip()
            if not reactivity_source:
                raise StreamCalculationError(
                    "missing_provenance",
                    "density/reactivity fusion calculations require reactivity_source for the supplied <sigma v>",
                    field="reactivity_source",
                )
            duration_seconds = _reaction_duration_seconds(data)
            reaction_count = _physical_call(
                fusion_reaction_count,
                _required_number(data, "reactant_1_number_density_m3", nonnegative=True),
                _required_number(data, "reactant_2_number_density_m3", nonnegative=True),
                _required_number(data, "reactivity_m3_s", nonnegative=True),
                _required_number(data, "volume_m3", nonnegative=True),
                duration_seconds,
                identical_reactants=_optional_boolean(data, "identical_reactants", False),
            )
            quantity_method = "quantity.nuclear.fusion_reactivity_volume_time.v1"
        total_quantity = _physical_call(
            nuclear_reaction_energy,
            reaction_count,
            q_value,
            output_unit=output_unit,
        )

    channels = _nuclear_channels(data, preset)
    selected = str(data.get("nuclear_channel", "total")).strip().lower().replace("-", "_")
    if channels:
        if selected == "total":
            quantity = total_quantity
            unit = _carrier_unit(output_unit, "_nuclear")
            factor = sum(channel["fraction"] * channel["exergy_factor"] for channel in channels)
            if math.isclose(factor, 1.0, rel_tol=0.0, abs_tol=1e-12):
                factor = 1.0
            selected_channel = None
        else:
            selected_channel = next(
                (channel for channel in channels if channel["name_key"] == selected), None
            )
            if selected_channel is None:
                names = ", ".join(channel["name_key"] for channel in channels)
                raise StreamCalculationError(
                    "unknown_channel",
                    f"unknown nuclear_channel: {selected}. Available channels: total, {names}",
                    field="nuclear_channel",
                )
            quantity = total_quantity * selected_channel["fraction"]
            unit = _carrier_unit(
                output_unit, _nuclear_carrier_suffix(str(selected_channel["carrier"]))
            )
            factor = selected_channel["exergy_factor"]
    else:
        if selected != "total":
            raise StreamCalculationError(
                "missing_input",
                "nuclear_channel requires reaction_channels or a reaction preset",
                field="reaction_channels",
            )
        declared_factor = data.get("fx", data.get("exergy_factor"))
        if declared_factor is None:
            raise StreamCalculationError(
                "missing_quality",
                "a non-preset reaction requires reaction_channels with channel Exergy Factors, or fx for the total product stream",
                field="reaction_channels",
            )
        quantity = total_quantity
        unit = _carrier_unit(output_unit, "_nuclear")
        factor = _finite_nonnegative(declared_factor, "fx")
        if factor > 1.0:
            raise StreamCalculationError(
                "out_of_range",
                "a released nuclear product stream Exergy Factor must not exceed 1",
                field="fx",
            )
        selected_channel = None

    reaction_name = str(preset["name"]) if preset is not None else "declared nuclear reaction"
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        reference="declared nuclear reaction products and receiving environment",
        boundary=str(data.get("boundary", "nuclear reaction-product boundary")),
        basis=(
            "reaction Q-value partitioned into physical product channels; downstream deposition and conversion losses are excluded"
        ),
        method="nuclear",
        method_id="nuclear.reaction.product_channel.v1",
        tier="F2",
        label=_label(data)
        or (
            f"{reaction_name} {selected.replace('_', ' ')}"
            if selected != "total"
            else f"{reaction_name} total products"
        ),
        metadata={
            "nuclear_mode": "reaction",
            "reaction_preset": preset_key or None,
            "q_value_mev": q_value,
            "reaction_count": reaction_count,
            "selected_channel": selected,
            "total_reaction_energy": total_quantity,
            "total_reaction_energy_unit": _carrier_unit(output_unit, "_nuclear"),
            "channels": [
                {key: value for key, value in channel.items() if key != "name_key"}
                for channel in channels
            ],
            "reactivity_source": data.get("reactivity_source"),
            "mass_convention": data.get(
                "mass_convention", preset.get("mass_convention") if preset is not None else None
            ),
            "reaction_data_source": (
                preset.get("reaction_data_source")
                if preset is not None
                else data.get("property_source")
            ),
            "constants_source": PHYSICAL_CONSTANTS_SOURCE,
        },
        assumptions=(
            "reaction Q-value and product fractions are boundary quantities; downstream transport, deposition, and conversion are excluded",
            *(
                (
                    "density, reactivity, and reacting volume are uniform and constant over the declared interval; depletion is excluded",
                )
                if quantity_method == "quantity.nuclear.fusion_reactivity_volume_time.v1"
                else ()
            ),
        ),
    )
    return record, quantity_method


def _dissipation_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    model = str(data.get("loss_model", "")).strip().lower().replace("-", "_")
    if not model:
        if "drag_coefficient" in data:
            model = "aerodynamic_drag"
        elif "coefficient_of_rolling_resistance" in data:
            model = "rolling_resistance"
        else:
            model = "friction_force"
    output_unit = str(data.get("output_unit", "kWh_th"))
    if model in {"friction", "friction_force"}:
        quantity = _physical_call(
            friction_loss_energy,
            _required_number(data, "friction_force_n", nonnegative=True),
            _required_number(data, "distance_m", nonnegative=True),
            output_unit=output_unit,
        )
        quantity_method = "quantity.loss.friction_force_distance.v1"
    elif model in {"rolling", "rolling_resistance"}:
        quantity = _physical_call(
            rolling_friction_loss_energy,
            _required_number(data, "coefficient_of_rolling_resistance", nonnegative=True),
            _required_number(data, "normal_force_n", nonnegative=True),
            _required_number(data, "distance_m", nonnegative=True),
            output_unit=output_unit,
        )
        quantity_method = "quantity.loss.rolling_resistance.v1"
    elif model in {"drag", "air_resistance", "aerodynamic_drag"}:
        quantity = _physical_call(
            aerodynamic_drag_loss_energy,
            _required_number(data, "fluid_density_kg_m3", nonnegative=True),
            _required_number(data, "drag_coefficient", nonnegative=True),
            _required_number(data, "frontal_area_m2", nonnegative=True),
            _required_number(data, "relative_speed_m_s", nonnegative=True),
            distance_m=_optional_number(data, "distance_m", None),
            duration_hours=_optional_number(data, "duration_hours", None),
            output_unit=output_unit,
        )
        quantity_method = "quantity.loss.aerodynamic_drag.v1"
    else:
        raise StreamCalculationError(
            "unsupported_mode",
            "loss_model must be friction_force, rolling_resistance, or aerodynamic_drag",
            field="loss_model",
        )
    sink_c = _optional_number(data, "sink_c", 20.0)
    dissipation_c = _optional_number(data, "dissipation_c", sink_c)
    factor = thermal_exergy_factor_c(dissipation_c, sink_c)
    destroyed = quantity * (1.0 - factor)
    record = QuantityQualityRecord(
        quantity=quantity,
        unit=_carrier_unit(output_unit, "_th"),
        exergy_factor=factor,
        reference=f"T0 = {sink_c:g} C",
        boundary=str(data.get("boundary", "dissipation boundary after mechanical loss")),
        basis=(
            f"mechanical work dissipated as heat at {dissipation_c:g} C; residual heat uses "
            "the Carnot factor"
        ),
        method="dissipation",
        method_id=f"dissipation.{model}.to_heat.v1",
        tier="F2",
        label=_label(data) or f"{model.replace('_', ' ')} dissipation",
        source_c=dissipation_c,
        sink_c=sink_c,
        assumptions=(
            "all calculated resisting work becomes heat at the declared dissipation temperature",
        ),
        metadata={
            "loss_model": model,
            "mechanical_work_lost": quantity,
            "mechanical_work_lost_unit": _carrier_unit(output_unit, "_m"),
            "residual_heat_exergy": quantity * factor,
            "exergy_destroyed": destroyed,
            "exergy_unit": exergy_unit(output_unit),
        },
    )
    return record, quantity_method


def _fuel_stream(data: Mapping[str, object]) -> Tuple[QuantityQualityRecord, str]:
    fuel_name = str(data.get("fuel", "natural gas"))
    basis = str(data.get("basis", "HHV")).upper()
    conversion = None
    note = ""
    mixture = None
    extra_assumptions: tuple[str, ...] = ()
    extra_warnings: tuple[str, ...] = ()
    if "components" in data:
        if any(
            field in data
            for field in ("chemical_exergy", "energy_basis_value", "fx", "exergy_factor")
        ):
            raise StreamCalculationError(
                "conflicting_inputs",
                "components is a complete quality path; do not also provide chemical_exergy, energy_basis_value, fx, or exergy_factor",
                field="components",
            )
        components = data["components"]
        if not isinstance(components, list):
            raise StreamCalculationError(
                "invalid_composition", "components must be an array", field="components"
            )
        mixture = _physical_call(chemical_mixture_properties, components)
        data = {
            **data,
            "heating_value": mixture["heating_value_mj_kg"],
            "heating_value_unit": "MJ/kg",
            "chemical_exergy": mixture["chemical_exergy_mj_kg"],
            "energy_basis_value": mixture["heating_value_mj_kg"],
        }
        extra_warnings = (
            "mixture factor excludes non-ideal mixing exergy; supply a complete mixture chemical-exergy value when material",
        )
    moisture = _optional_number(data, "moisture_fraction", None)
    ash = _optional_number(data, "ash_fraction", None)
    for field, value in (("moisture_fraction", moisture), ("ash_fraction", ash)):
        if value is not None and not 0.0 <= value <= 1.0:
            raise StreamCalculationError(
                "out_of_range", f"{field} must be between 0 and 1", field=field
            )
    if moisture is not None and ash is not None and moisture + ash > 1.0:
        raise StreamCalculationError(
            "invalid_composition",
            "moisture_fraction plus ash_fraction must not exceed 1",
            field="ash_fraction",
        )
    has_mass = "mass" in data
    has_volume = "volume" in data
    if has_mass and has_volume:
        raise StreamCalculationError(
            "conflicting_inputs", "provide mass or volume, not both", field="mass"
        )
    if has_mass or has_volume or "heating_value" in data:
        if "quantity" in data or "power" in data:
            raise StreamCalculationError(
                "conflicting_inputs",
                "provide mass or volume with heating value, quantity, or power and duration; use only one quantity path",
            )
        symbol = FUEL_SYMBOLS.get(_fuel_key(fuel_name), _fuel_key(fuel_name))
        output_unit = str(data.get("output_unit", f"MWh_{basis}_{symbol}"))
        if has_volume:
            quantity = energy_from_volume(
                _required_number(data, "volume", nonnegative=True),
                _required_number(data, "heating_value", positive=True),
                volume_unit=str(data.get("volume_unit", "m3")),
                heating_value_unit=str(data.get("heating_value_unit", "MJ/m3")),
                output_unit=output_unit,
            )
            quantity_method = "quantity.fuel.volume_heating_value.v1"
        else:
            mass_value = _required_number(data, "mass", nonnegative=True)
            mass_unit = str(data.get("mass_unit", "kg"))
            heating_value_basis = str(data.get("heating_value_basis", "as_received")).lower()
            if heating_value_basis in {"dry", "dry_basis"}:
                moisture = _required_number(data, "moisture_fraction", nonnegative=True)
                mass_value = _mass_kg(mass_value, mass_unit) * (1.0 - moisture)
                mass_unit = "kg"
                extra_assumptions = (
                    f"dry-basis heating value applied to dry matter after removing {moisture:.3g} mass-fraction moisture",
                )
                extra_warnings = (
                    *extra_warnings,
                    "a measured as-received heating value is preferred because drying and vaporization requirements are process-specific",
                )
            elif heating_value_basis not in {"as_received", "received", "wet"}:
                raise StreamCalculationError(
                    "unsupported_mode",
                    "heating_value_basis must be as_received or dry",
                    field="heating_value_basis",
                )
            quantity = energy_from_mass(
                mass_value,
                _required_number(data, "heating_value", positive=True),
                mass_unit=mass_unit,
                heating_value_unit=str(data.get("heating_value_unit", "MJ/kg")),
                output_unit=output_unit,
            )
            quantity_method = "quantity.fuel.mass_heating_value.v1"
        unit = output_unit
    else:
        supplied_unit = str(data.get("unit", ""))
        conversion = fuel_volume_conversion(supplied_unit) if supplied_unit else None
        if conversion is not None:
            amount = _required_number(data, "quantity", nonnegative=True)
            mwh_per_unit, reference_id, reference_basis, note = conversion
            if "fuel" not in data:
                fuel_name = "crude oil" if "crude" in reference_id else "natural gas"
            if "basis" not in data and reference_basis in {"HHV", "LHV"}:
                basis = reference_basis
            symbol = FUEL_SYMBOLS.get(_fuel_key(fuel_name), _fuel_key(fuel_name))
            output_unit = str(data.get("output_unit", f"MWh_{basis}_{symbol}"))
            quantity = convert_energy(amount * mwh_per_unit, "MWh", output_unit)
            unit = output_unit
            quantity_method = "quantity.fuel.volume_reference_heating_value.v1"
            data = {**data, "heating_value_assumption": note}
        else:
            quantity, unit, quantity_method = _common_quantity(data, suffix="")
            symbol = FUEL_SYMBOLS.get(_fuel_key(fuel_name), _fuel_key(fuel_name))
            unit = _ensure_suffix(unit, f"_{basis}_{symbol}")
    has_declared_factor_inputs = "chemical_exergy" in data or "energy_basis_value" in data
    if has_declared_factor_inputs:
        record = chemical(
            quantity,
            unit,
            chemical_exergy=_required_number(data, "chemical_exergy", positive=True),
            energy_basis=_required_number(data, "energy_basis_value", positive=True),
            basis_label=basis,
            boundary=str(data.get("boundary", "fuel inventory or fuel-flow meter")),
            label=_label(data) or f"{fuel_name} on {basis} basis",
        )
        record = replace(
            record,
            fuel=_fuel_key(fuel_name),
            energy_basis=basis,
            metadata={
                **record.metadata,
                "quality_basis_unit": str(
                    data.get("quality_basis_unit", "matching caller-supplied units")
                ),
                "property_source": str(data.get("property_source", "caller supplied")),
            },
        )
    elif "fx" in data or "exergy_factor" in data:
        factor = _finite_nonnegative(data.get("fx", data.get("exergy_factor")), "fx")
        record = report(
            quantity,
            unit,
            fx=factor,
            reference=str(data.get("reference", f"declared {basis} chemical reference")),
            boundary=str(data.get("boundary", "fuel inventory or fuel-flow meter")),
            basis=f"declared chemical exergy factor on {basis} basis",
            label=_label(data) or f"{fuel_name} on {basis} basis",
            method="fuel",
            tier="F2",
        )
        record = replace(record, fuel=_fuel_key(fuel_name), energy_basis=basis)
    else:
        try:
            record = fuel(
                quantity,
                fuel_name,
                basis=basis,
                unit=unit,
                boundary=str(data.get("boundary", "fuel inventory or fuel-flow meter")),
            )
        except ValueError as exc:
            raise StreamCalculationError(
                "missing_quality",
                f"{fuel_name} has no universal Exergy Factor; provide chemical_exergy and energy_basis_value, a component analysis, or fx",
                field="chemical_exergy",
            ) from exc
    if mixture is not None:
        record = replace(
            record,
            method_id="chemical.mixture.supplied_component_properties.v1",
            tier="F2",
            metadata={**record.metadata, **mixture},
        )
    if conversion is not None:
        record = replace(
            record,
            data_quality_flag="estimated_reference",
            assumptions=(f"heating value assumed: {note}",),
            warnings=(
                "fuel-volume energy uses a statistical estimate; provide a measured heating "
                "value for a meter-specific result",
            ),
        )
    if extra_assumptions or extra_warnings:
        record = replace(
            record,
            assumptions=(*record.assumptions, *extra_assumptions),
            warnings=(*record.warnings, *extra_warnings),
        )
    fuel_key = _fuel_key(fuel_name)
    if fuel_key in {"biomass", "biogas", "syngas", "waste", "waste_fuel"}:
        heterogeneous_metadata = {
            "heating_value_basis": str(data.get("heating_value_basis", "as_received")),
            "feedstock_class": data.get("feedstock_class"),
            "moisture_fraction": moisture,
            "ash_fraction": ash,
            "composition_source": data.get("composition_source"),
        }
        record = replace(
            record,
            metadata={
                **record.metadata,
                **{
                    key: value for key, value in heterogeneous_metadata.items() if value is not None
                },
            },
            warnings=(
                *record.warnings,
                *(
                    ()
                    if data.get("feedstock_class")
                    else (
                        "feedstock_class is recommended because heterogeneous bioenergy properties vary by material",
                    )
                ),
            ),
        )
    return record, quantity_method


def _common_quantity(data: Mapping[str, object], *, suffix: str) -> Tuple[float, str, str]:
    has_quantity = "quantity" in data
    has_power = "power" in data
    if has_quantity and has_power:
        raise StreamCalculationError(
            "conflicting_inputs", "provide quantity or power and duration, not both"
        )
    if has_quantity:
        quantity = _required_number(data, "quantity", nonnegative=True)
        unit = str(data.get("unit", "")).strip()
        if not unit:
            raise StreamCalculationError(
                "missing_input", "unit is required with quantity", field="unit"
            )
        if not is_energy_unit(unit):
            raise StreamCalculationError(
                "unsupported_unit", f"{unit} is not a supported energy unit", field="unit"
            )
        output_unit = str(data.get("output_unit", "")).strip()
        if output_unit:
            quantity = convert_energy(quantity, unit, output_unit)
            unit = output_unit
        return quantity, _ensure_suffix(unit, suffix), "quantity.supplied.v1"
    if has_power:
        power_unit = str(data.get("power_unit", "")).strip()
        if not power_unit:
            raise StreamCalculationError(
                "missing_input", "power_unit is required with power", field="power_unit"
            )
        default_output = _POWER_ENERGY_UNITS.get(power_unit.partition("_")[0].lower())
        if default_output is None:
            raise StreamCalculationError(
                "unsupported_unit", f"unsupported power_unit: {power_unit}", field="power_unit"
            )
        output_unit = str(data.get("output_unit", _ensure_suffix(default_output, suffix)))
        quantity = energy_from_power(
            _required_number(data, "power", nonnegative=True),
            _required_number(data, "duration_hours", nonnegative=True),
            power_unit=power_unit,
            output_unit=output_unit,
        )
        return quantity, _ensure_suffix(output_unit, suffix), "quantity.power_times_duration.v1"
    raise StreamCalculationError(
        "missing_input",
        "provide quantity and unit, or power, power_unit, and duration_hours",
        field="quantity",
    )


def _ensure_suffix(unit: str, suffix: str) -> str:
    if not suffix or "_" in unit:
        return unit
    return f"{unit}{suffix}"


def _carrier_unit(unit: str, suffix: str) -> str:
    """Attach the calculated carrier, replacing a conflicting supplied suffix."""

    base = str(unit).partition("_")[0]
    return f"{base}{suffix}" if suffix else base


def _mass_kg(value: object, unit: str) -> float:
    mass = _finite_nonnegative(value, "mass")
    key = str(unit).strip().lower().replace(" ", "").replace("_", "")
    factor = _MASS_TO_KG.get(key)
    if factor is None:
        known = ", ".join(sorted(_MASS_TO_KG))
        raise StreamCalculationError(
            "unsupported_unit",
            f"unsupported mass_unit: {unit}. Supported units: {known}",
            field="mass_unit",
        )
    return mass * factor


def _volume_m3(value: object, unit: str) -> float:
    volume = _finite_nonnegative(value, "volume")
    key = str(unit).strip().lower().replace(" ", "").replace("_", "")
    factor = _VOLUME_TO_M3.get(key)
    if factor is None:
        known = ", ".join(sorted(_VOLUME_TO_M3))
        raise StreamCalculationError(
            "unsupported_unit",
            f"unsupported volume_unit: {unit}. Supported units: {known}",
            field="volume_unit",
        )
    return volume * factor


def _specific_energy_key(unit: str) -> str:
    return str(unit).strip().lower().replace(" ", "").replace("per", "/")


def _fuel_key(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def _total_mass_kg(data: Mapping[str, object]) -> float:
    has_mass = "mass" in data
    has_flow = "mass_flow_kg_s" in data
    if has_mass and has_flow:
        raise StreamCalculationError(
            "conflicting_inputs", "provide mass or mass_flow_kg_s, not both", field="mass"
        )
    if has_mass:
        return _mass_kg(data["mass"], str(data.get("mass_unit", "kg")))
    if has_flow:
        flow = _required_number(data, "mass_flow_kg_s", nonnegative=True)
        duration = _required_number(data, "duration_hours", nonnegative=True)
        return flow * duration * 3600.0
    raise StreamCalculationError(
        "missing_input", "provide mass or mass_flow_kg_s with duration_hours", field="mass"
    )


def _temperature_k(data: Mapping[str, object], prefix: str) -> float:
    key_k = f"{prefix}_k"
    key_c = f"{prefix}_c"
    if key_k in data:
        temperature = _required_number(data, key_k, positive=True)
    elif key_c in data:
        temperature = _required_number(data, key_c) + 273.15
        if temperature <= 0.0:
            raise StreamCalculationError(
                "out_of_range", f"{key_c} must be above absolute zero", field=key_c
            )
    else:
        raise StreamCalculationError("missing_input", f"provide {key_k} or {key_c}", field=key_k)
    return temperature


def _pressure_pa(data: Mapping[str, object], prefix: str) -> float:
    key_pa = f"{prefix}_pa"
    if key_pa in data:
        return _required_number(data, key_pa, positive=True)
    if prefix in data:
        return _physical_call(
            pressure_to_pa,
            _required_number(data, prefix, positive=True),
            str(data.get("pressure_unit", "Pa")),
        )
    raise StreamCalculationError(
        "missing_input", f"provide {key_pa} or {prefix} with pressure_unit", field=key_pa
    )


def _number_sequence(
    data: Mapping[str, object], field: str, *, positive: bool = False
) -> tuple[float, ...]:
    value = data.get(field)
    if not isinstance(value, (list, tuple)):
        raise StreamCalculationError(
            "invalid_value", f"{field} must be an array of numbers", field=field
        )
    converter = _finite_positive if positive else _finite_nonnegative
    return tuple(converter(item, field) for item in value)


def _reaction_duration_seconds(data: Mapping[str, object]) -> float:
    has_seconds = "duration_seconds" in data
    has_hours = "duration_hours" in data
    if has_seconds == has_hours:
        raise StreamCalculationError(
            "conflicting_inputs",
            "fusion reactivity requires exactly one of duration_seconds or duration_hours",
            field="duration_seconds",
        )
    if has_seconds:
        return _required_number(data, "duration_seconds", nonnegative=True)
    return _required_number(data, "duration_hours", nonnegative=True) * 3600.0


def _optional_boolean(data: Mapping[str, object], field: str, default: bool) -> bool:
    if field not in data:
        return default
    value = data[field]
    if not isinstance(value, bool):
        raise StreamCalculationError("invalid_value", f"{field} must be true or false", field=field)
    return value


def _nuclear_channels(
    data: Mapping[str, object], preset: Optional[Mapping[str, object]]
) -> list[dict[str, object]]:
    if preset is not None and "reaction_channels" in data:
        raise StreamCalculationError(
            "conflicting_inputs",
            "reaction_preset supplies product channels; do not also provide reaction_channels",
            field="reaction_channels",
        )
    raw_channels = (
        preset.get("channels", ()) if preset is not None else data.get("reaction_channels", ())
    )
    if not raw_channels:
        return []
    if not isinstance(raw_channels, (list, tuple)):
        raise StreamCalculationError(
            "invalid_channels", "reaction_channels must be an array", field="reaction_channels"
        )
    channels: list[dict[str, object]] = []
    for index, raw in enumerate(raw_channels):
        if not isinstance(raw, Mapping):
            raise StreamCalculationError(
                "invalid_channels",
                f"reaction_channels[{index}] must be an object",
                field="reaction_channels",
            )
        name = str(raw.get("name", "")).strip()
        carrier = str(raw.get("carrier", "")).strip().lower().replace("-", "_")
        if not name or not carrier:
            raise StreamCalculationError(
                "missing_input",
                f"reaction_channels[{index}] requires name and carrier",
                field="reaction_channels",
            )
        _nuclear_carrier_suffix(carrier)
        if raw.get("fraction") is None or raw.get("exergy_factor") is None:
            raise StreamCalculationError(
                "missing_input",
                f"reaction_channels[{index}] requires fraction and exergy_factor",
                field="reaction_channels",
            )
        fraction = _finite_nonnegative(raw["fraction"], f"reaction_channels[{index}].fraction")
        if fraction > 1.0:
            raise StreamCalculationError(
                "out_of_range",
                f"reaction_channels[{index}].fraction must not exceed 1",
                field="reaction_channels",
            )
        channel_factor = _finite_nonnegative(
            raw["exergy_factor"], f"reaction_channels[{index}].exergy_factor"
        )
        if channel_factor > 1.0:
            raise StreamCalculationError(
                "out_of_range",
                f"reaction_channels[{index}].exergy_factor must not exceed 1",
                field="reaction_channels",
            )
        channels.append(
            {
                "name": name,
                "name_key": name.lower().replace(" ", "_").replace("-", "_"),
                "carrier": carrier,
                "fraction": fraction,
                "exergy_factor": channel_factor,
            }
        )
    if not math.isclose(
        sum(float(channel["fraction"]) for channel in channels),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise StreamCalculationError(
            "invalid_channels",
            "reaction channel fractions must sum to 1",
            field="reaction_channels",
        )
    return channels


def _nuclear_carrier_suffix(carrier: str) -> str:
    suffixes = {
        "neutron": "_neutron",
        "charged_particle": "_charged_particle",
        "alpha": "_charged_particle",
        "photon": "_rad",
        "gamma": "_rad",
        "xray": "_rad",
        "x_ray": "_rad",
        "neutrino": "_neutrino",
        "other": "_nuclear",
        "nuclear": "_nuclear",
    }
    try:
        return suffixes[carrier]
    except KeyError as exc:
        raise StreamCalculationError(
            "unsupported_carrier",
            "nuclear channel carrier must be neutron, charged_particle, photon, gamma, xray, neutrino, nuclear, or other",
            field="reaction_channels",
        ) from exc


def _physical_call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except PhysicalCalculationError as exc:
        raise StreamCalculationError(exc.code, str(exc), field=exc.field) from exc


def _label(data: Mapping[str, object]) -> Optional[str]:
    value = str(data.get("label", "")).strip()
    return value or None


def _required_number(
    data: Mapping[str, object],
    field: str,
    *,
    nonnegative: bool = False,
    positive: bool = False,
) -> float:
    if field not in data or data[field] in (None, ""):
        raise StreamCalculationError("missing_input", f"{field} is required", field=field)
    if positive:
        return _finite_positive(data[field], field)
    if nonnegative:
        return _finite_nonnegative(data[field], field)
    return _finite_number(data[field], field)


def _optional_number(
    data: Mapping[str, object], field: str, default: Optional[float]
) -> Optional[float]:
    if field not in data or data[field] in (None, ""):
        return default
    return _finite_number(data[field], field)


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise StreamCalculationError(
            "invalid_number", f"{field} must be a finite number", field=field
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StreamCalculationError(
            "invalid_number", f"{field} must be a finite number", field=field
        ) from exc
    if not math.isfinite(number):
        raise StreamCalculationError(
            "invalid_number", f"{field} must be a finite number", field=field
        )
    return number


def _finite_nonnegative(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number < 0:
        raise StreamCalculationError("out_of_range", f"{field} must be nonnegative", field=field)
    return number


def _finite_positive(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number <= 0:
        raise StreamCalculationError("out_of_range", f"{field} must be positive", field=field)
    return number
