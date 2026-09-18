import pytest

from app.pricing import (
    InvalidQuantityError,
    apply_discount,
    cart_total,
    free_shipping_eligible,
    line_total,
)


def test_line_total_basic():
    assert line_total(10.0, 3) == 30.0


def test_line_total_rejects_negative_quantity():
    with pytest.raises(InvalidQuantityError):
        line_total(10.0, -1)


def test_apply_discount_zero():
    assert apply_discount(100.0, 0) == 100.0


def test_apply_discount_half():
    assert apply_discount(100.0, 50) == 50.0


def test_apply_discount_out_of_range():
    with pytest.raises(ValueError):
        apply_discount(100.0, 150)


def test_cart_total_multiple_items():
    items = [
        {"unit_price": 10.0, "quantity": 2},
        {"unit_price": 5.0, "quantity": 3},
    ]
    assert cart_total(items) == 35.0


def test_cart_total_with_discount():
    items = [{"unit_price": 20.0, "quantity": 5}]
    assert cart_total(items, discount_pct=10) == 90.0


def test_free_shipping_eligible_true():
    assert free_shipping_eligible(50.0) is True


def test_free_shipping_eligible_false():
    assert free_shipping_eligible(49.99) is False


def test_free_shipping_custom_threshold():
    assert free_shipping_eligible(20.0, threshold=15.0) is True
