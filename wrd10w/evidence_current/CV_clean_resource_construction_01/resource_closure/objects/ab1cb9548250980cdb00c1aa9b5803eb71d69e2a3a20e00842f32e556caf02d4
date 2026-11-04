#!/usr/bin/env python3
"""Shared CV PDF extraction helpers for the cv-jd-interview-screening skill.

Design rules:
- Explicit errors (missing/empty/corrupt/zero-page PDF) are returned, never
  fabricated into an empty success.
- Text is returned per page; candidate identity is anchored by file content
  (sha256), never by filename conventions.
- Whitespace normalization is shared with evidence_check.py so literal quotes
  are matched identically in both tools.
"""

import hashlib
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None


class ExtractError(Exception):
    """Raised with a precise reason when a PDF cannot be extracted."""


# A watermark line: a single long alphanumeric token alone on one line,
# typical of resume-platform trackers. Dropped from cleaned text.
_WATERMARK_RE = re.compile(r"^[A-Za-z0-9_-]{24,}$")


def normalize(text):
    """Collapse all whitespace so quotes match across PDF line breaks."""
    return re.sub(r"\s+", "", text)


def clean_page_text(raw):
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _WATERMARK_RE.match(stripped):
            continue
        lines.append(stripped)
    return lines


def extract_pdf(path):
    """Extract per-page text from one PDF path. Raises ExtractError."""
    if pymupdf is None:
        raise ExtractError("pymupdf not available in this environment")
    p = Path(path)
    if not p.exists():
        raise ExtractError(f"file not found: {p}")
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise ExtractError(f"unreadable file: {p}: {exc}")
    if len(data) == 0:
        raise ExtractError(f"empty file (0 bytes): {p}")
    if not data.startswith(b"%PDF-"):
        raise ExtractError(f"not a PDF (bad header): {p}")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ExtractError(f"corrupt/unopenable PDF: {p}: {exc}")
    if doc.page_count == 0:
        raise ExtractError(f"PDF has zero pages: {p}")
    pages = []
    for i, page in enumerate(doc):
        raw = page.get_text()
        cleaned = clean_page_text(raw)
        pages.append({
            "page": i + 1,
            "lines": cleaned,
            "text": "\n".join(cleaned),
        })
    doc.close()
    sha = hashlib.sha256(data).hexdigest()
    identity_lines = pages[0]["lines"][:6]
    return {
        "file": str(p),
        "candidate_id": "cv_" + sha[:12],
        "sha256": sha,
        "bytes": len(data),
        "page_count": len(pages),
        "identity_lines": identity_lines,
        "pages": pages,
    }


def extract_many(paths):
    """Extract a batch. Returns (results, errors); candidates never mix
    because each result carries its own candidate_id and page list."""
    results, errors = [], []
    for path in paths:
        try:
            results.append(extract_pdf(path))
        except ExtractError as exc:
            errors.append({"file": str(path), "error": str(exc)})
    return results, errors


def find_quote(cv, quote, page=None):
    """Locate a normalized literal quote. Returns dict with ok/reason and the
    page(s) where the quote actually occurs (for mismatch diagnostics)."""
    norm = normalize(quote)
    if not norm:
        return {"ok": False, "reason": "empty quote"}
    hits = [pg["page"] for pg in cv["pages"] if norm in normalize(pg["text"])]
    if page is not None and (page < 1 or page > cv["page_count"]):
        return {
            "ok": False,
            "reason": f"page {page} out of range (1..{cv['page_count']})",
            "found_pages": hits,
        }
    if page is not None:
        if page in hits:
            return {"ok": True, "page": page}
        return {"ok": False, "reason": "quote not on claimed page", "found_pages": hits}
    if hits:
        return {"ok": True, "page": hits[0]}
    return {"ok": False, "reason": "quote not found in document", "found_pages": []}


if __name__ == "__main__":
    print("cvlib is a library; run cv_extract.py or evidence_check.py", file=sys.stderr)
    sys.exit(1)
