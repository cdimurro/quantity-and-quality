"""First-principles tests for the extended physical stream calculators."""

from __future__ import annotations

import math
import random

import pytest
from jsonschema import ValidationError, validate

import quantity_quality as qq


def test_mechanical_energy_equations_and_work_quality():
    assert qq.shaft_energy(1, 60, 1, output_unit="Wh_m") == pytest.approx(2 * math.pi)
    assert qq.kinetic_energy(2, 3, output_unit="J_m") == pytest.approx(9)
    assert qq.gravitational_potential_energy(2, 3, output_unit="J_m") == pytest.approx(
        2 * 9.80665 * 3
    )
    assert qq.rotational_energy(2, 60 / (2 * math.pi), output_unit="J_m") == pytest.approx(1)
    assert qq.elastic_energy(100, 0.2, output_unit="J_m") == pytest.approx(2)
    assert qq.hydraulic_energy(1, 1, pressure_unit="bar", output_unit="kJ_m") == pytest.approx(100)

    shaft = qq.calculate_stream(
        {
            "stream_type": "mechanical",
            "mechanical_mode": "shaft",
            "torque_nm": 500,
            "rotational_speed_rpm": 1800,
            "duration_hours": 2,
        }
    )
    assert shaft.quantity == pytest.approx(500 * 1800 * 2 * math.pi / 60 * 7200 / 3.6e6)
    assert shaft.unit == "kWh_m"
    assert shaft.fx == 1
    assert shaft.method_identifier == "mechanical.work_equivalent.v1"


def test_mechanical_reference_states_and_invalid_combinations_are_rejected():
    assert qq.kinetic_energy(10, 5, reference_velocity_m_s=5) == 0
    with pytest.raises(qq.PhysicalCalculationError, match="reference_velocity"):
        qq.kinetic_energy(10, 4, reference_velocity_m_s=5)
    with pytest.raises(qq.StreamCalculationError, match="mechanical_mode"):
        qq.calculate_stream({"stream_type": "mechanical", "mass": 1})
    with pytest.raises(qq.StreamCalculationError, match="exactly one model"):
        qq.calculate_stream(
            {
                "stream_type": "mechanical",
                "mass": 1,
                "velocity_m_s": 3,
                "height_difference_m": 2,
            }
        )


def test_electrical_measurement_and_field_energy_paths():
    assert qq.electrical_energy(100, 10, 1) == pytest.approx(1)
    assert qq.electrical_energy(100, 10, 1, phase="single_phase", power_factor=0.8) == (
        pytest.approx(0.8)
    )
    expected_three_phase = math.sqrt(3) * 400 * 10 * 0.9 * 2 / 1000
    result = qq.calculate_stream(
        {
            "stream_type": "electricity",
            "voltage_v": 400,
            "current_a": 10,
            "duration_hours": 2,
            "electrical_phase": "three_phase",
            "power_factor": 0.9,
        }
    )
    assert result.quantity == pytest.approx(expected_three_phase)
    assert result.unit == "kWh_e"
    assert qq.capacitor_energy(1, 10, output_unit="J_e") == pytest.approx(50)
    assert qq.inductor_energy(2, 3, output_unit="J_e") == pytest.approx(9)
    assert qq.battery_energy(100, 3.7) == pytest.approx(0.37)

    capacitor = qq.calculate_stream(
        {"stream_type": "electricity", "capacitance_f": 1, "voltage_v": 10}
    )
    assert capacitor.quantity == pytest.approx(50 / 3.6e6)
    with pytest.raises(qq.PhysicalCalculationError, match="DC"):
        qq.electrical_energy(100, 10, 1, phase="dc", power_factor=0.8)


def test_latent_heat_is_separate_from_sensible_heat():
    assert qq.phase_change_energy(1, 2257, output_unit="kJ_th") == pytest.approx(2257)
    steam = qq.calculate_stream(
        {
            "stream_type": "heat",
            "mass": 100,
            "latent_heat_kj_kg": 2257,
            "phase_change_c": 100,
            "sink_c": 20,
        }
    )
    assert steam.quantity == pytest.approx(225700 / 3600)
    assert steam.fx == pytest.approx(1 - 293.15 / 373.15)
    assert steam.method_identifier == "thermal.phase_change.constant_temperature.v1"
    with pytest.raises(qq.StreamCalculationError, match="combined sensible and latent"):
        qq.calculate_stream(
            {
                "stream_type": "heat",
                "mass": 1,
                "latent_heat_kj_kg": 2257,
                "phase_change_c": 100,
                "return_c": 20,
            }
        )


def test_ideal_gas_pressure_and_temperature_exergy():
    t0 = 293.15
    p0 = 101325.0
    result = qq.ideal_gas_physical_exergy(
        1,
        t0,
        2 * p0,
        reference_temperature_k=t0,
        reference_pressure_pa=p0,
        output_unit="J_m",
    )
    assert result == pytest.approx(287.05 * t0 * math.log(2))
    assert qq.ideal_gas_physical_exergy(
        10,
        t0,
        p0,
        reference_temperature_k=t0,
        reference_pressure_pa=p0,
        output_unit="J_m",
    ) == pytest.approx(0, abs=1e-12)

    stream = qq.calculate_stream(
        {
            "stream_type": "fluid",
            "property_model": "ideal_gas",
            "fluid": "Air",
            "mass": 100,
            "temperature_c": 40,
            "pressure_pa": 700000,
        }
    )
    assert stream.quantity > 0
    assert stream.unit == "kWh_m"
    assert stream.fx == 1


def test_supplied_enthalpy_entropy_path_uses_full_flow_exergy_equation():
    value = qq.physical_exergy_from_properties(
        2,
        500,
        1.5,
        100,
        0.5,
        300,
        velocity_m_s=10,
        height_difference_m=4,
        output_unit="kJ_m",
    )
    expected_kj_kg = (500 - 100) - 300 * (1.5 - 0.5) + (0.5 * 10**2 + 9.80665 * 4) / 1000
    assert value == pytest.approx(2 * expected_kj_kg)

    record = qq.calculate_stream(
        {
            "stream_type": "fluid",
            "property_model": "supplied_properties",
            "mass": 2,
            "enthalpy_kj_kg": 500,
            "entropy_kj_kg_k": 1.5,
            "reference_enthalpy_kj_kg": 100,
            "reference_entropy_kj_kg_k": 0.5,
            "reference_temperature_c": 26.85,
        }
    )
    assert record.quantity == pytest.approx(200 / 3600)
    assert record.fidelity_tier == "F2"


def test_coolprop_fluid_state_matches_independent_property_calls():
    coolprop = pytest.importorskip("CoolProp")
    from CoolProp.CoolProp import PropsSI

    result = qq.fluid_physical_exergy(
        "Air",
        100,
        temperature_c=40,
        pressure_pa=700000,
        reference_temperature_c=20,
        reference_pressure_pa=101325,
    )
    h = PropsSI("Hmass", "T", 313.15, "P", 700000, "Air")
    s = PropsSI("Smass", "T", 313.15, "P", 700000, "Air")
    h0 = PropsSI("Hmass", "T", 293.15, "P", 101325, "Air")
    s0 = PropsSI("Smass", "T", 293.15, "P", 101325, "Air")
    expected_kwh = 100 * ((h - h0) - 293.15 * (s - s0)) / 3.6e6
    assert result["quantity"] == pytest.approx(expected_kwh, rel=1e-12)
    assert result["property_backend_version"] == coolprop.__version__


def test_condensing_steam_state_change_matches_enthalpy_entropy_definition():
    pytest.importorskip("CoolProp")
    from CoolProp.CoolProp import PropsSI

    record = qq.calculate_stream(
        {
            "stream_type": "fluid",
            "fluid": "Water",
            "mass": 1000,
            "inlet_pressure_pa": 1_000_000,
            "inlet_vapor_quality": 1,
            "outlet_pressure_pa": 1_000_000,
            "outlet_vapor_quality": 0,
            "reported_energy_basis": "enthalpy_change",
            "reference_temperature_c": 20,
        }
    )
    metadata = record.metadata
    delta_h = metadata["inlet"]["enthalpy_kj_kg"] - metadata["outlet"]["enthalpy_kj_kg"]
    delta_s = metadata["inlet"]["entropy_kj_kg_k"] - metadata["outlet"]["entropy_kj_kg_k"]
    assert record.quantity == pytest.approx(1000 * delta_h / 3600)
    assert record.accessible_exergy == pytest.approx(1000 * (delta_h - 293.15 * delta_s) / 3600)
    # Condensation is isothermal at saturation, so this independently reduces to Carnot.
    saturation_c = PropsSI("T", "P", 1_000_000, "Q", 0, "Water") - 273.15
    assert record.fx == pytest.approx(qq.thermal_exergy_factor_c(saturation_c, 20), rel=1e-9)
    # The library's separate IAPWS-IF97 saturation equation remains close to
    # CoolProp's Helmholtz-equation backend; their documented formulations are
    # not numerically identical away from benchmark rounding points.
    assert qq.steam_saturation_temperature_c(10) == pytest.approx(saturation_c, abs=0.01)
    assert record.quantity == pytest.approx(559.609315, rel=1e-6)
    assert record.accessible_exergy == pytest.approx(197.491592, rel=1e-6)
    assert record.missing_context == ()
    assert record.conformance_issues == ()
    assert not record.needs_attention


def test_refrigerant_and_cryogenic_states_use_the_same_fluid_contract():
    pytest.importorskip("CoolProp")
    refrigerant = qq.calculate_stream(
        {
            "stream_type": "fluid",
            "fluid": "R134a",
            "mass": 10,
            "temperature_c": 40,
            "pressure_pa": 1_000_000,
        }
    )
    cryogen = qq.calculate_stream(
        {
            "stream_type": "fluid",
            "fluid": "Nitrogen",
            "mass": 10,
            "temperature_c": -190,
            "pressure_pa": 200000,
        }
    )
    assert refrigerant.quantity >= 0
    assert cryogen.quantity > 0
    assert refrigerant.metadata["property_backend"] == "CoolProp"


def test_humid_air_exergy_includes_temperature_pressure_and_composition():
    t0 = 293.15
    p0 = 101325.0
    w0 = 0.0073
    assert qq.humid_air_physical_exergy(
        100,
        t0,
        p0,
        w0,
        reference_temperature_k=t0,
        reference_pressure_pa=p0,
        reference_humidity_ratio=w0,
        output_unit="J_m",
    ) == pytest.approx(0, abs=1e-8)

    state = qq.calculate_stream(
        {
            "stream_type": "humid_air",
            "dry_air_mass_kg": 1000,
            "temperature_c": 30,
            "pressure_pa": 101325,
            "relative_humidity": 0.6,
            "reference_temperature_c": 20,
            "reference_relative_humidity": 0.5,
        }
    )
    assert state.quantity > 0
    assert state.metadata["humidity_ratio"] > state.metadata["reference_humidity_ratio"]
    assert state.distinguishability["basis"].startswith("humid_air")


def test_radiation_generalizes_petela_without_changing_solar():
    source_k = 1173.15
    reference_k = 293.15
    ratio = reference_k / source_k
    expected = 1 - 4 * ratio / 3 + ratio**4 / 3
    assert qq.blackbody_radiation_exergy_factor(source_k, reference_k) == pytest.approx(expected)
    record = qq.calculate_stream(
        {
            "stream_type": "radiation",
            "quantity": 1,
            "unit": "MWh_rad",
            "source_temperature_c": 900,
            "reference_c": 20,
        }
    )
    assert record.fx == pytest.approx(expected)
    assert record.unit == "MWh_rad"
    assert record.distinguishability["basis"] == "radiative_state_difference"


def test_ideal_separation_is_gibbs_mixing_work():
    fractions = [0.21, 0.79]
    expected = (
        -1000
        * qq.MOLAR_GAS_CONSTANT_J_MOL_K
        * 298.15
        * sum(value * math.log(value) for value in fractions)
    )
    assert qq.ideal_mixture_separation_energy(
        1000, fractions, 298.15, output_unit="J_m"
    ) == pytest.approx(expected)
    record = qq.calculate_stream(
        {
            "stream_type": "separation",
            "amount_mol": 1000,
            "mole_fractions": fractions,
            "temperature_k": 298.15,
        }
    )
    assert record.accessible_exergy == record.quantity
    with pytest.raises(qq.PhysicalCalculationError, match="sum to 1"):
        qq.ideal_mixture_separation_energy(1, [0.2, 0.7], 300)


def test_biomass_and_bioenergy_require_real_fuel_quality_inputs():
    biomass = qq.calculate_stream(
        {
            "stream_type": "biomass",
            "mass": 1000,
            "heating_value": 18,
            "heating_value_unit": "MJ/kg",
            "basis": "LHV",
            "chemical_exergy": 19,
            "energy_basis_value": 18,
        }
    )
    assert biomass.quantity == pytest.approx(5)
    assert biomass.unit == "MWh_LHV_biomass"
    assert biomass.fx == pytest.approx(19 / 18)
    assert biomass.fuel == "biomass"
    assert biomass.stream_type == "fuel"

    dry = qq.calculate_stream(
        {
            "stream_type": "bioenergy",
            "mass": 1000,
            "heating_value": 20,
            "heating_value_basis": "dry",
            "moisture_fraction": 0.2,
            "basis": "HHV",
            "chemical_exergy": 21,
            "energy_basis_value": 20,
        }
    )
    assert dry.quantity == pytest.approx(800 * 20 / 3600)
    assert dry.assumptions
    assert dry.warnings

    with pytest.raises(qq.StreamCalculationError, match="no universal Exergy Factor"):
        qq.calculate_stream(
            {
                "stream_type": "biomass",
                "mass": 1000,
                "heating_value": 18,
                "basis": "HHV",
            }
        )

    with pytest.raises(ValidationError):
        validate(
            {
                "stream_type": "biomass",
                "mass": 1000,
                "heating_value": 18,
                "basis": "HHV",
            },
            qq.load_stream_request_schema(),
        )


def test_biomass_metadata_and_composition_bounds_are_preserved():
    record = qq.calculate_stream(
        {
            "stream_type": "biomass",
            "mass": 100,
            "heating_value": 15,
            "chemical_exergy": 16,
            "energy_basis_value": 15,
            "quality_basis_unit": "MJ/kg as received",
            "feedstock_class": "wood chips",
            "moisture_fraction": 0.25,
            "ash_fraction": 0.03,
            "property_source": "lot analysis 2026-08-18",
        }
    )
    assert record.metadata["feedstock_class"] == "wood chips"
    assert record.metadata["moisture_fraction"] == pytest.approx(0.25)
    assert record.metadata["ash_fraction"] == pytest.approx(0.03)
    assert record.metadata["quality_basis_unit"] == "MJ/kg as received"
    with pytest.raises(qq.StreamCalculationError, match="must not exceed 1"):
        qq.calculate_stream(
            {
                "stream_type": "biomass",
                "mass": 1,
                "heating_value": 10,
                "chemical_exergy": 11,
                "energy_basis_value": 10,
                "moisture_fraction": 0.8,
                "ash_fraction": 0.3,
            }
        )


def test_composition_based_fuels_use_supplied_component_properties():
    components = [
        {
            "name": "dry biomass",
            "mass_fraction": 0.8,
            "heating_value_mj_kg": 20,
            "chemical_exergy_mj_kg": 21,
        },
        {
            "name": "water",
            "mass_fraction": 0.2,
            "heating_value_mj_kg": 0,
            "chemical_exergy_mj_kg": 0,
        },
    ]
    mixture = qq.chemical_mixture_properties(components)
    assert mixture["heating_value_mj_kg"] == pytest.approx(16)
    assert mixture["chemical_exergy_mj_kg"] == pytest.approx(16.8)
    assert mixture["exergy_factor"] == pytest.approx(1.05)
    record = qq.calculate_stream(
        {"stream_type": "fuel", "fuel": "biomass", "mass": 1000, "components": components}
    )
    assert record.quantity == pytest.approx(16_000 / 3600)
    assert record.fx == pytest.approx(1.05)
    assert record.data_quality_flag is None
    assert any("mixing exergy" in warning for warning in record.warnings)


def test_nuclear_inventory_calculations_do_not_invent_accessibility():
    assert qq.nuclear_mass_energy(1, output_unit="J_fission") == pytest.approx(
        qq.SPEED_OF_LIGHT_M_S**2
    )
    expected = 1 / 235 * qq.AVOGADRO_CONSTANT * 200e6 * 1.602176634e-19
    assert qq.fission_reaction_energy(0.001, 235, 200, output_unit="J_fission") == pytest.approx(
        expected
    )
    with pytest.raises(qq.StreamCalculationError, match="accessible_fraction"):
        qq.calculate_stream({"stream_type": "nuclear", "mass_defect_kg": 1e-9})
    record = qq.calculate_stream(
        {"stream_type": "nuclear", "mass_defect_kg": 1e-9, "accessible_fraction": 0.33}
    )
    assert record.fx == pytest.approx(0.33)


def test_friction_drag_and_rolling_losses_become_heat_and_exergy_destruction():
    assert qq.friction_loss_energy(10, 100, output_unit="J_m") == pytest.approx(1000)
    assert qq.rolling_friction_loss_energy(0.01, 10_000, 100, output_unit="J_m") == (
        pytest.approx(10_000)
    )
    drag_expected = 0.5 * 1.225 * 0.3 * 2.2 * 25**2 * 10_000
    assert qq.aerodynamic_drag_loss_energy(
        1.225, 0.3, 2.2, 25, distance_m=10_000, output_unit="J_m"
    ) == pytest.approx(drag_expected)

    ambient = qq.calculate_stream(
        {
            "stream_type": "dissipation",
            "loss_model": "aerodynamic_drag",
            "fluid_density_kg_m3": 1.225,
            "drag_coefficient": 0.3,
            "frontal_area_m2": 2.2,
            "relative_speed_m_s": 25,
            "distance_m": 10_000,
            "sink_c": 20,
        }
    )
    assert ambient.fx == 0
    assert ambient.metadata["exergy_destroyed"] == pytest.approx(ambient.quantity)
    assert ambient.metadata["residual_heat_exergy"] == 0

    hot_bearing = qq.calculate_stream(
        {
            "stream_type": "dissipation",
            "friction_force_n": 10,
            "distance_m": 100,
            "dissipation_c": 80,
            "sink_c": 20,
        }
    )
    assert hot_bearing.fx == pytest.approx(1 - 293.15 / 353.15)
    assert hot_bearing.metadata["exergy_destroyed"] < hot_bearing.quantity


def test_randomized_first_principles_invariants():
    rng = random.Random(20260818)
    for _ in range(1000):
        mass = rng.uniform(0, 1e5)
        velocity = rng.uniform(0, 200)
        height = rng.uniform(0, 1000)
        assert qq.kinetic_energy(mass, velocity, output_unit="J_m") == pytest.approx(
            0.5 * mass * velocity**2, rel=1e-15
        )
        assert qq.gravitational_potential_energy(mass, height, output_unit="J_m") == pytest.approx(
            mass * 9.80665 * height, rel=1e-15
        )


def test_extended_schema_and_capabilities_are_agent_discoverable():
    schema = qq.load_stream_request_schema()
    valid = [
        {"stream_type": "mechanical", "mass": 1, "velocity_m_s": 2},
        {
            "stream_type": "fluid",
            "mass": 1,
            "fluid": "Water",
            "pressure_pa": 101325,
            "vapor_quality": 0,
        },
        {
            "stream_type": "humid_air",
            "dry_air_mass_kg": 1,
            "temperature_c": 25,
            "pressure_pa": 101325,
            "relative_humidity": 0.5,
        },
        {
            "stream_type": "dissipation",
            "friction_force_n": 10,
            "distance_m": 2,
        },
    ]
    for request in valid:
        validate(request, schema)
    with pytest.raises(ValidationError):
        validate({"stream_type": "nuclear", "mass_defect_kg": 1e-9}, schema)

    capabilities = qq.stream_capabilities()
    assert "biomass" in capabilities["stream_type_aliases"]
    expected = {
        "mechanical",
        "fluid",
        "humid_air",
        "radiation",
        "separation",
        "nuclear",
        "dissipation",
    }
    assert expected <= set(capabilities["stream_types"])
    assert qq.carrier_family("MWh_LHV_biomass") == "chemical"
    assert qq.carrier_family("MWh_rad") == "radiative"
