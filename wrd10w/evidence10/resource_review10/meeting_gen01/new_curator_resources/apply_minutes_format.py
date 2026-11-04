#!/usr/bin/env python3
"""Format top-level DOCX paragraphs; preserve inline XML during prefix edits.

New curator repair of the archived formatter. It does not transcribe audio,
verify meeting facts, format tables/headers/footnotes, or prove skill utility.
Heading/Title paragraph sizes stay unchanged and first-line indent is zero.
Body first-line indent is in characters; zero explicitly clears it. No network.
"""
import argparse
import json
import math
import os
import sys
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.run import Run


def paragraph_runs(paragraph):
    """Yield visible top-level runs and hyperlink runs in document order."""
    for item in paragraph.iter_inner_content():
        if isinstance(item, Run):
            yield item
        else:
            yield from item.runs


def is_heading(paragraph):
    try:
        name = paragraph.style.name or ""
    except Exception:
        name = ""
    return name.startswith("Heading") or "标题" in name or name in {"Title", "Subtitle"}


def strip_leading_star(paragraph):
    """Remove only a leading marker's visible prefix, preserving other XML.

    Do not assign Run.text: that would remove field/drawing nodes. Build the
    exact visible text sequence first. Unsupported inline structures fail
    before mutation, and main does not save a partially edited document.
    """
    original = paragraph.text
    stripped = original.lstrip()
    if not stripped.startswith("*"):
        return 0
    skip = len(original) - len(stripped) + 1
    if stripped[1:2] in (" ", "\u3000"):
        skip += 1
    slots = []
    for run in paragraph_runs(paragraph):
        for node in run._r:
            if node.tag == qn("w:t"):
                slots.append((node, node.text or ""))
            elif node.tag == qn("w:tab"):
                slots.append((node, "\t"))
            elif node.tag in {qn("w:br"), qn("w:cr")}:
                slots.append((node, "\n"))
    if "".join(text for _, text in slots) != original:
        raise ValueError("unsupported inline text structure; prefix unchanged")
    for node, text in slots:
        if skip == 0:
            break
        count = min(skip, len(text))
        if node.tag == qn("w:t"):
            node.text = text[count:]
            if node.text and (node.text[:1].isspace() or node.text[-1:].isspace()):
                node.set(qn("xml:space"), "preserve")
        elif count:
            node.getparent().remove(node)
        skip -= count
    assert skip == 0
    return 1


def set_run_fonts(run, cn_font, western_font):
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    for attribute in ["w:ascii", "w:hAnsi", "w:cs"]:
        fonts.set(qn(attribute), western_font)
    fonts.set(qn("w:eastAsia"), cn_font)


def set_first_line_indent_chars(paragraph, chars):
    ind = paragraph._element.get_or_add_pPr().get_or_add_ind()
    for attribute in ["w:firstLine", "w:firstLineChars", "w:hanging", "w:hangingChars"]:
        ind.attrib.pop(qn(attribute), None)
    ind.set(qn("w:firstLineChars"), str(int(chars * 100)))


def main():
    ap = argparse.ArgumentParser(description="Format top-level meeting DOCX paragraphs without rewriting their content.")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cn-font", default="楷体")
    ap.add_argument("--western-font", default="Times New Roman")
    ap.add_argument("--body-size", type=float, default=12)
    ap.add_argument("--line-spacing", type=float, default=1.5)
    ap.add_argument("--first-line-indent", type=float, default=2, help="body first-line indent in characters; 0 clears it")
    ap.add_argument("--remove-stars", action="store_true")
    ap.add_argument("--report")
    args = ap.parse_args()
    if (not all(math.isfinite(v) for v in [args.body_size, args.line_spacing, args.first_line_indent])
            or args.body_size <= 0 or args.line_spacing <= 0 or args.first_line_indent < 0):
        ap.error("positive finite font/spacing and nonnegative finite indent required")
    if not os.path.isfile(args.input):
        print("error: input file not found: " + args.input, file=sys.stderr)
        return 2
    try:
        doc = Document(args.input)
    except Exception as exc:
        print("error: input is not a valid docx: " + str(exc), file=sys.stderr)
        return 2
    total = styled = stars = headings = 0
    try:
        for paragraph in doc.paragraphs:
            total += 1
            if args.remove_stars:
                stars += strip_leading_star(paragraph)
            heading = is_heading(paragraph)
            headings += int(heading)
            runs = list(paragraph_runs(paragraph))
            for run in runs:
                set_run_fonts(run, args.cn_font, args.western_font)
                if not heading:
                    run.font.size = Pt(args.body_size)
            styled += int(bool(runs))
            paragraph.paragraph_format.line_spacing = args.line_spacing
            if heading:
                set_first_line_indent_chars(paragraph, 0)
            elif paragraph.text.strip():
                set_first_line_indent_chars(paragraph, args.first_line_indent)
    except ValueError as exc:
        print("error: unsupported document structure: " + str(exc), file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    doc.save(args.out)
    report = {
        "cn_font": args.cn_font, "western_font": args.western_font,
        "body_size_pt": args.body_size, "line_spacing": args.line_spacing,
        "first_line_indent_chars": args.first_line_indent,
        "remove_stars": bool(args.remove_stars),
        "paragraphs_total": total, "paragraphs_styled": styled,
        "headings_kept_size": headings, "stars_removed": stars,
        "paragraph_texts": [p.text for p in doc.paragraphs],
        "scope": "top-level paragraphs and hyperlinks; tables/headers/footnotes unchanged",
    }
    print(json.dumps(report, ensure_ascii=False))
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
