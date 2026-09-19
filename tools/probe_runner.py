"""Captures the app's actual HTTP responses so base and head can be compared.

This is a capture tool, not a test: it asserts nothing and never fails on a
"wrong" value. Deciding whether a difference matters happens later, in
AutoRelease AI. Keeping judgement out of here is what lets the same script run
unchanged against both commits.

Runs in-process through Starlette's TestClient -- the same way tests/test_main.py
already drives the app -- so there is no server to start, no port to pick and
no network involved.

Python 3.8 compatible on purpose: requirements.txt is pinned to 3.8 (see its
header for why) and ci.yml matches.
"""
from __future__ import annotations

import argparse
import json
import sys


def run_probes(spec):
    # Imported inside the function so that --help still works if the app or its
    # dependencies fail to import, and so the import error is reported as a
    # capture error rather than a stack trace.
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    captured = []

    for probe in spec.get("probes", []):
        method = str(probe.get("method", "GET")).upper()
        path = probe["path"]
        record = {
            "id": probe["id"],
            "method": method,
            "path": path,
            "identity_tokens": probe.get("identity_tokens", []),
            "foreign_tokens": probe.get("foreign_tokens", []),
        }
        try:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.request(method, path, json=probe.get("json"))
            try:
                body = resp.json()
            except ValueError:
                # Non-JSON response: keep a bounded snippet so a diff is still
                # possible without dragging an entire HTML page into the report.
                body = {"_raw": resp.text[:2000]}
            record["status"] = resp.status_code
            record["body"] = body
        except Exception as exc:  # noqa: BLE001 - a broken probe must not abort the rest
            record["status"] = None
            record["body"] = {}
            record["error"] = "{0}: {1}".format(type(exc).__name__, exc)
        captured.append(record)

    return captured


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capture app responses for semantic diffing.")
    parser.add_argument("--probes", default="probes.json", help="path to the probe contract file")
    parser.add_argument("--out", required=True, help="where to write the capture JSON")
    parser.add_argument("--label", default="", help="free-text label recorded in the capture")
    args = parser.parse_args(argv)

    with open(args.probes) as handle:
        spec = json.load(handle)

    captured = run_probes(spec)

    payload = {
        "label": args.label,
        "probe_contract_version": spec.get("version"),
        "probes": captured,
    }
    with open(args.out, "w") as handle:
        # sort_keys so two captures of identical behaviour are byte-identical
        # and a diff shows only real changes, never key ordering.
        json.dump(payload, handle, indent=2, sort_keys=True)

    errors = [p for p in captured if p.get("error")]
    print("wrote {0}: {1} probes, {2} errors".format(args.out, len(captured), len(errors)))
    for probe in errors:
        print("  probe {0} failed: {1}".format(probe["id"], probe["error"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
