"""Tests for the behaviour-contract evaluator (tools/invariants.py).

The contract is repository data and is treated as untrusted input, so half of
these check what the evaluator refuses to do. Runs on Python 3.8 in CI, where
subscripts are wrapped in ast.Index -- a path newer Pythons never take.
"""
from tools.invariants import evaluate_contract


def _records(**bodies):
    return [{"id": k, "status": 200, "request": v.pop("_request", {}), "body": v} for k, v in bodies.items()]


def _one(rule, records, probe="p"):
    contract = {"invariants": [{"id": "r", "rule": rule, "applies_to": [probe]}]}
    return evaluate_contract(contract, records)[0]


def test_holding_rule():
    recs = _records(p={"total": 10.0, "tax": 1.8, "net": 8.2})
    assert _one("approx(body.total, body.net + body.tax)", recs)["status"] == "holds"


def test_violated_rule_reports_both_sides():
    recs = _records(p={"total": 12.0, "tax": 1.8, "net": 8.2})
    result = _one("approx(body.total, body.net + body.tax)", recs)
    assert result["status"] == "violated"
    assert "12.00" in result["observed"] and "10.00" in result["observed"]


def test_comprehension_over_request_items():
    recs = _records(p={"subtotal": 50.0, "_request": {"items": [{"unit_price": 10.0, "quantity": 2}, {"unit_price": 15.0, "quantity": 2}]}})
    assert _one("approx(body.subtotal, sum(i.unit_price * i.quantity for i in request.items))", recs)["status"] == "holds"


def test_subscript_access():
    recs = _records(p={"lines": [{"qty": 3}], "_request": {"items": [{"quantity": 3}]}})
    assert _one("body['lines'][0]['qty'] == request['items'][0]['quantity']", recs)["status"] == "holds"


def test_cross_probe_rule():
    recs = _records(with_coupon={"total": 80.0}, without_coupon={"total": 100.0})
    assert _one("probe('with_coupon').total <= probe('without_coupon').total", recs, probe="with_coupon")["status"] == "holds"


def test_missing_field_is_an_error_not_a_pass():
    result = _one("body.total > 0", _records(p={"subtotal": 1.0}))
    assert result["status"] == "error"
    assert "total" in result["error"]


def test_non_2xx_response_is_an_error():
    recs = [{"id": "p", "status": 500, "request": {}, "body": {"detail": "boom"}}]
    assert _one("body.total > 0", recs)["status"] == "error"


def test_refuses_imports():
    assert _one("__import__('os').system('true')", _records(p={}))["status"] == "error"


def test_refuses_python_attribute_access():
    # dotted names read JSON keys only -- never Python attributes like __class__
    assert _one("().__class__", _records(p={}))["status"] == "error"


def test_refuses_exponentiation():
    # ** is excluded so a rule cannot allocate an enormous integer
    assert _one("2 ** 100000000 > 0", _records(p={}))["status"] == "error"


def test_refuses_lambdas_and_unknown_functions():
    assert _one("(lambda: 1)() == 1", _records(p={}))["status"] == "error"
    assert _one("open('x') == 1", _records(p={}))["status"] == "error"
