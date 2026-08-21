from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Optional

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.openapi.docs import get_swagger_ui_html
    from pydantic import BaseModel, Field
    from starlette.responses import HTMLResponse
except ImportError as exc:  # pragma: no cover - exercised only without API extra
    raise ImportError("API support requires: pip install quantity-and-quality[api]") from exc

from . import api as qq
from .accounting import EnergyAccountingError, account_energy_chain
from .api_keys import (
    api_keys_required,
    issue_api_key,
    return_keys_in_response,
    revoke_api_key,
    validate_api_key,
)
from .clean import clean_records, clean_summary
from .core import solar_exergy_rate
from .records import REPORT_SCHEMA_VERSION
from .reference import filter_reference_examples, get_reference_example
from .registry import registry_as_dict
from .scenario import compare_scenario
from .schema import (
    load_energy_accounting_request_schema,
    load_record_schema,
    load_stream_request_schema,
)
from .streams import StreamCalculationError, calculate_stream, stream_capabilities
from .tiers import tiers_as_dict
from .web_export import build_web_data

API_VERSION = "v1"


class ReportRequest(BaseModel):
    quantity: float = 1.0
    unit: str = "MWh"
    fx: Optional[float] = None
    exergy_factor: Optional[float] = None
    reference: str = ""
    boundary: str = ""
    basis: str = ""
    label: Optional[str] = None
    tier: str = ""


class ParseRequest(BaseModel):
    notation: str
    reference: str = ""
    boundary: str = ""
    basis: str = ""
    label: Optional[str] = None
    tier: str = ""


class ThermalRequest(BaseModel):
    quantity: float = 1.0
    unit: str = "MWh_th"
    source_c: float
    sink_c: Optional[float] = None
    reference: str = ""
    boundary: str = "thermal stream"
    basis: str = ""
    label: Optional[str] = None


class CoolingRequest(BaseModel):
    quantity: float = 1.0
    unit: str = "MWh_cooling"
    cold_service_c: float
    ambient_sink_c: float
    boundary: str = "cooling service boundary"
    label: Optional[str] = None


class SolarRequest(BaseModel):
    quantity: float = 1.0
    unit: str = "MWh_solar"
    reference_c: float = 20.0
    reference: str = ""
    boundary: str = "solar resource boundary"
    basis: str = ""
    label: Optional[str] = None
    irradiance_w_m2: Optional[float] = None
    area_m2: Optional[float] = None


class FuelRequest(BaseModel):
    quantity: float = 1.0
    fuel: str = "natural gas"
    basis: str = "HHV"
    unit: Optional[str] = None
    boundary: str = "fuel inventory or fuel-flow meter"


class FissionRequest(BaseModel):
    quantity: float = 1.0
    fx: float
    unit: str = "MWh_fission"
    isotope: str = ""
    enrichment: str = ""
    burnup: str = ""
    boundary: str = "nuclear fuel inventory"
    label: Optional[str] = None


class StreamRequest(BaseModel):
    model_config = {"extra": "forbid"}

    stream_type: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    power: Optional[float] = None
    power_unit: Optional[str] = None
    duration_hours: Optional[float] = None
    output_unit: Optional[str] = None
    source_c: Optional[float] = None
    return_c: Optional[float] = None
    sink_c: Optional[float] = None
    cold_service_c: Optional[float] = None
    ambient_sink_c: Optional[float] = None
    mass: Optional[float] = None
    mass_unit: Optional[str] = None
    mass_flow_kg_s: Optional[float] = None
    volume: Optional[float] = None
    volume_unit: Optional[str] = None
    specific_heat_kj_kg_k: Optional[float] = None
    heating_value: Optional[float] = None
    heating_value_unit: Optional[str] = None
    chemical_exergy: Optional[float] = None
    energy_basis_value: Optional[float] = None
    irradiance_w_m2: Optional[float] = None
    area_m2: Optional[float] = None
    reference_c: Optional[float] = None
    fuel: Optional[str] = None
    basis: Optional[str] = None
    fx: Optional[float] = None
    exergy_factor: Optional[float] = None
    reference: Optional[str] = None
    boundary: Optional[str] = None
    operating_basis: Optional[str] = None
    label: Optional[str] = None
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    electrical_phase: Optional[str] = None
    power_factor: Optional[float] = None
    capacitance_f: Optional[float] = None
    reference_voltage_v: Optional[float] = None
    inductance_h: Optional[float] = None
    reference_current_a: Optional[float] = None
    charge_ah: Optional[float] = None
    average_voltage_v: Optional[float] = None
    field_model: Optional[str] = None
    volume_m3: Optional[float] = None
    electric_field_v_m: Optional[float] = None
    magnetic_flux_density_t: Optional[float] = None
    reference_electric_field_v_m: Optional[float] = None
    reference_magnetic_flux_density_t: Optional[float] = None
    relative_permittivity: Optional[float] = None
    relative_permeability: Optional[float] = None
    field_cells: Optional[list[dict[str, Any]]] = None
    power_flux_density_w_m2: Optional[float] = None
    normal_or_capture_factor: Optional[float] = None
    electric_field_rms_v_m: Optional[float] = None
    wave_impedance_ohm: Optional[float] = None
    mechanical_mode: Optional[str] = None
    torque_nm: Optional[float] = None
    rotational_speed_rpm: Optional[float] = None
    reference_speed_rpm: Optional[float] = None
    moment_of_inertia_kg_m2: Optional[float] = None
    velocity_m_s: Optional[float] = None
    reference_velocity_m_s: Optional[float] = None
    height_difference_m: Optional[float] = None
    gravity_m_s2: Optional[float] = None
    spring_constant_n_m: Optional[float] = None
    displacement_m: Optional[float] = None
    reference_displacement_m: Optional[float] = None
    pressure_difference: Optional[float] = None
    pressure_unit: Optional[str] = None
    volume_flow_m3_s: Optional[float] = None
    latent_heat_kj_kg: Optional[float] = None
    phase_change_c: Optional[float] = None
    fluid: Optional[str] = None
    temperature_c: Optional[float] = None
    temperature_k: Optional[float] = None
    pressure_pa: Optional[float] = None
    pressure: Optional[float] = None
    reference_temperature_c: Optional[float] = None
    reference_temperature_k: Optional[float] = None
    reference_pressure_pa: Optional[float] = None
    vapor_quality: Optional[float] = None
    inlet_temperature_c: Optional[float] = None
    inlet_pressure_pa: Optional[float] = None
    inlet_vapor_quality: Optional[float] = None
    outlet_temperature_c: Optional[float] = None
    outlet_pressure_pa: Optional[float] = None
    outlet_vapor_quality: Optional[float] = None
    reported_energy_basis: Optional[str] = None
    enthalpy_kj_kg: Optional[float] = None
    entropy_kj_kg_k: Optional[float] = None
    reference_enthalpy_kj_kg: Optional[float] = None
    reference_entropy_kj_kg_k: Optional[float] = None
    cp_j_kg_k: Optional[float] = None
    gas_constant_j_kg_k: Optional[float] = None
    property_model: Optional[str] = None
    dry_air_mass_kg: Optional[float] = None
    humidity_ratio: Optional[float] = None
    reference_humidity_ratio: Optional[float] = None
    relative_humidity: Optional[float] = None
    reference_relative_humidity: Optional[float] = None
    dry_air_cp_j_kg_k: Optional[float] = None
    water_vapor_cp_j_kg_k: Optional[float] = None
    dry_air_gas_constant_j_kg_k: Optional[float] = None
    source_temperature_c: Optional[float] = None
    source_temperature_k: Optional[float] = None
    radiation_model: Optional[str] = None
    radiation_entropy_j_k: Optional[float] = None
    components: Optional[list[dict[str, Any]]] = None
    moisture_fraction: Optional[float] = None
    ash_fraction: Optional[float] = None
    heating_value_basis: Optional[str] = None
    feedstock_class: Optional[str] = None
    quality_basis_unit: Optional[str] = None
    property_source: Optional[str] = None
    composition_source: Optional[str] = None
    amount_mol: Optional[float] = None
    mole_fractions: Optional[list[float]] = None
    mass_defect_kg: Optional[float] = None
    isotope_mass_kg: Optional[float] = None
    atomic_mass_g_mol: Optional[float] = None
    energy_per_fission_mev: Optional[float] = None
    fissioned_fraction: Optional[float] = None
    accessible_fraction: Optional[float] = None
    nuclear_mode: Optional[str] = None
    reaction_preset: Optional[str] = None
    q_value_mev: Optional[float] = None
    reaction_count: Optional[float] = None
    reaction_amount_mol: Optional[float] = None
    reactant_atomic_masses_u: Optional[list[float]] = None
    product_atomic_masses_u: Optional[list[float]] = None
    reactant_1_number_density_m3: Optional[float] = None
    reactant_2_number_density_m3: Optional[float] = None
    reactivity_m3_s: Optional[float] = None
    duration_seconds: Optional[float] = None
    identical_reactants: Optional[bool] = None
    reaction_channels: Optional[list[dict[str, Any]]] = None
    nuclear_channel: Optional[str] = None
    reactivity_source: Optional[str] = None
    mass_convention: Optional[str] = None
    plasma_model: Optional[str] = None
    plasma_species: Optional[list[dict[str, Any]]] = None
    loss_model: Optional[str] = None
    friction_force_n: Optional[float] = None
    distance_m: Optional[float] = None
    coefficient_of_rolling_resistance: Optional[float] = None
    normal_force_n: Optional[float] = None
    fluid_density_kg_m3: Optional[float] = None
    drag_coefficient: Optional[float] = None
    frontal_area_m2: Optional[float] = None
    relative_speed_m_s: Optional[float] = None
    dissipation_c: Optional[float] = None


class AccountingStageRequest(BaseModel):
    model_config = {"extra": "forbid"}

    quantity: float
    unit: str
    fx: Optional[float] = None
    exergy_factor: Optional[float] = None
    label: Optional[str] = None
    reference: Optional[str] = None
    boundary: Optional[str] = None
    basis: Optional[str] = None
    method: Optional[str] = None
    method_id: Optional[str] = None
    tier: Optional[str] = None
    source_c: Optional[float] = None
    return_c: Optional[float] = None
    sink_c: Optional[float] = None
    cold_service_c: Optional[float] = None
    ambient_sink_c: Optional[float] = None
    fuel: Optional[str] = None
    energy_basis: Optional[str] = None
    reference_id: Optional[str] = None
    stream_type: Optional[str] = None
    quantity_method_id: Optional[str] = None
    calculation_inputs: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    assumptions: Optional[list[str]] = None
    warnings: Optional[list[str]] = None
    accounting_method: Optional[str] = None
    source_dataset: Optional[str] = None
    source_variable: Optional[str] = None


class AppliedExergyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    quantity: float
    unit: str
    basis: Optional[str] = None
    boundary: Optional[str] = None


class EnergyServiceRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    quantity: float
    unit: str
    category: Optional[str] = None
    boundary: Optional[str] = None
    notes: Optional[str] = None


class AccountingRequest(BaseModel):
    model_config = {"extra": "forbid"}

    primary: Optional[AccountingStageRequest] = None
    secondary: Optional[AccountingStageRequest] = None
    final: Optional[AccountingStageRequest] = None
    useful: Optional[AccountingStageRequest] = None
    applied_exergy: Optional[AppliedExergyRequest] = None
    end_use_exergy_efficiency: Optional[float] = None
    service: Optional[EnergyServiceRequest] = None
    output_exergy_unit: Optional[str] = None
    label: Optional[str] = None
    boundary: Optional[str] = None


class ValidateRequest(BaseModel):
    records: list[dict[str, Any]]
    mapping: Optional[dict[str, Any]] = None
    defaults: Optional[dict[str, Any]] = None
    assume_default_sink: bool = True
    default_sink_c: float = 20.0


class ScenarioRequest(BaseModel):
    scenario: dict[str, Any]


class ApiKeyRequest(BaseModel):
    email: str = Field(max_length=320)
    name: str = Field(default="", max_length=200)
    organization: str = Field(default="", max_length=200)
    intended_use: str = Field(default="", max_length=1000)
    accept_terms: bool


def create_app() -> FastAPI:
    app = FastAPI(
        title="Exergy Factor API",
        version=REPORT_SCHEMA_VERSION,
        docs_url=None,
        redoc_url=None,
        description=(
            "Calculate and report energy quantity, Exergy Factor, and accessible exergy "
            "for individual streams, with optional end-use accounting through Applied Exergy."
        ),
        terms_of_service="https://exergyfactor.com/terms.html",
        contact={
            "name": "Exergy Factor",
            "url": "https://exergyfactor.com",
            "email": "chrisdimurro@gmail.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://github.com/cdimurro/quantity-and-quality/blob/main/LICENSE",
        },
    )

    @app.get("/docs", include_in_schema=False)
    def docs() -> HTMLResponse:
        """Serve the interactive API docs inside the Exergy Factor site shell."""

        page = get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title="Exergy Factor API · Docs",
            swagger_ui_parameters={
                "deepLinking": True,
                "displayRequestDuration": True,
                "docExpansion": "none",
                "filter": True,
                "defaultModelsExpandDepth": -1,
                "showExtensions": False,
                "showCommonExtensions": False,
            },
        )
        html = page.body.decode("utf-8")
        html = html.replace(
            "</head>",
            """
            <style>
              :root {
                color-scheme: light;
                --docs-ink: #17201d;
                --docs-muted: #586761;
                --docs-line: #cbd8d3;
                --docs-paper: #f8faf7;
                --docs-panel: #ffffff;
                --docs-teal: #0d766f;
                --docs-teal-deep: #0a4f4a;
              }
              * { box-sizing: border-box; }
              body {
                margin: 0;
                background: var(--docs-paper);
                color: var(--docs-ink);
                font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                  BlinkMacSystemFont, "Segoe UI", sans-serif;
              }
              .docs-header {
                border-bottom: 1px solid rgba(23, 32, 29, 0.12);
                background: rgba(248, 250, 247, 0.96);
              }
              .docs-header-inner {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
                max-width: 1220px;
                margin: 0 auto;
                padding: 18px 28px;
              }
              .docs-brand {
                display: inline-flex;
                align-items: center;
                gap: 12px;
                color: var(--docs-ink);
                font-size: 1.1rem;
                font-weight: 800;
                text-decoration: none;
              }
              .docs-mark {
                width: 28px;
                height: 28px;
                border: 2px solid var(--docs-teal);
                border-radius: 50%;
                background:
                  linear-gradient(90deg, transparent 46%, var(--docs-teal) 47%,
                    var(--docs-teal) 53%, transparent 54%),
                  linear-gradient(0deg, transparent 46%, #b66d12 47%, #b66d12 53%,
                    transparent 54%);
              }
              .docs-header a:last-child {
                color: var(--docs-teal-deep);
                font-weight: 700;
                text-decoration: none;
              }
              .docs-shell {
                max-width: 1220px;
                margin: 0 auto;
                padding: 36px 28px 72px;
              }
              .docs-intro {
                display: flex;
                align-items: end;
                justify-content: space-between;
                gap: 24px;
                margin-bottom: 24px;
              }
              .docs-intro h1 {
                margin: 0 0 8px;
                color: var(--docs-ink);
                font-size: clamp(2rem, 4vw, 3.2rem);
                line-height: 1.05;
              }
              .docs-intro p { margin: 0; color: var(--docs-muted); }
              .docs-base-url {
                padding: 10px 12px;
                border: 1px solid var(--docs-line);
                border-radius: 8px;
                background: var(--docs-panel);
                color: var(--docs-teal-deep);
                font: 700 0.86rem ui-monospace, SFMono-Regular, Menlo, Consolas,
                  monospace;
                white-space: nowrap;
              }
              #swagger-ui {
                padding: 24px;
                border: 1px solid var(--docs-line);
                border-radius: 12px;
                background: var(--docs-panel);
                box-shadow: 0 20px 50px rgba(23, 32, 29, 0.08);
              }
              .swagger-ui { color: var(--docs-ink); font-family: inherit; }
              .swagger-ui .topbar { display: none; }
              .swagger-ui .info { margin: 0 0 18px; }
              .swagger-ui .info .title { display: none; }
              .swagger-ui .info p, .swagger-ui .info li { color: var(--docs-muted); }
              .swagger-ui .opblock-tag {
                margin: 18px 0 8px;
                padding: 10px 0;
                border-bottom: 1px solid var(--docs-line);
                color: var(--docs-teal-deep);
                font-size: 1.1rem;
              }
              .swagger-ui .opblock {
                border-color: var(--docs-line);
                border-radius: 8px;
                box-shadow: none;
              }
              .swagger-ui .opblock .opblock-summary { border-color: var(--docs-line); }
              .swagger-ui .opblock.opblock-get { background: rgba(49, 95, 151, 0.05); }
              .swagger-ui .opblock.opblock-post { background: rgba(13, 118, 111, 0.06); }
              .swagger-ui .opblock.opblock-get .opblock-summary-method { background: #315f97; }
              .swagger-ui .opblock.opblock-post .opblock-summary-method { background: var(--docs-teal); }
              .swagger-ui .btn.execute {
                border-color: var(--docs-teal-deep);
                background: var(--docs-teal-deep);
                color: #fff;
              }
              .swagger-ui input[type=text], .swagger-ui textarea, .swagger-ui select {
                border-color: var(--docs-line);
                border-radius: 6px;
              }
              @media (max-width: 720px) {
                .docs-header-inner, .docs-shell { padding-left: 16px; padding-right: 16px; }
                .docs-intro { align-items: start; flex-direction: column; }
                .docs-base-url { white-space: normal; overflow-wrap: anywhere; }
                #swagger-ui { padding: 12px; }
              }
            </style>
            </head>""",
        )
        html = html.replace(
            "<body>",
            """
            <body>
              <header class="docs-header">
                <div class="docs-header-inner">
                  <a class="docs-brand" href="https://exergyfactor.com">
                    <span class="docs-mark" aria-hidden="true"></span>
                    <span>Exergy Factor API</span>
                  </a>
                  <a href="https://exergyfactor.com">Back to calculator</a>
                </div>
              </header>
              <main class="docs-shell">
                <div class="docs-intro">
                  <div>
                    <h1>API documentation</h1>
                    <p>Explore the public, keyless quantity and quality calculation contract.</p>
                  </div>
                  <code class="docs-base-url">https://api.exergyfactor.com/v1</code>
                </div>
            """,
        )
        html = html.replace("</body>", "</main></body>")
        return HTMLResponse(content=html)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Last-Event-ID",
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
            "X-API-Key",
        ],
        expose_headers=["Mcp-Session-Id"],
    )

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        return {
            "ok": True,
            "service": "exergy-factor-api",
            "api_version": API_VERSION,
            "schema_version": REPORT_SCHEMA_VERSION,
        }

    @app.get("/v1/health")
    def v1_health() -> dict:
        return health()

    @app.get("/v1/registry", include_in_schema=False)
    def registry() -> dict:
        return {"schema_version": REPORT_SCHEMA_VERSION, "records": registry_as_dict()}

    @app.get("/v1/tiers", include_in_schema=False)
    def tiers() -> dict:
        return {"schema_version": REPORT_SCHEMA_VERSION, "records": tiers_as_dict()}

    @app.get("/v1/reference-examples", include_in_schema=False)
    def reference_examples(category: Optional[str] = None, text: Optional[str] = None) -> dict:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "records": filter_reference_examples(category=category, text=text),
        }

    @app.get("/v1/reference-examples/{reference_id}", include_in_schema=False)
    def reference_example(reference_id: str) -> dict:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "record": _or_404(lambda: get_reference_example(reference_id)),
        }

    @app.get("/v1/schema", include_in_schema=False)
    def record_schema() -> dict:
        return load_record_schema()

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return stream_capabilities()

    @app.get("/v1/calculate/schema")
    def calculation_schema() -> dict:
        return load_stream_request_schema()

    @app.get("/v1/accounting/schema")
    def accounting_schema() -> dict:
        return load_energy_accounting_request_schema()

    @app.post("/v1/calculate", dependencies=[Depends(_require_api_key)])
    def calculate(request: StreamRequest) -> dict:
        record = _or_400(lambda: calculate_stream(request.model_dump(exclude_none=True)))
        return _record_response(record.as_dict())

    @app.post("/v1/account", dependencies=[Depends(_require_api_key)])
    def account(request: AccountingRequest) -> dict:
        result = _or_400(
            lambda: account_energy_chain(request.model_dump(exclude_none=True)).as_dict()
        )
        return result

    @app.post("/v1/report", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def report(request: ReportRequest) -> dict:
        factor = request.exergy_factor if request.exergy_factor is not None else request.fx
        if factor is None:
            raise HTTPException(status_code=400, detail="fx or exergy_factor is required")
        record = _or_400(
            lambda: qq.report(
                request.quantity,
                request.unit,
                fx=factor,
                reference=request.reference,
                boundary=request.boundary,
                basis=request.basis,
                label=request.label,
                tier=request.tier,
            )
        )
        return _record_response(record.as_dict())

    @app.post("/v1/parse", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def parse(request: ParseRequest) -> dict:
        record = _or_400(
            lambda: qq.from_notation(
                request.notation,
                reference=request.reference,
                boundary=request.boundary,
                basis=request.basis,
                label=request.label,
                tier=request.tier,
            )
        )
        return _record_response(record.as_dict())

    @app.post("/v1/calc/thermal", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def calc_thermal(request: ThermalRequest) -> dict:
        record = _or_400(lambda: qq.thermal(**request.model_dump()))
        return _record_response(record.as_dict())

    @app.post("/v1/calc/cooling", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def calc_cooling(request: CoolingRequest) -> dict:
        record = _or_400(lambda: qq.cooling(**request.model_dump()))
        return _record_response(record.as_dict())

    @app.post("/v1/calc/solar", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def calc_solar(request: SolarRequest) -> dict:
        payload = request.model_dump()
        irradiance = payload.pop("irradiance_w_m2")
        area = payload.pop("area_m2")
        record = _or_400(lambda: qq.solar(**payload).as_dict())
        if irradiance is not None and area is not None:
            record["solar_exergy_rate_w"] = _or_400(
                lambda: solar_exergy_rate(irradiance, area, request.reference_c + 273.15)
            )
        return _record_response(record)

    @app.post("/v1/calc/fuel", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def calc_fuel(request: FuelRequest) -> dict:
        record = _or_400(
            lambda: qq.fuel(
                request.quantity,
                request.fuel,
                basis=request.basis,
                unit=request.unit,
                boundary=request.boundary,
            )
        )
        return _record_response(record.as_dict())

    @app.post("/v1/calc/fission", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def calc_fission(request: FissionRequest) -> dict:
        record = _or_400(lambda: qq.fission(**request.model_dump()))
        return _record_response(record.as_dict())

    @app.post("/v1/compare", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def compare(request: ScenarioRequest) -> dict:
        return _or_400(lambda: compare_scenario(request.scenario))

    @app.post("/v1/validate", include_in_schema=False, dependencies=[Depends(_require_api_key)])
    def validate(request: ValidateRequest) -> dict:
        cleaned = _or_400(
            lambda: clean_records(
                request.records,
                mapping=request.mapping,
                defaults=request.defaults,
                assume_default_sink=request.assume_default_sink,
                default_sink_c=request.default_sink_c,
            )
        )
        summary = clean_summary(cleaned)
        summary["schema_version"] = REPORT_SCHEMA_VERSION
        summary["records"] = cleaned
        return summary

    @app.post(
        "/v1/export/web-data", include_in_schema=False, dependencies=[Depends(_require_api_key)]
    )
    def export_web_data() -> dict:
        return build_web_data()

    @app.post("/v1/api-keys/request", include_in_schema=False)
    def request_api_key(request: ApiKeyRequest) -> dict:
        if not request.accept_terms:
            raise HTTPException(
                status_code=400,
                detail="accept_terms must be true to request an API key",
            )
        result = _or_400(
            lambda: issue_api_key(
                request.email,
                name=request.name,
                organization=request.organization,
                intended_use=request.intended_use,
                terms_version="2026-08-18",
            )
        )
        return result.public_dict(include_key=return_keys_in_response())

    @app.post("/v1/api-keys/revoke", include_in_schema=False)
    def revoke_key(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
        authorization: Optional[str] = Header(default=None),
    ) -> dict:
        candidate = x_api_key or _bearer_token(authorization or "")
        if not candidate or not revoke_api_key(candidate):
            raise HTTPException(status_code=401, detail="valid API key required")
        return {"ok": True, "detail": "API key revoked"}

    if _truthy(os.environ.get("QQ_MCP_HTTP_ENABLED", "0")):
        try:
            from .mcp_server import create_mcp_server
        except RuntimeError as exc:
            raise RuntimeError("QQ_MCP_HTTP_ENABLED=1 requires quantity-and-quality[mcp]") from exc
        mcp_app = create_mcp_server(
            streamable_http_path="/",
            stateless_http=True,
            host="0.0.0.0",
        ).streamable_http_app()
        app.mount("/mcp", mcp_app)
        previous_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(application):
            async with previous_lifespan(application):
                async with mcp_app.router.lifespan_context(mcp_app):
                    yield

        app.router.lifespan_context = combined_lifespan

    return app


def _record_response(record: dict) -> dict:
    return {"schema_version": REPORT_SCHEMA_VERSION, "record": record}


def _require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> None:
    if not api_keys_required():
        return
    candidate = x_api_key or _bearer_token(authorization or "")
    if not candidate or not validate_api_key(candidate):
        raise HTTPException(status_code=401, detail="valid API key required")


def _bearer_token(header_value: str) -> str:
    prefix = "bearer "
    if header_value.lower().startswith(prefix):
        return header_value[len(prefix) :].strip()
    return ""


def _or_400(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except StreamCalculationError as exc:
        raise HTTPException(status_code=400, detail=exc.as_dict()) from exc
    except EnergyAccountingError as exc:
        raise HTTPException(status_code=400, detail=exc.as_dict()) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _or_404(fn):
    try:
        return fn()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "QQ_API_CORS_ORIGINS",
        "https://exergyfactor.com,https://www.exergyfactor.com,http://localhost:8765,http://127.0.0.1:8765",
    )
    raw = raw.strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


app = create_app()
