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
                {"symbol": "TCS", "broker": "mock", "action": "BUY", "quantity": 5},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert len(body["results"]) == 2

    # Now sell what was just bought -- exercises the positions ledger through the API.
    sell_resp = client.post(
        "/execute-portfolio",
        params={"user_id": "user1"},
        json={"instructions": [{"symbol": "TCS", "broker": "mock", "action": "SELL", "quantity": 3}]},
    )
    assert sell_resp.status_code == 200
    assert sell_resp.json()["status"] == "COMPLETED"

    positions = client.get("/positions", params={"user_id": "user1"}).json()["positions"]
    assert positions["mock"]["INFY"] == 10
    assert positions["mock"]["TCS"] == 2  # 5 bought, 3 sold


def test_sell_without_holdings_fails_via_api(client: TestClient):
    client.post("/auth/mock/callback", params={"user_id": "user2"}, json={})
    resp = client.post(
        "/execute-portfolio",
        params={"user_id": "user2"},
        json={"instructions": [{"symbol": "RELIANCE", "broker": "mock", "action": "SELL", "quantity": 1}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "Insufficient holdings" in body["results"][0]["error_message"]


def test_login_url_for_redirect_broker(client: TestClient):
    resp = client.get("/auth/mock/login-url", params={"user_id": "user1"})
    assert resp.status_code == 200
    assert resp.json()["login_url"] is not None


def test_unsupported_broker_returns_404(client: TestClient):
    resp = client.get("/auth/not-a-broker/login-url", params={"user_id": "user1"})
    assert resp.status_code == 404


def test_zerodha_login_url_falls_back_to_simulated_login_without_api_key(client: TestClient):
    resp = client.get("/auth/zerodha/login-url", params={"user_id": "user1"})
    assert resp.status_code == 200
    assert resp.json()["login_url"] == "/auth/zerodha/simulate-login?user_id=user1"


def test_simulated_login_page_renders(client: TestClient):
    resp = client.get("/auth/zerodha/simulate-login", params={"user_id": "user1"})
    assert resp.status_code == 200
    assert "Zerodha Kite" in resp.text
    assert "request_token" in resp.text


def test_credential_broker_login_url_is_null(client: TestClient):
    resp = client.get("/auth/angelone/login-url", params={"user_id": "user1"})
    assert resp.status_code == 200
    assert resp.json()["login_url"] is None
