"""Application config loader.

DEMO NOTE (Team Stormbreakers): this file is the "reachable critical CVE"
scenario for AutoRelease AI. `requirements.txt` pins pyyaml==5.3.1, which is
vulnerable to CVE-2020-14343 / GHSA-8q59-q68h-6hv4 (arbitrary code execution
via yaml.full_load / FullLoader / unsafe_load — the fix landed in 5.4).

`load_store_config` below calls `yaml.full_load`, which is exactly the
vulnerable code path. That makes this package "reachable": the Security
Agent's search_imports + search_symbol_usage tools should find this file
importing yaml AND calling full_load, and classify the CVE as reachable /
critical -> -35 in the scorer.

For the S3 demo scenario, this line is what a PR would introduce (or land on
a branch) to flip GitHub's checks green while AutoRelease AI blocks it.
"""
from __future__ import annotations

import yaml

DEFAULT_CONFIG = {
    "store_name": "Stormbreakers Demo Shop",
    "currency": "USD",
    "free_shipping_threshold": 50.0,
}


def load_store_config(yaml_text: str | None = None) -> dict:
    """Load store config from a YAML string.

    Intentionally vulnerable for demo purposes: yaml.full_load() on
    untrusted input is CVE-2020-14343. A safe replacement would be
    `yaml.safe_load(yaml_text)`.
    """
    if yaml_text is None:
        return dict(DEFAULT_CONFIG)
    loaded = yaml.full_load(yaml_text)
    if not isinstance(loaded, dict):
        raise ValueError("store config must be a YAML mapping")
    merged = dict(DEFAULT_CONFIG)
    merged.update(loaded)
    return merged
