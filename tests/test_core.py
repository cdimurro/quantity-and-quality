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
    build_web_data,
    carrier_family,
    conformance_issues,
    chemical_exergy_factor,
    clean_dataframe,
    clean_file,
    clean_record,
    clean_records,
    clean_sql,
    clean_stream,
    compare,
    compare_scenario_file,
    cooling_exergy_factor_c,
    electricity,
    efficiency_from_loss_angle,
    exergy_capital_efficiency,
    exergy_loss_angle,
    exergy_loss_angle_from_efficiency,
    exergy_unit,
    f3_thermal_summary,
    fuel,
    get_carrier_entry,
    format_energy_notation,
    format_exergy_factor,
    infer_fidelity_tier,
    list_carrier_registry,
    list_fidelity_tiers,
    get_reference_example,
    load_record_schema,
    load_reference_examples,
    lookup,
    parse_energy_notation,
    petela_exergy_factor,
    report,
    source_temperature_for_fx_c,
    thermal_interval,
    scenario_to_markdown,
    scenario_to_table,
    thermal,
    thermal_exergy_factor_c,
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
    assert COMMON_NOTATION_EXAMPLES[0]["notation"] == "845 kWh, fx = 1.000"


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
    write_web_data(output, js_output=js_output)
    assert '"naturalGasHhv"' in output.read_text(encoding="utf-8")
    assert js_output.read_text(encoding="utf-8").startswith("window.EXERGY_FACTOR_REFERENCE_DATA = ")


def test_record_json_schema_is_packaged():
    schema = load_record_schema()
    assert schema["title"] == "Quantity + Quality Energy Record"
    assert "exergy_factor" in schema["properties"]
    assert "unit" in schema["required"]


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
    connection.execute("create table energy (asset text, energy_kwh real, fx real)")
    connection.execute("insert into energy values ('meter 1', 100, 0.5)")
    rows = clean_sql(connection, "select * from energy")
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
    assert electricity(1, "MWh").notation == "1 MWh, fx = 1.000"


def test_the_factor_is_a_fixed_width_field_but_the_quantity_is_not():
    # `1 MWh`, not `1.000 MWh` — only the factor is padded.
    assert format_exergy_factor(0.17) == "0.170"
    assert format_exergy_factor(1) == "1.000"
    assert format_energy_notation(1, "MWh", 0.5) == "1 MWh, fx = 0.500"
    assert format_energy_notation(2.738, "kWh_th", 0.64) == "2.738 kWh_th, fx = 0.640"


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
        "1 MWh, fx = 0.170 [Th = 80°C, T0 = 20°C]",   # as the paper typesets it
        "1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]",   # ASCII wire form
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
    # `1 MWh, fx = 1.000` as suspect.
    check = verify_notation("1 MWh, fx = 1.000")
    assert not check.verifiable
    assert "T0" in check.reason


def test_cooling_declarations_verify_against_their_own_bracket():
    # 7 C service against a 30 C ambient. Independently: 303.15/280.15 - 1.
    check = verify_notation("1 MWh_cooling, fx = 0.082 [Tcold = 7 C, T0 = 30 C]")
    assert check.verifiable and check.agrees
    assert check.equation == "fx = T0/Tcold - 1"


def test_cli_verify_exit_code_can_gate_a_pipeline(capsys):
    # The exit code is the contract: a report whose stated factors no longer match
    # the temperatures printed beside them should fail a build, not be published.
    from quantity_quality.cli import main

    assert main(["verify", "1 MWh, fx = 0.170 [Th = 80 C, T0 = 20 C]"]) == 0
    assert main(["verify", "1 MWh_th, fx = 0.900 [Th = 80 C, T0 = 20 C]"]) == 1
    # An unverifiable record has not been contradicted, so it must not fail a build.
    assert main(["verify", "1 MWh, fx = 1.000"]) == 0
    assert "MISMATCH" in capsys.readouterr().out


def test_tolerance_follows_the_precision_the_record_claims():
    # Stated to three decimals, so checked to three decimals. Demanding more
    # precision than the notation claims would fail correctly-rounded records.
    assert verify_notation("1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]").agrees
    loose = verify_notation("1 MWh_th, fx = 0.17 [Th = 80 C, T0 = 20 C]")
    assert loose.agrees
    assert loose.tolerance == pytest.approx(0.005)
