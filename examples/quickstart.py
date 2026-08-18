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

measured_loop = qq.calculate_stream(
    {
        "stream_type": "heat",
        "mass_flow_kg_s": 2.5,
        "duration_hours": 8,
        "specific_heat_kj_kg_k": 4.186,
        "source_c": 80,
        "return_c": 50,
        "sink_c": 20,
    }
)
print(measured_loop.full_notation)
print(measured_loop.quantity_method_id, measured_loop.method_identifier)

shaft = qq.calculate_stream(
    {
        "stream_type": "mechanical",
        "mechanical_mode": "shaft",
        "torque_nm": 500,
        "rotational_speed_rpm": 1800,
        "duration_hours": 2,
    }
)
print(shaft.full_notation)

biomass = qq.calculate_stream(
    {
        "stream_type": "biomass",
        "mass": 1000,
        "mass_unit": "kg",
        "heating_value": 18,
        "heating_value_unit": "MJ/kg",
        "basis": "LHV",
        "chemical_exergy": 19,
        "energy_basis_value": 18,
    }
)
print(biomass.full_notation)

fusion_neutron = qq.calculate_stream(
    {
        "stream_type": "thermonuclear",
        "reaction_preset": "dt_fusion",
        "reaction_count": 1e20,
        "nuclear_channel": "neutron",
    }
)
print(fusion_neutron.full_notation)

plasma = qq.calculate_stream(
    {
        "stream_type": "plasma",
        "volume_m3": 1,
        "plasma_species": [
            {"name": "electron", "number_density_m3": 1e20, "temperature_ev": 1000},
            {"name": "deuteron", "number_density_m3": 1e20, "temperature_ev": 1000},
        ],
        "magnetic_flux_density_t": 0.01,
    }
)
print(plasma.full_notation)
