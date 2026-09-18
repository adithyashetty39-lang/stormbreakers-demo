# S4 — Real regression demo scenario

Like S5, this isn't baked into `main` because a permanently broken test would
poison the "clean baseline" that S1/S2's history depends on. Apply this on a
throwaway branch when you want to demo it.

**To set up S4:**

1. `git checkout -b scenario/s4-regression`
2. Introduce a genuine bug in `app/pricing.py`'s `apply_discount`, e.g. flip
   the sign so discounts *increase* the price:
   ```python
   def apply_discount(subtotal: float, discount_pct: float) -> float:
       if not 0 <= discount_pct <= 100:
           raise ValueError(f"discount_pct out of range: {discount_pct}")
       return round(subtotal * (1 + discount_pct / 100), 2)  # BUG: was (1 - ...)
   ```
3. Push and open a PR. `test_apply_discount_half` and
   `test_cart_total_with_discount` in `tests/test_pricing.py` will now fail
   -- and because this test has **no prior failure history** (unlike
   `test_flaky.py`), the Build & Test Agent's `get_test_history` call should
   come back "never failed before on this test", which is what should drive
   the **new_regression** classification (not flaky).
4. Confirm the agent's `compare_commits` call correctly names this commit
   and `app/pricing.py` as the suspect.

Expected AutoRelease AI result: `new_regression` finding, -40 (capped),
band likely Block or caveats depending on what else is on the PR --
see the plan's Phase 6 table for the full expected-score matrix.
