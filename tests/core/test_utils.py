from app.services.helpers import normalize_str

def test_normalize_str():
    assert normalize_str("  teSt    ") == "test"
    assert normalize_str("TEst  ") == "test"
    assert normalize_str("  ") is None
    assert normalize_str(None) is None