import quantity_quality as qq


record = qq.report(1, "MWh", fx=0.73)
print(record.notation)
print(record.capabilities)
print(record.missing_context)

heat = qq.thermal(2.738, "kWh_th", source_c=541)
print(heat.full_notation)
print(heat.accessible_exergy, heat.accessible_exergy_unit)

district_heat = qq.lookup("heat-80c-standard", quantity=1.8)
print(district_heat.full_notation)

messy_records = [
    {"asset": "Grid meter", "energy_kwh": 845, "reference_id": "electricity-delivered"},
    {"asset": "Kiln exhaust", "energy_kwh": 2738, "supply_temp_f": 1005.8},
    {"asset": "Unknown stream", "quantity": 2.738, "unit": "kWh_th", "fx": 0.64},
]
cleaned = qq.clean_records(messy_records)
for cleaned_record in cleaned:
    print(cleaned_record["full_notation"], cleaned_record["missing_context"])

mapped = qq.clean_record(
    {"asset": "Kiln exhaust", "measured_energy": 2.738, "supply_temp_f": 1005.8},
    mapping={
        "label": "asset",
        "quantity": "measured_energy",
        "unit": "kWh_th",
        "source_f": "supply_temp_f",
    },
)
print(mapped["full_notation"])

comparison = qq.compare([
    qq.electricity(1, "MWh"),
    qq.thermal(1000, "kWh_th", source_c=80),
    qq.fuel(850, "natural gas", basis="HHV", unit="MMBtu_HHV"),
])
print(comparison)
