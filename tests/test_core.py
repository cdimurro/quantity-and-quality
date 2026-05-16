import math

import pytest

from quantity_quality import (
    COMMON_NOTATION_EXAMPLES,
    EnergyReport,
    ReferenceContext,
    annotate_record,
    chemical_exergy_factor,
    exergy_unit,
    format_energy_notation,
    get_reference_example,
    load_reference_examples,
    parse_energy_notation,
    petela_exergy_factor,
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
    assert notation == "1 MWh, f_X = 0.73"
    parsed = parse_energy_notation(notation)
    assert parsed.quantity == 1
    assert parsed.unit == "MWh"
    assert parsed.exergy_factor == pytest.approx(0.73)


def test_petela_solar_factor():
    assert petela_exergy_factor() == pytest.approx(0.931, abs=0.001)


def test_common_examples_have_20_records():
    assert len(COMMON_NOTATION_EXAMPLES) == 20
    assert COMMON_NOTATION_EXAMPLES[0]["notation"] == "1 MWh, f_X = 1"


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
    assert annotated.record["notation"] == "1 MWh_th, f_X = 0.17"
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
