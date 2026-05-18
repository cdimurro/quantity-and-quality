from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Optional, Union

from .reference import extract_temperature_context, load_reference_examples


WEB_DATA_SCHEMA_VERSION = "exergy_factor_web_data_v1"


WEB_PRESET_REFERENCE_IDS = {
    "electricity": "electricity-delivered",
    "battery": "battery-discharge",
    "solar": "solar-radiation-standard",
    "heat60": "heat-60c-standard",
    "heat80": "heat-80c-standard",
    "heat120": "heat-120c-standard",
    "steam150": "heat-150c-standard",
    "heat250": "heat-250c-standard",
    "heat500": "heat-500c-standard",
    "cooling5": "cooling-5c-20c-ambient",
    "methane": "methane-lhv",
    "naturalGasLhv": "methane-lhv",
    "naturalGasHhv": "methane-hhv",
    "dieselLhv": "diesel-lhv",
    "gasolineLhv": "gasoline-lhv",
    "crudeOil": "crude-oil-approximate",
    "coalLhv": "coal-lhv",
    "hydrogenLhv": "hydrogen-lhv",
    "hydrogen": "hydrogen-hhv",
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
        "presets": presets,
    }


def write_web_data(
    output: Union[str, Path],
    *,
    js_output: Optional[Union[str, Path]] = None,
    variable_name: str = "EXERGY_FACTOR_REFERENCE_DATA",
) -> dict:
    """Write web reference JSON and optionally a synchronous browser data bundle."""

    data = build_web_data()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    if js_output is not None:
        js_path = Path(js_output)
        js_path.parent.mkdir(parents=True, exist_ok=True)
        js_path.write_text(_browser_bundle(data, variable_name=variable_name), encoding="utf-8")

    return data


def _web_preset(web_key: str, reference: Mapping[str, object]) -> dict:
    temperatures = extract_temperature_context(dict(reference))
    preset = {
        "key": web_key,
        "reference_id": reference["id"],
        "fx": float(reference["exergy_factor"]),
        "unit": _web_unit(str(reference["quantity_unit"])),
        "basis": str(reference["basis"]),
        "reference": str(reference["reference"]),
        "boundary": str(reference["boundary"]),
        "calculation": str(reference["calculation"]),
        "source": str(reference["source"]),
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


def _browser_bundle(data: Mapping[str, object], *, variable_name: str) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return (
        "window."
        f"{variable_name}"
        " = "
        f"{payload}"
        ";\n"
    )
