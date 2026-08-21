"""Local Model Context Protocol server for Quantity + Quality.

The server uses the installed library directly over MCP stdio. It does not call
the hosted HTTP API and therefore does not require an API key, account, or
network connection. The optional ``mcp`` dependency keeps the core package
small; install it with ``quantity-and-quality[mcp]``.
"""

from __future__ import annotations

from typing import Any, Optional

from .accounting import account_energy_chain
from .api import cooling as _cooling
from .api import report as _report
from .api import thermal as _thermal
from .reference import filter_reference_examples, get_reference_example
from .registry import registry_as_dict
from .streams import calculate_stream as _calculate_stream
from .streams import stream_capabilities as _stream_capabilities
from .tiers import tiers_as_dict


def create_mcp_server(
    *,
    streamable_http_path: str = "/mcp",
    stateless_http: bool = False,
    host: str = "127.0.0.1",
):
    """Build the MCP server and register the public, keyless calculation tools."""

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("MCP support requires: pip install quantity-and-quality[mcp]") from exc

    server = FastMCP(
        "Quantity and Quality",
        instructions=(
            "Calculate energy quantity, Exergy Factor, accessible exergy, and "
            "Applied Exergy. This local server calls the deterministic Python "
            "library directly; no API key or network access is used."
        ),
        streamable_http_path=streamable_http_path,
        stateless_http=stateless_http,
        host=host,
    )

    @server.tool()
    def calculate_stream(request: dict[str, Any]) -> dict[str, Any]:
        """Calculate one physical energy stream from a stream request object."""

        return _calculate_stream(request).as_dict()

    @server.tool()
    def account_energy(request: dict[str, Any]) -> dict[str, Any]:
        """Account primary/secondary/final/useful energy and Applied Exergy."""

        return account_energy_chain(request).as_dict()

    @server.tool()
    def report_energy(
        quantity: float,
        unit: str,
        exergy_factor: float,
        reference: str = "",
        boundary: str = "",
        basis: str = "",
        label: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a quantity-plus-quality record from a supplied Exergy Factor."""

        return _report(
            quantity,
            unit,
            fx=exergy_factor,
            reference=reference,
            boundary=boundary,
            basis=basis,
            label=label,
        ).as_dict()

    @server.tool()
    def thermal_exergy(
        quantity: float,
        source_c: float,
        sink_c: Optional[float] = None,
        unit: str = "MWh_th",
    ) -> dict[str, Any]:
        """Calculate thermal Exergy Factor from source and reference temperatures."""

        return _thermal(quantity=quantity, unit=unit, source_c=source_c, sink_c=sink_c).as_dict()

    @server.tool()
    def cooling_exergy(
        quantity: float,
        cold_service_c: float,
        ambient_sink_c: float,
        unit: str = "MWh_cooling",
    ) -> dict[str, Any]:
        """Calculate cooling-service Exergy Factor below an ambient sink."""

        return _cooling(
            quantity=quantity,
            unit=unit,
            cold_service_c=cold_service_c,
            ambient_sink_c=ambient_sink_c,
        ).as_dict()

    @server.tool()
    def capabilities() -> dict[str, Any]:
        """List supported stream types and their calculation capabilities."""

        return _stream_capabilities()

    @server.tool()
    def registry() -> list[dict[str, Any]]:
        """List the typed carrier suffix registry."""

        return registry_as_dict()

    @server.tool()
    def tiers() -> list[dict[str, Any]]:
        """List Exergy Factor fidelity tiers."""

        return tiers_as_dict()

    @server.tool()
    def reference_examples(
        category: Optional[str] = None,
        text: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Find bundled reference examples by category or text."""

        return filter_reference_examples(category=category, text=text)

    @server.tool()
    def reference_example(reference_id: str) -> dict[str, Any]:
        """Return one bundled reference example by stable identifier."""

        return get_reference_example(reference_id)

    return server


def run_mcp_server(transport: str = "stdio") -> None:
    """Run the local MCP server over stdio or streamable HTTP."""

    create_mcp_server().run(transport=transport)


if __name__ == "__main__":  # pragma: no cover - exercised by an MCP host
    run_mcp_server()
