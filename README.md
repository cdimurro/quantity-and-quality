# Quantity and Quality

Companion repository for Christopher DiMurro's paper, **Quantity and Quality: A Standard Reporting Framework for Energy Systems**.

The central idea is simple: do not report energy quantity alone. The new everyday notation should look like this:

```text
1 MWh, f_X = 0.73
```

That means "one megawatt-hour of energy carrying 0.73 megawatt-hours of accessible work potential." The same pattern works for any scale or unit: `1 kWh, f_X = 0.73`, `12 GJ, f_X = 0.41`, or `4.2 MW, f_X = 0.18`.

Public examples should usually use a factor like `0.73` instead of `1.00` so readers immediately see that `f_X` is a quality field, not just another way to repeat the energy quantity.

The formal version is:

```text
Energy quantity: (E, f_X)
Power rate:      (P, f_X)
```

`E` or `P` says how much energy is present or moving. `f_X` says how much accessible work potential that energy carries at a declared reporting boundary.

## What is in this repository

- `index.html` - the GitHub Pages companion site.
- `data/reference_examples.json` and `data/reference_examples.csv` - starter reference examples for common energy carriers, heat grades, storage types, and reporting cases.
- `src/quantity_quality/` - a small Python library for computing and reporting records like `1 MWh, f_X = 0.73`.
- `examples/quickstart.py` - a direct adoption example.
- `paper/quantity-and-quality-standard-reporting-framework.pdf` - the source paper PDF.

## Install the Python library locally

```bash
python -m pip install -e .
```

Then:

```python
from quantity_quality import EnergyReport, ReferenceContext, thermal_exergy_factor_c

context = ReferenceContext(
    reference="standard thermal sink",
    boundary="building heating loop",
    operating_basis="source and sink temperatures in C",
)

factor = thermal_exergy_factor_c(source_c=80, sink_c=20)
stream = EnergyReport(quantity=1.0, unit="MWh", exergy_factor=factor, context=context)

print(stream.accessible_exergy)
```

## Command-line examples

```bash
quantity-quality thermal --source-c 80 --sink-c 20 --quantity 1 --unit MWh
quantity-quality lookup heat-80c-standard
quantity-quality list --category thermal
```

## Reporting fields

A minimum record should include:

- `quantity` or `power`
- `unit`
- `exergy_factor`
- `reference`
- `boundary`
- `operating_basis`

For chemical carriers, also declare the energy basis, such as `LHV`, `HHV`, or `chemical_exergy_table`.

## License

Software, site source, and starter data are released under the MIT License unless otherwise noted. The paper remains attributable to Christopher DiMurro.
