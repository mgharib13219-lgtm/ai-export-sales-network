from fastapi import HTTPException

from app.hs_catalog import (
    _header_token,
    _normalize_code,
    _parse_hs_csv,
    _pick,
    search_hs_catalog,
)


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
    assert _normalize_code("123456789", "8") == ""
    assert _normalize_code("12345", "4") == ""


def test_persian_and_arabic_digits_are_normalized_to_ascii():
    assert _normalize_code("۰۱۰۱۲۱", "۶") == "010121"
    assert _normalize_code("٠١٠١٢١", "٦") == "010121"


def test_header_aliases_accept_arabic_letter_variants_and_spacing():
    assert _header_token("كود\u200cتعرفه") == _header_token("کد تعرفه")
    assert _pick({"كود تعرفه": "0101"}, ("کد تعرفه",)) == "0101"
    assert _pick({"شماره تعرفه": "010121"}, ("tariff_code", "شماره تعرفه")) == "010121"


def test_parser_accepts_persian_code_and_header_variants():
    csv_data = "كود تعرفه,شرح کالا,تعداد رقم\n۰۱۰۱,حیوانات زنده,۴\n".encode("utf-8")
    rows, _ = _parse_hs_csv(csv_data, "IRICA", "2026")
    assert len(rows) == 1
    assert rows[0][0] == "0101"
    assert rows[0][1] == "حیوانات زنده"


def test_parser_rejects_rows_without_a_description():
    csv_data = "hs_code,description_fa,digits\n0101,,4\n".encode("utf-8")
    try:
        _parse_hs_csv(csv_data, "IRICA", "2026")
    except ValueError as exc:
        assert str(exc) == "missing_hs_description_at_line_2"
    else:
        raise AssertionError("description-free tariff row was accepted")


def test_parser_rejects_code_longer_than_declared_level():
    csv_data = "hs_code,description_fa,digits\n12345,شرح,4\n".encode("utf-8")
    try:
        _parse_hs_csv(csv_data, "IRICA", "2026")
    except ValueError as exc:
        assert str(exc) == "invalid_hs_code_at_line_2"
    else:
        raise AssertionError("HS code longer than its level was accepted")


def test_hs_level_filter_only_accepts_hierarchy_widths():
    for level in (3, 5, 7, 9):
        try:
            search_hs_catalog(level=level)
        except HTTPException as exc:
            assert exc.status_code == 422
            assert exc.detail == "invalid_hs_level"
        else:
            raise AssertionError(f"unsupported HS level accepted: {level}")
