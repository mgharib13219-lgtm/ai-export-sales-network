import io
import pytest
from docx import Document
from agents.document_extractor import DocumentExtractor, DocumentExtractionError


def test_extracts_text_and_candidate_fields_without_verifying_document():
    content = b"Supplier: Example\\nEmail: sales@example.com\\nHS: 123456\\nPrice: USD 12.50"
    result = DocumentExtractor().extract("invoice.txt", content)
    assert result["status"] == "extracted"
    assert "sales@example.com" in result["extracted_fields"]["emails"]
    assert "123456" in result["extracted_fields"]["hs_code_candidates"]
    assert result["authenticity_verified"] is False
    assert result["stored"] is False


def test_extracts_docx_paragraphs_and_table():
    doc = Document()
    doc.add_paragraph("Certificate of origin")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Country"
    table.cell(0, 1).text = "Oman"
    buffer = io.BytesIO()
    doc.save(buffer)
    result = DocumentExtractor().extract("certificate.docx", buffer.getvalue())
    assert "Certificate of origin" in result["text"]
    assert "Country | Oman" in result["text"]


def test_rejects_unsupported_large_and_empty_files():
    with pytest.raises(DocumentExtractionError, match="unsupported_file_type"):
        DocumentExtractor().extract("payload.exe", b"no")
    with pytest.raises(DocumentExtractionError, match="empty_file"):
        DocumentExtractor().extract("empty.txt", b"")
    with pytest.raises(DocumentExtractionError, match="file_too_large"):
        DocumentExtractor().extract("huge.txt", b"x" * (8 * 1024 * 1024 + 1))


def test_extracts_csv_rows():
    result = DocumentExtractor().extract("spec.csv", b"field,value\\nproduct,dates\\norigin,Oman")
    assert "product | dates" in result["text"]
