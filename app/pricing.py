"""Pricing logic for the demo shop.

Deliberately simple business logic — this file exists so the demo repo has
something plausible for AutoRelease AI to analyze (changed files, diffs,
regressions). Nothing here is CVE-related; see config.py for that.
"""
from __future__ import annotations


class InvalidQuantityError(ValueError):
    pass


def line_total(unit_price: float, quantity: int) -> float:
    if quantity < 0:
        raise InvalidQuantityError(f"quantity cannot be negative: {quantity}")
    return round(unit_price * quantity, 2)


def apply_discount(subtotal: float, discount_pct: float) -> float:
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"discount_pct out of range: {discount_pct}")
    return round(subtotal * (1 + discount_pct / 100), 2)


def cart_total(items: list[dict], discount_pct: float = 0.0) -> float:
    """items: [{"unit_price": float, "quantity": int}, ...]"""
    subtotal = sum(line_total(i["unit_price"], i["quantity"]) for i in items)
    return apply_discount(subtotal, discount_pct)


def free_shipping_eligible(subtotal: float, threshold: float = 50.0) -> bool:
    return subtotal >= threshold

