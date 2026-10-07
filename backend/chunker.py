import hashlib
import re
from typing import Literal
from backend.models import DocumentChunk


class Chunker:
    @staticmethod
    def _split_into_units(text: str, max_chars: int) -> list[str]:
        """Splits large text recursively by paragraphs -> sentences -> words -> chars."""
        if len(text) <= max_chars:
            return [text]

        # Try paragraph split
        paras = re.split(r"(\n\s*\n)", text)
        if len(paras) > 1:
            units = []
            for p in paras:
                if not p:
                    continue
                if len(p) <= max_chars:
                    units.append(p)
                else:
                    units.extend(Chunker._split_into_units(p, max_chars))
            return units

        # Try sentence split (". ", "? ", "! ", "\n")
        sentences = re.split(r"(?<=[.!?\n])\s+", text)
        if len(sentences) > 1:
            units = []
            for s in sentences:
                if not s:
                    continue
                if len(s) <= max_chars:
                    units.append(s)
                else:
                    units.extend(Chunker._split_into_units(s, max_chars))
            return units

        # Try whitespace / words split
        words = text.split(" ")
        if len(words) > 1:
            units = []
            current_word_chunk = []
            current_len = 0
            for w in words:
                w_len = len(w) + (1 if current_word_chunk else 0)
                if current_len + w_len <= max_chars:
                    current_word_chunk.append(w)
                    current_len += w_len
                else:
                    if current_word_chunk:
                        units.append(" ".join(current_word_chunk))
                        current_word_chunk = []
                        current_len = 0
                    if len(w) <= max_chars:
                        current_word_chunk.append(w)
                        current_len = len(w)
                    else:
                        units.extend(Chunker._split_into_units(w, max_chars))
            if current_word_chunk:
                units.append(" ".join(current_word_chunk))
            return units

        # Hard char split for single long tokens/words (e.g. 100k char single word)
        units = []
        for i in range(0, len(text), max_chars):
            units.append(text[i:i + max_chars])
        return units

    @classmethod
    def chunk(
        cls,
        text: str,
        chunk_size: int = 450,
        overlap: int = 60,
        doc_name: str = "",
        category: Literal["CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE", "GENERAL"] = "GENERAL",
        doc_id: str = ""
    ) -> list[DocumentChunk]:
        # 1. Validation
        if overlap >= chunk_size:
            raise ValueError(f"overlap ({overlap}) must be strictly less than chunk_size ({chunk_size})")

        if not text or not text.strip():
            return []

        # If total text length <= chunk_size, single chunk
        raw_lines = text.split("\n")
        total_lines = len(raw_lines)

        if len(text) <= chunk_size:
            cid = f"{doc_id}_chunk_0" if doc_id else f"chunk_0"
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return [
                DocumentChunk(
                    id=cid,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    category=category,
                    content=text,
                    chunk_index=0,
                    word_count=len(text.split()),
                    page_number=1,
                    start_line=1,
                    end_line=max(1, total_lines),
                    sha256=sha
                )
            ]

        # Break text down into atomic atomic units
        step_size = max(1, chunk_size - overlap)
        atomic_units = cls._split_into_units(text, step_size)

        # Map character offsets in original text to line numbers
        line_start_offsets = []
        current_offset = 0
        for line in raw_lines:
            line_start_offsets.append(current_offset)
            current_offset += len(line) + 1

        def get_line_number(char_pos: int) -> int:
            if char_pos <= 0:
                return 1
            low, high = 0, len(line_start_offsets) - 1
            while low <= high:
                mid = (low + high) // 2
                if line_start_offsets[mid] <= char_pos:
                    low = mid + 1
                else:
                    high = mid - 1
            return max(1, high + 1)

        chunks: list[DocumentChunk] = []
        accumulated_text = ""
        search_cursor = 0

        for unit in atomic_units:
            if not unit.strip():
                continue

            test_text = (accumulated_text + " " + unit).strip() if accumulated_text else unit

            if len(test_text) <= chunk_size:
                accumulated_text = test_text
            else:
                if accumulated_text:
                    c_text = accumulated_text[:chunk_size]
                    c_idx = len(chunks)
                    cid = f"{doc_id}_chunk_{c_idx}" if doc_id else f"chunk_{c_idx}"
                    sha = hashlib.sha256(c_text.encode("utf-8")).hexdigest()

                    found_pos = text.find(c_text[:50], search_cursor)
                    if found_pos == -1:
                        found_pos = search_cursor
                    start_char = found_pos
                    end_char = min(len(text), start_char + len(c_text))
                    search_cursor = max(0, end_char - overlap)

                    s_line = get_line_number(start_char)
                    e_line = max(s_line, get_line_number(end_char))
                    p_num = (s_line - 1) // 50 + 1

                    chunks.append(
                        DocumentChunk(
                            id=cid,
                            doc_id=doc_id,
                            doc_name=doc_name,
                            category=category,
                            content=c_text,
                            chunk_index=c_idx,
                            word_count=len(c_text.split()),
                            page_number=p_num,
                            start_line=s_line,
                            end_line=e_line,
                            sha256=sha
                        )
                    )

                    overlap_prefix = c_text[-overlap:].strip()
                    next_str = (overlap_prefix + " " + unit).strip() if overlap_prefix else unit
                    accumulated_text = next_str[:chunk_size]
                else:
                    accumulated_text = unit[:chunk_size]

        if accumulated_text and accumulated_text.strip():
            c_text = accumulated_text[:chunk_size]
            c_idx = len(chunks)
            cid = f"{doc_id}_chunk_{c_idx}" if doc_id else f"chunk_{c_idx}"
            sha = hashlib.sha256(c_text.encode("utf-8")).hexdigest()

            found_pos = text.find(c_text[:50], search_cursor)
            if found_pos == -1:
                found_pos = search_cursor
            start_char = found_pos
            end_char = min(len(text), start_char + len(c_text))

            s_line = get_line_number(start_char)
            e_line = max(s_line, get_line_number(end_char))
            p_num = (s_line - 1) // 50 + 1

            chunks.append(
                DocumentChunk(
                    id=cid,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    category=category,
                    content=c_text,
                    chunk_index=c_idx,
                    word_count=len(c_text.split()),
                    page_number=p_num,
                    start_line=s_line,
                    end_line=e_line,
                    sha256=sha
                )
            )

        return chunks
