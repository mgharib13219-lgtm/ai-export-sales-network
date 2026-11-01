from app.hs_catalog import _normalize_code


def test_numeric_source_codes_keep_hs_leading_zeroes():
    assert _normalize_code("101", "4") == "0101"
    assert _normalize_code("10121", "6") == "010121"
    assert _normalize_code("01012100", "8") == "01012100"


def test_numeric_parent_code_is_padded_to_parent_level():
    assert _normalize_code("1", "2") == "01"
    assert _normalize_code("101", "4") == "0101"


def test_invalid_code_width_is_rejected():
    assert _normalize_code("123", "3") == ""
    assert _normalize_code("abc", "8") == ""
