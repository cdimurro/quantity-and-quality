"""Pinned public-data and authoritative numerical conformance tests.

The fixture contains only a few source rows and published constants. The full
live-data pass is performed by ``scripts/validate_real_data.py`` so CI remains
fast and does not depend on network availability.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

import quantity_quality as qq
from quantity_quality.units import ENERGY_TO_MWH, fuel_volume_conversion

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "real_world_benchmarks.json"


@pytest.fixture(scope="module")
def benchmarks() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_nist_energy_conversions_and_all_unit_round_trips(benchmarks):
    nist = benchmarks["sources"]["nist_si"]
    assert qq.convert_energy(1, "Wh", "J") == pytest.approx(nist["watt_hour_j"], rel=1e-15)
    assert qq.convert_energy(1, "Btu", "J") == pytest.approx(nist["btu_it_j"], rel=1e-15)
    assert qq.convert_energy(1, "therm", "J") == pytest.approx(nist["therm_us_j"], rel=1e-15)

    for unit in ENERGY_TO_MWH:
        normalized = qq.convert_energy(17.25, unit, "MWh")
        assert qq.convert_energy(normalized, "MWh", unit) == pytest.approx(17.25, rel=1e-14)

    assert qq.convert_energy(1, "TWh", "MWh") == 1_000_000
    assert qq.convert_energy(3.6, "GJ", "MWh") == pytest.approx(1.0, rel=1e-15)
    # A U.S. legal therm and 100,000 International Table Btu are close but not identical.
    assert qq.convert_energy(1, "therm", "MWh") != qq.convert_energy(100_000, "Btu", "MWh")


@pytest.mark.parametrize("unit", ["ton_hour", "ton_hrs", "ton-hours", "ton hours"])
def test_real_refrigeration_unit_spellings_are_dimensionally_energy(unit):
    assert qq.is_energy_unit(unit)
    assert not qq.is_non_energy_unit(unit)
    assert qq.convert_energy(1, unit, "Btu") == pytest.approx(12_000, rel=1e-15)


def test_non_energy_volume_cannot_receive_an_exergy_factor():
    with pytest.raises(ValueError, match="volume or mass"):
        qq.report(4100, "gallons", fx=1.06)

    annotated = qq.annotate_record({"quantity": 4100, "unit": "gallons", "fx": 1.06})
    assert not annotated.ok
    assert annotated.record["accessible_exergy"] is None
    assert any("heating value" in issue.message for issue in annotated.issues)


def test_eia_fuel_volume_estimates_are_numerically_correct_and_labeled(benchmarks):
    eia = benchmarks["sources"]["eia_2026_estimates"]
    gas = fuel_volume_conversion("scf(natural gas)")
    assert gas is not None
    gas_mwh, _, _, gas_note = gas
    assert qq.convert_energy(gas_mwh, "MWh", "Btu") == pytest.approx(
        eia["natural_gas_btu_per_scf"], rel=1e-15
    )
    assert "estimated" in gas_note.lower()

    oil = fuel_volume_conversion("bbl(oil)")
    assert oil is not None
    oil_mwh, _, _, oil_note = oil
    assert qq.convert_energy(oil_mwh, "MWh", "Btu") == pytest.approx(
        eia["crude_oil_btu_per_barrel"], rel=1e-15
    )
    assert "estimated" in oil_note.lower()

    record = qq.calculate_stream(
        {"stream_type": "fuel", "quantity": 1000, "unit": "scf(natural gas)"}
    )
    assert record.quantity == pytest.approx(qq.convert_energy(1.036, "MMBtu", "MWh"))
    assert record.data_quality_flag == "estimated_reference"
    assert record.needs_attention
    assert any("statistical estimate" in warning for warning in record.warnings)


def test_iapws_if97_saturation_temperature_benchmarks(benchmarks):
    points = benchmarks["sources"]["iapws_if97"]["saturation_points"]
    for point in points:
        actual = qq.steam_saturation_temperature_c(point["pressure_bar_absolute"])
        assert actual == pytest.approx(point["temperature_c"], abs=1e-10)

    assert qq.steam_saturation_temperature_c(0) is None
    assert qq.steam_saturation_temperature_c(221) is None
    assert qq.steam_saturation_temperature_c(float("nan")) is None


def test_xai4heat_public_telemetry_rows_match_independent_results(benchmarks):
    rows = benchmarks["sources"]["xai4heat"]["rows"]
    for row in rows:
        assert qq.thermal_exergy_factor_c(row["t_sup_prim"], row["t_amb"]) == pytest.approx(
            row["expected_primary_carnot_fx"], abs=2e-15
        )
        assert qq.sensible_heat_exergy_factor_c(
            row["t_sup_prim"], row["t_ret_prim"], row["t_amb"]
        ) == pytest.approx(row["expected_primary_integrated_fx"], abs=2e-15)
        assert qq.sensible_heat_exergy_factor_c(
            row["t_sup_sec"], row["t_ret_sec"], row["t_amb"]
        ) == pytest.approx(row["expected_secondary_integrated_fx"], abs=2e-15)

    invalid = benchmarks["sources"]["xai4heat"]["invalid_state"]
    assert invalid["logarithmic_mean_c"] < invalid["t_amb"]
    with pytest.raises(ValueError, match="logarithmic-mean"):
        qq.sensible_heat_exergy_factor_c(
            invalid["t_sup_sec"], invalid["t_ret_sec"], invalid["t_amb"]
        )


def test_generated_xai4heat_portfolio_is_pinned_to_validated_results(benchmarks):
    expected = benchmarks["sources"]["xai4heat"]["portfolio"]
    path = Path("paper/generated/xai4heat_f3_model_sensitivity.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = {row["model"]: row for row in csv.DictReader(handle)}

    mappings = {
        "primary_supply_ambient_carnot": ("primary_carnot_fx", "rows"),
        "primary_supply_return_integrated_ambient": (
            "primary_integrated_fx",
            "primary_integrated_valid_intervals",
        ),
        "secondary_supply_return_integrated_ambient": (
            "secondary_integrated_fx",
            "secondary_integrated_valid_intervals",
        ),
        "primary_return_sink_carnot": (
            "primary_return_sink_fx",
            "primary_return_sink_valid_intervals",
        ),
    }
    for model, (factor_key, count_key) in mappings.items():
        assert float(rows[model]["portfolio_fx"]) == pytest.approx(expected[factor_key], abs=1e-15)
        assert int(rows[model]["valid_intervals"]) == expected[count_key]


def test_owid_real_rows_normalize_without_inventing_physical_exergy(benchmarks):
    for row in benchmarks["sources"]["owid_energy"]["rows"]:
        result = qq.account_energy_chain(
            {
                "primary": {
                    "quantity": row["renewables_consumption_twh"],
                    "unit": "TWh",
                    "accounting_method": row["renewables_accounting_method"],
                    "source_dataset": "OWID Energy dataset",
                    "source_variable": "renewables_consumption",
                },
                "secondary": {
                    "quantity": row["electricity_generation_twh"],
                    "unit": "TWh_e",
                    "fx": 1.0,
                    "source_dataset": "OWID Energy dataset",
                    "source_variable": "electricity_generation",
                },
            }
        ).as_dict()
        primary = result["stages"]["primary"]
        secondary = result["stages"]["secondary"]
        assert primary["energy_mwh"] == pytest.approx(row["renewables_consumption_twh"] * 1_000_000)
        assert primary["energy_quantity_type"] == "counterfactual_energy_equivalent"
        assert "exergy_mwh" not in primary
        assert secondary["exergy_mwh"] == pytest.approx(
            row["electricity_generation_twh"] * 1_000_000
        )
        assert math.isfinite(result["efficiencies"]["primary_to_secondary_energy"])


def test_small_scientific_notation_round_trips_and_uses_printed_precision():
    notation = qq.format_energy_notation(1e-6, "MWh", 1.0)
    assert notation.startswith("1e-06 MWh")
    assert qq.parse_energy_notation(notation).quantity == pytest.approx(1e-6)
    check = qq.verify_notation("1e-6 MWh_th, fx = 1.70e-1 [Th = 8e1 C, T0 = 2e1 C]")
    assert check.agrees
    assert check.tolerance == pytest.approx(0.0005)


def test_physical_domain_guards_prevent_plausible_but_invalid_numbers():
    with pytest.raises(ValueError, match="solar source"):
        qq.petela_exergy_factor(6000)
    with pytest.raises(ValueError, match="absolute zero"):
        qq.source_temperature_for_fx_c(0.5, sink_c=-273.15)
    with pytest.raises(ValueError, match="thermal fx"):
        qq.source_temperature_for_fx_c(float("nan"))

    schema = qq.load_energy_accounting_request_schema()
    with pytest.raises(ValidationError):
        validate(
            {"applied_exergy": {"quantity": 1, "unit": "MWh_extra"}},
            schema,
        )
    with pytest.raises(qq.EnergyAccountingError, match="_ex suffix"):
        qq.account_energy_chain({"applied_exergy": {"quantity": 1, "unit": "MWh_extra"}})
