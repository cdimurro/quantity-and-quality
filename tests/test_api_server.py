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

    issued = client.post("/v1/api-keys/request", json={"email": "User@example.com"})
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
