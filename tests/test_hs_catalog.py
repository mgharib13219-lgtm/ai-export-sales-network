import pytest

from app.hs_catalog import _normalize_code, _prepare_csv_rows


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
    assert _normalize_code("123456", "4") == ""
    assert _normalize_code("１２３４", "4") == ""


def test_numeric_excel_values_can_be_normalized_without_losing_zeroes():
    assert _normalize_code("101.0", "4") == "0101"
    assert _normalize_code("0101.0", "4") == "0101"


def test_hs_level_filter_only_accepts_hierarchy_widths():
    from fastapi import HTTPException
    from app.hs_catalog import search_hs_catalog

    for level in (3, 5, 7, 9):
        with pytest.raises(HTTPException) as exc:
            search_hs_catalog(level=level)
        assert exc.value.status_code == 422
        assert exc.value.detail == "invalid_hs_level"


def test_csv_parser_accepts_bom_and_preserves_code_and_source_metadata():
    csv_text = "\ufeffhs_code,description_fa,description_en,digits\n101,نمونه,Sample,4\n"
    rows = _prepare_csv_rows(csv_text, "Official source", "1405-v1", "2026-11-05T00:00:00Z")
    assert rows == [("0101", "نمونه", "Sample", None, "Official source",
                     "1405-v1", "2026-11-05T00:00:00Z", 1)]


@pytest.mark.parametrize("csv_text,error", [
    ("", "missing_csv_header"),
    ("hs_code,description_fa\n101,\n", "missing_persian_description_at_line_2"),
    ("hs_code,description_fa,digits\n123,شرح,3\n", "invalid_hs_code_at_line_2"),
    ("hs_code,description_fa,digits\n0101,شرح,4\n0101,شرح دوم,4\n",
     "duplicate_hs_code_at_line_3"),
    ("hs_code,description_fa,parent_code\n010121,شرح,9999\n",
     "invalid_parent_code_at_line_2"),
    ("hs_code,description_fa\n101,\n", "missing_persian_description_at_line_2"),
    ("hs_code,description_fa\n,\n", "no_valid_rows_found"),
])
def test_csv_parser_rejects_invalid_rows(csv_text, error):
    with pytest.raises(ValueError, match=error):
        _prepare_csv_rows(csv_text, "source", "v1", "timestamp")


def test_csv_parser_infers_parent_from_code_hierarchy():
    csv_text = "hs_code,description_fa\n010121,شرح\n"
    rows = _prepare_csv_rows(csv_text, "source", "v1", "timestamp")
    assert rows[0][3] == "0101"
