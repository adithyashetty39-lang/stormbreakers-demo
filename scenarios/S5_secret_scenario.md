# S5 — Secret-in-diff demo scenario

This scenario is not baked into the default branch on purpose: leaving a
secret-shaped string permanently in the repo is bad hygiene even when it's
fake, and you only need this on the branch you demo it from.

**To set up S5 during the hackathon:**

1. Create a branch: `git checkout -b scenario/s5-secret`
2. Add this line to `app/config.py` (or any file) as a fake constant:
   ```python
   # NEVER a real credential -- this is AWS's own published example key,
   # used throughout their docs and every secret-scanner's test suite.
   DEBUG_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
   ```
3. Push the branch and open a PR against `main`.
4. gitleaks (in `ci.yml`) should flag it and upload a SARIF result to Code
   Scanning; confirm the alert appears under the repo's Security tab.
5. In AutoRelease AI, this should trip the `secret_detected` GATE -> BLOCK,
   regardless of what the computed score would otherwise have been.

**Verify before judging:** run this once ahead of time and confirm gitleaks
actually catches `AKIA` + 16 chars as a pattern with the ruleset your pinned
gitleaks-action version ships. If it doesn't fire, gitleaks' default config
also flags high-entropy generic strings -- swap in something entropic instead
and re-test.
