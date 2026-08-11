from __future__ import annotations

from typing import Any, Optional

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - exercised only without API extra
    raise ImportError("API support requires: pip install quantity-quality[api]") from exc

from . import api as qq
from .api_keys import (
    api_keys_required,
    issue_api_key,
    return_keys_in_response,
    validate_api_key,
)
from .clean import clean_records, clean_summary
from .core import solar_exergy_rate
from .records import REPORT_SCHEMA_VERSION
from .reference import filter_reference_examples, get_reference_example
from .registry import registry_as_dict
from .scenario import SCENARIO_SCHEMA_VERSION, compare_scenario
from .schema import load_record_schema
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


class ValidateRequest(BaseModel):
    records: list[dict[str, Any]]
    mapping: Optional[dict[str, Any]] = None
    defaults: Optional[dict[str, Any]] = None
    assume_default_sink: bool = True
    default_sink_c: float = 20.0


class ScenarioRequest(BaseModel):
    scenario: dict[str, Any]


class ApiKeyRequest(BaseModel):
    email: str
    name: str = ""
    organization: str = ""
    intended_use: str = Field(default="", max_length=1000)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Exergy Factor API",
        version=REPORT_SCHEMA_VERSION,
        description="Deterministic HTTP API for the Quantity + Quality energy reporting library.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    @app.get("/health")
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

    @app.get("/v1/registry")
    def registry() -> dict:
        return {"schema_version": REPORT_SCHEMA_VERSION, "records": registry_as_dict()}

    @app.get("/v1/tiers")
    def tiers() -> dict:
        return {"schema_version": REPORT_SCHEMA_VERSION, "records": tiers_as_dict()}

    @app.get("/v1/reference-examples")
    def reference_examples(category: Optional[str] = None, text: Optional[str] = None) -> dict:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "records": filter_reference_examples(category=category, text=text),
        }

    @app.get("/v1/reference-examples/{reference_id}")
    def reference_example(reference_id: str) -> dict:
        return {"schema_version": REPORT_SCHEMA_VERSION, "record": _or_404(lambda: get_reference_example(reference_id))}

    @app.get("/v1/schema")
    def record_schema() -> dict:
        return load_record_schema()

    @app.post("/v1/report", dependencies=[Depends(_require_api_key)])
    def report(request: ReportRequest) -> dict:
        factor = request.exergy_factor if request.exergy_factor is not None else request.fx
        if factor is None:
            raise HTTPException(status_code=400, detail="fx or exergy_factor is required")
        record = qq.report(
            request.quantity,
            request.unit,
            fx=factor,
            reference=request.reference,
            boundary=request.boundary,
            basis=request.basis,
            label=request.label,
            tier=request.tier,
        )
        return _record_response(record.as_dict())

    @app.post("/v1/parse", dependencies=[Depends(_require_api_key)])
    def parse(request: ParseRequest) -> dict:
        record = qq.from_notation(
            request.notation,
            reference=request.reference,
            boundary=request.boundary,
            basis=request.basis,
            label=request.label,
            tier=request.tier,
        )
        return _record_response(record.as_dict())

    @app.post("/v1/calc/thermal", dependencies=[Depends(_require_api_key)])
    def calc_thermal(request: ThermalRequest) -> dict:
        record = qq.thermal(**request.model_dump())
        return _record_response(record.as_dict())

    @app.post("/v1/calc/cooling", dependencies=[Depends(_require_api_key)])
    def calc_cooling(request: CoolingRequest) -> dict:
        record = qq.cooling(**request.model_dump())
        return _record_response(record.as_dict())

    @app.post("/v1/calc/solar", dependencies=[Depends(_require_api_key)])
    def calc_solar(request: SolarRequest) -> dict:
        payload = request.model_dump()
        irradiance = payload.pop("irradiance_w_m2")
        area = payload.pop("area_m2")
        record = qq.solar(**payload).as_dict()
        if irradiance is not None and area is not None:
            record["solar_exergy_rate_w"] = solar_exergy_rate(irradiance, area, request.reference_c + 273.15)
        return _record_response(record)

    @app.post("/v1/calc/fuel", dependencies=[Depends(_require_api_key)])
    def calc_fuel(request: FuelRequest) -> dict:
        record = qq.fuel(
            request.quantity,
            request.fuel,
            basis=request.basis,
            unit=request.unit,
            boundary=request.boundary,
        )
        return _record_response(record.as_dict())

    @app.post("/v1/calc/fission", dependencies=[Depends(_require_api_key)])
    def calc_fission(request: FissionRequest) -> dict:
        record = qq.fission(**request.model_dump())
        return _record_response(record.as_dict())

    @app.post("/v1/compare", dependencies=[Depends(_require_api_key)])
    def compare(request: ScenarioRequest) -> dict:
        return _or_400(lambda: compare_scenario(request.scenario))

    @app.post("/v1/validate", dependencies=[Depends(_require_api_key)])
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

    @app.post("/v1/export/web-data", dependencies=[Depends(_require_api_key)])
    def export_web_data() -> dict:
        return build_web_data()

    @app.post("/v1/api-keys/request")
    def request_api_key(request: ApiKeyRequest) -> dict:
        result = _or_400(
            lambda: issue_api_key(
                request.email,
                name=request.name,
                organization=request.organization,
                intended_use=request.intended_use,
            )
        )
        return result.public_dict(include_key=return_keys_in_response())

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
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _or_404(fn):
    try:
        return fn()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _cors_origins() -> list[str]:
    raw = (
        __import__("os").environ.get(
            "QQ_API_CORS_ORIGINS",
            "https://exergyfactor.com,https://www.exergyfactor.com,http://localhost:8765,http://127.0.0.1:8765",
        )
        .strip()
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


app = create_app()
