from pathlib import Path
import pytest
from backend.document_loader import DocumentLoader
from backend.errors import (
    DocumentParseError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)


def test_document_loader_e10_zero_byte_file_raises_empty(tmp_path: Path):
    f = tmp_path / "zero.txt"
    f.write_bytes(b"")
    with pytest.raises(EmptyDocumentError, match="empty"):
        DocumentLoader.load(f)


def test_document_loader_e11_file_too_large_raises_error(tmp_path: Path):
    f = tmp_path / "large.txt"
    f.write_text("Small content", encoding="utf-8")
    with pytest.raises(FileTooLargeError):
        DocumentLoader.load(f, max_upload_bytes=5)


def test_document_loader_e12_unsupported_extension_raises_error(tmp_path: Path):
    f = tmp_path / "unsupported.exe"
    f.write_bytes(b"MZ\x90\x00")
    with pytest.raises(UnsupportedFileTypeError):
        DocumentLoader.load(f)


def test_document_loader_e14_corrupt_pdf_raises_parse_error(tmp_path: Path):
    f = tmp_path / "corrupt.pdf"
    f.write_bytes(b"NOT_A_PDF_CONTENT")
    with pytest.raises(DocumentParseError):
        DocumentLoader.load(f)


def test_document_loader_e15_crlf_normalized_to_lf(tmp_path: Path):
    f = tmp_path / "crlf.txt"
    f.write_bytes(b"Line 1\r\nLine 2\rLine 3\nLine 4")
    text, doc_type = DocumentLoader.load(f)
    assert "\r" not in text
    assert text == "Line 1\nLine 2\nLine 3\nLine 4"
    assert doc_type == "TXT"


def test_document_loader_e16_no_trailing_newline_captures_last_line(tmp_path: Path):
    f = tmp_path / "no_newline.txt"
    f.write_text("Alpha\nBeta\nGamma", encoding="utf-8")
    text, _ = DocumentLoader.load(f)
    lines = text.split("\n")
    assert len(lines) == 3
    assert lines[-1] == "Gamma"


def test_document_loader_e18_whitespace_only_raises_empty(tmp_path: Path):
    f = tmp_path / "spaces.txt"
    f.write_text("   \n\t   \n  ", encoding="utf-8")
    with pytest.raises(EmptyDocumentError, match="whitespace"):
        DocumentLoader.load(f)


def test_document_loader_e19_utf16_bom_decoded_correctly(tmp_path: Path):
    f = tmp_path / "utf16.txt"
    raw = b"\xff\xfe" + "Hello UTF-16 World".encode("utf-16-le")
    f.write_bytes(raw)
    text, _ = DocumentLoader.load(f)
    assert "Hello UTF-16 World" in text


def test_document_loader_e20_unicode_filename_preserved(tmp_path: Path):
    f = tmp_path / "दस्तावेज़_rapport_中文.txt"
    f.write_text("International content: नमस्ते, Bonjour, 你好", encoding="utf-8")
    text, doc_type = DocumentLoader.load(f)
    assert "नमस्ते" in text
    assert doc_type == "TXT"


def test_document_loader_valid_pdf_extracted(tmp_path: Path, sample_pdf_bytes: bytes):
    f = tmp_path / "valid.pdf"
    f.write_bytes(sample_pdf_bytes)
    text, doc_type = DocumentLoader.load(f)
    assert "Minimal Valid PDF Document Content" in text
    assert doc_type == "PDF"


def test_document_loader_various_supported_extensions(tmp_path: Path):
    extensions = [".md", ".py", ".js", ".ts", ".json", ".csv", ".html", ".xml"]
    for ext in extensions:
        f = tmp_path / f"test{ext}"
        f.write_text(f"Content for {ext} file testing.", encoding="utf-8")
        text, doc_type = DocumentLoader.load(f)
        assert f"Content for {ext}" in text
        assert doc_type == ext.lstrip(".").upper()


def test_document_loader_encodings_and_boms(tmp_path: Path):
    # UTF-8 BOM
    f_utf8_bom = tmp_path / "utf8_bom.txt"
    f_utf8_bom.write_bytes(b"\xef\xbb\xbfUTF8 BOM content line")
    t1, _ = DocumentLoader.load(f_utf8_bom)
    assert "UTF8 BOM content line" in t1

    # UTF-16 BE
    f_utf16_be = tmp_path / "utf16_be.txt"
    f_utf16_be.write_bytes(b"\xfe\xff" + "UTF16 BE content".encode("utf-16-be"))
    t2, _ = DocumentLoader.load(f_utf16_be)
    assert "UTF16 BE content" in t2

    # Latin-1 fallback
    f_latin1 = tmp_path / "latin1.txt"
    f_latin1.write_bytes(b"Caf\xe9 and na\xefve in French.")
    t3, _ = DocumentLoader.load(f_latin1)
    assert "Caf" in t3


def test_document_loader_pdf_stream_fallback(tmp_path: Path):
    from backend.document_loader import _unescape_pdf_string
    unescaped = _unescape_pdf_string(b"Hello\\nWorld\\tTest\\(Escaped\\)")
    assert "Hello\nWorld\tTest(Escaped)" in unescaped
