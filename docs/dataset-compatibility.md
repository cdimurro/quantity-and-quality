# Dataset Compatibility

The library should accept energy data without becoming another energy-data
warehouse. Dataset adoption therefore means:

1. preserve the source variable, unit, boundary, and accounting convention;
2. map physical flows to primary, secondary, final, or useful stages;
3. calculate exergy only when a defensible carrier-specific `fx` is available;
4. keep counterfactual accounting quantities, such as substitution-method
   primary energy, out of physical exergy calculations.

## Primary-energy conventions

Use `accounting_method` on any imported stage:

| Value | Meaning | Can `X = E × fx` be used? |
|---|---|---:|
| `physical_energy_content` | Physical energy content convention | Yes, when the carrier and `fx` are known |
| `total_energy_supply` | Total energy supply under a declared statistical balance | Yes, for disaggregated physical carriers with a defensible `fx` |
| `direct` | Direct primary-energy convention | Yes, for disaggregated physical carriers with a defensible `fx` |
| `substitution` | Counterfactual fossil-input equivalent | No |
| `reported` | Convention not yet identified | Only when the supplied quantity is known to represent a physical stream |

The substitution method divides non-fossil electricity by an assumed thermal
efficiency. It is useful for some historical comparisons, but the resulting
number is not a physical stream at that magnitude. The library accepts it as an
energy-only record and refuses a physical `fx` on that stage.

The Energy Institute and Our World in Data changed their headline primary-energy
series to the physical-energy-content/total-energy-supply method in 2025–2026.
Older downloads and publications can still contain substitution-method values,
so the method must travel with the number.

## Recommended datasets

| Dataset | Best use here | Recommendation |
|---|---|---|
| [CL-PFU Energy and Exergy Database](https://doi.org/10.5518/1199) | Primary, final, and useful energy/exergy; direct comparison with Applied Exergy | Highest-value validation dataset. Support selected CSV imports, but do not vendor the roughly 252 MB database or its licensed upstream IEA inputs. |
| [Our World in Data Energy](https://github.com/owid/energy-data) | Broad country-year primary/TES indicators and secondary electricity generation | Maintain examples and compatibility tests. Check each variable's codebook and source licence. It does not provide a complete open final/useful chain. |
| [Eurostat energy balances](https://ec.europa.eu/eurostat/cache/metadata/en/nrg_bal_esms.htm) | Detailed EU supply, transformation, secondary-carrier, and final-consumption flows | Strong future adapter candidate because products, flows, units, and flags are explicit. Preserve zero/confidential/not-available flags. |
| [U.S. EIA Open Data](https://www.eia.gov/opendata/documentation.php) | US electricity, fuels, state balances, and end-use series | Strong future adapter candidate. The API requires a key and each route has its own facets and units. |
| [UNSD Energy Statistics](https://unstats.un.org/unsd/energystats/data/) | Global production, transformation, primary/secondary products, and final consumption | Semantically useful, especially outside OECD/EU coverage. Do not redistribute without checking the non-profit reuse condition. |
| [IEA World Energy Balances](https://www.iea.org/data-and-statistics/data-product/world-energy-balances) and [end-use indicators](https://www.iea.org/data-and-statistics/data-product/energy-end-uses-and-efficiency-indicators) | The most complete international balance and activity/intensity structure | Accept user-supplied licensed extracts; do not bundle them. The free highlights are useful fixtures but not a full open database. |
| [Energy Institute Statistical Review](https://energyinst.org/statistical-review/resources-and-data-downloads), [Ember](https://ember-energy.org/data/yearly-electricity-data/), and [IRENA](https://www.irena.org/Data/Downloads/Tools) | Timely total-energy-supply or secondary electricity generation | Already compatible through CSV/XLSX mapping. Add a dedicated adapter only if repeated user demand justifies maintaining source-specific column mappings. |

## Import contract

CSV, JSON, JSONL, Excel, DataFrame, SQL, stream, and HTTP(S) inputs are already
supported. Wide national datasets should first select or reshape one physical
quantity per record. Preserve provenance with `source_dataset` and
`source_variable`.

Historical substitution-method data can be represented without pretending it
has a physical Exergy Factor:

```json
{
  "primary": {
    "quantity": 250,
    "unit": "TWh",
    "accounting_method": "substitution",
    "source_dataset": "Our World in Data Energy dataset (historical methodology)",
    "source_variable": "solar_consumption"
  },
  "secondary": {
    "quantity": 100,
    "unit": "TWh_e",
    "fx": 1.0,
    "source_variable": "solar_electricity"
  }
}
```

An aggregate mix without carrier-level quality can also be retained by omitting
`fx`. The output reports energy and provenance, marks quality as unavailable,
and does not invent aggregate exergy.

## Release decision

The core product is complete without bundling another large dataset. The CL-PFU
database is the best external validation target, while OWID, Eurostat, and EIA
are the best adapter candidates. Source-specific download clients should remain
optional: the durable public contract is the stage, accounting method, carrier,
unit, boundary, `fx`, and provenance—not a particular provider's current column
layout.
