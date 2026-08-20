from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Optional, Union

from . import __version__ as PACKAGE_VERSION
from .conformance import (
    conformance_contract_sha256,
    load_conformance_contract,
    reference_data_sha256,
)
from .reference import extract_temperature_context, load_reference_examples
from .registry import registry_as_dict
from .tiers import tiers_as_dict

WEB_DATA_SCHEMA_VERSION = "exergy_factor_web_data_v1"


WEB_PRESET_REFERENCE_IDS = {
    "electricity": "electricity-delivered",
    "mechanical": "shaft-work",
    "pvDc": "pv-dc-output",
    "battery": "battery-discharge",
    "pumpedHydro": "pumped-hydro-output",
    "solar": "solar-radiation-standard",
    "heat35": "heat-35c-standard",
    "heat40": "heat-40c-standard",
    "heat50": "heat-50c-standard",
    "heat60": "heat-60c-standard",
    "heat70": "heat-70c-standard",
    "heat80": "heat-80c-standard",
    "district80to50": "district-80c-to-50c",
    "heat90": "heat-90c-standard",
    "heat120": "heat-120c-standard",
    "steam150": "heat-150c-standard",
    "heat180": "heat-180c-standard",
    "heat250": "heat-250c-standard",
    "heat500": "heat-500c-standard",
    "cooling5": "cooling-5c-20c-ambient",
    "methane": "methane-lhv",
    "methaneHhv": "methane-hhv",
    "naturalGasLhv": "methane-lhv",
    "naturalGasHhv": "methane-hhv",
    "dieselLhv": "diesel-lhv",
    "gasolineLhv": "gasoline-lhv",
    "crudeOil": "crude-oil-approximate",
    "coalLhv": "coal-lhv",
    "hydrogenLhv": "hydrogen-lhv",
    "hydrogen": "hydrogen-hhv",
}


WEB_TYPED_UNIT_OVERRIDES = {
    "naturalGasHhv": "MWh_HHV_NG",
}


def build_web_data(*, records: Optional[Iterable[Mapping[str, object]]] = None) -> dict:
    """Build the compact reference data consumed by the static web calculator.

    The website keeps its own labels and layout. This payload only supplies the
    canonical factors and calculation context that should not drift from Python.
    """

    source_records = [dict(record) for record in (records or load_reference_examples())]
    records_by_id = {str(record["id"]): record for record in source_records}
    presets = {}
    for web_key, reference_id in WEB_PRESET_REFERENCE_IDS.items():
        reference = records_by_id[reference_id]
        presets[web_key] = _web_preset(web_key, reference)

    return {
        "schema_version": WEB_DATA_SCHEMA_VERSION,
        "source": "quantity-quality bundled reference_examples.json",
        "source_version": f"quantity-and-quality@{PACKAGE_VERSION}",
        "source_sha256": reference_data_sha256(),
        "conformance_contract": {
            "schema_version": "exergy_conformance_contract_v1",
            "sha256": conformance_contract_sha256(),
        },
        "presets": presets,
        "carrier_registry": registry_as_dict(),
        "fidelity_tiers": tiers_as_dict(),
    }


def write_web_data(
    output: Union[str, Path],
    *,
    js_output: Optional[Union[str, Path]] = None,
    conformance_output: Optional[Union[str, Path]] = None,
    variable_name: str = "EXERGY_FACTOR_REFERENCE_DATA",
) -> dict:
    """Write web reference JSON, browser bundle, and canonical contract copy."""

    data = build_web_data()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    if js_output is not None:
        js_path = Path(js_output)
        js_path.parent.mkdir(parents=True, exist_ok=True)
        js_path.write_text(_browser_bundle(data, variable_name=variable_name), encoding="utf-8")

    if conformance_output is not None:
        conformance_path = Path(conformance_output)
        conformance_path.parent.mkdir(parents=True, exist_ok=True)
        conformance_path.write_text(
            json.dumps(load_conformance_contract(), indent=2) + "\n",
            encoding="utf-8",
        )

    return data


def _web_preset(web_key: str, reference: Mapping[str, object]) -> dict:
    temperatures = extract_temperature_context(dict(reference))
    source_unit = str(reference["quantity_unit"])
    typed_unit = _typed_unit(web_key, reference)
    preset = {
        "key": web_key,
        "reference_id": reference["id"],
        "fx": float(reference["exergy_factor"]),
        "unit": _web_unit(source_unit),
        "base_unit": _web_unit(source_unit),
        "typed_unit": typed_unit,
        "category": str(reference.get("category", "")),
        "carrier": str(reference.get("carrier", "")),
        "basis": str(reference["basis"]),
        "reference": str(reference["reference"]),
        "boundary": str(reference["boundary"]),
        "calculation": str(reference["calculation"]),
        "source": str(reference["source"]),
        "adoption_note": str(reference.get("adoption_note", "")),
        "basis_type": str(reference.get("basis_type", "")),
        "confidence": str(reference.get("confidence", "")),
        "tier": str(reference.get("tier", "")) or _default_tier(reference),
    }
    if "source_c" in temperatures:
        preset["sourceC"] = temperatures["source_c"]
    if "sink_c" in temperatures:
        preset["sinkC"] = temperatures["sink_c"]
    if "cold_service_c" in temperatures:
        preset["coldServiceC"] = temperatures["cold_service_c"]
    if "ambient_sink_c" in temperatures:
        preset["ambientSinkC"] = temperatures["ambient_sink_c"]
    return preset


def _web_unit(unit: str) -> str:
    return unit.split("_", 1)[0]


def _typed_unit(web_key: str, reference: Mapping[str, object]) -> str:
    if web_key in WEB_TYPED_UNIT_OVERRIDES:
        return WEB_TYPED_UNIT_OVERRIDES[web_key]

    unit = str(reference["quantity_unit"])
    if "_" in unit:
        return unit

    category = str(reference.get("category", "")).lower()
    carrier = str(reference.get("carrier", "")).lower()
    base = _web_unit(unit)
    if category == "mechanical" or carrier == "mechanical work":
        return f"{base}_m"
    if category == "electrical" or carrier == "electric charge" or "electrical" in carrier:
        return f"{base}_e"
    return unit


def _default_tier(reference: Mapping[str, object]) -> str:
    category = str(reference.get("category", "")).lower()
    basis_type = str(reference.get("basis_type", "")).lower()
    if category == "thermal" or basis_type in {
        "thermal_carnot",
        "cooling_service",
        "radiative_petela",
    }:
        return "F2"
    return "F1"


def _browser_bundle(data: Mapping[str, object], *, variable_name: str) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return f"window.{variable_name} = {payload};\n"
