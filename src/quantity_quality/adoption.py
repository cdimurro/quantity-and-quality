from __future__ import annotations

from typing import List, Optional

from .model import QuantityQualityRecord


def _example_notation(
    quantity: float,
    unit: str,
    fx: float,
    *,
    method: str = "supplied",
    source_c: Optional[float] = None,
    sink_c: Optional[float] = None,
    cold_service_c: Optional[float] = None,
    ambient_sink_c: Optional[float] = None,
    energy_basis: Optional[str] = None,
) -> dict[str, str]:
    """Return both compatibility short notation and the canonical full form.

    The examples catalog often knows the temperatures or fuel basis even when a
    generic caller does not. Keep the short ``notation`` field for compatibility,
    but expose ``full_notation`` so examples teach the self-verifying standard.
    """

    record = QuantityQualityRecord(
        quantity=quantity,
        unit=unit,
        exergy_factor=fx,
        method=method,
        source_c=source_c,
        sink_c=sink_c,
        cold_service_c=cold_service_c,
        ambient_sink_c=ambient_sink_c,
        energy_basis=energy_basis,
    )
    return {"notation": record.notation, "full_notation": record.full_notation}


COMMON_NOTATION_EXAMPLES: List[dict] = [
    {
        "name": "Grid electricity delivered",
        **_example_notation(845, "kWh_e", 1.0),
        "where_used": "utility bills, procurement, facility meters",
        "basis": "electrical work at delivery boundary",
    },
    {
        "name": "PV AC output",
        **_example_notation(1.2, "MWh_e", 1.0),
        "where_used": "solar project reporting, power purchase agreements",
        "basis": "electrical output after conversion",
    },
    {
        "name": "Battery discharge",
        **_example_notation(2.4, "MWh_e", 1.0),
        "where_used": "storage dispatch, grid services, microgrids",
        "basis": "electrical output boundary",
    },
    {
        "name": "Motor shaft work",
        **_example_notation(12.5, "GJ_m", 1.0),
        "where_used": "industrial drives, pumps, compressors",
        "basis": "mechanical work at shaft boundary",
    },
    {
        "name": "Solar radiation resource",
        **_example_notation(5.2, "MWh_solar", 0.932, method="solar", sink_c=20),
        "where_used": "solar resource assessment, PV exergy accounting",
        "basis": "Petela radiation factor at 20 C reference",
    },
    {
        "name": "40 C low-temperature heat",
        **_example_notation(35000, "BTU_th", 0.064, method="thermal", source_c=40, sink_c=20),
        "where_used": "space heating, data-center heat recovery",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "60 C domestic hot water heat",
        **_example_notation(500, "kWh_th", 0.12, method="thermal", source_c=60, sink_c=20),
        "where_used": "buildings, campuses, hotels, hospitals",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "80 C district heat",
        **_example_notation(1.8, "MWh_th", 0.17, method="thermal", source_c=80, sink_c=20),
        "where_used": "district energy delivery and tariffs",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "80 C district heat to 50 C return",
        **_example_notation(1, "MWh_th", 0.085, method="thermal", source_c=80, sink_c=50),
        "where_used": "district heating operations",
        "basis": "Carnot factor to measured return-line sink",
    },
    {
        "name": "90 C district heat to 50 C return",
        **_example_notation(3.1, "MWh_th", 0.11, method="thermal", source_c=90, sink_c=50),
        "where_used": "campus and city heat networks",
        "basis": "Carnot factor to measured return-line sink",
    },
    {
        "name": "150 C low-pressure steam",
        **_example_notation(12, "GJ_th", 0.307, method="thermal", source_c=150, sink_c=20),
        "where_used": "process heat, food, pharma, paper, drying",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "250 C process heat",
        **_example_notation(0.004, "EJ_th", 0.44, method="thermal", source_c=250, sink_c=20),
        "where_used": "industrial heat recovery and electrification",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "500 C high-temperature heat",
        **_example_notation(22, "MMBTU_th", 0.621, method="thermal", source_c=500, sink_c=20),
        "where_used": "cement, metals, chemicals, high-grade process heat",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "Methane / natural gas on LHV basis",
        **_example_notation(249, "MWh_LHV_CH4", 1.04, method="fuel", energy_basis="LHV"),
        "where_used": "fuel inventories, gas procurement, industrial boilers",
        "basis": "chemical exergy divided by LHV",
    },
    {
        "name": "Methane / natural gas on HHV basis",
        **_example_notation(850, "MMBtu_HHV_NG", 0.93, method="fuel", energy_basis="HHV"),
        "where_used": "North American gas bills and fuel accounting",
        "basis": "chemical exergy divided by HHV",
    },
    {
        "name": "Hydrogen on LHV basis",
        **_example_notation(6.8, "MWh_LHV_H2", 0.98, method="fuel", energy_basis="LHV"),
        "where_used": "electrolyzer output, fuel policy, ammonia, refining",
        "basis": "chemical exergy divided by LHV",
    },
    {
        "name": "Hydrogen on HHV basis",
        **_example_notation(6.8, "MWh_HHV_H2", 0.83, method="fuel", energy_basis="HHV"),
        "where_used": "hydrogen reporting where HHV is the declared denominator",
        "basis": "chemical exergy divided by HHV",
    },
    {
        "name": "80 C hot-water thermal storage",
        **_example_notation(14, "MWh_th", 0.17, method="thermal", source_c=80, sink_c=20),
        "where_used": "thermal storage, campuses, district energy",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "150 C process-heat storage",
        **_example_notation(3.5, "MWh_th", 0.307, method="thermal", source_c=150, sink_c=20),
        "where_used": "thermal oil, molten-salt, industrial storage",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "7 C cooling service against 30 C ambient",
        **_example_notation(
            900,
            "kWh_cooling",
            0.082,
            method="cooling",
            cold_service_c=7,
            ambient_sink_c=30,
        ),
        "where_used": "chilled water, cold storage, district cooling",
        "basis": "minimum work potential per unit cooling service",
    },
]


ADOPTION_FIELDS = [
    "quantity",
    "unit",
    "exergy_factor",
    "reference",
    "boundary",
    "operating_basis",
]


INPUT_PATTERNS = {
    "known_fx": ["quantity", "unit", "fx"],
    "reference_lookup": ["quantity", "unit", "reference_id"],
    "thermal_measurement": ["quantity", "unit", "source_c", "sink_c"],
    "chemical_calculation": ["quantity", "unit", "chemical_exergy", "energy_basis"],
    "fuel_preset": ["quantity", "unit", "fuel", "energy_basis"],
}


STANDARD_INTEGRATION_POINTS = [
    {
        "standard": "ISO 50001 energy management",
        "adoption_path": "Use fx as a supplemental energy performance indicator alongside kWh, cost, and emissions.",
    },
    {
        "standard": "IPMVP measurement and verification",
        "adoption_path": "Report both energy savings and avoided accessible exergy: delta X_A = fx_baseline E_baseline - fx_post E_post.",
    },
    {
        "standard": "ISO 14040 life-cycle assessment",
        "adoption_path": "Attach fx to energy and material flow inventory lines so low-grade heat, fuels, and electricity are not collapsed into identical MWh.",
    },
    {
        "standard": "Utility tariffs and market products",
        "adoption_path": "Publish MWh and MWh_ex attributes for heat, storage, hydrogen, and flexible demand products.",
    },
    {
        "standard": "Procurement and engineering specifications",
        "adoption_path": "Require every quoted energy stream to declare quantity, fx, reference, boundary, and basis.",
    },
]
