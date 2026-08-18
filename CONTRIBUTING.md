# Contributing

Issues, corrections, documentation improvements, and carefully sourced carrier
examples are welcome.

## Development setup

```bash
python -m pip install -e ".[all,dev]"
python scripts/sync_reference_data.py --check
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=quantity_quality --cov-report=term-missing
python -m build
python -m twine check dist/*
```

## Reference-data changes

Edit `data/reference_examples.json`, include a stable source or DOI and the
calculation basis, then run `python scripts/sync_reference_data.py`. Commit the
source JSON, generated CSV, packaged JSON, and tests together. Never introduce a
factor whose carrier, denominator basis, reference environment, or boundary is
ambiguous.

## Pull requests

Keep each change focused, add regression tests, update `CHANGELOG.md` for public
behavior, and explain any numerical tolerance. By contributing, you agree that
your contribution is licensed under the repository's MIT license.
