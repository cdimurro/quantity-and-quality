"""Production wrapper for the public Exergy Factor API deployment."""

from quantity_quality.api_server import app

_DISABLED_PUBLIC_BETA_PATHS = {
    "/v1/api-keys/request",
    "/v1/api-keys/revoke",
}

# This deployment is intentionally keyless. Leaving the package's optional
# SQLite-backed key-management routes in the generated OpenAPI document would
# invite users into an ephemeral workflow whose keys are not required. Keep the
# reusable package surface intact while removing those routes only from this
# public-beta process.
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
