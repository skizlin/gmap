"""mapping_related_feed_id_keys — COMP: vs plain numeric equivalence for entity lookups."""

from __future__ import annotations

from backend.domain_ids import mapping_feed_id_key, mapping_related_feed_id_keys


def test_comp_prefix_also_yields_plain_numeric_key():
    keys = set(mapping_related_feed_id_keys("COMP:10041282"))
    assert mapping_feed_id_key("COMP:10041282") in keys
    assert "10041282" in keys


def test_plain_numeric_also_yields_comp_prefixed_key():
    keys = set(mapping_related_feed_id_keys("10041282"))
    assert "10041282" in keys
    assert mapping_feed_id_key("COMP:10041282") in keys


def test_empty_returns_empty_list():
    assert mapping_related_feed_id_keys("") == []
    assert mapping_related_feed_id_keys(None) == []
