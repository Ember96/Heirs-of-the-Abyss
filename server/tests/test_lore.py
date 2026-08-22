"""T4.5 — lore quarantine: ring buffer bound, session isolation, wrap-as-data."""

from app.rag.lore import LoreRingBuffer, wrap_as_data


def test_ring_buffer_bound():
    store = LoreRingBuffer(max_entries=500)
    for i in range(1000):
        store.add("s1", f"fragment {i}")
    assert store.size() <= 500


def test_no_cross_session_leakage():
    store = LoreRingBuffer()
    store.add("s1", "beast lore")
    store.add("s2", "boss lore")
    assert store.retrieve("s1") == [{"session_id": "s1", "fragment": "beast lore", "is_generated": True}]
    assert all(e["session_id"] == "s2" for e in store.retrieve("s2"))
    assert store.retrieve("s3") == []


def test_provenance_forced():
    store = LoreRingBuffer()
    entry = store.add("s1", "a claim")
    assert entry["is_generated"] is True


def test_wrap_as_data():
    assert '<lore untrusted="true">' in wrap_as_data("the beast has wings")
    assert "the beast has wings" in wrap_as_data("the beast has wings")
