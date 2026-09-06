from __future__ import annotations

from fastapi.testclient import TestClient

from ppc_simulator.api import app


client = TestClient(app)


def test_home_page_serves_browser_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Version 1 · Evaluate" in response.text
    assert "Version 2 · Compare" in response.text


def test_sample_fixtures_are_served_to_the_ui():
    policy = client.get("/fixtures/sample_policy_v1.json")
    claims = client.get("/fixtures/sample_claims.csv")
    assert policy.status_code == 200
    assert claims.status_code == 200
    assert "R-TF-90" in policy.text
    assert "C001" in claims.text
    json_claims = client.get("/fixtures/sample_claims.json")
    assert json_claims.status_code == 200
    assert json_claims.json()[0]["claim_id"] == "C001"
    assert client.get("/fixtures/not-a-file.json").status_code == 404
