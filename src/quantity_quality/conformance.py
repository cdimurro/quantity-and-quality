from __future__ import annotations

import hashlib
import json
from importlib import resources
from typing import Any

CONFORMANCE_SCHEMA_VERSION = "exergy_conformance_contract_v1"


def _data_text(name: str) -> str:
    path = resources.files("quantity_quality").joinpath(f"data/{name}")
    return path.read_text(encoding="utf-8")


def load_conformance_contract() -> dict[str, Any]:
    """Load the versioned cross-product physics and reporting contract."""

    contract = json.loads(_data_text("conformance_contract_v1.json"))
    if contract.get("schema_version") != CONFORMANCE_SCHEMA_VERSION:
        raise ValueError("unsupported conformance contract schema")
    return contract


def conformance_contract_sha256() -> str:
    """Return the SHA-256 fingerprint of normalized packaged contract text."""

    return hashlib.sha256(_data_text("conformance_contract_v1.json").encode("utf-8")).hexdigest()


def reference_data_sha256() -> str:
    """Return the cross-platform SHA-256 fingerprint exported to consumers."""

    return hashlib.sha256(_data_text("reference_examples.json").encode("utf-8")).hexdigest()
