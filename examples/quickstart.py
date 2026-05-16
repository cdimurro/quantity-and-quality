from quantity_quality import EnergyReport, ReferenceContext, thermal_exergy_factor_c


context = ReferenceContext(
    reference="20 C sink",
    boundary="district heating delivery point",
    operating_basis="Carnot factor from measured source and sink temperatures",
)

factor = thermal_exergy_factor_c(source_c=80, sink_c=20)
report = EnergyReport(
    quantity=1.0,
    unit="MWh",
    exergy_factor=factor,
    context=context,
    label="80 C heat delivered to a 20 C sink",
)

print(report.as_dict())

