"""Checkout quote: the priced breakdown a storefront shows before payment.

Business rules (probes.json holds the machine-checked version of these):

1. The coupon is taken off the item subtotal.
2. GST (18%) is charged on the value AFTER the discount -- the transaction
   value -- not on the list price.
3. Orders whose discounted value is at least FREE_SHIPPING_MIN ship free;
   everything else pays SHIPPING_FEE.
4. total = taxable amount + GST + shipping. Nothing else goes into it.

Each rule is an ordinary place for an ordinary bug: tax computed before the
discount, the shipping threshold read off the undiscounted subtotal, a `>` that
should be `>=`, a subtraction that became an addition. Most of them do not
change the happy-path total a typical test asserts.
"""
from __future__ import annotations

GST_RATE = 0.18
FREE_SHIPPING_MIN = 499.0
SHIPPING_FEE = 49.0
MAX_COUPON_PCT = 50


class QuoteError(ValueError):
    pass


def _subtotal(items: list) -> float:
    if not items:
        raise QuoteError("cart is empty")
    subtotal = 0.0
    for item in items:
        quantity = int(item.get("quantity", 0))
        unit_price = float(item.get("unit_price", 0))
        if quantity <= 0:
            raise QuoteError(f"quantity must be positive: {quantity}")
        if unit_price < 0:
            raise QuoteError(f"unit_price cannot be negative: {unit_price}")
        subtotal += unit_price * quantity
    return round(subtotal, 2)


def quote(items: list, coupon_pct: float = 0.0) -> dict:
    if not 0 <= coupon_pct <= MAX_COUPON_PCT:
        raise QuoteError(f"coupon_pct must be between 0 and {MAX_COUPON_PCT}: {coupon_pct}")

    subtotal = _subtotal(items)
    discount = round(subtotal * coupon_pct / 100, 2)
    taxable_amount = round(subtotal - discount, 2)
    gst = round(taxable_amount * GST_RATE, 2)
    shipping = 0.0 if taxable_amount >= FREE_SHIPPING_MIN else SHIPPING_FEE
    total = round(taxable_amount + gst + shipping, 2)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "taxable_amount": taxable_amount,
        "gst": gst,
        "shipping": shipping,
        "total": total,
        "free_shipping": shipping == 0.0,
        "currency": "INR",
    }
