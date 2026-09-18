from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_cart_total_endpoint():
    resp = client.post(
        "/cart/total",
        json={"items": [{"unit_price": 25.0, "quantity": 2}], "discount_pct": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 50.0
    assert body["free_shipping"] is True


def test_cart_total_endpoint_rejects_negative_quantity():
    resp = client.post(
        "/cart/total",
        json={"items": [{"unit_price": 25.0, "quantity": -1}]},
    )
    assert resp.status_code == 400
