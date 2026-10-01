from fastapi.testclient import TestClient


def test_execution_creates_a_retrievable_notification(client: TestClient):
    client.post("/auth/mock/callback", params={"user_id": "user1"}, json={})

    exec_resp = client.post(
        "/execute-portfolio",
        params={"user_id": "user1"},
        json={"instructions": [{"symbol": "INFY", "broker": "mock", "action": "BUY", "quantity": 10}]},
    )
    assert exec_resp.status_code == 200
    batch_id = exec_resp.json()["batch_id"]

    notif_resp = client.get("/notifications", params={"user_id": "user1"})
    assert notif_resp.status_code == 200
    notifications = notif_resp.json()
    assert len(notifications) == 1
    assert notifications[0]["batch_id"] == batch_id
    assert notifications[0]["channel"] == "console"
    assert notifications[0]["delivered"] is True
    assert notifications[0]["summary"]["succeeded_count"] == 1
    assert notifications[0]["summary"]["orders"][0]["symbol"] == "INFY"


def test_notifications_are_scoped_per_user(client: TestClient):
    client.post("/auth/mock/callback", params={"user_id": "userA"}, json={})
    client.post(
        "/execute-portfolio",
        params={"user_id": "userA"},
        json={"instructions": [{"symbol": "INFY", "broker": "mock", "action": "BUY", "quantity": 1}]},
    )

    resp = client.get("/notifications", params={"user_id": "userB"})
    assert resp.status_code == 200
    assert resp.json() == []
