import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import validate

import quantity_quality as qq

ROOT = Path(__file__).resolve().parents[1]


def _run(operation, inputs):
    if operation == "thermal_exergy_factor_c":
        return qq.thermal_exergy_factor_c(inputs["source_c"], inputs["reference_c"])
    if operation == "cooling_exergy_factor_c":
        return qq.cooling_exergy_factor_c(inputs["cold_c"], inputs["ambient_c"])
    if operation == "sensible_heat_exergy_factor_c":
        return qq.sensible_heat_exergy_factor_c(
            inputs["supply_c"], inputs["return_c"], inputs["reference_c"]
        )
    if operation == "petela_exergy_factor":
        if inputs["radiation_temperature_k"] != qq.T_SUN_K:
            raise AssertionError("quantity-and-quality fixes the solar source at T_SUN_K")
        return qq.petela_exergy_factor(inputs["reference_k"])
    if operation == "accessible_exergy":
        return qq.accessible_exergy(inputs["energy"], inputs["exergy_factor"])
    if operation == "weighted_exergy_factor":
        return qq.weighted_exergy_factor(inputs["records"])
    if operation == "format_energy_notation":
        return qq.format_energy_notation(
            inputs["quantity"],
            inputs["unit"],
            inputs["exergy_factor"],
            precision=inputs["precision"],
        )
    raise AssertionError(f"unhandled contract operation: {operation}")


def test_contract_schema_reference_revision_and_unique_ids():
    contract = qq.load_conformance_contract()
    schema = json.loads(
        (ROOT / "data" / "conformance_contract_v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=contract, schema=schema)
    reference_text = (ROOT / contract["reference_data"]["path"]).read_text(encoding="utf-8")
    assert contract["reference_data"]["hash_basis"] == "utf8_text_with_lf_line_endings"
    assert (
        hashlib.sha256(reference_text.encode("utf-8")).hexdigest()
        == contract["reference_data"]["sha256"]
    )
    assert len(json.loads(reference_text)) == contract["reference_data"]["record_count"]
    ids = [case["id"] for section in ("valid_cases", "invalid_cases") for case in contract[section]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in qq.load_conformance_contract()["valid_cases"]
        if "quantity-and-quality" in case["implementations"]
    ],
    ids=lambda case: case["id"],
)
def test_valid_conformance_case(case):
    actual = _run(case["operation"], case["inputs"])
    if isinstance(case["expected"], str):
        assert actual == case["expected"]
    else:
        assert actual == pytest.approx(case["expected"], abs=case["absolute_tolerance"])


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in qq.load_conformance_contract()["invalid_cases"]
        if "quantity-and-quality" in case["implementations"]
    ],
    ids=lambda case: case["id"],
)
def test_invalid_conformance_case(case):
    with pytest.raises((TypeError, ValueError)):
        _run(case["operation"], case["inputs"])
