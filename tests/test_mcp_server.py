import pytest

pytest.importorskip("mcp.server.fastmcp")

from quantity_quality.mcp_server import create_mcp_server


def test_mcp_server_exposes_keyless_calculation_tools():
    server = create_mcp_server()
    tools = server._tool_manager._tools
    assert {
        "calculate_stream",
        "account_energy",
        "report_energy",
        "thermal_exergy",
        "cooling_exergy",
        "capabilities",
        "registry",
        "tiers",
        "reference_examples",
        "reference_example",
    } <= set(tools)

    result = tools["thermal_exergy"].fn(
        quantity=1,
        source_c=80,
        sink_c=20,
        unit="MWh_th",
    )
    assert result["exergy_factor"] == pytest.approx(1 - 293.15 / 353.15)
    assert result["accessible_exergy_unit"] == "MWh_ex"


def test_mcp_stream_tool_uses_the_unified_calculation_contract():
    server = create_mcp_server()
    result = server._tool_manager._tools["calculate_stream"].fn(
        {
            "stream_type": "heat",
            "mass": 1000,
            "specific_heat_kj_kg_k": 4.186,
            "source_c": 80,
            "return_c": 50,
            "sink_c": 20,
        }
    )
    assert result["method_id"] == "thermal.sensible.integrated.v1"
    assert result["distinguishability"]["basis"] == "sensible_temperature_path"
