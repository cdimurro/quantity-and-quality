from __future__ import annotations

import json
from importlib import resources


RECORD_SCHEMA_ID = "https://github.com/cdimurro/quantity-and-quality/schemas/quantity_quality_record.schema.json"


def load_record_schema() -> dict:
    """Load the packaged JSON Schema for Quantity + Quality records."""

    path = resources.files("quantity_quality").joinpath("data/quantity_quality_record.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def minimum_record_fields() -> tuple[str, ...]:
    """Return the minimum portable field set for direct `fx` records."""

    return ("quantity", "unit", "exergy_factor")
