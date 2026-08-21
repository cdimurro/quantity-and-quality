"""Production wrapper for the public Exergy Factor API deployment."""

from quantity_quality.api_server import app

_DISABLED_PUBLIC_BETA_PATHS = {
    "/health",
    "/v1/registry",
    "/v1/tiers",
    "/v1/reference-examples",
    "/v1/reference-examples/{reference_id}",
    "/v1/schema",
    "/v1/report",
    "/v1/parse",
    "/v1/calc/thermal",
    "/v1/calc/cooling",
    "/v1/calc/solar",
    "/v1/calc/fuel",
    "/v1/calc/fission",
    "/v1/compare",
    "/v1/validate",
    "/v1/export/web-data",
    "/v1/api-keys/request",
    "/v1/api-keys/revoke",
}

# This deployment is intentionally keyless and exposes one small, stable
# contract. Keep the reusable package surface intact while removing legacy
# compatibility routes and optional key-management routes from this public
# process. The package's local API can still expose those routes for migrations.
app.router.routes = [
    route
    for route in app.router.routes
    if getattr(route, "path", None) not in _DISABLED_PUBLIC_BETA_PATHS
]


@app.get("/", include_in_schema=False)
def service_root() -> dict[str, str]:
    return {
        "service": "exergy-factor-api",
        "status": "ok",
        "documentation": "/docs",
        "health": "/v1/health",
        "api_base": "/v1",
        "authentication": "none (public beta)",
        "source": "https://github.com/cdimurro/quantity-and-quality",
    }
