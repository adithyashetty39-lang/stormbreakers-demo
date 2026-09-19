"""Tests for the checkout quote endpoint.

Typical coverage for this kind of endpoint: the happy path pinned exactly, the
shape checked, the validation errors checked. What is NOT pinned is every
branch of the pricing arithmetic -- coupon-and-tax interplay, the free-shipping
boundary after a discount. Tests rarely enumerate those, which is why the
business rules also live in probes.json, where they are checked against the
real responses on every PR whether or not a test covers the path.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _quote(items, coupon_pct=0):
    return client.post("/checkout/quote", json={"items": items, "coupon_pct": coupon_pct})


def test_quote_happy_path():
    resp = _quote([{"unit_price": 999.0, "quantity": 1}])
    assert resp.status_code == 200
    body = resp.json()
    assert body["subtotal"] == 999.0
    assert body["gst"] == 179.82
    assert body["shipping"] == 0.0
    assert body["total"] == 1178.82


def test_quote_returns_full_breakdown():
    body = _quote([{"unit_price": 100.0, "quantity": 2}], coupon_pct=10).json()
    for field in ("subtotal", "discount", "taxable_amount", "gst", "shipping", "total", "free_shipping", "currency"):
        assert field in body
    assert body["currency"] == "INR"


def test_small_order_pays_shipping():
    body = _quote([{"unit_price": 100.0, "quantity": 1}]).json()
    assert body["shipping"] == 49.0
    assert body["free_shipping"] is False


def test_coupon_reduces_total():
    body = _quote([{"unit_price": 999.0, "quantity": 1}], coupon_pct=20).json()
    assert body["discount"] > 0
    assert body["total"] > 0


def test_empty_cart_rejected():
    assert _quote([]).status_code == 400


def test_coupon_above_limit_rejected():
    assert _quote([{"unit_price": 10.0, "quantity": 1}], coupon_pct=80).status_code == 400


def test_non_positive_quantity_rejected():
    assert _quote([{"unit_price": 10.0, "quantity": 0}]).status_code == 400
