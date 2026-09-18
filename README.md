# stormbreakers-demo-shop

The **target repo** AutoRelease AI validates against. Not the AI itself —
that's in the sibling `autorelease-ai/` repo. This is a tiny, boring FastAPI
app whose only job is to produce realistic CI evidence:

- ~18 passing tests + one **deterministically flaky** test (`tests/test_flaky.py`)
- A **reachable critical CVE**: `app/config.py` calls `yaml.full_load()` on
  pinned `pyyaml==5.3.1` (CVE-2020-14343 / GHSA-8q59-q68h-6hv4)
- An **unreachable critical CVE**: `app/image_utils.py` imports pinned
  `pillow==8.4.0` (CVE-2022-22817 / GHSA-8vj2-vxx3-667w) but never calls the
  vulnerable `PIL.ImageMath.eval`
- CI (`.github/workflows/ci.yml`) that produces JUnit XML, coverage XML,
  CodeQL alerts, and gitleaks SARIF — everything AutoRelease AI's evidence
  collector needs
- `deploy.yml`, triggered only by AutoRelease AI after a human clicks Approve

## Python version — read this first

**Pinned to Python 3.8, everywhere: CI and every dev laptop.**
`pyyaml==5.3.1` has no prebuilt wheel for Python 3.9+ and needs a C compiler
(MSVC on Windows) to build from source — confirmed by testing locally.
`pillow==8.4.0` was chosen over the more commonly-cited `8.1.0` for the same
reason: `8.1.0` has no Windows wheel for any Python newer than 3.9 either.
If a teammate's laptop only has Python 3.11+, install 3.8 alongside it
(via [pyenv](https://github.com/pyenv-win/pyenv-win) on Windows, or the
official installer) rather than fighting build tools mid-hackathon.

## Setup

```bash
python3.8 -m pip install -r requirements-dev.txt
pytest --junitxml=reports/junit.xml --cov=app --cov-report=xml:reports/coverage.xml
```

Verified locally: 18 tests pass, 100% coverage, both XML reports generate
correctly.

## Simulating flaky-test history before the event

`test_flaky.py` fails deterministically on every `GITHUB_RUN_NUMBER` divisible
by 3 — not true randomness, so you can plan the demo around it. Push ~10
throwaway commits to `main` before judging (or trigger the CI workflow
manually 10 times via `workflow_dispatch` if you add that trigger) so
`test_history` in AutoRelease AI has a real pass/fail pattern to reason
about, instead of hoping real flakiness cooperates live. **Check the
hackathon rules on pre-event repo activity before doing this.**

## Demo scenarios

- `scenarios/S4_regression_patch.md` — introduce a genuine regression
- `scenarios/S5_secret_scenario.md` — trip the secret-detected gate

S1 (clean), S2 (flaky + unreachable CVE), and S3 (reachable critical CVE) all
run against `main` as-is / with `app/config.py` wired up — no extra patching
needed. See the AutoRelease AI plan's Phase 6 table for the full expected-
score matrix.

## What's NOT here

No database, no auth, no frontend. This app exists to be validated, not to
be a real shop — don't over-invest in it.
