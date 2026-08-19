import json
import math
import sqlite3
from pathlib import Path

import pytest
from jsonschema import ValidationError
from jsonschema import validate as validate_json

import quantity_quality as qq
from quantity_quality import (
    COMMON_NOTATION_EXAMPLES,
    EnergyReport,
    ReferenceContext,
    ReferenceEnvironment,
    annotate_file,
    annotate_record,
    build_web_data,
    carrier_family,
    chemical,
    chemical_exergy_factor,
    clean_dataframe,
    clean_file,
    clean_record,
    clean_records,
    clean_sql,
    clean_stream,
    clean_url,
    compare,
    compare_scenario,
    compare_scenario_file,
    conformance_issues,
    cooling_exergy_factor_c,
    efficiency_from_loss_angle,
    electricity,
    exergy_capital_efficiency,
    exergy_loss_angle,
    exergy_loss_angle_from_efficiency,
    exergy_unit,
    f3_thermal_summary,
    format_energy_notation,
    format_exergy_factor,
    from_notation,
    fuel,
    get_carrier_entry,
    get_reference_example,
    infer_fidelity_tier,
    is_energy_unit,
    is_non_energy_unit,
    list_carrier_registry,
    list_fidelity_tiers,
    load_record_schema,
    load_reference_examples,
    lookup,
    minimum_record_fields,
    parse_energy_notation,
    petela_exergy_factor,
    report,
    scenario_to_markdown,
    scenario_to_table,
    sensible_heat_exergy_factor_c,
    solar,
    source_temperature_for_fx_c,
    steam_saturation_temperature_c,
    thermal,
    thermal_exergy_factor_c,
    thermal_interval,
    verify_notation,
    weighted_exergy_factor,
    write_web_data,
)
from quantity_quality.reference import extract_temperature_context


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


def test_integrated_sensible_heat_factor_matches_the_paper_equation():
    expected = 1 - (293.15 * math.log(353.15 / 323.15) / (353.15 - 323.15))
    assert sensible_heat_exergy_factor_c(80, 50, 20) == pytest.approx(expected)
    with pytest.raises(ValueError, match="supply temperature"):
        sensible_heat_exergy_factor_c(50, 80, 20)


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


def test_reference_examples_are_self_consistent():
    required = {
        "id",
        "name",
        "category",
        "carrier",
        "basis",
        "quantity_unit",
        "exergy_factor",
        "reference",
        "boundary",
        "calculation",
        "source",
        "basis_type",
        "confidence",
    }
    for example in load_reference_examples():
        assert required <= set(example)
        assert isinstance(example["exergy_factor"], (int, float))
        assert example["exergy_factor"] >= 0

        context = extract_temperature_context(example)
        if "Carnot factor" in example["basis"] and "source_c" in context:
            assert "source_c" in example
            assert "sink_c" in example
            assert example["exergy_factor"] == pytest.approx(
                thermal_exergy_factor_c(context["source_c"], context["sink_c"]),
                abs=0.001,
            )
        if example["category"] == "cooling":
            assert "cold_service_c" in example
            assert "ambient_sink_c" in example
            assert example["exergy_factor"] == pytest.approx(
                cooling_exergy_factor_c(context["cold_service_c"], context["ambient_sink_c"]),
                abs=0.001,
            )
        if example["category"] == "chemical":
            assert "_HHV" in example["quantity_unit"] or "_LHV" in example["quantity_unit"]
            assert "basis" in example["reference"].lower()
            assert example["fuel_basis"] in {"HHV", "LHV"}


def test_invalid_thermal_factor_rejects_reversed_temperatures():
    with pytest.raises(ValueError):
        thermal_exergy_factor_c(20, 80)


def test_adoption_notation_format_and_parse():
    notation = format_energy_notation(1, "MWh", 0.73)
    assert notation == "1 MWh, fx = 0.730"
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
    assert COMMON_NOTATION_EXAMPLES[0]["notation"] == "845 kWh, fx = 1.0"


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
    assert annotated.record["notation"] == "1 MWh_th, fx = 0.170"
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
    assert annotated.record["full_notation"] == "1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"


def test_progressive_report_accepts_minimum_inputs_and_reports_missing_context():
    record = report(1, "MWh", fx=0.73)
    assert record.notation == "1 MWh, fx = 0.730"
    assert "notation" in record.capabilities
    assert "accessible_exergy" in record.capabilities
    assert record.missing_context == ("reference", "boundary", "basis")
    assert record.accessible_exergy == pytest.approx(0.73)
    assert record.needs_attention


def test_thermal_helper_defaults_to_20c_and_is_self_verifying():
    record = thermal(2.738, "kWh_th", source_c=541)
    assert "self_verifying" in record.capabilities
    assert record.fx == pytest.approx(0.640, abs=0.001)
    assert record.full_notation == "2.738 kWh_th, fx = 0.640 [Th = 541 C, T0 = 20 C]"
    assert record.accessible_exergy_mwh == pytest.approx(0.001752, abs=0.000001)
    assert source_temperature_for_fx_c(0.64) == pytest.approx(541.156, abs=0.001)


def test_lookup_returns_contextual_record():
    record = get_reference_example("heat-80c-standard")
    assert record["reference"] == "20 C thermal sink"
    qq_record = lookup("heat-80c-standard", quantity=1.8)
    assert "self_verifying" in qq_record.capabilities
    assert "reference_lookup" in qq_record.capabilities
    assert qq_record.full_notation == "1.8 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"


def test_fuel_preset_and_comparison_helpers():
    gas = fuel(850, "natural gas", basis="HHV", unit="MMBtu_HHV")
    default_gas = fuel(1, "natural gas", basis="HHV")
    electric = electricity(0.2, "MWh")
    rows = compare([gas, electric])
    assert gas.fx == pytest.approx(0.93)
    assert default_gas.unit == "MWh_HHV_NG"
    assert rows[0]["label"] == "natural gas on HHV basis"
    assert rows[0]["accessible_exergy_mwh"] > rows[1]["accessible_exergy_mwh"]


def test_third_draft_registry_tiers_and_diagnostics():
    assert get_carrier_entry("MWh_solar").suffix == "_solar"
    assert carrier_family("MWh_HHV_CH4") == "chemical"
    assert any(entry.suffix == "_fission" for entry in list_carrier_registry())
    assert [tier.tier for tier in list_fidelity_tiers()] == ["F0", "F1", "F2", "F3", "F4"]

    interval = thermal_interval(
        10,
        source_c=80,
        sink_c=5,
        timestamp="2025-02-20T00:00:00",
        stream_id="L4",
    )
    assert interval.fidelity_tier == "F3"
    assert interval.fx == pytest.approx(1 - 278.15 / 353.15)
    assert infer_fidelity_tier(interval.as_dict()) == "F3"
    assert conformance_issues(interval.as_dict()) == ()

    f4_incomplete = {
        "quantity": 1,
        "unit": "MWh_m",
        "fx": 1,
        "tier": "F4",
        "reference": "declared environment",
        "boundary": "control volume",
        "basis": "full state-vector balance",
    }
    assert "state_variables" in conformance_issues(f4_incomplete)[0]
    assert "balance_closure" in conformance_issues(f4_incomplete)[1]

    summary = f3_thermal_summary(
        [
            {"quantity": 10, "source_c": 80, "sink_c": 5},
            {"quantity": 5, "source_c": 70, "sink_c": 10},
        ],
        fixed_sink_c=20,
    )
    assert summary.intervals == 2
    assert summary.weighted_fx > summary.weighted_fixed_sink_fx

    assert exergy_capital_efficiency(92.1, 1.5) == pytest.approx(61.4)
    assert exergy_loss_angle(1.0, 0.5) == pytest.approx(45.0)
    assert exergy_loss_angle_from_efficiency(0.5) == pytest.approx(45.0)
    assert efficiency_from_loss_angle(45.0) == pytest.approx(0.5)


def test_web_export_uses_canonical_reference_values(tmp_path):
    data = build_web_data()
    assert data["schema_version"] == "exergy_factor_web_data_v1"
    assert data["presets"]["naturalGasHhv"]["fx"] == pytest.approx(0.93)
    assert data["presets"]["hydrogenLhv"]["fx"] == pytest.approx(0.98)
    assert data["presets"]["heat80"]["typed_unit"] == "MWh_th"
    assert data["presets"]["solar"]["typed_unit"] == "MWh_solar"
    assert data["presets"]["electricity"]["typed_unit"] == "MWh_e"
    assert data["presets"]["mechanical"]["typed_unit"] == "MWh_m"
    assert data["presets"]["naturalGasHhv"]["typed_unit"] == "MWh_HHV_NG"
    assert data["presets"]["electricity"]["base_unit"] == "MWh"
    assert data["presets"]["heat80"]["sourceC"] == 80
    assert data["presets"]["heat80"]["sinkC"] == 20
    assert data["presets"]["heat80"]["tier"] == "F2"
    assert data["carrier_registry"]
    assert data["fidelity_tiers"][0]["tier"] == "F0"

    output = tmp_path / "reference_examples.json"
    js_output = tmp_path / "reference_examples.js"
    contract_output = tmp_path / "conformance_contract_v1.json"
    payload = write_web_data(
        output,
        js_output=js_output,
        conformance_output=contract_output,
    )
    assert '"naturalGasHhv"' in output.read_text(encoding="utf-8")
    assert payload["source_version"] == f"quantity-and-quality@{qq.__version__}"
    assert js_output.read_text(encoding="utf-8").startswith(
        "window.EXERGY_FACTOR_REFERENCE_DATA = "
    )
    assert json.loads(contract_output.read_text(encoding="utf-8")) == json.loads(
        Path("data/conformance_contract_v1.json").read_text(encoding="utf-8")
    )


def test_record_json_schema_is_packaged():
    schema = load_record_schema()
    assert schema["title"] == "Quantity + Quality Energy Record"
    assert "exergy_factor" in schema["properties"]
    assert schema["$id"].endswith("/data/quantity_quality_record.schema.json")
    assert "anyOf" in schema


def test_scenario_comparison_json_and_markdown(tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(
        """
{
  "name": "test scenario",
  "demand": {"label": "80 C demand", "quantity": 1, "unit": "MWh_th", "source_c": 80, "sink_c": 20},
  "options": [
    {"id": "grid", "label": "Grid electricity", "type": "electricity", "quantity": 1, "unit": "MWh", "cost_per_mwh": 70},
    {"id": "heat", "label": "80 C heat", "quantity": 1, "unit": "MWh_th", "source_c": 80, "sink_c": 20, "cost_per_mwh": 20}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    result = compare_scenario_file(scenario_path)
    assert result["schema_version"] == "quantity_quality_scenario_v1"
    assert result["rows"][0]["accessible_exergy_mwh"] == pytest.approx(1.0)
    assert result["rows"][1]["accessible_exergy_mwh"] == pytest.approx(0.17, abs=0.001)
    assert "Grid electricity" in scenario_to_table(result)
    assert "| Option | Energy | fx |" in scenario_to_markdown(result)


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
    assert record["full_notation"] == "2738 kWh_th, fx = 0.640 [Th = 541 C, T0 = 20 C]"
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
    assert record["notation"] == "2.738 kWh_th, fx = 0.640"
    assert record["accessible_exergy"] == pytest.approx(1.752, abs=0.001)


def test_clean_records_supports_notation_and_fuel_presets():
    records = clean_records(
        [
            {"notation": "1 MWh, fx = 0.730"},
            {"fuel_type": "natural gas", "energy_mmbtu_hhv": 850, "energy_basis": "HHV"},
        ]
    )
    assert records[0]["notation"] == "1 MWh, fx = 0.730"
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
    assert records[0]["notation"] == "100 kWh, fx = 0.500"


def test_clean_sql_and_stream_helpers():
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("create table energy (asset text, energy_kwh real, fx real)")
        connection.execute("insert into energy values ('meter 1', 100, 0.5)")
        rows = clean_sql(connection, "select * from energy")
    finally:
        connection.close()
    streamed = list(clean_stream([{"energy_kwh": 200, "fx": 0.25}]))
    assert rows[0]["notation"] == "100 kWh, fx = 0.500"
    assert streamed[0]["notation"] == "200 kWh, fx = 0.250"


# ---------------------------------------------------------------------------
# The full operational notation, and the property it exists for.
#
# The paper defines a completely specified stream declaration as
#
#     1 MWh, fx = 0.170 [Th = 80°C, T0 = 20°C]
#
# and its value is that the recipient can re-derive the factor in one step,
# without trusting the sender:
#
#     fx = 1 - T0/Th = 1 - 293.15/353.15 = 0.170
#
# Three things had to be true for that to hold and none of them were. The
# factor printed as 0.17, so the published figure did not look like the value a
# reader recomputes. The parser rejected the bracket outright — the library
# emitted a canonical form it could not read back. And nothing anywhere actually
# performed the check.
# ---------------------------------------------------------------------------


def test_notation_matches_the_paper_exactly():
    record = thermal(1, "MWh_th", source_c=80, sink_c=20)
    assert record.full_notation == "1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"
    # The paper's short form for an unambiguous stream keeps its trailing zeros.
    assert electricity(1, "MWh").notation == "1 MWh, fx = 1.0"


def test_a_computed_factor_keeps_its_zeros_but_an_exact_one_is_not_padded():
    # Trailing zeros on a computed value are the precision being claimed, so
    # 0.170 rather than 0.17 and 0.730 rather than 0.73.
    assert format_exergy_factor(0.17) == "0.170"
    assert format_exergy_factor(0.73) == "0.730"
    assert format_energy_notation(1, "MWh", 0.5) == "1 MWh, fx = 0.500"
    assert format_energy_notation(2.738, "kWh_th", 0.64) == "2.738 kWh_th, fx = 0.640"
    # Electricity is 1 BY DEFINITION, not 1 measured to three decimals. Padding a
    # definition to 1.000 dresses it up as a measurement and is noise on the page.
    assert format_exergy_factor(1) == "1.0"
    assert format_energy_notation(1, "MWh", 1.0) == "1 MWh, fx = 1.0"
    # The quantity is never padded either.
    assert format_energy_notation(1, "MWh", 0.17).startswith("1 MWh")


def test_full_declaration_round_trips():
    record = thermal(1, "MWh_th", source_c=80, sink_c=20)
    parsed = parse_energy_notation(record.full_notation)
    assert parsed.quantity == 1
    assert parsed.unit == "MWh_th"
    assert parsed.source_c == pytest.approx(80)
    assert parsed.sink_c == pytest.approx(20)
    assert parsed.is_fully_specified


@pytest.mark.parametrize(
    "text",
    [
        "1 MWh, fx = 0.170 [Th = 80°C, T0 = 20°C]",  # as the paper typesets it
        "1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]",  # ASCII wire form
        "1 MWh, fx = 0.170 [Th = 353.15 K, T0 = 293.15 K]",  # stated in kelvin
    ],
)
def test_a_reader_can_confirm_the_factor_in_one_step(text):
    check = verify_notation(text)
    assert check.verifiable
    assert check.agrees
    assert check.recomputed_exergy_factor == pytest.approx(0.16990, abs=1e-5)
    assert check.equation == "fx = 1 - T0/Th"


def test_a_wrong_factor_is_caught():
    check = verify_notation("1 MWh_th, fx = 0.900 [Th = 80 C, T0 = 20 C]")
    assert check.verifiable
    assert not check.agrees
    assert check.difference == pytest.approx(0.730, abs=0.001)


def test_an_unverifiable_record_is_not_reported_as_wrong():
    # A short-form record contradicts nothing; there is simply nothing to check
    # against. Returning "wrong" here would brand every legitimate
    # `1 MWh, fx = 1.0` as suspect.
    check = verify_notation("1 MWh, fx = 1.0")
    assert not check.verifiable
    assert "T0" in check.reason


def test_cooling_declarations_verify_against_their_own_bracket():
    # 7 C service against a 30 C ambient. Independently: 303.15/280.15 - 1.
    check = verify_notation("1 MWh_cooling, fx = 0.082 [Tcold = 7 C, T0 = 30 C]")
    assert check.verifiable and check.agrees
    assert check.equation == "fx = T0/Tcold - 1"


# ---------------------------------------------------------------------------
# Whether a real spreadsheet can actually be used.
#
# A representative facility export — Site / Meter / Month / Usage / Units / Notes,
# with therms, ton-hours, MMBtu and gallons in it — produced ZERO usable records.
# Every row came back "provide exergy_factor/fx, reference_id, source_c+sink_c, or
# chemical_exergy+energy_basis": the tool asked the reporter for the number they
# came to get, while `electricity-delivered` and `methane-hhv` already sat in the
# bundled data. The reporter's own columns were dropped from the output, so the
# results could not even be joined back to the rows they came from.
# ---------------------------------------------------------------------------


def test_the_reporters_own_columns_survive(tmp_path):
    source = tmp_path / "meters.csv"
    source.write_text(
        "Site,Meter,Month,Usage,Units,Notes\nPlant A,Main electric,Jan-2026,845000,kWh,\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    clean_file(source, output=out)
    header = out.read_text(encoding="utf-8").splitlines()[0].split(",")
    # Their columns, first and unchanged. Without this the output cannot be joined
    # back to the reporter's data and is unusable however correct the numbers are.
    assert header[:6] == ["Site", "Meter", "Month", "Usage", "Units", "Notes"]
    assert "fx" in header


def test_ordinary_meter_names_are_understood():
    records = clean_records(
        [
            {"Meter": "Main electric", "Usage": 845000, "Units": "kWh"},
            {"Meter": "Natural gas boiler", "Usage": 1240, "Units": "therms"},
            {"Meter": "Chilled water", "Usage": 910, "Units": "ton-hours"},
        ]
    )
    assert [record["fx"] for record in records] == [1.0, 0.93, 0.082]
    # And every inferred carrier says so, in the record, naming what it matched.
    for record in records:
        assert any("presumptive" in assumption for assumption in record["assumptions"])


def test_an_explicit_value_always_beats_an_inferred_one():
    # The guess must never overwrite what the reporter actually stated.
    record = clean_records(
        [
            {"Meter": "Main electric", "Usage": 100, "Units": "kWh", "fx": 0.42},
        ]
    )[0]
    assert record["fx"] == 0.42
    assert not any("presumptive" in assumption for assumption in record["assumptions"])


def test_utility_units_reach_a_comparable_MWh_ex():
    # The whole point is that rows can be added up. A unit that parses but yields
    # no accessible_exergy_mwh silently breaks that, which is worse than refusing.
    records = clean_records(
        [
            {"Usage": 1240, "Units": "therms", "fx": 0.93},
            {"Usage": 910, "Units": "ton-hours", "fx": 0.082},
            {"Usage": 430, "Units": "MMBtu", "fx": 0.353},
        ]
    )
    for record in records:
        assert record["accessible_exergy_mwh"] is not None, record["unit"]
    assert records[0]["accessible_exergy_mwh"] == pytest.approx(33.789, abs=0.01)
    assert records[1]["accessible_exergy_mwh"] == pytest.approx(0.2624, abs=0.001)


def test_a_volume_is_never_given_an_exergy_factor():
    # 4100 gallons of diesel x 1.06 produced "4346 gallons_ex", which reads like a
    # result and is not one: an Exergy Factor is work potential per unit ENERGY.
    record = clean_records([{"Meter": "Diesel genset", "Usage": 4100, "Units": "gallons"}])[0]
    # An unrated row carries no `fx` key at all rather than a null one, so read it
    # defensively — this asserts no factor was invented, not the key's presence.
    assert record.get("fx") in (None, "")
    assert record["needs_attention"]
    message = " ".join(issue["message"] for issue in record["issues"])
    assert "volume or mass" in message
    assert "heating value" in message


def test_a_temperature_written_in_a_notes_column_is_read():
    # The single most common way a real export carries the one fact that decides
    # the Exergy Factor. These rows used to ask the reporter for a number they had
    # already written down.
    hot = clean_records(
        [
            {
                "Meter": "Waste heat recovered",
                "Usage": 430,
                "Units": "MMBtu",
                "Notes": "exhaust ~340F",
            },
        ]
    )[0]
    assert hot["fx"] == pytest.approx(0.340, abs=0.002)
    assert any("340" in a for a in hot["assumptions"])

    cold = clean_records(
        [
            {"Meter": "Chilled water", "Usage": 910, "Units": "ton-hours", "Notes": "44F supply"},
        ]
    )[0]
    # Below ambient is a cooling service, and it needs an ambient to be held
    # against — supplying only the service temperature left it unanswerable.
    assert cold["fx"] == pytest.approx(0.048, abs=0.002)
    assert cold["accessible_exergy_mwh"] is not None


def test_a_unit_name_is_never_mistaken_for_a_temperature():
    # "845000 kWh" must not read as 845000 K. The unit letter has to be a whole
    # word or every electricity row acquires a source hotter than the sun.
    record = clean_records([{"Meter": "Main electric", "Usage": 845000, "Units": "kWh"}])[0]
    assert record["fx"] == 1.0
    assert "source_c" not in record or record.get("source_c") in (None, "")


def test_steam_pressure_becomes_a_delivery_temperature():
    # A plant records pressure; the Exergy Factor needs the temperature the heat
    # is delivered at. 165 psig is 12.4 bar absolute, saturating near 189 C.
    assert steam_saturation_temperature_c(1.01325) == pytest.approx(100.0, abs=0.5)
    assert steam_saturation_temperature_c(10.0) == pytest.approx(179.9, abs=0.5)
    record = clean_records(
        [
            {"Meter": "Steam header", "Usage": 2738, "Units": "kWh", "Notes": "supply 165 psig"},
        ]
    )[0]
    assert record["fx"] == pytest.approx(0.366, abs=0.005)
    assert any("saturat" in a for a in record["assumptions"])


def test_a_fuel_volume_that_names_its_fuel_converts():
    # The website offered these units and converted them; the library refused
    # them, so the same record was usable in one place and rejected in the other.
    # The unit carries the fuel, so a published equivalent applies.
    gas = clean_records([{"Usage": 1000, "Units": "scf(natural gas)"}])[0]
    assert gas["quantity"] == pytest.approx(0.30362, abs=1e-4)  # EIA 2026: 1.036 MMBtu
    assert gas["unit"] == "MWh"
    assert gas["fx"] == 0.93

    oil = clean_records([{"Usage": 1, "Units": "bbl(oil)"}])[0]
    assert oil["quantity"] == pytest.approx(1.6673, abs=1e-3)  # EIA 2026: 5.689 MMBtu
    assert oil["accessible_exergy_mwh"] == pytest.approx(1.7673, abs=1e-3)

    # The conversion is stated, including the basis, because the paper's
    # enforcement mechanism is that a chemical token is incomplete when its basis
    # is not recoverable.
    note = " ".join(gas["assumptions"])
    assert "1,036 Btu per scf" in note
    assert "HHV" in note


def test_a_volume_that_does_not_name_its_fuel_is_still_refused():
    # A gallon of what, at what heating value. Converting this would be inventing
    # the number the reporter came here to have checked.
    record = clean_records([{"Meter": "Diesel genset", "Usage": 4100, "Units": "gallons"}])[0]
    assert record.get("fx") in (None, "")
    assert record["needs_attention"]


def test_a_ton_hour_is_energy_not_a_ton():
    # `ton_hour` splits on the underscore to the mass unit `ton` plus a `_hour`
    # carrier suffix, which rejected every chilled-water row in a building export.
    assert is_energy_unit("ton-hours")
    assert not is_non_energy_unit("ton-hours")
    assert is_non_energy_unit("gallons")
    assert is_non_energy_unit("tonnes")


def test_cli_verify_exit_code_can_gate_a_pipeline(capsys):
    # The exit code is the contract: a report whose stated factors no longer match
    # the temperatures printed beside them should fail a build, not be published.
    from quantity_quality.cli import main

    assert main(["verify", "1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]"]) == 0
    assert main(["verify", "1 MWh_th, fx = 0.900 [Th = 80 C, T0 = 20 C]"]) == 1
    # An unverifiable record has not been contradicted, so it must not fail a build.
    assert main(["verify", "1 MWh, fx = 1.0"]) == 0
    assert "MISMATCH" in capsys.readouterr().out


def test_tolerance_follows_the_precision_the_record_claims():
    # Stated to three decimals, so checked to three decimals. Demanding more
    # precision than the notation claims would fail correctly-rounded records.
    assert verify_notation("1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]").agrees
    loose = verify_notation("1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]")
    assert loose.agrees
    assert loose.tolerance == pytest.approx(0.005)


def test_high_level_full_notation_round_trip_preserves_context():
    thermal_record = from_notation("1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]")
    assert thermal_record.full_notation == ("1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]")
    assert thermal_record.method == "thermal"
    assert "self_verifying" in thermal_record.capabilities

    cooling_record = from_notation("1 MWh_cooling, fx = 0.082 [Tcold = 7 C, T0 = 30 C]")
    assert cooling_record.ambient_sink_c == 30
    assert cooling_record.full_notation.endswith("[Tcold = 7 C, T0 = 30 C]")

    cleaned = clean_record({"notation": "1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"})
    assert cleaned["source_c"] == 80
    assert cleaned["sink_c"] == 20
    assert cleaned["full_notation"].endswith("[Th = 80 C, T0 = 20 C]")


def test_tiny_nonzero_quantity_never_formats_as_zero():
    assert format_energy_notation(0.000293071, "MWh", 0.93).startswith("0.000293 MWh")


@pytest.mark.parametrize(
    ("unit", "expected_mwh"),
    [("Mcf", 0.3036216287), ("MMcf", 303.6216287)],
)
def test_bare_gas_billing_volumes_convert(unit, expected_mwh):
    record = clean_record({"Usage": 1, "Units": unit})
    assert record["quantity"] == pytest.approx(expected_mwh)
    assert record["unit"] == "MWh"
    assert record["fx"] == pytest.approx(0.93)
    assert "natural gas" in " ".join(record["assumptions"])


def test_nonfinite_cleaner_values_become_row_issues():
    record = clean_record({"quantity": math.nan, "unit": "MWh", "fx": 0.5})
    assert record["needs_attention"]
    assert any("finite" in issue["message"] for issue in record["issues"])


def test_malformed_notation_becomes_a_row_issue():
    record = clean_record({"notation": "not an energy record"})
    assert record["needs_attention"]
    assert any(issue["field"] == "notation" for issue in record["issues"])


def test_url_cleaning_rejects_unsafe_or_unbounded_options():
    with pytest.raises(ValueError, match="http"):
        clean_url("file:///tmp/records.csv")
    with pytest.raises(ValueError, match="credentials"):
        clean_url("https://user:secret@example.com/records.csv")
    with pytest.raises(ValueError, match="timeout"):
        clean_url("https://example.com/records.csv", timeout=0)


def test_blank_excel_cell_does_not_abort_the_file(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    path = tmp_path / "records.xlsx"
    pd.DataFrame(
        [
            {"quantity": 1.0, "unit": "MWh", "fx": 0.5},
            {"quantity": None, "unit": "MWh", "fx": 0.5},
        ]
    ).to_excel(path, index=False)
    result = clean_file(path)
    assert result["total_records"] == 2
    assert result["invalid_records"] == 1


def test_pressure_is_only_interpreted_as_saturated_steam_with_steam_context():
    compressed_air = clean_record(
        {
            "Meter": "Compressed air header",
            "Usage": 100,
            "Units": "kWh",
            "Notes": "165 psig",
        }
    )
    assert compressed_air.get("source_c") in (None, "")
    assert compressed_air.get("fx") in (None, "")


def test_schema_accepts_each_supported_minimal_input_shape():
    schema = load_record_schema()
    validate_json(
        {"notation": "1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"},
        schema,
    )
    validate_json({"quantity": 1, "unit": "MWh", "fx": 0.5}, schema)
    validate_json({"quantity": 1, "unit": "MWh", "tier": "F0"}, schema)
    validate_json(
        {
            "quantity": 1,
            "unit": "MWh_HHV_CH4",
            "chemical_exergy": 55.5,
            "energy_basis": "HHV",
            "energy_basis_value": 50.0,
        },
        schema,
    )
    assert minimum_record_fields() == ("quantity", "unit", "exergy_factor")


def test_power_input_retains_rate_semantics():
    record = annotate_record({"power": 10, "unit": "MW", "fx": 0.7}).record
    assert "quantity" not in record
    assert record["power"] == 10
    assert record["accessible_exergy_rate"] == pytest.approx(7)
    assert record["accessible_exergy_rate_unit"] == "MW_ex"


def test_scenario_grade_difference_only_applies_to_matched_energy():
    result = compare_scenario(
        {
            "demand": {"quantity": 2, "unit": "MWh", "fx": 0.2},
            "options": [{"label": "Supply | A", "quantity": 10, "unit": "MWh", "fx": 0.8}],
        }
    )
    row = result["rows"][0]
    assert row["matched_energy_mwh"] == 2
    assert row["grade_mismatch_mwh_ex"] == pytest.approx(1.2)
    assert "Supply \\| A" in scenario_to_markdown(result)


def test_capabilities_only_claim_verification_the_library_can_perform():
    solar_record = solar()
    assert "self_verifying" in solar_record.capabilities
    assert verify_notation(solar_record.full_notation).agrees
    assert (
        "self_verifying" not in chemical(1, "MWh", chemical_exergy=55, energy_basis=50).capabilities
    )
    assert lookup("methane-hhv").energy_basis == "HHV"
    assert thermal(1, source_c=80, sink_c=20).as_dict()["method_id"] == (
        "thermal.carnot.constant_temperature.v1"
    )
    assert thermal(1, source_c=80, sink_c=20).as_dict()["carrier_registry_version"] == "0.3"
    assert qq.__version__ == "0.13.0"


def test_stream_calculator_meets_users_at_quantity_or_physical_inputs():
    electricity_record = qq.calculate_stream(
        {
            "stream_type": "electricity",
            "power": 100,
            "power_unit": "kW",
            "duration_hours": 8,
        }
    )
    assert electricity_record.quantity == pytest.approx(800)
    assert electricity_record.unit == "kWh_e"
    assert electricity_record.fx == 1
    assert electricity_record.quantity_method_id == "quantity.power_times_duration.v1"

    supplied_heat = qq.calculate_stream(
        {
            "stream_type": "heat",
            "quantity": 1,
            "unit": "MWh",
            "source_c": 80,
            "sink_c": 20,
        }
    )
    assert supplied_heat.unit == "MWh_th"
    assert supplied_heat.fx == pytest.approx(0.170, abs=0.001)
    assert supplied_heat.as_dict()["stream_type"] == "heat"
    assert "stream_calculation" in supplied_heat.capabilities


def test_sensible_heat_stream_calculates_quantity_quality_and_reproducible_notation():
    record = qq.calculate_stream(
        {
            "stream_type": "heat",
            "mass": 1000,
            "mass_unit": "kg",
            "specific_heat_kj_kg_k": 4.186,
            "source_c": 80,
            "return_c": 50,
            "sink_c": 20,
        }
    )
    assert record.quantity == pytest.approx(0.03488333333333333)
    assert record.unit == "MWh_th"
    assert record.fx == pytest.approx(sensible_heat_exergy_factor_c(80, 50, 20))
    assert record.method_identifier == "thermal.sensible.integrated.v1"
    assert record.quantity_method_id == "quantity.sensible_heat.mass_cp_delta_t.v1"
    assert "[Ts = 80 C, Tr = 50 C, T0 = 20 C]" in record.full_notation
    assert verify_notation(record.full_notation).agrees
    parsed = from_notation(record.full_notation)
    assert parsed.return_c == 50
    assert parsed.method_identifier == "thermal.sensible.integrated.v1"


def test_solar_and_fuel_physical_quantity_helpers():
    solar_record = qq.calculate_stream(
        {
            "stream_type": "solar",
            "irradiance_w_m2": 800,
            "area_m2": 50,
            "duration_hours": 6,
        }
    )
    assert solar_record.quantity == pytest.approx(240)
    assert solar_record.unit == "kWh_solar"
    assert solar_record.accessible_exergy == pytest.approx(240 * petela_exergy_factor())

    fuel_record = qq.calculate_stream(
        {
            "stream_type": "fuel",
            "mass": 100,
            "mass_unit": "kg",
            "heating_value": 50,
            "heating_value_unit": "MJ/kg",
            "fuel": "natural gas",
            "basis": "LHV",
        }
    )
    assert fuel_record.quantity == pytest.approx(5000 / 3600)
    assert fuel_record.unit == "MWh_LHV_NG"
    assert fuel_record.fx == pytest.approx(1.04)

    assert qq.energy_from_power(10, 2, power_unit="kW", output_unit="kWh") == 20
    assert qq.solar_energy(1000, 2, 3) == 6
    assert qq.energy_from_mass(1, 50, heating_value_unit="MJ/kg") == pytest.approx(50 / 3600)

    volume_fuel = qq.calculate_stream(
        {
            "stream_type": "fuel",
            "volume": 1000,
            "volume_unit": "m3",
            "heating_value": 35.8,
            "heating_value_unit": "MJ/m3",
            "fuel": "natural gas",
            "basis": "HHV",
            "chemical_exergy": 51.6,
            "energy_basis_value": 55.5,
        }
    )
    assert volume_fuel.quantity == pytest.approx(35_800 / 3600)
    assert volume_fuel.fx == pytest.approx(51.6 / 55.5)
    assert volume_fuel.method_identifier == "chemical.ratio.declared_basis.v1"
    assert volume_fuel.quantity_method_id == "quantity.fuel.volume_heating_value.v1"
    assert qq.energy_from_volume(1, 10, heating_value_unit="kWh/m3") == pytest.approx(0.01)


def test_stream_calculation_errors_and_capabilities_are_machine_readable(capsys):
    with pytest.raises(qq.StreamCalculationError) as exc_info:
        qq.calculate_stream({"stream_type": "heat", "quantity": 1, "unit": "MWh"})
    assert exc_info.value.as_dict() == {
        "code": "missing_input",
        "message": "source_c is required",
        "field": "source_c",
    }
    capabilities = qq.stream_capabilities()
    assert capabilities["schema_version"] == "1.2"
    assert set(capabilities["stream_types"]) == {
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
    request_schema = qq.load_stream_request_schema()
    for definition in capabilities["stream_types"].values():
        validate_json(definition["example"], request_schema)
    with pytest.raises(ValidationError):
        validate_json({"stream_type": "heat", "quantity": 1, "unit": "MWh"}, request_schema)
    with pytest.raises(ValidationError):
        validate_json(
            {"stream_type": "electricity", "quantity": 1, "unit": "MWh", "typo": 4},
            request_schema,
        )

    from quantity_quality.cli import main

    assert main(["capabilities", "--json"]) == 0
    assert main(["capabilities", "--json-schema"]) == 0
    assert (
        main(
            [
                "calculate",
                '{"stream_type":"electricity","power":5,"power_unit":"kW","duration_hours":2}',
                "--json",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"quantity_method_id": "quantity.power_times_duration.v1"' in output


def test_cleaner_distinguishes_return_temperature_from_reference_environment():
    record = clean_record(
        {
            "quantity": 1,
            "unit": "MWh_th",
            "supply_temp_c": 80,
            "return_temp_c": 50,
            "reference_temp_c": 20,
        }
    )
    assert record["return_c"] == 50
    assert record["sink_c"] == 20
    assert record["method_id"] == "thermal.sensible.integrated.v1"
    assert "Tr = 50 C" in record["full_notation"]

    subzero = clean_record(
        {
            "quantity": 1,
            "unit": "MWh_cooling",
            "cold_service_c": -10,
            "ambient_sink_c": 20,
        }
    )
    assert subzero["exergy_factor"] > 0


def test_distinguishability_is_exposed_without_a_second_multiplier():
    hot = thermal(1, source_c=80, sink_c=20)
    assessment = hot.distinguishability
    assert assessment["status"] == "distinguishable"
    assert assessment["basis"] == "temperature_gradient"
    assert assessment["difference"]["temperature_k"] == 60
    assert assessment["exergy_factor"] == hot.fx
    assert "no separate distinguishability multiplier" in assessment["factor_role"]
    assert "distinguishability_assessment" in hot.capabilities

    equilibrium = thermal(1, source_c=20, sink_c=20)
    assert equilibrium.fx == 0
    assert equilibrium.distinguishability["status"] == "indistinguishable"
    assert cooling_exergy_factor_c(20, 20) == 0


def test_end_use_accounting_keeps_energy_exergy_and_service_separate():
    account = qq.account_energy_chain(
        {
            "primary": {"quantity": 2.5, "unit": "MWh_LHV_NG", "fx": 1.04},
            "final": {
                "quantity": 1,
                "unit": "MWh_e",
                "fx": 1,
                "method": "electricity",
            },
            "useful": {
                "quantity": 0.9,
                "unit": "MWh_mech",
                "fx": 1,
                "method": "mechanical",
                "boundary": "motor shaft to task",
            },
            "service": {
                "name": "Conveyor movement",
                "quantity": 12000,
                "unit": "tonne_metre",
            },
        }
    )
    result = account.as_dict()
    assert result["complete"] is True
    assert result["applied_exergy"] == pytest.approx(0.9)
    assert result["applied_exergy_unit"] == "MWh_ex"
    assert result["stages"]["primary"]["exergy_mwh"] == pytest.approx(2.6)
    assert "anergy_mwh" not in result["stages"]["primary"]
    assert result["stages"]["useful"]["anergy_mwh"] == 0
    assert result["efficiencies"]["final_to_applied_exergy"] == pytest.approx(0.9)
    assert result["service"]["energy_unit"] is False
    assert result["service"]["applied_exergy_intensity_unit"] == "MWh_ex/tonne_metre"


def test_secondary_energy_is_an_optional_physical_boundary():
    result = qq.account_energy_chain(
        {
            "primary": {"quantity": 3, "unit": "MWh_fuel", "fx": 1},
            "secondary": {"quantity": 1.1, "unit": "MWh_e", "fx": 1},
            "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
            "useful": {"quantity": 0.9, "unit": "MWh_mech", "fx": 1},
        }
    ).as_dict()
    assert list(result["stages"]) == ["primary", "secondary", "final", "useful"]
    assert result["efficiencies"]["primary_to_secondary_energy"] == pytest.approx(1.1 / 3)
    assert result["efficiencies"]["secondary_to_final_exergy"] == pytest.approx(1 / 1.1)
    assert result["complete"] is True


def test_substitution_energy_is_retained_but_never_treated_as_physical_exergy():
    result = qq.account_energy_chain(
        {
            "primary": {
                "quantity": 250,
                "unit": "TWh",
                "accounting_method": "substitution",
                "source_dataset": "OWID historical energy data",
                "source_variable": "solar_consumption",
            },
            "secondary": {"quantity": 100, "unit": "TWh_e", "fx": 1},
        }
    ).as_dict()
    primary = result["stages"]["primary"]
    assert primary["energy_mwh"] == 250_000_000
    assert primary["energy_quantity_type"] == "counterfactual_energy_equivalent"
    assert primary["thermodynamic_conversion_allowed"] is False
    assert primary["quality_status"] == "not_applicable_to_counterfactual_equivalent"
    assert primary["missing_quality"] == ["physical_energy_basis"]
    assert "fx" not in primary
    assert "exergy_mwh" not in primary
    assert "primary_to_secondary_exergy" not in result["efficiencies"]
    assert "primary.physical_energy_basis" in result["missing"]
    assert any("counterfactual" in warning for warning in result["warnings"])

    with pytest.raises(qq.EnergyAccountingError, match="counterfactual"):
        qq.account_energy_chain(
            {
                "primary": {
                    "quantity": 250,
                    "unit": "TWh",
                    "fx": 1,
                    "accounting_method": "substitution",
                }
            }
        )

    with pytest.raises(qq.EnergyAccountingError, match="primary-energy"):
        qq.account_energy_chain(
            {
                "secondary": {
                    "quantity": 250,
                    "unit": "TWh",
                    "accounting_method": "substitution",
                }
            }
        )


def test_energy_only_dataset_stage_does_not_invent_quality():
    result = qq.account_energy_chain(
        {
            "primary": {
                "quantity": 100,
                "unit": "TWh",
                "accounting_method": "physical_energy_content",
                "source_dataset": "OWID Energy dataset",
            }
        }
    ).as_dict()
    assert result["stages"]["primary"]["quality_status"] == "not_supplied"
    assert "exergy_mwh" not in result["stages"]["primary"]
    assert any("no Exergy Factor" in warning for warning in result["warnings"])

    with pytest.raises(qq.EnergyAccountingError, match="final.fx"):
        qq.account_energy_chain(
            {
                "final": {"quantity": 1, "unit": "MWh_e"},
                "end_use_exergy_efficiency": 0.9,
            }
        )


def test_applied_exergy_can_be_derived_when_useful_energy_exceeds_final_energy():
    # A heat pump can deliver more useful heat than its final electricity input;
    # the second-law constraint applies to exergy, not to that energy ratio.
    result = qq.account_energy_chain(
        {
            "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
            "useful": {
                "quantity": 3,
                "unit": "MWh_th",
                "fx": 0.064,
                "source_c": 40,
                "sink_c": 20,
            },
            "service": {
                "name": "Warm home",
                "quantity": 720,
                "unit": "occupied_comfort_hour",
            },
        }
    ).as_dict()
    assert result["efficiencies"]["final_to_useful_energy"] == 3
    assert result["applied_exergy"] == pytest.approx(0.192)
    assert result["efficiencies"]["final_to_applied_exergy"] == pytest.approx(0.192)
    assert result["stages"]["useful"]["anergy_mwh"] == pytest.approx(2.808)


def test_applied_exergy_can_be_measured_directly_or_confirm_a_derived_value():
    direct = qq.account_energy_chain(
        {
            "applied_exergy": {
                "quantity": 500,
                "unit": "kWh_ex",
                "basis": "shaft power integrated over the reporting interval",
                "boundary": "motor shaft to pump",
            },
            "service": {
                "name": "Water delivered",
                "quantity": 1000,
                "unit": "cubic_metre_delivered",
            },
        }
    ).as_dict()
    assert direct["complete"] is False
    assert direct["applied_exergy"] == pytest.approx(0.5)
    assert direct["applied_exergy_basis"].startswith("shaft power")
    assert direct["service"]["service_productivity"] == pytest.approx(2000)

    confirmed = qq.account_energy_chain(
        {
            "useful": {"quantity": 0.5, "unit": "MWh_mech", "fx": 1},
            "applied_exergy": {"quantity": 500, "unit": "kWh_ex"},
        }
    ).as_dict()
    assert "confirmed by directly declared" in confirmed["applied_exergy_basis"]


def test_end_use_accounting_rejects_energy_services_and_broken_exergy_balances():
    with pytest.raises(qq.EnergyAccountingError, match="outcome"):
        qq.account_energy_chain(
            {
                "useful": {"quantity": 1, "unit": "MWh_th", "fx": 0.1},
                "service": {"name": "Warm home", "quantity": 1, "unit": "MWh"},
            }
        )
    with pytest.raises(qq.EnergyAccountingError, match="cannot exceed final exergy"):
        qq.account_energy_chain(
            {
                "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
                "applied_exergy": {"quantity": 1.1, "unit": "MWh_ex"},
            }
        )


def test_accounting_schema_capabilities_and_cli(capsys):
    schema = qq.load_energy_accounting_request_schema()
    example = qq.accounting_capabilities()["example"]
    validate_json(example, schema)
    validate_json(
        json.loads(Path("examples/end-use-accounting.json").read_text(encoding="utf-8")),
        schema,
    )
    validate_json(
        json.loads(Path("examples/owid-substitution-accounting.json").read_text(encoding="utf-8")),
        schema,
    )
    with pytest.raises(ValidationError):
        validate_json(
            {
                "primary": {
                    "quantity": 250,
                    "unit": "TWh",
                    "fx": 1,
                    "accounting_method": "substitution",
                }
            },
            schema,
        )

    from quantity_quality.cli import main

    assert main(["account", "examples/end-use-accounting.json", "--json"]) == 0
    assert main(["account", "--json-schema"]) == 0
    output = capsys.readouterr().out
    assert '"applied_exergy": 0.9' in output
    assert "Primary-Secondary-Final-Useful-Applied Exergy Accounting Request" in output


def test_accounting_cli_prints_energy_only_stages(capsys):
    from quantity_quality.cli import main

    assert main(["account", "examples/owid-substitution-accounting.json"]) == 0
    output = capsys.readouterr().out
    assert "primary: 250 TWh, fx = not supplied (substitution)" in output
    assert "secondary: 100 TWh_e, fx = 1.000" in output
