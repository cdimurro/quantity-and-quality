import math
import sqlite3

import pytest

from quantity_quality import (
    COMMON_NOTATION_EXAMPLES,
    EnergyReport,
    ReferenceEnvironment,
    ReferenceContext,
    annotate_file,
    annotate_record,
    chemical_exergy_factor,
    clean_dataframe,
    clean_file,
    clean_record,
    clean_records,
    clean_sql,
    clean_stream,
    compare,
    electricity,
    exergy_unit,
    fuel,
    format_energy_notation,
    get_reference_example,
    load_reference_examples,
    lookup,
    parse_energy_notation,
    petela_exergy_factor,
    report,
    source_temperature_for_fx_c,
    thermal,
    thermal_exergy_factor_c,
    weighted_exergy_factor,
)


def test_thermal_exergy_factor_matches_paper_reference_values():
    assert thermal_exergy_factor_c(80, 20) == pytest.approx(0.170, abs=0.001)
    assert thermal_exergy_factor_c(40, 20) == pytest.approx(0.064, abs=0.001)
    assert thermal_exergy_factor_c(150, 20) == pytest.approx(0.307, abs=0.001)


def test_dynamic_sink_example():
    standard_sink = thermal_exergy_factor_c(70, 20)
    warm_sink = thermal_exergy_factor_c(70, 35)
    assert standard_sink == pytest.approx(0.146, abs=0.001)
    assert warm_sink == pytest.approx(0.102, abs=0.001)
    assert warm_sink < standard_sink


def test_energy_report_accessible_exergy():
    context = ReferenceContext(
        reference="20 C sink",
        boundary="thermal delivery",
        operating_basis="Carnot factor",
    )
    report = EnergyReport(1.0, "MWh", thermal_exergy_factor_c(80, 20), context)
    assert report.accessible_exergy == pytest.approx(0.170, abs=0.001)
    assert report.as_dict()["accessible_exergy_unit"] == "MWh_ex"
    assert exergy_unit("MWh_th") == "MWh_ex"
    assert exergy_unit("MWh_LHV") == "MWh_ex"


def test_chemical_factor_uses_declared_basis():
    methane_lhv = chemical_exergy_factor(51.9, 50.0)
    methane_hhv = chemical_exergy_factor(51.9, 55.5)
    assert methane_lhv == pytest.approx(1.04, abs=0.01)
    assert methane_hhv == pytest.approx(0.93, abs=0.01)


def test_weighted_exergy_factor():
    value = weighted_exergy_factor([(2.0, 1.0), (1.0, 0.1)])
    assert value == pytest.approx(0.7)


def test_reference_examples_are_bundled():
    examples = load_reference_examples()
    assert len(examples) >= 20
    heat = get_reference_example("heat-80c-standard")
    assert heat["exergy_factor"] == pytest.approx(0.170, abs=0.001)


def test_invalid_thermal_factor_rejects_reversed_temperatures():
    with pytest.raises(ValueError):
        thermal_exergy_factor_c(20, 80)


def test_adoption_notation_format_and_parse():
    notation = format_energy_notation(1, "MWh", 0.73)
    assert notation == "1 MWh, fx = 0.73"
    parsed = parse_energy_notation(notation)
    assert parsed.quantity == 1
    assert parsed.unit == "MWh"
    assert parsed.exergy_factor == pytest.approx(0.73)
    assert parse_energy_notation("1 MWh, f_X = 0.73").exergy_factor == pytest.approx(0.73)
    assert parse_energy_notation("1 MWh, fX = 0.73").exergy_factor == pytest.approx(0.73)


def test_petela_solar_factor():
    assert petela_exergy_factor() == pytest.approx(0.932, abs=0.001)
    assert petela_exergy_factor(298.15) == pytest.approx(0.931, abs=0.001)


def test_reference_environment_uses_paper_default():
    environment = ReferenceEnvironment()
    assert environment.id == "standard_ambient_20c_101325pa"
    assert environment.temperature_k == pytest.approx(293.15)
    assert environment.pressure_pa == pytest.approx(101325.0)


def test_common_examples_have_20_records():
    assert len(COMMON_NOTATION_EXAMPLES) == 20
    assert COMMON_NOTATION_EXAMPLES[0]["notation"] == "845 kWh, fx = 1"


def test_annotate_record_from_reference_id():
    annotated = annotate_record(
        {
            "quantity": "1",
            "unit": "MWh_th",
            "reference_id": "heat-80c-standard",
            "reference": "20 C sink",
            "boundary": "district heating delivery",
        }
    )
    assert annotated.ok
    assert annotated.record["notation"] == "1 MWh_th, fx = 0.17"
    assert annotated.record["accessible_exergy"] == pytest.approx(0.17)
    assert annotated.record["accessible_exergy_unit"] == "MWh_ex"
    assert annotated.record["operating_basis"] == "Carnot factor, source=80 C, sink=20 C"


def test_annotate_record_from_temperatures():
    annotated = annotate_record(
        {
            "quantity": 1,
            "unit": "MWh_th",
            "source_c": 80,
            "sink_c": 20,
        }
    )
    assert annotated.ok
    assert annotated.record["exergy_factor"] == pytest.approx(0.170, abs=0.001)
    assert "self_verifying" in annotated.record["capabilities"]
    assert annotated.record["full_notation"] == "1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]"


def test_progressive_report_accepts_minimum_inputs_and_reports_missing_context():
    record = report(1, "MWh", fx=0.73)
    assert record.notation == "1 MWh, fx = 0.73"
    assert "notation" in record.capabilities
    assert "accessible_exergy" in record.capabilities
    assert record.missing_context == ("reference", "boundary", "basis")
    assert record.accessible_exergy == pytest.approx(0.73)
    assert record.needs_attention


def test_thermal_helper_defaults_to_20c_and_is_self_verifying():
    record = thermal(2.738, "kWh_th", source_c=541)
    assert "self_verifying" in record.capabilities
    assert record.fx == pytest.approx(0.640, abs=0.001)
    assert record.full_notation == "2.738 kWh_th, fx = 0.64 [Th = 541 C, T0 = 20 C]"
    assert record.accessible_exergy_mwh == pytest.approx(0.001752, abs=0.000001)
    assert source_temperature_for_fx_c(0.64) == pytest.approx(541.156, abs=0.001)


def test_lookup_returns_contextual_record():
    record = get_reference_example("heat-80c-standard")
    assert record["reference"] == "20 C thermal sink"
    qq_record = lookup("heat-80c-standard", quantity=1.8)
    assert "self_verifying" in qq_record.capabilities
    assert "reference_lookup" in qq_record.capabilities
    assert qq_record.full_notation == "1.8 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]"


def test_fuel_preset_and_comparison_helpers():
    gas = fuel(850, "natural gas", basis="HHV", unit="MMBtu_HHV")
    electric = electricity(0.2, "MWh")
    rows = compare([gas, electric])
    assert gas.fx == pytest.approx(0.93)
    assert rows[0]["label"] == "natural gas on HHV basis"
    assert rows[0]["accessible_exergy_mwh"] > rows[1]["accessible_exergy_mwh"]


def test_annotate_file_returns_records_and_can_write(tmp_path):
    output = tmp_path / "annotated.csv"
    summary = annotate_file("examples/adoption_records.csv", output=output)
    assert summary["ok"]
    assert output.exists()
    assert "self_verifying" in summary["records"][1]["capabilities"]


def test_clean_record_maps_messy_fields_and_converts_temperatures():
    record = clean_record(
        {
            "asset": "Kiln exhaust",
            "energy_kwh": 2738,
            "supply_temp_f": 1005.8,
        }
    )
    assert record["label"] == "Kiln exhaust"
    assert record["unit"] == "kWh_th"
    assert record["source_c"] == pytest.approx(541.0)
    assert record["sink_c"] == pytest.approx(20.0)
    assert record["full_notation"] == "2738 kWh_th, fx = 0.64 [Th = 541 C, T0 = 20 C]"
    assert "self_verifying" in record["capabilities"]


def test_clean_record_supports_explicit_mapping_and_constants():
    record = clean_record(
        {"asset": "Kiln exhaust", "measured_energy": 2.738, "supply_temp_f": 1005.8},
        mapping={
            "label": "asset",
            "quantity": "measured_energy",
            "unit": "kWh_th",
            "source_f": "supply_temp_f",
        },
    )
    assert record["notation"] == "2.738 kWh_th, fx = 0.64"
    assert record["accessible_exergy"] == pytest.approx(1.752, abs=0.001)


def test_clean_records_supports_notation_and_fuel_presets():
    records = clean_records(
        [
            {"notation": "1 MWh, fx = 0.73"},
            {"fuel_type": "natural gas", "energy_mmbtu_hhv": 850, "energy_basis": "HHV"},
        ]
    )
    assert records[0]["notation"] == "1 MWh, fx = 0.73"
    assert records[1]["reference_id"] == "methane-hhv"
    assert records[1]["fx"] == pytest.approx(0.93)


def test_clean_file_supports_jsonl_and_json_output(tmp_path):
    input_path = tmp_path / "records.jsonl"
    input_path.write_text(
        '{"asset":"Grid","energy_kwh":845,"reference_id":"electricity-delivered"}\n'
        '{"asset":"Heat","energy_kwh":2738,"supply_temp_f":1005.8}\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "clean.json"
    summary = clean_file(input_path, output=output_path)
    assert summary["ok"]
    assert output_path.exists()
    assert summary["records"][1]["unit"] == "kWh_th"


def test_clean_dataframe_accepts_pandas_like_objects():
    class FakeFrame:
        def to_dict(self, orient="records"):
            assert orient == "records"
            return [{"energy_kwh": 100, "fx": 0.5}]

    records = clean_dataframe(FakeFrame())
    assert records[0]["notation"] == "100 kWh, fx = 0.5"


def test_clean_sql_and_stream_helpers():
    connection = sqlite3.connect(":memory:")
    connection.execute("create table energy (asset text, energy_kwh real, fx real)")
    connection.execute("insert into energy values ('meter 1', 100, 0.5)")
    rows = clean_sql(connection, "select * from energy")
    streamed = list(clean_stream([{"energy_kwh": 200, "fx": 0.25}]))
    assert rows[0]["notation"] == "100 kWh, fx = 0.5"
    assert streamed[0]["notation"] == "200 kWh, fx = 0.25"
