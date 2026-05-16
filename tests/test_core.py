import math

import pytest

from quantity_quality import (
    EnergyReport,
    ReferenceContext,
    chemical_exergy_factor,
    get_reference_example,
    load_reference_examples,
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

