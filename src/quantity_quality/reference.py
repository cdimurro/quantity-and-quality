from __future__ import annotations

import json
from importlib import resources
from typing import Iterable, List, Optional


def load_reference_examples() -> List[dict]:
    """Load bundled starter reference examples."""

    path = resources.files("quantity_quality").joinpath("data/reference_examples.json")
    return json.loads(path.read_text(encoding="utf-8"))


def get_reference_example(example_id: str) -> dict:
    """Return one reference example by stable id."""

    for record in load_reference_examples():
        if record["id"] == example_id:
            return record
    raise KeyError(f"unknown reference example: {example_id}")


def filter_reference_examples(
    *,
    category: Optional[str] = None,
    text: Optional[str] = None,
    records: Optional[Iterable[dict]] = None,
) -> List[dict]:
    """Filter reference examples by category and free text."""

    source = list(records) if records is not None else load_reference_examples()
    category_query = category.lower() if category else None
    text_query = text.lower() if text else None

    result = []
    for record in source:
        if category_query and record.get("category", "").lower() != category_query:
            continue
        if text_query:
            haystack = " ".join(str(value) for value in record.values()).lower()
            if text_query not in haystack:
                continue
        result.append(record)
    return result

