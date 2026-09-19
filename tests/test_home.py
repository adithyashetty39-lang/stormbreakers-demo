"""Tests for the partner storefront endpoint.

Written the way this kind of endpoint usually gets tested in a real codebase:
check it responds, check the shape is right, check the error path. Nobody
writes an assertion pinning every banner string to its partner, because at the
time of writing it feels like testing the dictionary rather than the code.

That is the gap on purpose. These tests stay green if the two banner values are
swapped, so the swap ships behind a green build. Catching it is the job of the
semantic response check (probes.json + tools/probe_runner.py), which compares
what the app actually returned before and after the change instead of only
what somebody thought to assert.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_responds_ok():
    resp = client.get("/home?partner=amazon")
    assert resp.status_code == 200


def test_home_defaults_to_a_partner():
    resp = client.get("/home")
    assert resp.status_code == 200
    assert resp.json()["partner"] == "amazon"


def test_home_returns_expected_shape():
    body = client.get("/home?partner=flipkart").json()
    assert "partner" in body
    assert "banner" in body
    assert "currency" in body


def test_home_banner_is_a_non_empty_string():
    body = client.get("/home?partner=amazon").json()
    assert isinstance(body["banner"], str)
    assert body["banner"].strip() != ""


def test_home_currency_is_inr():
    assert client.get("/home?partner=amazon").json()["currency"] == "INR"


def test_home_unknown_partner_is_404():
    resp = client.get("/home?partner=nosuchpartner")
    assert resp.status_code == 404
