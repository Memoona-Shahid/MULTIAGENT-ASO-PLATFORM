def test_dashboard_page_loads(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "ASO Intelligence" in response.text
    assert "Generate Daily Ideas Report" in response.text
    assert "/api/dashboard/overview" in response.text


def test_root_page_loads_dashboard(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Product Ideas" in response.text
    assert "Market opportunities" in response.text or "Opportunities" in response.text
    assert "Daily & weekly reports" in response.text or "Reports" in response.text


def test_dashboard_overview_endpoint(client):
    response = client.get("/api/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "ideas" in data
    assert "reports" in data
    assert "trends" in data
    assert "opportunities" in data
