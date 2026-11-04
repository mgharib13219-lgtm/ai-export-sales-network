"""Bounded, in-memory text extraction for trade-document review."""
from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from pathlib import PurePath

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_DOCX_UNCOMPRESSED = 20 * 1024 * 1024
MAX_DOCX_ENTRIES = 500
MAX_PDF_PAGES = 100


class DocumentExtractionError(ValueError):
    pass


class DocumentExtractor:
    SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".tsv", ".md"}

    def extract(self, filename: str, content: bytes) -> dict:
        name = PurePath(filename or "").name
        suffix = PurePath(name).suffix.lower()
        if suffix not in self.SUPPORTED:
            raise DocumentExtractionError("unsupported_file_type")
        if not isinstance(content, bytes) or not content:
            raise DocumentExtractionError("empty_file")
        if len(content) > MAX_FILE_BYTES:
            raise DocumentExtractionError("file_too_large")
        if b"\x00" in content[:4096] and suffix not in {".pdf", ".docx"}:
            raise DocumentExtractionError("binary_content_not_supported")

        warnings = []
        if suffix in {".txt", ".md", ".csv", ".tsv"}:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = content.decode("cp1252")
                    warnings.append("decoded_using_windows_1252")
                except UnicodeDecodeError as exc:
                    raise DocumentExtractionError("text_encoding_not_supported") from exc
            if suffix in {".csv", ".tsv"}:
                delimiter = "\t" if suffix == ".tsv" else self._detect_delimiter(text)
                rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
                text = "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
        elif suffix == ".pdf":
            text, page_count = self._pdf(content)
            if not text.strip():
                warnings.append("no_embedded_text_ocr_required")
        else:
            text = self._docx(content)

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text[:MAX_TEXT_CHARS]
        if len(text) >= MAX_TEXT_CHARS:
            warnings.append("text_truncated_at_safety_limit")
        fields = {
            "emails": sorted(set(re.findall(r"(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b", text)))[:100],
            "hs_code_candidates": sorted(set(re.findall(r"(?<!\\d)\\d{6,10}(?!\\d)", text)))[:100],
            "date_candidates": sorted(set(re.findall(r"\\b(?:\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}|\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})\\b", text)))[:100],
            "currency_amount_candidates": sorted(set(re.findall(r"(?i)(?:USD|EUR|GBP|AED|CNY|\\$|€|£)\\s?\\d[\\d,]*(?:\\.\\d{1,4})?", text)))[:100],
        }
        result = {
            "status": "extracted" if text.strip() else "no_text_extracted",
            "filename": name,
            "file_extension": suffix,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "text": text,
            "character_count": len(text),
            "extracted_fields": fields,
            "warnings": warnings,
            "stored": False,
            "authenticity_verified": False,
            "issuer_verified": False,
            "legal_or_compliance_clearance": False,
            "human_review_required": True,
        }
        if suffix == ".pdf":
            result["page_count"] = page_count
        return result

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        sample = text[:8192]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\\t").delimiter
        except csv.Error:
            return ","

    @staticmethod
    def _pdf(content: bytes):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise DocumentExtractionError("encrypted_pdf_not_supported")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise DocumentExtractionError("pdf_page_limit_exceeded")
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
                if sum(map(len, parts)) > MAX_TEXT_CHARS:
                    break
            return "\n".join(parts), len(reader.pages)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("invalid_or_unsupported_pdf") from exc

    @staticmethod
    def _docx(content: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                infos = archive.infolist()
                if len(infos) > MAX_DOCX_ENTRIES or sum(x.file_size for x in infos) > MAX_DOCX_UNCOMPRESSED:
                    raise DocumentExtractionError("docx_expansion_limit_exceeded")
                if any(x.flag_bits & 0x1 for x in infos):
                    raise DocumentExtractionError("encrypted_docx_not_supported")
            from docx import Document
            document = Document(io.BytesIO(content))
            parts = [p.text for p in document.paragraphs if p.text]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))
            return "\n".join(parts)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("invalid_or_unsupported_docx") from exc
