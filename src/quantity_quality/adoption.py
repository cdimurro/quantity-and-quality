from __future__ import annotations

from typing import List

from .core import format_energy_notation


COMMON_NOTATION_EXAMPLES: List[dict] = [
    {
        "name": "Grid electricity delivered",
        "notation": format_energy_notation(845, "kWh", 1.0),
        "where_used": "utility bills, procurement, facility meters",
        "basis": "electrical work at delivery boundary",
    },
    {
        "name": "PV AC output",
        "notation": format_energy_notation(1.2, "MWh", 1.0),
        "where_used": "solar project reporting, power purchase agreements",
        "basis": "electrical output after conversion",
    },
    {
        "name": "Battery discharge",
        "notation": format_energy_notation(2.4, "MWh", 1.0),
        "where_used": "storage dispatch, grid services, microgrids",
        "basis": "electrical output boundary",
    },
    {
        "name": "Motor shaft work",
        "notation": format_energy_notation(12.5, "GJ", 1.0),
        "where_used": "industrial drives, pumps, compressors",
        "basis": "mechanical work at shaft boundary",
    },
    {
        "name": "Solar radiation resource",
        "notation": format_energy_notation(5.2, "MWh_solar", 0.932),
        "where_used": "solar resource assessment, PV exergy accounting",
        "basis": "Petela radiation factor at 20 C reference",
    },
    {
        "name": "40 C low-temperature heat",
        "notation": format_energy_notation(35000, "Btu_th", 0.064),
        "where_used": "space heating, data-center heat recovery",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "60 C domestic hot water heat",
        "notation": format_energy_notation(500, "kWh_th", 0.12),
        "where_used": "buildings, campuses, hotels, hospitals",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "80 C district heat",
        "notation": format_energy_notation(1.8, "MWh_th", 0.17),
        "where_used": "district energy delivery and tariffs",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "80 C district heat to 50 C return",
        "notation": format_energy_notation(1, "MWh_th", 0.085),
        "where_used": "district heating operations",
        "basis": "Carnot factor to measured return-line sink",
    },
    {
        "name": "90 C district heat to 50 C return",
        "notation": format_energy_notation(3.1, "MWh_th", 0.11),
        "where_used": "campus and city heat networks",
        "basis": "Carnot factor to measured return-line sink",
    },
    {
        "name": "150 C low-pressure steam",
        "notation": format_energy_notation(12, "GJ_th", 0.307),
        "where_used": "process heat, food, pharma, paper, drying",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "250 C process heat",
        "notation": format_energy_notation(0.004, "EJ_th", 0.44),
        "where_used": "industrial heat recovery and electrification",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "500 C high-temperature heat",
        "notation": format_energy_notation(22, "MMBtu_th", 0.621),
        "where_used": "cement, metals, chemicals, high-grade process heat",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "Methane / natural gas on LHV basis",
        "notation": format_energy_notation(249, "MWh_LHV", 1.04),
        "where_used": "fuel inventories, gas procurement, industrial boilers",
        "basis": "chemical exergy divided by LHV",
    },
    {
        "name": "Methane / natural gas on HHV basis",
        "notation": format_energy_notation(850, "MMBtu_HHV", 0.93),
        "where_used": "North American gas bills and fuel accounting",
        "basis": "chemical exergy divided by HHV",
    },
    {
        "name": "Hydrogen on LHV basis",
        "notation": format_energy_notation(6.8, "MWh_LHV", 0.98),
        "where_used": "electrolyzer output, fuel policy, ammonia, refining",
        "basis": "chemical exergy divided by LHV",
    },
    {
        "name": "Hydrogen on HHV basis",
        "notation": format_energy_notation(6.8, "MWh_HHV", 0.83),
        "where_used": "hydrogen reporting where HHV is the declared denominator",
        "basis": "chemical exergy divided by HHV",
    },
    {
        "name": "80 C hot-water thermal storage",
        "notation": format_energy_notation(14, "MWh_th", 0.17),
        "where_used": "thermal storage, campuses, district energy",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "150 C process-heat storage",
        "notation": format_energy_notation(3.5, "MWh_th", 0.307),
        "where_used": "thermal oil, molten-salt, industrial storage",
        "basis": "Carnot factor to 20 C sink",
    },
    {
        "name": "7 C cooling service against 30 C ambient",
        "notation": format_energy_notation(900, "kWh_cooling", 0.082),
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
