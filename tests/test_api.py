from fastapi.testclient import TestClient


def test_execute_portfolio_endpoint(client: TestClient):
    cb = client.post("/auth/mock/callback", params={"user_id": "user1"}, json={})
    assert cb.status_code == 200
    assert cb.json()["connected"] is True

    resp = client.post(
        "/execute-portfolio",
        params={"user_id": "user1"},
        json={
            "instructions": [
                {"symbol": "INFY", "broker": "mock", "action": "BUY", "quantity": 10},
                {"symbol": "TCS", "broker": "mock", "action": "SELL", "quantity": 3},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert len(body["results"]) == 2


def test_login_url_for_redirect_broker(client: TestClient):
    resp = client.get("/auth/mock/login-url")
    assert resp.status_code == 200
    assert resp.json()["login_url"] is not None


def test_unsupported_broker_returns_404(client: TestClient):
    resp = client.get("/auth/not-a-broker/login-url")
    assert resp.status_code == 404
