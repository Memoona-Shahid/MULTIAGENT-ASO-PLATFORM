def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app_env" in body
    assert "agent_runtime" in body


def test_health_runtime_endpoint(client):
    response = client.get("/health/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["agent_runtime"] == "mock"
    assert body["healthy"] is True
