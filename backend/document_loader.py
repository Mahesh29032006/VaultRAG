import os
import re
import subprocess
import zlib
from pathlib import Path
from backend.errors import (
    DocumentParseError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv", ".html", ".xml"
}


def _unescape_pdf_string(s: bytes) -> str:
    res = []
    i = 0
    while i < len(s):
        if s[i] == 92 and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == 110:
                res.append("\n")
                i += 2
            elif nxt == 114:
                res.append("\r")
                i += 2
            elif nxt == 116:
                res.append("\t")
                i += 2
            elif nxt == 98:
                res.append("\b")
                i += 2
            elif nxt == 102:
                res.append("\f")
                i += 2
            elif nxt in (40, 41, 92):
                res.append(chr(nxt))
                i += 2
            else:
                oct_m = re.match(rb"^\d{1,3}", s[i + 1:])
                if oct_m:
                    res.append(chr(int(oct_m.group(0), 8)))
                    i += 1 + len(oct_m.group(0))
                else:
                    res.append(chr(nxt))
                    i += 2
        else:
            res.append(chr(s[i]))
            i += 1
    return "".join(res)


class DocumentLoader:
    @staticmethod
    def _extract_pdf_tier1_macos(path: Path) -> str:
        """Tier 1: macOS PDFKit via osascript."""
        try:
            osa_script = f'''
            use framework "PDFKit"
            set theURL to current application's NSURL's fileURLWithPath:"{path.resolve()}"
            set pdfDoc to current application's PDFDocument's alloc()'s initWithURL:theURL
            if pdfDoc is missing value then return ""
            return (pdfDoc's string()) as text
            '''
            proc = subprocess.run(
                ["osascript", "-e", osa_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_pdf_tier2_pypdf(path: Path) -> str:
        """Tier 2: pypdf.PdfReader."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                try:
                    # Attempt empty password decrypt
                    decrypted = reader.decrypt("")
                    if decrypted == 0:
                        raise DocumentParseError("Password-protected PDF cannot be decrypted")
                except Exception as e:
                    raise DocumentParseError("Password-protected PDF") from e

            if len(reader.pages) == 0:
                raise EmptyDocumentError("PDF has 0 pages")

            pages_text = []
            for page in reader.pages:
                txt = page.extract_text() or ""
                pages_text.append(txt)
            return "\n\n".join(pages_text).strip()
        except DocumentParseError:
            raise
        except EmptyDocumentError:
            raise
        except Exception as e:
            # Check if corruption related
            err_msg = str(e).lower()
            if "password" in err_msg or "encrypt" in err_msg:
                raise DocumentParseError("Password-protected PDF") from e
            if "eof" in err_msg or "header" in err_msg or "cannot read an empty file" in err_msg:
                raise DocumentParseError("Corrupt PDF file header or structure") from e
            return ""

    @staticmethod
    def _extract_pdf_tier3_fitz(path: Path) -> str:
        """Tier 3: PyMuPDF (fitz) if installed."""
        try:
            import fitz
            doc = fitz.open(str(path))
            if doc.needs_pass:
                raise DocumentParseError("Password-protected PDF")
            if doc.page_count == 0:
                raise EmptyDocumentError("PDF has 0 pages")
            texts = [page.get_text() for page in doc]
            return "\n\n".join(texts).strip()
        except (DocumentParseError, EmptyDocumentError):
            raise
        except Exception:
            return ""

    @staticmethod
    def _extract_pdf_tier4_pure_stream(path: Path) -> str:
        """Tier 4: Pure-Python stream parser for FlateDecode text."""
        try:
            with open(path, "rb") as f:
                content = f.read()

            extracted_chunks = []
            for stream in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", content, re.DOTALL):
                raw = stream.group(1)
                decompressed = None
                try:
                    decompressed = zlib.decompress(raw)
                except Exception:
                    decompressed = raw

                if decompressed:
                    # Match Tj, TJ operators
                    for tj in re.finditer(rb"\((.*?)\)\s*Tj", decompressed, re.DOTALL):
                        extracted_chunks.append(_unescape_pdf_string(tj.group(1)))
                    for array_m in re.finditer(rb"\[(.*?)\]\s*TJ", decompressed, re.DOTALL):
                        inner = array_m.group(1)
                        for tj_part in re.finditer(rb"\((.*?)\)", inner, re.DOTALL):
                            extracted_chunks.append(_unescape_pdf_string(tj_part.group(1)))

            return " ".join(extracted_chunks).strip()
        except Exception:
            return ""

    @classmethod
    def load(
        cls,
        path: Path,
        max_upload_bytes: int = 50 * 1024 * 1024,
        max_extracted_chars: int = 5_000_000
    ) -> tuple[str, str]:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        file_size = path.stat().st_size
        if file_size == 0:
            raise EmptyDocumentError("File is empty (0 bytes)")

        if file_size > max_upload_bytes:
            raise FileTooLargeError(
                f"File size {file_size} bytes exceeds maximum {max_upload_bytes} bytes"
            )

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Unsupported file extension: {ext}")

        doc_type = ext.lstrip(".").upper()

        if ext == ".pdf":
            # Quick corrupt header check
            with open(path, "rb") as f:
                header = f.read(1024)
            if not header.startswith(b"%PDF"):
                raise DocumentParseError("Corrupt PDF: Missing %PDF header")

            # Try tiers in order
            extracted = ""
            for tier in [
                cls._extract_pdf_tier1_macos,
                cls._extract_pdf_tier2_pypdf,
                cls._extract_pdf_tier3_fitz,
                cls._extract_pdf_tier4_pure_stream
            ]:
                try:
                    extracted = tier(path)
                    if extracted and extracted.strip():
                        break
                except (DocumentParseError, EmptyDocumentError):
                    raise
                except Exception:
                    continue

            if not extracted or not extracted.strip():
                raise EmptyDocumentError("PDF contains no extractable text or is a scanned document")

            text = extracted
        else:
            # Read text / code bytes
            with open(path, "rb") as f:
                raw_bytes = f.read()

            # Detect UTF-16 BOM
            if raw_bytes.startswith(b"\xff\xfe"):
                text = raw_bytes[2:].decode("utf-16-le", errors="replace")
            elif raw_bytes.startswith(b"\xfe\xff"):
                text = raw_bytes[2:].decode("utf-16-be", errors="replace")
            elif raw_bytes.startswith(b"\xef\xbb\xbf"):
                # Strip UTF-8 BOM
                text = raw_bytes[3:].decode("utf-8", errors="replace")
            else:
                try:
                    text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw_bytes.decode("latin-1", errors="replace")

        # Strip null bytes and normalize line endings
        normalized = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")


        if not normalized.strip():
            raise EmptyDocumentError("Document contains only whitespace")

        if len(normalized) > max_extracted_chars:
            raise FileTooLargeError(
                f"Extracted text length {len(normalized)} exceeds limit of {max_extracted_chars} characters"
            )

        return normalized, doc_type
