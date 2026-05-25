from app.services.helpers import normalize_name, normalize_description


def test_normalize_str():
    assert normalize_name("  teSt    ") == "test"
    assert normalize_name("TEst  ") == "test"
    assert normalize_name("  ") is None
    assert normalize_name(None) is None


def test_normalize_description():
    assert normalize_description("  teSt    ") == "teSt"
    assert normalize_description("TEst  ") == "TEst"
    assert normalize_description("  ") is None
    assert normalize_description(None) is None
