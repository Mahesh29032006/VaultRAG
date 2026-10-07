import logging
import re
from typing import Any, Callable, Literal
from backend.models import DetectedEntity, RedactionResult

logger = logging.getLogger(__name__)

# Comprehensive HIPAA Safe Harbor 18-Category extraction rules:
# Tuple: (entity_type, regex_pattern, capture_group_idx, confidence)
# capture_group_idx == 0 indicates full regex match; > 0 extracts designated capturing group.
PII_RULES: list[tuple[str, re.Pattern, int, float, Any]] = [
    # 1. SSN
    ("SSN", re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"), 0, 0.99, lambda t: any(c in t for c in "0123456789")),

    # 2. EMAIL
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b"), 0, 0.99, lambda t: "@" in t),

    # 3. FAX
    ("FAX", re.compile(r"(?i)\b(?:fax[:\s]+)((?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4})\b"), 1, 0.98, lambda t: "fax" in t.lower()),

    # 4. PROVIDER_ID (Evaluated before generic 10-digit phone)
    ("PROVIDER_ID", re.compile(r"(?i)\b(?:NPI:?\s*)(\d{10})\b"), 1, 0.99, lambda t: "npi" in t.lower()),

    # 5. PHONE: formatted 10-digit US/Intl, labeled 10-digit, or plain Indian 10-digit
    ("PHONE", re.compile(r"(?i)\b(?:phone(?:/cell)?(?:\s*no\.?)?|cell|mobile|tel(?:ephone)?)[: \t#.]*(\+?[0-9 \t().-]{7,16})\b"), 1, 0.98, lambda t: any(c in t for c in "0123456789")),
    ("PHONE", re.compile(r"\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b"), 0, 0.96, lambda t: any(c in t for c in "0123456789")),
    ("PHONE", re.compile(r"\b(?:\+?91[-. ]?)?[6-9]\d{9}\b"), 0, 0.95, lambda t: any(c in t for c in "0123456789")),

    # 6. HEALTH_PLAN_ID (Evaluated before generic alphanumeric IDs)
    ("HEALTH_PLAN_ID", re.compile(r"(?i)\b(?:Health\s*Plan|Member\s*ID|Policy)[:\s#]+([A-Z]{2,4}\d{6,12})\b"), 1, 0.98, lambda t: any(w in t.lower() for w in ("health", "member", "policy"))),

    # 7. MRN & Clinical / Healthcare / Lab / Accession Identifiers (Category 8 & 18)
    ("MRN", re.compile(r"(?i)\b(?:MRN:?\s*|Record:?\s*)([0-9]{4,5}-[0-9]{4,5}-[A-Z0-9]{2,4})\b"), 1, 0.98, lambda t: any(c in t for c in "0123456789")),
    ("MRN", re.compile(r"(?i)\b(?:PATIENT\s*ID|PID|UHID)\s*[:.]?\s*([A-Za-z0-9-]{6,20})\b"), 1, 0.98, lambda t: any(w in t.lower() for w in ("patient", "pid", "uhid"))),
    ("MRN", re.compile(r"(?i)\b([A-Z]{2,4}\d{6,12})\s*PATIENT\s*ID\b"), 1, 0.98, lambda t: "patient" in t.lower()),
    ("MRN", re.compile(r"(?i)\b(?:LAB\s*NO\.?|TEST\s*NO\.?)\s*[:.]?\s*([A-Za-z0-9-]{6,20})\b"), 1, 0.98, lambda t: "lab" in t.lower() or "test" in t.lower()),
    ("MRN", re.compile(r"(?i)\b(?:ACCESSION\s*(?:NO\.?|ID)?)\s*[:.]?\s*(\d{6,12}|[A-Za-z0-9-]{6,20}?)(?=\s*WARD|\s*:|\b)"), 1, 0.98, lambda t: "accession" in t.lower()),

    # 8. ACCOUNT
    ("ACCOUNT", re.compile(r"(?i)\b(?:Account|Acct)[:\s#]+([A-Za-z0-9-]{6,18})\b"), 1, 0.95, lambda t: "acc" in t.lower()),

    # 9. LICENSE
    ("LICENSE", re.compile(r"(?i)\b(?:License|Lic)(?:\s*#)?[:\s#]+([A-Za-z0-9-]{6,18})\b"), 1, 0.95, lambda t: "lic" in t.lower()),

    # 10. VEHICLE_ID
    ("VEHICLE_ID", re.compile(r"\b(?:[A-HJ-NPR-Z0-9]{17}|(?:VIN|Plate)[:\s]+[A-Za-z0-9-]{5,10})\b"), 0, 0.95, lambda t: any(c in t for c in "0123456789")),

    # 11. DEVICE_ID
    ("DEVICE_ID", re.compile(r"(?i)\b(?:Device|Serial|IMEI)[:\s]+([A-Za-z0-9-]{8,20})\b"), 1, 0.95, lambda t: any(w in t.lower() for w in ("device", "serial", "imei"))),

    # 12. URL & IP
    ("URL", re.compile(r"\bhttps?://[^\s/$.?#].[^\s]*|\bwww\.[^\s/$.?#].[^\s]*\b"), 0, 0.99, lambda t: "http" in t or "www." in t),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"), 0, 0.99, lambda t: "." in t or ":" in t),

    # 13. BIOMETRIC
    ("BIOMETRIC_REF", re.compile(r"(?i)\b(?:fingerprint|voiceprint|retina\s*scan|iris\s*scan)[:\s]+([A-Za-z0-9_-]{6,32})\b"), 1, 0.95, lambda t: any(w in t.lower() for w in ("fingerprint", "voiceprint", "scan"))),

    # 14. FINANCIAL
    ("FINANCIAL", re.compile(r"\b(?:[A-Z]{2}\d{2}[A-Z0-9]{12,30}|(?:[\$€£]|USD\s*|EUR\s*)?\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4})\b"), 0, 0.95, lambda t: any(c in t for c in "0123456789")),

    # 15. AGE & DEMOGRAPHICS (Category 3 / DATE under HIPAA § 164.514(b)(2)(i)(C))
    ("DATE", re.compile(r"(?i)\b(?:AGE(?:/SEX)?|Age)\s*[:.]?\s*(\d{1,3}\s*(?:Y(?:ears?)?|Yrs?|M(?:onths?)?)?(?:\s*/\s*[MFmf])?)\b"), 1, 0.96, lambda t: "age" in t.lower()),
    ("DATE", re.compile(r"\b\d{1,3}\s*(?:Y/F|Y/M|Yrs?|Years?)\b"), 0, 0.95, lambda t: any(c in t for c in "0123456789")),
    ("DATE", re.compile(r"\b\d{1,3}-year-old\s+(?:female|male|boy|girl|man|woman|patient)\b"), 0, 0.95, lambda t: "year-old" in t.lower()),

    # 16. DATE & TIMESTAMP (Category 3)
    ("DATE", re.compile(r"(?i)\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})(?:\s*[-–@,]?\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)?\b"), 0, 0.92, lambda t: any(c in t for c in "0123456789")),

    # 17. ADDRESS & HEALTHCARE INSTITUTIONS (Category 2)
    ("ADDRESS", re.compile(r"(?i)\b(?:SAMPLE\s*COLLECTED\s*AT|COLLECTED\s*AT)\s*[:.]?\s*([A-Za-z0-9\s.,&-]+?)(?=\s*:|\n|$)"), 1, 0.92, lambda t: "collected" in t.lower()),
    ("ADDRESS", re.compile(r"(?i)\b(?:REFERRED\s*BY)\s*[:.]?\s*([A-Za-z0-9\s.,&-]+?)(?=\s*:|\n|$)"), 1, 0.92, lambda t: "referred" in t.lower()),
    ("ADDRESS", re.compile(r"(?i)(?:^|[\n:])\s*([A-Z0-9\s.,&-]{3,30}?)\s+(?:REPORTING\s*DATE|COLLECTION\s*DATE)"), 1, 0.90, lambda t: "date" in t.lower()),
    ("ADDRESS", re.compile(r"\b\d{1,5}\s+[A-Za-z0-9\s.,]+?\b(?:Street|St|Avenue|Ave|Terrace|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Way)\b(?:[,\s]+[A-Za-z\s]+[,\s]+[A-Z]{2}\s+\d{5})?", re.IGNORECASE), 0, 0.90, lambda t: any(c in t for c in "0123456789")),

    # 18. NAME: Honorifics, doctors, operators, labeled names (single-line bounds)
    ("NAME", re.compile(r"(?i)\b(?:Miss|Mr|Mrs|Ms|Master|Mast|Dr|DR|Doctor|Prof|Professor|Shri|Smt)\.?\s+([A-Za-z]{2,}(?:[ \t]+[A-Za-z]{2,}){1,3})\b"), 0, 0.96, lambda t: any(w in t.lower() for w in ("dr", "mr", "ms", "miss", "prof", "shri", "smt"))),
    ("NAME", re.compile(r"(?i)(?:Patient\s*Name|Patient|:\s*Name|Name\s*:|Attending(?:\s*Physician)?|Emergency\s*Contact|Physician)\s*[:.]?\s*(?:Miss|Mr|Mrs|Ms|Dr|DR)?\.?\s*([A-Za-z]{2,}(?:[ \t]+[A-Za-z]{2,}){1,3})\b"), 1, 0.94, lambda t: any(w in t.lower() for w in ("name", "patient", "attending", "emergency", "physician"))),
    ("NAME", re.compile(r"(?i)\b(?:Printed\s*By|Operator|Technician|Verified\s*By)\s*[:.]?\s*([A-Za-z0-9_-]{3,20})\b"), 1, 0.92, lambda t: any(w in t.lower() for w in ("printed", "operator", "technician", "verified"))),
    ("NAME", re.compile(r"(?i)\b([A-Za-z0-9_-]{3,20})(?:\s*Printed\s*By)\b"), 1, 0.92, lambda t: "printed" in t.lower()),
]

# Legacy dictionary mapping for backward compatibility
PATTERNS = {
    rule[0]: rule[1] for rule in PII_RULES
}


class PrivacyGuard:
    """HIPAA Safe Harbor 18-identifier category de-identification engine."""

    @classmethod
    def redact(cls, text: str) -> RedactionResult:
        if "\x00" in text:
            raise ValueError("Null bytes not permitted in input text")

        if not text or not text.strip():
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                detected_entities=[],
                token_map={},
                reverse_token_map={},
                risk_score_heuristic=0,
                safe_harbor_oriented=True
            )

        # 1. Collect candidate spans (start, end, type, raw, confidence)
        candidates = []

        for p_type, regex, grp_idx, conf, pre_check in PII_RULES:
            if not pre_check(text):
                continue
            for m in regex.finditer(text):
                if grp_idx > 0 and m.lastindex and m.lastindex >= grp_idx:
                    raw = m.group(grp_idx).strip()
                    s_idx = m.start(grp_idx)
                    e_idx = m.end(grp_idx)
                else:
                    raw = m.group(0).strip()
                    s_idx = m.start(0)
                    e_idx = m.end(0)

                if raw:
                    candidates.append((s_idx, e_idx, p_type, raw, conf))

        # 2. Sort by start ASC, then by length DESC, then confidence DESC
        candidates.sort(key=lambda x: (x[0], -(x[1] - x[0]), -x[4]))

        # 3. Greedy remove overlaps: keep longest / highest confidence span
        non_overlapping = []
        last_end = -1
        for start, end, p_type, raw, conf in candidates:
            if start >= last_end:
                non_overlapping.append((start, end, p_type, raw, conf))
                last_end = end
            else:
                if non_overlapping:
                    prev_start, prev_end, prev_type, prev_raw, prev_conf = non_overlapping[-1]
                    if (end - start) > (prev_end - prev_start):
                        non_overlapping[-1] = (start, end, p_type, raw, conf)
                        last_end = end

        # 4. Generate unique tokens and token maps
        token_map: dict[str, str] = {}
        reverse_token_map: dict[str, str] = {}
        type_counters: dict[str, int] = {}
        detected_entities: list[DetectedEntity] = []

        def get_unique_token(ent_type: str, raw_str: str) -> str:
            if raw_str in reverse_token_map:
                return reverse_token_map[raw_str]

            type_counters[ent_type] = type_counters.get(ent_type, 0) + 1
            tok = f"[SAFE_{ent_type}_{type_counters[ent_type]}]"

            while tok in text:
                tok = f"{tok[:-1]}_X]"

            token_map[tok] = raw_str
            reverse_token_map[raw_str] = tok
            return tok

        spans_with_tokens = []
        for start, end, p_type, raw, conf in non_overlapping:
            token = get_unique_token(p_type, raw)
            ent_id = f"ent_{len(detected_entities) + 1}"
            detected_entities.append(
                DetectedEntity(
                    id=ent_id,
                    type=p_type,  # type: ignore
                    raw=raw,
                    token=token,
                    start_index=start,
                    end_index=end,
                    confidence=conf
                )
            )
            spans_with_tokens.append((start, end, token))

        # 5. Apply replacements from right to left (highest index first)
        spans_with_tokens.sort(key=lambda x: x[0], reverse=True)
        redacted_chars = list(text)
        for start, end, token in spans_with_tokens:
            redacted_chars[start:end] = list(token)

        redacted_text = "".join(redacted_chars)
        risk_score = min(100, len(detected_entities) * 12)

        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            detected_entities=detected_entities,
            token_map=token_map,
            reverse_token_map=reverse_token_map,
            risk_score_heuristic=risk_score,
            safe_harbor_oriented=True
        )

    @classmethod
    def restore(cls, redacted_text: str, token_map: dict[str, str]) -> str:
        """Restores redacted tokens with raw entities."""
        if not redacted_text or not token_map:
            return redacted_text

        present_tokens = re.findall(r"\[SAFE_[A-Z_]+_\d+(?:_X)*\]", redacted_text)
        for tok in set(present_tokens):
            if tok not in token_map:
                logger.warning("Token %s present in text but missing from token_map", tok)

        restored = redacted_text
        for token, raw in token_map.items():
            restored = restored.replace(token, raw)

        return restored
