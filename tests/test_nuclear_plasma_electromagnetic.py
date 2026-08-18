"""First-principles tests for fields, plasma states, and nuclear reactions."""

from __future__ import annotations

import math

import pytest
from jsonschema import ValidationError, validate

import quantity_quality as qq


def test_uniform_electromagnetic_field_energy_and_field_map_integral():
    volume = 2.0
    electric = 1000.0
    magnetic = 0.01
    expected_j = volume * (
        0.5 * qq.VACUUM_PERMITTIVITY_F_M * electric**2
        + magnetic**2 / (2 * qq.VACUUM_PERMEABILITY_H_M)
    )
    assert qq.electromagnetic_field_energy(
        volume,
        electric_field_v_m=electric,
        magnetic_flux_density_t=magnetic,
        output_unit="J_em",
    ) == pytest.approx(expected_j, rel=1e-15)
    assert qq.electromagnetic_field_energy(
        1, magnetic_flux_density_t=1, output_unit="J_em"
    ) == pytest.approx(397_887.357_782_272_5, rel=1e-14)
    assert qq.electromagnetic_field_map_energy(
        [
            {"volume_m3": 1, "electric_field_v_m": electric},
            {"volume_m3": 2, "magnetic_flux_density_t": magnetic},
        ],
        output_unit="J_em",
    ) == pytest.approx(
        0.5 * qq.VACUUM_PERMITTIVITY_F_M * electric**2
        + 2 * magnetic**2 / (2 * qq.VACUUM_PERMEABILITY_H_M)
    )
    assert (
        qq.electromagnetic_field_energy(
            1,
            electric_field_v_m=10,
            reference_electric_field_v_m=10,
            output_unit="J_em",
        )
        == 0
    )
    with pytest.raises(qq.PhysicalCalculationError, match="less stored energy"):
        qq.electromagnetic_field_energy(
            1,
            electric_field_v_m=5,
            reference_electric_field_v_m=10,
        )


def test_poynting_flux_and_plane_wave_energy_are_explicit_about_amplitude():
    assert qq.poynting_flux_energy(1000, 2, 1, output_unit="kWh_em") == pytest.approx(2)
    expected_kwh = 0.05308837459577507
    assert qq.plane_wave_energy(100, 2, 1, output_unit="kWh_em") == pytest.approx(expected_kwh)
    with pytest.raises(qq.PhysicalCalculationError, match="between 0 and 1"):
        qq.poynting_flux_energy(1, 1, 1, normal_or_capture_factor=1.1)

    record = qq.calculate_stream(
        {
            "stream_type": "electromagnetic_field",
            "electric_field_rms_v_m": 100,
            "area_m2": 2,
            "duration_hours": 1,
            "boundary": "receiving aperture",
        }
    )
    assert record.quantity == pytest.approx(expected_kwh)
    assert record.unit == "kWh_em"
    assert record.fx == 1
    assert record.distinguishability["basis"] == "electromagnetic_field_or_flux_difference"
    with pytest.raises(qq.StreamCalculationError, match="conflicts with"):
        qq.calculate_stream(
            {
                "stream_type": "electromagnetic_field",
                "field_model": "stored_field",
                "electric_field_rms_v_m": 100,
                "area_m2": 2,
                "duration_hours": 1,
            }
        )


def test_radiation_energy_entropy_availability():
    result = qq.radiation_exergy_from_energy_entropy(
        1,
        "kWh_rad",
        3600,
        300,
        output_unit="kWh_ex",
    )
    assert result["exergy"] == pytest.approx(0.7)
    assert result["exergy_factor"] == pytest.approx(0.7)
    record = qq.calculate_stream(
        {
            "stream_type": "radiation",
            "quantity": 1,
            "unit": "kWh_rad",
            "radiation_model": "spectral_entropy",
            "radiation_entropy_j_k": 3600,
            "reference_temperature_k": 300,
        }
    )
    assert record.fx == pytest.approx(0.7)
    assert record.method_identifier == "radiation.energy_entropy.availability.v1"
    with pytest.raises(qq.PhysicalCalculationError, match="exceeds"):
        qq.radiation_exergy_from_energy_entropy(1, "J_rad", 1, 300)


def test_nuclear_q_value_event_energy_and_fusion_reaction_count():
    q_value = qq.nuclear_reaction_q_value_mev(
        [2.01410177812, 3.01604928199],
        [4.00260325413, 1.00866491595],
    )
    assert q_value == pytest.approx(17.589, abs=0.002)
    assert qq.nuclear_reaction_energy(1, 17.6, output_unit="J_nuclear") == pytest.approx(
        2.81983087584e-12, rel=1e-15
    )
    count = qq.fusion_reaction_count(1e20, 2e20, 1e-22, 3, 4)
    assert count == pytest.approx(2.4e19)
    identical = qq.fusion_reaction_count(1e20, 1e20, 1e-22, 3, 4, identical_reactants=True)
    assert identical == pytest.approx(6e18)
    with pytest.raises(qq.PhysicalCalculationError, match="equal reactant"):
        qq.fusion_reaction_count(1e20, 2e20, 1e-22, 3, 4, identical_reactants=True)


def test_dt_fusion_total_and_particle_channels_are_not_conflated_with_photons():
    total = qq.calculate_stream(
        {
            "stream_type": "thermonuclear",
            "reaction_preset": "dt_fusion",
            "reaction_count": 1e20,
        }
    )
    expected_mwh = 0.07832863544
    assert total.quantity == pytest.approx(expected_mwh)
    assert total.unit == "MWh_nuclear"
    assert total.fx == 1
    assert total.metadata["channels"][0]["carrier"] == "neutron"

    neutron = qq.calculate_stream(
        {
            "stream_type": "nuclear",
            "nuclear_mode": "reaction",
            "reaction_preset": "dt_fusion",
            "reaction_count": 1e20,
            "nuclear_channel": "neutron",
        }
    )
    alpha = qq.calculate_stream(
        {
            "stream_type": "fusion",
            "reaction_preset": "dt_fusion",
            "reaction_count": 1e20,
            "nuclear_channel": "alpha",
        }
    )
    assert neutron.unit == "MWh_neutron"
    assert alpha.unit == "MWh_charged_particle"
    assert neutron.quantity == pytest.approx(expected_mwh * 14.1 / 17.6)
    assert alpha.quantity == pytest.approx(expected_mwh * 3.5 / 17.6)
    assert neutron.quantity + alpha.quantity == pytest.approx(total.quantity)


def test_fusion_rate_and_custom_reaction_channels_require_complete_physics():
    rate = qq.calculate_stream(
        {
            "stream_type": "fusion",
            "reaction_preset": "dt_fusion",
            "reactant_1_number_density_m3": 1e20,
            "reactant_2_number_density_m3": 2e20,
            "reactivity_m3_s": 1e-22,
            "volume_m3": 3,
            "duration_seconds": 4,
            "reactivity_source": "declared test coefficient",
        }
    )
    assert rate.metadata["reaction_count"] == pytest.approx(2.4e19)
    with pytest.raises(qq.StreamCalculationError, match="reactivity_source"):
        qq.calculate_stream(
            {
                "stream_type": "fusion",
                "reaction_preset": "dt_fusion",
                "reactant_1_number_density_m3": 1e20,
                "reactant_2_number_density_m3": 2e20,
                "reactivity_m3_s": 1e-22,
                "volume_m3": 3,
                "duration_seconds": 4,
            }
        )

    custom = qq.calculate_stream(
        {
            "stream_type": "nuclear",
            "nuclear_mode": "reaction",
            "q_value_mev": 10,
            "reaction_count": 100,
            "reaction_channels": [
                {"name": "gamma", "carrier": "gamma", "fraction": 0.8, "exergy_factor": 1},
                {
                    "name": "neutrino",
                    "carrier": "neutrino",
                    "fraction": 0.2,
                    "exergy_factor": 0,
                },
            ],
        }
    )
    assert custom.fx == pytest.approx(0.8)
    with pytest.raises(qq.StreamCalculationError, match="must sum to 1"):
        qq.calculate_stream(
            {
                "stream_type": "nuclear",
                "nuclear_mode": "reaction",
                "q_value_mev": 10,
                "reaction_count": 1,
                "reaction_channels": [
                    {"name": "gamma", "carrier": "gamma", "fraction": 0.8, "exergy_factor": 1}
                ],
            }
        )
    with pytest.raises(qq.StreamCalculationError, match="must not exceed 1"):
        qq.calculate_stream(
            {
                "stream_type": "nuclear",
                "nuclear_mode": "reaction",
                "q_value_mev": 10,
                "reaction_count": 1,
                "fx": 1.1,
            }
        )


def test_nuclear_mass_convention_and_direct_mass_defect_partition_are_explicit():
    with pytest.raises(qq.StreamCalculationError, match="mass_convention"):
        qq.calculate_stream(
            {
                "stream_type": "fusion",
                "reactant_atomic_masses_u": [2.01410177812, 3.01604928199],
                "product_atomic_masses_u": [4.00260325413, 1.00866491595],
                "reaction_count": 1,
                "fx": 1,
            }
        )

    mass_derived = qq.calculate_stream(
        {
            "stream_type": "fusion",
            "reactant_atomic_masses_u": [2.01410177812, 3.01604928199],
            "product_atomic_masses_u": [4.00260325413, 1.00866491595],
            "mass_convention": "neutral atomic masses with balanced electron count",
            "reaction_count": 1,
            "fx": 1,
        }
    )
    assert mass_derived.metadata["q_value_mev"] == pytest.approx(17.589, abs=0.002)
    assert mass_derived.metadata["mass_convention"].startswith("neutral atomic")

    with pytest.raises(qq.StreamCalculationError, match="not both"):
        qq.calculate_stream(
            {
                "stream_type": "fusion",
                "q_value_mev": 17.6,
                "reactant_atomic_masses_u": [2.01410177812, 3.01604928199],
                "product_atomic_masses_u": [4.00260325413, 1.00866491595],
                "mass_convention": "neutral atomic masses",
                "reaction_count": 1,
                "fx": 1,
            }
        )

    neutron = qq.calculate_stream(
        {
            "stream_type": "fusion",
            "reaction_preset": "dt_fusion",
            "mass_defect_kg": 1e-9,
            "nuclear_channel": "neutron",
        }
    )
    total_j = 1e-9 * qq.SPEED_OF_LIGHT_M_S**2
    assert neutron.quantity == pytest.approx(total_j * (14.1 / 17.6) / 3.6e9)
    assert neutron.unit == "MWh_neutron"
    with pytest.raises(qq.StreamCalculationError, match="cannot be combined"):
        qq.calculate_stream(
            {
                "stream_type": "fusion",
                "mass_defect_kg": 1e-9,
                "reactivity_m3_s": 1e-22,
                "fx": 1,
            }
        )
    with pytest.raises(qq.StreamCalculationError, match="belongs to a nuclear inventory"):
        qq.calculate_stream(
            {
                "stream_type": "nuclear",
                "nuclear_mode": "reaction",
                "reaction_preset": "dt_fusion",
                "reaction_count": 1,
                "accessible_fraction": 0.5,
            }
        )


def test_ideal_plasma_species_energy_and_constant_volume_availability():
    density = 1e20
    temperature_ev = 1000.0
    result = qq.plasma_species_energy(
        [
            {"name": "electron", "number_density_m3": density, "temperature_ev": temperature_ev},
            {"name": "deuteron", "number_density_m3": density, "temperature_ev": temperature_ev},
        ],
        1,
        reference_temperature_k=293.15,
        output_unit="J_plasma",
    )
    expected_energy = 48_065.29902
    temperature_k = temperature_ev * 1.602176634e-19 / 1.380649e-23
    expected_exergy = (
        2
        * 1.5
        * density
        * qq.BOLTZMANN_CONSTANT_J_K
        * ((temperature_k - 293.15) - 293.15 * math.log(temperature_k / 293.15))
    )
    assert result["energy"] == pytest.approx(expected_energy, rel=1e-15)
    assert result["exergy"] == pytest.approx(expected_exergy, rel=1e-15)

    record = qq.calculate_stream(
        {
            "stream_type": "plasma",
            "volume_m3": 1,
            "plasma_species": [
                {
                    "name": "electron",
                    "number_density_m3": density,
                    "temperature_ev": temperature_ev,
                },
                {
                    "name": "deuteron",
                    "number_density_m3": density,
                    "temperature_ev": temperature_ev,
                },
            ],
            "magnetic_flux_density_t": 0.01,
        }
    )
    field_j = 0.01**2 / (2 * qq.VACUUM_PERMEABILITY_H_M)
    assert record.quantity == pytest.approx((expected_energy + field_j) / 3.6e6)
    assert record.accessible_exergy == pytest.approx((expected_exergy + field_j) / 3.6e6)
    assert record.unit == "kWh_plasma"
    assert record.distinguishability["basis"].startswith("plasma_")


def test_plasma_advanced_distribution_and_internal_state_are_explicit():
    supplied = qq.plasma_species_energy(
        [
            {
                "name": "measured electrons",
                "particle_count": 1e10,
                "mean_kinetic_energy_ev_per_particle": 50_000,
                "kinetic_exergy_factor": 0.95,
            }
        ],
        1,
        output_unit="J_plasma",
    )
    assert supplied["exergy_factor"] == pytest.approx(0.95)
    with pytest.raises(qq.PhysicalCalculationError, match="kinetic_exergy_factor"):
        qq.plasma_species_energy(
            [
                {
                    "name": "nonthermal electrons",
                    "particle_count": 1,
                    "mean_kinetic_energy_ev_per_particle": 1,
                }
            ],
            1,
        )
    with pytest.raises(qq.PhysicalCalculationError, match="internal_exergy_factor"):
        qq.plasma_species_energy(
            [
                {
                    "name": "ion",
                    "particle_count": 1,
                    "temperature_ev": 1,
                    "internal_energy_ev_per_particle": 10,
                }
            ],
            1,
        )
    with pytest.raises(qq.PhysicalCalculationError, match="relativistic"):
        qq.plasma_species_energy(
            [{"name": "electron", "particle_count": 1, "temperature_ev": 100_000}],
            1,
        )
    with pytest.raises(qq.PhysicalCalculationError, match="bulk motion"):
        qq.plasma_species_energy(
            [
                {
                    "name": "electron",
                    "particle_count": 1,
                    "temperature_ev": 1,
                    "bulk_velocity_m_s": 0.1 * qq.SPEED_OF_LIGHT_M_S,
                }
            ],
            1,
        )


def test_plasma_field_paths_cannot_silently_overlap():
    with pytest.raises(qq.StreamCalculationError, match="not both"):
        qq.calculate_stream(
            {
                "stream_type": "plasma",
                "volume_m3": 1,
                "plasma_species": [{"name": "electron", "particle_count": 1, "temperature_ev": 1}],
                "field_cells": [{"volume_m3": 1, "electric_field_v_m": 1}],
                "magnetic_flux_density_t": 1,
            }
        )


def test_new_request_contract_and_carriers_are_agent_discoverable():
    schema = qq.load_stream_request_schema()
    valid = [
        {"stream_type": "electromagnetic_field", "volume_m3": 1, "electric_field_v_m": 10},
        {
            "stream_type": "thermonuclear",
            "reaction_preset": "dt_fusion",
            "reaction_count": 1e20,
        },
        {
            "stream_type": "plasma",
            "volume_m3": 1,
            "plasma_species": [
                {"name": "electron", "number_density_m3": 1e20, "temperature_ev": 1000}
            ],
        },
        {
            "stream_type": "nuclear",
            "q_value_mev": 10,
            "reaction_count": 1,
            "fx": 1,
        },
        {
            "stream_type": "fusion",
            "reactant_atomic_masses_u": [2.01410177812, 3.01604928199],
            "product_atomic_masses_u": [4.00260325413, 1.00866491595],
            "mass_convention": "neutral atomic masses",
            "reaction_count": 1,
            "fx": 1,
        },
        {
            "stream_type": "nuclear",
            "mass_defect_kg": 1e-9,
            "accessible_fraction": 0.5,
        },
    ]
    for request in valid:
        validate(request, schema)
    with pytest.raises(ValidationError):
        validate(
            {
                "stream_type": "fusion",
                "reaction_preset": "dt_fusion",
                "reactant_1_number_density_m3": 1e20,
                "reactant_2_number_density_m3": 1e20,
                "reactivity_m3_s": 1e-22,
                "volume_m3": 1,
                "duration_seconds": 1,
            },
            schema,
        )
    with pytest.raises(ValidationError):
        validate(
            {
                "stream_type": "radiation",
                "quantity": 1,
                "unit": "MWh_rad",
                "radiation_model": "spectral_entropy",
            },
            schema,
        )
    capabilities = qq.stream_capabilities()
    assert capabilities["schema_version"] == "1.2"
    assert {"electromagnetic_field", "nuclear", "plasma"} <= set(capabilities["stream_types"])
    assert qq.carrier_family("MWh_em") == "electromagnetic"
    assert qq.carrier_family("MWh_neutron") == "nuclear particle"
    assert qq.carrier_family("kWh_plasma") == "plasma"
