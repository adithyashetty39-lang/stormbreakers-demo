from app.config import DEFAULT_CONFIG, load_store_config


def test_default_config():
    assert load_store_config() == DEFAULT_CONFIG


def test_load_store_config_merges_overrides():
    cfg = load_store_config("store_name: Custom Shop\ncurrency: EUR\n")
    assert cfg["store_name"] == "Custom Shop"
    assert cfg["currency"] == "EUR"
    assert cfg["free_shipping_threshold"] == 50.0


def test_load_store_config_rejects_non_mapping():
    import pytest

    with pytest.raises(ValueError):
        load_store_config("- just\n- a\n- list\n")
