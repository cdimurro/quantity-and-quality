import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from quantity_quality.api_server import create_app


def test_api_public_metadata_and_calculation_without_key(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    client = TestClient(create_app())

    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    tiers = client.get("/v1/tiers")
    assert tiers.status_code == 200
    assert tiers.json()["records"][0]["tier"] == "F0"

    registry = client.get("/v1/registry")
    assert registry.status_code == 200
    assert any(entry["suffix"] == "_th" for entry in registry.json()["records"])

    response = client.post(
        "/v1/calc/thermal",
        json={"quantity": 4, "unit": "MWh_th", "source_c": 80, "sink_c": 20},
    )
    assert response.status_code == 200
    record = response.json()["record"]
    assert record["notation"] == "4 MWh_th, fx = 0.170"
    assert record["accessible_exergy_unit"] == "MWh_ex"
    assert record["tier"] == "F2"

    capabilities = client.get("/v1/capabilities")
    assert capabilities.status_code == 200
    assert "heat" in capabilities.json()["stream_types"]
    calculation_schema = client.get("/v1/calculate/schema")
    assert calculation_schema.status_code == 200
    assert calculation_schema.json()["title"] == "Quantity + Quality Stream Calculation Request"

    calculated = client.post(
        "/v1/calculate",
        json={
            "stream_type": "heat",
            "mass": 1000,
            "specific_heat_kj_kg_k": 4.186,
            "source_c": 80,
            "return_c": 50,
            "sink_c": 20,
        },
    )
    assert calculated.status_code == 200
    calculated_record = calculated.json()["record"]
    assert calculated_record["method_id"] == "thermal.sensible.integrated.v1"
    assert calculated_record["quantity_method_id"] == "quantity.sensible_heat.mass_cp_delta_t.v1"
    assert calculated_record["distinguishability"]["basis"] == "sensible_temperature_path"

    accounting_schema = client.get("/v1/accounting/schema")
    assert accounting_schema.status_code == 200
    assert "Applied Exergy" in accounting_schema.json()["title"]

    accounted = client.post(
        "/v1/account",
        json={
            "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
            "useful": {
                "quantity": 3,
                "unit": "MWh_th",
                "fx": 0.064,
                "source_c": 40,
                "sink_c": 20,
            },
            "service": {
                "name": "Warm home",
                "quantity": 720,
                "unit": "occupied_comfort_hour",
            },
        },
    )
    assert accounted.status_code == 200
    assert accounted.json()["applied_exergy"] == pytest.approx(0.192)
    assert accounted.json()["service"]["energy_unit"] is False

    statistical = client.post(
        "/v1/account",
        json={
            "primary": {
                "quantity": 250,
                "unit": "TWh",
                "accounting_method": "substitution",
                "source_dataset": "OWID historical energy data",
            },
            "secondary": {"quantity": 100, "unit": "TWh_e", "fx": 1},
        },
    )
    assert statistical.status_code == 200
    assert statistical.json()["stages"]["primary"]["thermodynamic_conversion_allowed"] is False
    assert "exergy_mwh" not in statistical.json()["stages"]["primary"]


def test_branded_interactive_docs_use_the_public_api_shell(monkeypatch):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    with TestClient(create_app()) as client:
        response = client.get("/docs")
        openapi = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'class="docs-header"' in response.text
    assert "https://api.exergyfactor.com/v1" in response.text
    assert "swagger-ui-bundle.js" in response.text
    assert openapi.status_code == 200
    assert set(openapi.json()["paths"]) == {
        "/v1/health",
        "/v1/capabilities",
        "/v1/calculate/schema",
        "/v1/calculate",
        "/v1/accounting/schema",
        "/v1/account",
    }


def test_extended_physical_streams_use_the_shared_api_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    client = TestClient(create_app())

    mechanical = client.post(
        "/v1/calculate",
        json={
            "stream_type": "mechanical",
            "mechanical_mode": "shaft",
            "torque_nm": 500,
            "rotational_speed_rpm": 1800,
            "duration_hours": 2,
        },
    )
    assert mechanical.status_code == 200
    assert mechanical.json()["record"]["unit"] == "kWh_m"
    assert mechanical.json()["record"]["fx"] == 1

    biomass = client.post(
        "/v1/calculate",
        json={
            "stream_type": "biomass",
            "mass": 1000,
            "heating_value": 18,
            "chemical_exergy": 19,
            "energy_basis_value": 18,
            "basis": "LHV",
        },
    )
    assert biomass.status_code == 200
    assert biomass.json()["record"]["fuel"] == "biomass"

    drag = client.post(
        "/v1/calculate",
        json={
            "stream_type": "dissipation",
            "fluid_density_kg_m3": 1.225,
            "drag_coefficient": 0.3,
            "frontal_area_m2": 2.2,
            "relative_speed_m_s": 25,
            "distance_m": 1000,
        },
    )
    assert drag.status_code == 200
    assert drag.json()["record"]["metadata"]["exergy_destroyed"] > 0

    field = client.post(
        "/v1/calculate",
        json={
            "stream_type": "electromagnetic_field",
            "electric_field_rms_v_m": 100,
            "area_m2": 2,
            "duration_hours": 1,
        },
    )
    assert field.status_code == 200
    assert field.json()["record"]["unit"] == "kWh_em"
    assert field.json()["record"]["fx"] == 1

    fusion = client.post(
        "/v1/calculate",
        json={
            "stream_type": "thermonuclear",
            "reaction_preset": "dt_fusion",
            "reaction_count": 1e20,
            "nuclear_channel": "neutron",
        },
    )
    assert fusion.status_code == 200
    assert fusion.json()["record"]["unit"] == "MWh_neutron"
    assert fusion.json()["record"]["metadata"]["selected_channel"] == "neutron"

    plasma = client.post(
        "/v1/calculate",
        json={
            "stream_type": "plasma",
            "volume_m3": 1,
            "plasma_species": [
                {
                    "name": "electron",
                    "number_density_m3": 1e20,
                    "temperature_ev": 1000,
                }
            ],
        },
    )
    assert plasma.status_code == 200
    assert plasma.json()["record"]["unit"] == "kWh_plasma"
    assert plasma.json()["record"]["metadata"]["species"][0]["particle_mass_kg"] > 0


def test_api_key_request_and_enforced_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "1")
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    monkeypatch.setenv("QQ_API_EMAIL_MODE", "console")
    monkeypatch.setenv("QQ_API_KEY_RETURN_IN_RESPONSE", "1")
    client = TestClient(create_app())

    unauthenticated = client.post(
        "/v1/calc/fuel",
        json={"quantity": 1, "fuel": "natural gas", "basis": "HHV"},
    )
    assert unauthenticated.status_code == 401

    issued = client.post(
        "/v1/api-keys/request",
        json={"email": "User@example.com", "accept_terms": True},
    )
    assert issued.status_code == 200
    payload = issued.json()
    assert payload["email"] == "user@example.com"
    assert payload["api_key"].startswith("qq_live_")

    authenticated = client.post(
        "/v1/calc/fuel",
        headers={"X-API-Key": payload["api_key"]},
        json={"quantity": 1, "fuel": "natural gas", "basis": "HHV"},
    )
    assert authenticated.status_code == 200
    record = authenticated.json()["record"]
    assert record["unit"] == "MWh_HHV_NG"
    assert record["exergy_factor"] == pytest.approx(0.93)

    revoked = client.post("/v1/api-keys/revoke", headers={"X-API-Key": payload["api_key"]})
    assert revoked.status_code == 200
    rejected = client.post(
        "/v1/calc/fuel",
        headers={"X-API-Key": payload["api_key"]},
        json={"quantity": 1, "fuel": "natural gas", "basis": "HHV"},
    )
    assert rejected.status_code == 401


def test_stateless_api_keys_survive_ephemeral_restart(monkeypatch, tmp_path):
    db_path = tmp_path / "keys.sqlite3"
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "1")
    monkeypatch.setenv("QQ_API_KEY_DB", str(db_path))
    monkeypatch.setenv("QQ_API_KEY_PEPPER", "test-stateless-secret")
    monkeypatch.setenv("QQ_API_KEY_STATELESS", "1")
    monkeypatch.setenv("QQ_API_KEY_RETURN_IN_RESPONSE", "1")
    monkeypatch.setenv("QQ_API_EMAIL_MODE", "disabled")
    client = TestClient(create_app())

    issued = client.post(
        "/v1/api-keys/request",
        json={"email": "stateless@example.com", "accept_terms": True},
    )
    assert issued.status_code == 200
    api_key = issued.json()["api_key"]
    assert "." in api_key

    # A free host may discard its local filesystem while retaining its secret
    # environment. Signature validation must keep the issued key usable.
    db_path.unlink()
    restarted = TestClient(create_app())
    authenticated = restarted.post(
        "/v1/calc/fuel",
        headers={"X-API-Key": api_key},
        json={"quantity": 1, "fuel": "natural gas", "basis": "HHV"},
    )
    assert authenticated.status_code == 200
    assert (
        restarted.post(
            "/v1/calc/fuel",
            headers={"X-API-Key": f"{api_key}x"},
            json={"quantity": 1, "fuel": "natural gas", "basis": "HHV"},
        ).status_code
        == 401
    )


def test_optional_keyless_mcp_http_mount(monkeypatch):
    monkeypatch.setenv("QQ_MCP_HTTP_ENABLED", "1")
    with TestClient(create_app()) as client:
        assert any(getattr(route, "path", "") == "/mcp" for route in client.app.routes)

        initialize = client.post(
            "/mcp/",
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "site-contract", "version": "1"},
                },
            },
        )
        assert initialize.status_code == 200
        assert initialize.headers["content-type"].startswith("text/event-stream")
        assert "Quantity and Quality" in initialize.text

        preflight = client.options(
            "/mcp/",
            headers={
                "Origin": "https://exergyfactor.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "accept,content-type,mcp-protocol-version",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "https://exergyfactor.com"
        assert "MCP-Protocol-Version" in preflight.headers["access-control-allow-headers"]


def test_api_validate_and_compare(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    client = TestClient(create_app())

    validation = client.post(
        "/v1/validate",
        json={"records": [{"quantity": 1, "unit": "MWh_th", "source_c": 80, "sink_c": 20}]},
    )
    assert validation.status_code == 200
    assert validation.json()["records"][0]["tier"] == "F2"

    comparison = client.post(
        "/v1/compare",
        json={
            "scenario": {
                "name": "api smoke",
                "options": [
                    {"id": "grid", "type": "electricity", "quantity": 1, "unit": "MWh"},
                    {"id": "heat", "quantity": 1, "unit": "MWh_th", "source_c": 80, "sink_c": 20},
                ],
            }
        },
    )
    assert comparison.status_code == 200
    assert comparison.json()["rows"][0]["id"] == "grid"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/report", {"quantity": -1, "unit": "MWh", "fx": 0.5}),
        ("/v1/parse", {"notation": "not notation"}),
        (
            "/v1/calc/thermal",
            {"quantity": 1, "unit": "MWh_th", "source_c": 20, "sink_c": 80},
        ),
        (
            "/v1/calc/cooling",
            {
                "quantity": 1,
                "unit": "MWh_cooling",
                "cold_service_c": 30,
                "ambient_sink_c": 20,
            },
        ),
        ("/v1/calc/fuel", {"quantity": 1, "fuel": "unobtainium", "basis": "HHV"}),
        (
            "/v1/calc/solar",
            {"quantity": 1, "unit": "MWh_solar", "reference_c": -300},
        ),
    ],
)
def test_invalid_domain_inputs_are_client_errors(monkeypatch, path, payload):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(path, json=payload)
    assert 400 <= response.status_code < 500
    assert "detail" in response.json()


def test_unified_calculation_api_returns_machine_readable_errors(monkeypatch):
    monkeypatch.setenv("QQ_API_REQUIRE_KEY", "0")
    client = TestClient(create_app())
    response = client.post(
        "/v1/calculate",
        json={"stream_type": "heat", "quantity": 1, "unit": "MWh"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "missing_input",
        "message": "source_c is required",
        "field": "source_c",
    }

    accounting = client.post(
        "/v1/account",
        json={
            "final": {"quantity": 1, "unit": "MWh_e", "fx": 1},
            "applied_exergy": {"quantity": 2, "unit": "MWh_ex"},
        },
    )
    assert accounting.status_code == 400
    assert accounting.json()["detail"]["code"] == "accounting_inconsistency"


def test_api_key_request_requires_terms_acceptance(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    client = TestClient(create_app())
    response = client.post(
        "/v1/api-keys/request",
        json={"email": "user@example.com", "accept_terms": False},
    )
    assert response.status_code == 400


def test_api_key_requests_are_rate_limited_per_email(monkeypatch, tmp_path):
    monkeypatch.setenv("QQ_API_KEY_DB", str(tmp_path / "keys.sqlite3"))
    monkeypatch.setenv("QQ_API_EMAIL_MODE", "disabled")
    monkeypatch.setenv("QQ_API_KEY_REQUESTS_PER_DAY", "2")
    client = TestClient(create_app())
    payload = {"email": "limited@example.com", "accept_terms": True}
    assert client.post("/v1/api-keys/request", json=payload).status_code == 200
    assert client.post("/v1/api-keys/request", json=payload).status_code == 200
    response = client.post("/v1/api-keys/request", json=payload)
    assert response.status_code == 400
    assert "limit" in response.json()["detail"]
