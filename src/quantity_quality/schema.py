from __future__ import annotations

import json
from importlib import resources

RECORD_SCHEMA_ID = (
    "https://raw.githubusercontent.com/cdimurro/quantity-and-quality/"
    "main/data/quantity_quality_record.schema.json"
)
STREAM_REQUEST_SCHEMA_ID = (
    "https://raw.githubusercontent.com/cdimurro/quantity-and-quality/"
    "main/data/stream_calculation_request.schema.json"
)
ENERGY_ACCOUNTING_REQUEST_SCHEMA_ID = (
    "https://raw.githubusercontent.com/cdimurro/quantity-and-quality/"
    "main/data/energy_accounting_request.schema.json"
)


def load_record_schema() -> dict:
    """Load the packaged JSON Schema for Quantity + Quality records."""

    path = resources.files("quantity_quality").joinpath("data/quantity_quality_record.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_stream_request_schema() -> dict:
    """Load the packaged JSON Schema for the unified stream request."""

    path = resources.files("quantity_quality").joinpath(
        "data/stream_calculation_request.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def load_energy_accounting_request_schema() -> dict:
    """Load the packaged schema for primary-secondary-final-useful end-use accounts."""

    path = resources.files("quantity_quality").joinpath(
        "data/energy_accounting_request.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def minimum_record_fields() -> tuple[str, ...]:
    """Return the minimum portable field set for direct `fx` records."""

    return ("quantity", "unit", "exergy_factor")
