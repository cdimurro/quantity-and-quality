# Quantity + Quality Stream Calculator

Use the smallest input you have. Every path returns energy quantity (`Q`),
Exergy Factor (`fx`), accessible exergy (`X = Q × fx`), and the methods used.

## 1. Use The Browser

Open [exergyfactor.com](https://exergyfactor.com), choose the energy form, and
enter the quantity and any temperatures the form requires. Nothing needs to be
installed.

## 2. Start With A Known Energy Quantity

```bash
quantity-quality calc thermal --quantity 1 --unit MWh_th --source-c 80 --sink-c 20
quantity-quality calc fuel --quantity 1 --fuel "natural gas" --basis HHV
quantity-quality calc electricity --quantity 1 --unit MWh
```

The equivalent Python call is:

```python
import quantity_quality as qq

record = qq.thermal(1, "MWh_th", source_c=80, sink_c=20)
print(record.full_notation)
print(record.accessible_exergy, record.accessible_exergy_unit)
```

## 3. Start With Power And Time

One JSON-shaped request works from Python, the CLI, or HTTP:

```json
{
  "stream_type": "electricity",
  "power": 100,
  "power_unit": "kW",
  "duration_hours": 8
}
```

```bash
quantity-quality calculate '{"stream_type":"electricity","power":100,"power_unit":"kW","duration_hours":8}' --json
```

The result is `800 kWh_e, fx = 1.0` and `800 kWh_ex`.

## 4. Calculate A Sensible-Heat Stream

Provide mass or mass flow, heat capacity, supply temperature, return
temperature, and reference temperature:

```bash
quantity-quality calculate examples/stream-calculation.json --json
```

The library calculates both:

```text
Q = m cp (Ts - Tr)
fx = 1 - T0 ln(Ts/Tr) / (Ts - Tr)
```

The result identifies the quantity and quality methods separately and prints all
three temperatures in its reproducible notation.

## 5. Calculate Fuel Energy From Mass Or Volume

```python
record = qq.calculate_stream({
    "stream_type": "fuel",
    "mass": 100,
    "mass_unit": "kg",
    "heating_value": 50,
    "heating_value_unit": "MJ/kg",
    "fuel": "natural gas",
    "basis": "LHV",
})
```

Always state HHV or LHV. The basis is retained in the unit and notation.
Use `volume` and `volume_unit` instead of `mass` and `mass_unit` when the
heating value is stated per unit volume.

## 6. Calculate Solar Or Cooling

```python
solar = qq.calculate_stream({
    "stream_type": "solar",
    "irradiance_w_m2": 800,
    "area_m2": 50,
    "duration_hours": 6,
})

cooling = qq.calculate_stream({
    "stream_type": "cooling",
    "quantity": 1,
    "unit": "MWh_cooling",
    "cold_service_c": 7,
    "ambient_sink_c": 30,
})
```

## 7. Discover Inputs Programmatically

AI agents and other clients should discover the contract instead of guessing
field names:

```bash
quantity-quality capabilities --json
quantity-quality capabilities --json-schema
```

With the optional HTTP API:

```text
GET  /v1/capabilities
GET  /v1/calculate/schema
POST /v1/calculate
```

Invalid requests return stable error codes and the field that needs attention.

## 8. Account For Applied Exergy At The Task

The stream calculator answers `Q`, `fx`, and `X` at one boundary. When you know
several boundaries, use a separate end-use account:

```bash
quantity-quality account examples/end-use-accounting.json --json
```

The stages have deliberately different meanings:

- primary energy is at the resource or statistical supply boundary;
- secondary energy is an optional transformed, transportable carrier before final delivery;
- final energy is the carrier delivered to the end user;
- useful energy is the end-use device output and can contain exergy and anergy;
- Applied Exergy is the exergy that crosses from the final device into the task;
- the energy service is the desired outcome in a non-energy unit.

For a heat pump, `3 MWh_th` of useful heat at `fx = 0.064` contains
`0.192 MWh_ex` of Applied Exergy. It can come from `1 MWh_e` of final energy
without violating conservation: the additional heat comes from the environment,
while the Applied Exergy remains below the final electrical exergy.

Services remain separate:

```json
{
  "name": "Warm home",
  "quantity": 720,
  "unit": "occupied_comfort_hour"
}
```

Other valid outcome units include `cold_beer_served`, `passenger_mile`,
`lumen_hour`, and `tonne_metre`. Do not use `MWh`, `J`, or another energy unit
for the service.

Energy balance data may omit `fx`. The account will retain the energy stage and
provenance without inventing exergy. Use `accounting_method: "substitution"` for
historical fossil-equivalent primary-energy series; the counterfactual quantity
is reported but cannot be multiplied by a physical Exergy Factor. See
[`dataset-compatibility.md`](dataset-compatibility.md) for provider-specific
guidance.

## 9. Add Quality To Existing Records

The cleaner remains available when the quantity is already in a file:

```bash
quantity-quality clean energy.csv --output energy_qq.csv
```

It accepts CSV, JSON, JSONL, Excel, DataFrame, SQL, streams, and HTTP(S) sources.
The output adds `fx`, notation, accessible exergy, methods, assumptions, warnings,
and validation issues without performing downstream process or economic analysis.
