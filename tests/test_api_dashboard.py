def test_dashboard_page_loads(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "AI ASO Platform Test UI" in response.text
    assert "/api/competitors/analyze" in response.text


def test_root_page_loads_dashboard(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Module 6: Reviews Intelligence" in response.text
    assert "Module 7: Market Opportunities" in response.text
    assert "Module 8: AI Idea Generator" in response.text
    assert "Module 9: Daily Ideas Report" in response.text
