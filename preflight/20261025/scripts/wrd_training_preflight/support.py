"""Inventory and extract immutable, local WRD support evidence.

This is an offline document reader, not an agent, trainer or code executor.
It reads the old bundle's sources/, source_materials/ and retained29 only.
All output is restricted working material awaiting a separate privacy review.
Duplicate paths/corpus views remain distinct provenance, never new SFT samples.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from email.parser import BytesParser
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import time
from typing import Any, Iterator
import xml.etree.ElementTree as ET
import zipfile


SCHEMA = "wrd-support-evidence-v1"
TRAINING_USE = "evidence_only_not_primary_sft"
WORK_STATUS = "UNREVIEWED_RESTRICTED_WORKING_TEXT"
MAX_XML_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_TEXT_BYTES = 256 * 1024 * 1024
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".pyi", ".xsd", ".xml", ".yaml", ".yml",
    ".ps1", ".js", ".html", ".htm", ".mjs", ".csv", ".sh", ".log",
    ".toml", ".sty", ".tex", ".ts", ".tsx", ".jsx", ".map", ".cjs", ".cts", ".mts",
    ".bib", ".nbib", ".ris", ".svg", ".rst", ".css", ".ini", ".cfg",
    ".r", ".c", ".h", ".cpp", ".hpp", ".sql", ".ipynb", ".json",
    ".jsonl", ".lock", ".template", ".j2", ".lark", ".readme", ".tmp",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".bmp", ".tif", ".tiff"}
BINARY_SUFFIXES = {
    ".node", ".so", ".dll", ".exe", ".a", ".o", ".pyc", ".pkl",
    ".npy", ".npz", ".woff", ".woff2", ".ttf", ".eot", ".mo",
    ".mp4", ".m4a", ".mp3", ".wav", ".doc", ".xls", ".ppt",
}
FORMAL_MARKERS = ("ablation49", "eval250", "eval226", "evaluation250", "evaluation226")
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def gzip_writer(path: Path, append: bool = False):
    # Stable gzip header; this output is reproducible on the same source/library.
    with path.open("ab" if append else "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as text:
                yield text


def natural_key(value: str) -> list[Any]:
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", value)]


def credential_path(path: str) -> bool:
    p = PurePosixPath(path.replace("\\", "/").replace("::", "/"))
    name = p.name.lower()
    return (
        p.suffix.lower() in SENSITIVE_SUFFIXES
        or name in {"credentials.json", "credentials.yaml", "secrets.json", "secrets.yaml",
                    "token.json", "token.txt", "cookies.json", "cookies.txt", "id_rsa", "id_ed25519"}
        or name == ".env" or name.startswith(".env.")
        or any(x.lower() in {".ssh", "credentials", "secrets"} for x in p.parts)
    )


def excluded_path(path: str) -> str | None:
    low = path.lower().replace("\\", "/").replace("::", "/")
    if any(x in low for x in FORMAL_MARKERS):
        return "formal_evaluation_or_live_ablation_path_not_allowed"
    if credential_path(path):
        return "credential_or_key_filename_controlled_not_extracted"
    if ".git" in PurePosixPath(low).parts:
        return "version_control_metadata_not_training_evidence"
    return None


def decode_text(raw: bytes) -> tuple[str, str]:
    choices = ["utf-8-sig"]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        choices = ["utf-16"] + choices
    choices += ["gb18030"]
    for enc in choices:
        try:
            text = raw.decode(enc, errors="strict")
        except UnicodeError:
            continue
        controls = sum(ord(c) < 32 and c not in "\n\r\t\f\b" for c in text)
        if "\x00" in text or (text and controls / len(text) > 0.005):
            continue
        return text, enc
    raise ValueError("not_strictly_decodable_text")


def xml_root(z: zipfile.ZipFile, name: str) -> ET.Element:
    item = z.getinfo(name)
    if item.file_size > MAX_XML_BYTES:
        raise ValueError("xml_member_over_size_limit")
    # ElementTree does not fetch external resources. Reject DTDs explicitly.
    raw = z.read(item)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("xml_dtd_or_entity_not_allowed")
    return ET.fromstring(raw)


def local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class XMLDeclarationGuard:
    """Reject entities/DTDs while allowing large worksheets to stream."""
    def __init__(self, stream):
        self.stream = stream
        self.tail = b""

    def read(self, size: int = -1) -> bytes:
        chunk = self.stream.read(size)
        probe = (self.tail + chunk).upper()
        if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
            raise ValueError("xml_dtd_or_entity_not_allowed")
        self.tail = probe[-16:]
        return chunk


def xml_end_nodes(z: zipfile.ZipFile, name: str) -> Iterator[ET.Element]:
    with z.open(name) as stream:
        for _, node in ET.iterparse(XMLDeclarationGuard(stream), events=("end",)):
            yield node


def office_text(raw: bytes, suffix: str) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = set(z.namelist())
        if suffix == ".docx":
            wanted = sorted((n for n in names if re.fullmatch(
                r"word/(?:document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml", n)), key=natural_key)
            for name in wanted:
                root = xml_root(z, name)
                paragraphs = []
                for node in root.iter():
                    if local_tag(node.tag) == "p":
                        text = "".join((x.text or "") if local_tag(x.tag) in {"t", "delText"}
                                       else "\t" if local_tag(x.tag) == "tab"
                                       else "\n" if local_tag(x.tag) in {"br", "cr"} else ""
                                       for x in node.iter())
                        if text:
                            paragraphs.append(text)
                if paragraphs:
                    parts.append(f"[{name}]\n" + "\n".join(paragraphs))
        elif suffix == ".pptx":
            wanted = sorted((n for n in names if re.fullmatch(
                r"ppt/(?:slides/slide|notesSlides/notesSlide)\d+\.xml", n)), key=natural_key)
            for name in wanted:
                root = xml_root(z, name)
                lines = ["".join(x.text or "" for x in node.iter() if local_tag(x.tag) == "t")
                         for node in root.iter() if local_tag(node.tag) == "p"]
                if any(lines):
                    parts.append(f"[{name}]\n" + "\n".join(x for x in lines if x))
        else:
            strings: list[str] = []
            if "xl/sharedStrings.xml" in names:
                for node in xml_end_nodes(z, "xl/sharedStrings.xml"):
                    if local_tag(node.tag) == "si":
                        strings.append("".join(x.text or "" for x in node.iter() if local_tag(x.tag) == "t"))
                        node.clear()
            if "xl/workbook.xml" in names:
                sheet_names = [{"name": n.get("name"), "sheetId": n.get("sheetId")}
                               for n in xml_root(z, "xl/workbook.xml").iter() if local_tag(n.tag) == "sheet"]
                parts.append("[xl/workbook.xml sheet_metadata]\n" + compact(sheet_names))
            wanted = sorted((n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)), key=natural_key)
            for name in wanted:
                lines = []
                for cell in xml_end_nodes(z, name):
                    if local_tag(cell.tag) == "row":
                        cell.clear()
                        continue
                    if local_tag(cell.tag) != "c":
                        continue
                    kind = cell.get("t")
                    value = next((x.text or "" for x in cell if local_tag(x.tag) == "v"), "")
                    formula = next((x.text or "" for x in cell if local_tag(x.tag) == "f"), None)
                    if kind == "s":
                        value = strings[int(value)] if value.isdigit() and int(value) < len(strings) else "[invalid_shared_string_index]"
                    elif kind == "inlineStr":
                        value = "".join(x.text or "" for x in cell.iter() if local_tag(x.tag) == "t")
                    if value or formula is not None:
                        lines.append(compact({"cell": cell.get("r"), "type": kind,
                                              "formula": formula, "stored_value": value}))
                    cell.clear()
                if lines:
                    parts.append(f"[{name}; formulas_not_evaluated]\n" + "\n".join(lines))
            # Comments can contain source assumptions absent from cell values.
            for name in sorted((n for n in names if re.fullmatch(r"xl/comments\d+\.xml", n)), key=natural_key):
                text = "\n".join(x.text or "" for x in xml_root(z, name).iter() if local_tag(x.tag) == "t")
                if text:
                    parts.append(f"[{name}]\n{text}")
        return "\n\n".join(parts), {"method": "zip_xml_text_only", "xml_parts": len(wanted),
            "macros_executed": False, "formulas_recalculated": False,
            "layout_images_and_embedded_objects_not_extracted": True}


def pdf_text(raw: bytes) -> tuple[str, dict[str, Any]]:
    try:
        import pymupdf as fitz
    except ImportError:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise ValueError("encrypted_pdf_not_decrypted")
        pages = [(p.extract_text() or "") for p in reader.pages]
        method = "pypdf_existing_text_layer"
    else:
        fitz.TOOLS.mupdf_display_errors(False)
        fitz.TOOLS.mupdf_display_warnings(False)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ValueError("encrypted_pdf_not_decrypted")
            pages = [page.get_text("text") for page in doc]
        method = "pymupdf_existing_text_layer"
    nonempty = sum(bool(p.strip()) for p in pages)
    text = "\n\n".join(f"[page {i + 1}]\n{p}" for i, p in enumerate(pages) if p.strip())
    return text, {"method": method, "pages": len(pages), "pages_with_text": nonempty,
                  "ocr_used": False, "layout_and_images_not_extracted": True}


def extract(raw: bytes, path: str) -> tuple[str | None, dict[str, Any]]:
    reason = excluded_path(path)
    if reason:
        return None, {"status": "excluded", "reason": reason}
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return None, {"status": "excluded", "reason": "image_no_ocr_local_original_preserved"}
    if suffix in BINARY_SUFFIXES:
        return None, {"status": "excluded", "reason": "binary_or_legacy_office_no_safe_text_reader"}
    if suffix in {".zip", ".gz", ".tar", ".bz2", ".7z", ".rar"}:
        return None, {"status": "excluded", "reason": "archive_container_handled_separately"}
    try:
        if suffix in {".docx", ".xlsx", ".pptx"}:
            content, meta = office_text(raw, suffix)
        elif suffix == ".pdf":
            content, meta = pdf_text(raw)
        elif suffix in TEXT_SUFFIXES or not suffix:
            content, enc = decode_text(raw)
            meta = {"method": "strict_text_decode_no_execution", "encoding": enc}
            if suffix in {".json", ".ipynb", ".map"}:
                try:
                    json.loads(content)
                    meta["json_parse_valid"] = True
                except (ValueError, RecursionError):
                    meta.update(json_parse_valid=False, original_text_preserved=True)
            elif suffix == ".jsonl":
                lines = content.splitlines()
                failures = []
                for no, line in enumerate(lines, 1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except (ValueError, RecursionError):
                        failures.append(no)
                meta.update(jsonl_lines=len(lines), jsonl_invalid_lines=failures,
                            jsonl_parse_valid=not failures)
        else:
            return None, {"status": "excluded", "reason": "unsupported_format_original_preserved"}
    except Exception as exc:
        # Exception messages can quote original source; keep only safe class/reason.
        reason = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else type(exc).__name__
        return None, {"status": "unextractable", "reason": reason}
    if not content.strip():
        return None, dict(meta, status="empty", reason="no_text_layer_or_empty_text")
    return content, dict(meta, status="extracted")


class Exporter:
    def __init__(self, output: Path, bundle: Path):
        self.output = output
        self.bundle = bundle
        self.stats: Counter = Counter()
        self.statuses: Counter = Counter()
        self.formats: Counter = Counter()
        self.reasons: Counter = Counter()
        self.content_hashes: Counter = Counter()
        self.source_hashes: Counter = Counter()
        self.dependencies: dict[tuple[str, str], dict[str, Any]] = {}
        self.runtime_member_formats: Counter = Counter()

    def emit(self, row: dict[str, Any], raw: bytes, text_out, manifest_out) -> None:
        path = row["logical_path"]
        suffix = PurePosixPath(path).suffix.lower() or "[no_extension]"
        content, derivation = extract(raw, path)
        support_id = digest((path + "\0" + row["source_sha256"] + "\0" + row["sha256"]).encode("utf-8"))[:32]
        wrapper = {"support_id": support_id, "logical_path": path,
                   "source_sha256": row["source_sha256"], "extraction_input_sha256": row["sha256"],
                   "format": suffix.lstrip("."), "derivation_scope": dict(derivation, source_scope=row["scope"]),
                   "training_use": TRAINING_USE, "publication_status": WORK_STATUS,
                   "human_gold": False, "independent_sft_sample": False}
        manifest = dict(wrapper, input_bytes=len(raw), credential_redacted_in_old_bundle=row.get("credential_redacted", False),
                        entry_kind=row.get("entry_kind", "source_file"), content_bytes=0)
        self.stats["entries_seen"] += 1
        self.statuses[derivation["status"]] += 1
        self.formats[suffix] += 1
        self.source_hashes[row["sha256"]] += 1
        if content is not None:
            text_bytes = content.encode("utf-8")
            manifest.update(content_bytes=len(text_bytes), content_characters=len(content),
                            content_sha256=digest(text_bytes))
            wrapper["content"] = content
            text_out.write(compact(wrapper) + "\n")
            self.stats["text_records"] += 1
            self.stats["content_bytes"] += len(text_bytes)
            self.stats["content_characters"] += len(content)
            self.content_hashes[manifest["content_sha256"]] += 1
        else:
            self.reasons[derivation.get("reason", "unknown")] += 1
        manifest_out.write(compact(manifest) + "\n")

    def members(self, row: dict[str, Any], raw: bytes, text_out, manifest_out, members_out) -> None:
        path = row["logical_path"]
        if path.lower().endswith((".tar.gz", ".tgz")):
            # This old environment snapshot includes ABI-specific libraries and
            # third-party test data; none is WRD source evidence or ARM64 runtime.
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r|gz") as tar:
                for item in tar:
                    self.stats["runtime_archive_members"] += 1
                    suffix = PurePosixPath(item.name).suffix.lower() or "[no_extension]"
                    self.runtime_member_formats[suffix] += 1
                    meta = {"parent_support_path": path, "parent_sha256": row["sha256"],
                            "member_path": item.name, "bytes": item.size, "is_file": item.isfile(),
                            "format": suffix,
                            "kind": "directory" if item.isdir() else "file" if item.isfile() else "link_or_other",
                            "status": "controlled_not_training_evidence",
                            "reason": "vendored_runtime_dependencies_and_third_party_tests_excluded",
                            "portable_to_spark_arm64": False}
                    if item.isfile():
                        stream = tar.extractfile(item)
                        if stream is not None:
                            if item.name.endswith(".dist-info/METADATA") and item.size < MAX_XML_BYTES:
                                payload = stream.read()
                                meta["member_sha256"] = digest(payload)
                            else:
                                member_hash = sha256()
                                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                    member_hash.update(chunk)
                                meta["member_sha256"] = member_hash.hexdigest()
                                payload = None
                        else:
                            payload = None
                        if payload is not None:
                            header = BytesParser().parsebytes(payload, headersonly=True)
                            name, version = header.get("Name", ""), header.get("Version", "")
                            if re.fullmatch(r"[A-Za-z0-9_.-]+", name) and re.fullmatch(r"[A-Za-z0-9_.+!-]+", version):
                                self.dependencies[(name.lower(), version)] = {
                                    "name": name, "version": version,
                                    "requires_dist": header.get_all("Requires-Dist", []),
                                    "metadata_sha256": digest(payload), "source_archive_sha256": row["sha256"],
                                    "purpose": "historical_environment_inventory_not_spark_install_lock"}
                                meta["metadata_sha256"] = digest(payload)
                    members_out.write(compact(meta) + "\n")
            return
        if not path.lower().endswith(".zip"):
            return
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                for no, info in enumerate(z.infolist()):
                    self.stats["zip_members"] += 1
                    member_path = PurePosixPath(info.filename.replace("\\", "/"))
                    safe = not member_path.is_absolute() and ".." not in member_path.parts and not re.match(r"^[A-Za-z]:", str(member_path))
                    meta = {"parent_support_path": path, "parent_sha256": row["sha256"],
                            "member_path": info.filename, "member_index": no, "bytes": info.file_size,
                            "compressed_bytes": info.compress_size, "kind": "directory" if info.is_dir() else "file"}
                    reason = None
                    if not safe:
                        reason = "unsafe_member_path_not_read"
                    elif info.is_dir():
                        reason = "directory_entry"
                    elif info.flag_bits & 1:
                        reason = "encrypted_archive_member_not_decrypted"
                    elif info.file_size > MAX_ARCHIVE_TEXT_BYTES:
                        reason = "archive_member_over_size_limit"
                    if reason:
                        meta.update(status="excluded", reason=reason)
                    else:
                        payload = z.read(info)
                        child = {"logical_path": path + "::" + info.filename, "sha256": digest(payload),
                                 "source_sha256": digest(payload), "scope": "archive_member_of_original_input_material",
                                 "entry_kind": "archive_member"}
                        self.emit(child, payload, text_out, manifest_out)
                        meta.update(status="member_handled_by_text_extractor", member_sha256=child["sha256"])
                    members_out.write(compact(meta) + "\n")
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            members_out.write(compact({"parent_support_path": path, "parent_sha256": row["sha256"],
                "status": "unextractable", "reason": type(exc).__name__}) + "\n")

    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        if self.output.is_relative_to(self.bundle):
            raise ValueError("output_must_not_be_inside_immutable_source_bundle")
        archive = self.bundle / "archive"
        index = archive / "file_index.jsonl"
        source_index_before = file_sha(index)
        retained = self.bundle / "skills" / "retained29"
        retained_before = {p.relative_to(retained).as_posix(): file_sha(p)
                           for p in sorted(retained.rglob("*")) if p.is_file()}
        self.output.mkdir(parents=True, exist_ok=True)
        groups: Counter = Counter()
        with gzip_writer(self.output / "support.text.jsonl.gz") as text_out, \
                gzip_writer(self.output / "support.manifest.jsonl.gz") as manifest_out, \
                gzip_writer(self.output / "archive_members.manifest.jsonl.gz") as members_out:
            with index.open(encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    if not row["logical_path"].startswith(("sources/", "source_materials/")):
                        continue
                    logical = PurePosixPath(row["logical_path"])
                    if logical.is_absolute() or ".." in logical.parts:
                        raise ValueError("unsafe_logical_path")
                    obj = (archive / row["object"]).resolve()
                    obj.relative_to((archive / "objects").resolve())
                    raw = obj.read_bytes()
                    if digest(raw) != row["sha256"] or len(raw) != row["bytes"]:
                        raise ValueError("archive_object_integrity_failure")
                    self.stats["verified_input_bytes"] += len(raw)
                    self.stats["archive_source_files"] += 1
                    groups[logical.parts[0]] += 1
                    self.emit(row, raw, text_out, manifest_out)
                    self.members(row, raw, text_out, manifest_out, members_out)
                    if self.stats["archive_source_files"] % 500 == 0:
                        print(compact({"progress_source_files": self.stats["archive_source_files"],
                                       "text_records": self.stats["text_records"]}), flush=True)
            for rel, expected in retained_before.items():
                p = retained / rel
                raw = p.read_bytes()
                if digest(raw) != expected:
                    raise ValueError("retained_file_changed_while_reading")
                row = {"logical_path": "retained29/" + rel, "sha256": expected, "source_sha256": expected,
                       "scope": "retained_skill_snapshot_not_independent_conversation"}
                self.emit(row, raw, text_out, manifest_out)
                groups["retained29"] += 1
                self.stats["verified_input_bytes"] += len(raw)
        retained_after = {p.relative_to(retained).as_posix(): file_sha(p)
                          for p in sorted(retained.rglob("*")) if p.is_file()}
        source_index_after = file_sha(index)
        if source_index_before != source_index_after or retained_before != retained_after:
            raise ValueError("source_index_or_retained_files_changed")
        deps = sorted(self.dependencies.values(), key=lambda r: (r["name"].lower(), r["version"]))
        (self.output / "historical_dependencies.json").write_text(json.dumps({
            "purpose": "historical_inventory_only; resolve_fresh_ARM64_dependencies_for_Spark",
            "not_spark_install_lock": True, "dependencies": deps}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (self.output / "historical_requirements_inventory.txt").write_text(
            "# Historical environment inventory only. Do not install as a Spark lock.\n"
            "# Old binary/venv snapshots are not portable to ARM64 GB10.\n" +
            "\n".join(f"{r['name']}=={r['version']}" for r in deps) + "\n", encoding="utf-8")
        # The same complete dependency JSON also enters the unified privacy pass.
        # A deterministic concatenated gzip member avoids rereading the text file.
        dependency_raw = (self.output / "historical_dependencies.json").read_bytes()
        dependency_sha = digest(dependency_raw)
        with gzip_writer(self.output / "support.text.jsonl.gz", append=True) as text_out, \
                gzip_writer(self.output / "support.manifest.jsonl.gz", append=True) as manifest_out:
            self.emit({"logical_path": "derived/historical_dependencies.json", "sha256": dependency_sha,
                       "source_sha256": dependency_sha, "entry_kind": "derived_metadata_inventory",
                       "scope": "historical_runtime_metadata_inventory_not_primary_source"},
                      dependency_raw, text_out, manifest_out)
        self.stats["derived_metadata_records"] += 1
        report = {"schema_version": SCHEMA, "status": "PASS", "input_groups": dict(groups),
                  "counts": dict(self.stats), "statuses": dict(self.statuses), "formats": dict(self.formats),
                  "exclusion_or_failure_reasons": dict(self.reasons),
                  "unique_extraction_input_sha256": len(self.source_hashes),
                  "duplicate_input_identity_extra_paths": sum(n - 1 for n in self.source_hashes.values()),
                  "unique_extracted_content_sha256": len(self.content_hashes),
                  "duplicate_extracted_content_extra_paths": sum(n - 1 for n in self.content_hashes.values()),
                  "historical_dependency_count": len(deps),
                  "runtime_archive_member_formats": dict(self.runtime_member_formats),
                  "source_index_sha256_before": source_index_before, "source_index_sha256_after": source_index_after,
                  "retained_file_count": len(retained_before), "retained_hashes_unchanged": retained_before == retained_after,
                  "source_object_sha_and_size_verified": True, "training_started": False, "model_calls": 0,
                  "network_calls": 0, "gpu_used": False, "ocr_used": False,
                  "binary_or_original_sources_published": False, "safe_to_publish_as_is": False,
                  "publication_status": WORK_STATUS, "human_gold": 0,
                  "training_use": TRAINING_USE, "independent_sft_samples_added": 0,
                  "limitations": ["Corpus and per-conversation views preserve distinct paths; counts are support records, not independent tasks.",
                    "Office XML and PDF text extraction omit layout/images/embedded objects; formulas are not evaluated.",
                    "Legacy binary Office, images, media, encrypted documents and unextractable items retain local originals and manifest gaps.",
                    "Historical vendored runtime and third-party test data are inventoried, not exported as WRD evidence.",
                    "All extracted text and paths require separate privacy discovery/freeze/clean/public-or-hold review."],
                  "elapsed_seconds": round(time.monotonic() - started, 3)}
        report["outputs"] = {p.name: {"sha256": file_sha(p), "bytes": p.stat().st_size}
                             for p in sorted(self.output.iterdir()) if p.is_file() and p.name != "support_extraction_report.json"}
        (self.output / "support_extraction_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = Exporter(args.output.resolve(), args.bundle.resolve()).run()
    print(compact({"status": report["status"], "input_groups": report["input_groups"],
                   "counts": report["counts"], "statuses": report["statuses"],
                   "elapsed_seconds": report["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
