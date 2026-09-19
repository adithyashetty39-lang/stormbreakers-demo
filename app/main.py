"""FastAPI app tying the demo shop together.

Small, deliberately boring surface: enough real endpoints that GitHub Actions,
CodeQL, and Dependabot all have something to look at, without needing a
database. See config.py and image_utils.py for the CVE demo scenarios, and
pricing.py for the plain business logic used by test_flaky.py's history.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.checkout import QuoteError, quote
from app.pricing import InvalidQuantityError, cart_total, free_shipping_eligible

app = FastAPI(title="Stormbreakers Demo Shop")

# Partner-specific storefront copy. Two entries whose values are individually
# plausible, which is exactly what makes a swap between them survive a test
# suite that only checks the key is present -- see tests/test_home.py.
PARTNER_BANNERS = {
    "amazon": "Amazon Big Billion Deals",
    "flipkart": "Flipkart Mega Sale",
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/home")
def home(partner: str = "amazon") -> dict:
    if partner not in PARTNER_BANNERS:
        raise HTTPException(status_code=404, detail=f"unknown partner: {partner}")
    return {
        "partner": partner,
        "banner": PARTNER_BANNERS[partner],
        "currency": "INR",
    }


@app.post("/cart/total")
def cart_total_endpoint(payload: dict) -> dict:
    items = payload.get("items", [])
    discount_pct = payload.get("discount_pct", 0.0)
    try:
        total = cart_total(items, discount_pct)
    except (InvalidQuantityError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "total": total,
        "free_shipping": free_shipping_eligible(total),
    }


@app.post("/checkout/quote")
def checkout_quote(payload: dict) -> dict:
    try:
        return quote(payload.get("items", []), float(payload.get("coupon_pct", 0.0)))
    except (QuoteError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
