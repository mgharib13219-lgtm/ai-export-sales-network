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


def test_hs_level_filter_only_accepts_hierarchy_widths():
    from fastapi import HTTPException
    from app.hs_catalog import search_hs_catalog

    for level in (3, 5, 7, 9):
        try:
            search_hs_catalog(level=level)
        except HTTPException as exc:
            assert exc.status_code == 422
            assert exc.detail == "invalid_hs_level"
        else:
            raise AssertionError(f"unsupported HS level accepted: {level}")
