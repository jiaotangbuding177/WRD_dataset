"""Second-pass credential scrub of an already closed, generated WRD bundle.

Original enterprise materials and model traces are never changed. Replaced CAS
objects and the old logical index are retained outside the deliverable bundle.
This is an offline data transformation, not an Agent or training loop.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from functools import lru_cache
import re
import shutil
import stat
import sys
import time
import zlib

import build


SHA = re.compile(r"[a-f0-9]{64}\Z")
CREDENTIAL_FILES = {
    "credentials", "credentials.json", "credentials.yaml", "credentials.yml",
    "credentials.toml", "credential.json", "auth.json", "auth-profiles.json",
    "model_credentials.json", "model-credentials.json", "secrets.json",
    "secrets.yaml", "secrets.yml", "secrets.toml",
}
CREDENTIAL_STEMS = {"credentials", "credential", "auth-profiles", "model_credentials", "model-credentials", "secrets"}


def linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def require_plain(path: Path, root: Path) -> None:
    absolute = path.absolute()
    if not absolute.resolve().is_relative_to(root.resolve()):
        raise ValueError("refusing path outside declared directory: " + str(path))
    relative = absolute.relative_to(root.absolute())
    current = root.absolute()
    if current.exists() and linked(current):
        raise ValueError("linked directory is forbidden: " + str(current))
    for component in relative.parts:
        current = current / component
        if current.exists() and linked(current):
            raise ValueError("linked path is forbidden: " + str(current))


def logical_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid logical path")
    parts = value.split("/")
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise ValueError("unsafe logical path")
    return value


def excluded_logical(value: str) -> bool:
    parts = [part.lower() for part in PurePosixPath(value).parts]
    return any(part == ".env" or part.startswith(".env.") or part in CREDENTIAL_FILES or PurePosixPath(part).stem in CREDENTIAL_STEMS for part in parts)


@lru_cache(maxsize=131072)
def object_path(objects: Path, relative: object, digest: object) -> Path:
    if not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise ValueError("index has invalid CAS SHA256")
    expected = "objects/" + digest[:2] + "/" + digest
    if relative != expected:
        raise ValueError("refusing a non-CAS object path")
    result = objects / digest[:2] / digest
    require_plain(result, objects)
    return result


def rows(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except ValueError as error:
                raise ValueError("logical index is not complete JSONL at line " + str(number)) from error
            if not isinstance(value, dict):
                raise ValueError("logical index row is not an object")
            yield value


def unknown_jsonl(raw: bytes) -> int:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        return 1
    bad = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            bad += 1
    return bad


def unique_outside(base: Path) -> Path:
    if not base.exists():
        return base
    for number in range(2, 100000):
        candidate = base.with_name(base.stem + ".run" + str(number) + base.suffix)
        if not candidate.exists():
            return candidate
    raise ValueError("too many prior outside backups")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def scrub_derived(bundle: Path, index: Path, counts: Counter) -> list[dict]:
    unknown = []
    objects = bundle / "archive/objects"
    for directory, folders, names in os.walk(bundle, followlinks=False):
        base = Path(directory)
        retained_folders = []
        for name in folders:
            child = base / name
            require_plain(child, bundle)
            if child != objects:
                retained_folders.append(name)
        folders[:] = retained_folders
        for name in names:
            path = base / name
            if path == index or path == bundle / "summary/credential_scrub.json":
                continue
            compressed = name.lower().endswith(".jsonl.gz")
            if not compressed and path.suffix.lower() not in (".json", ".jsonl"):
                continue
            require_plain(path, bundle)
            counts["derived_files_scanned"] += 1
            if compressed:
                temporary = path.with_name(path.name + ".scrubbing.tmp")
                changed = False
                malformed = 0
                try:
                    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as source:
                        with temporary.open("wb") as raw_output:
                            with gzip.GzipFile(filename="", fileobj=raw_output, mode="wb", mtime=0) as compressed_output:
                                for line in source:
                                    if not line.strip():
                                        cleaned = line
                                    else:
                                        try:
                                            value = json.loads(line)
                                            sanitized = build.clean_value(value)
                                            cleaned = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")) + "\n" if sanitized != value else line
                                        except ValueError:
                                            malformed += 1
                                            cleaned = build.clean_text(line)[0]
                                    changed |= cleaned != line
                                    compressed_output.write(cleaned.encode("utf-8"))
                    if changed:
                        temporary.replace(path)
                        counts["derived_files_changed"] += 1
                    else:
                        temporary.unlink()
                except (OSError, UnicodeError, EOFError, zlib.error):
                    if temporary.exists():
                        temporary.unlink()
                    # A damaged compressed stream cannot be losslessly rewritten.
                    # Keep its exact source bytes and report the unresolved scope.
                    unknown.append({"path": path.relative_to(bundle).as_posix(), "reason": "gzip_unreadable_preserved_without_claim_of_complete_scrub"})
                    continue
                if malformed:
                    unknown.append({"path": path.relative_to(bundle).as_posix(), "malformed_lines": malformed, "reason": "bad_jsonl_lines_preserved_with_text_only_scrub"})
            else:
                raw = path.read_bytes()
                malformed = unknown_jsonl(raw) if path.suffix.lower() == ".jsonl" else 0
                sanitized, _ = build.sanitized_bytes(path, raw)
                if sanitized != raw:
                    temporary = path.with_name(path.name + ".scrubbing.tmp")
                    temporary.write_bytes(sanitized)
                    temporary.replace(path)
                    counts["derived_files_changed"] += 1
                if malformed:
                    unknown.append({"path": path.relative_to(bundle).as_posix(), "malformed_lines": malformed, "reason": "bad_jsonl_lines_preserved_with_text_only_scrub"})
    return unknown


def sanitize(bundle: Path) -> dict:
    # The closed archive is immutable during this pass. Validate each unique
    # CAS path once rather than resolving the same path for 650k references;
    # move operations still perform their own fresh require_plain checks.
    object_path.cache_clear()
    bundle = bundle.absolute()
    if not bundle.is_dir() or linked(bundle):
        raise ValueError("bundle must be an existing real directory")
    archive = bundle / "archive"
    objects = archive / "objects"
    index = archive / "file_index.jsonl"
    require_plain(index, bundle)
    require_plain(objects, bundle)
    if not index.is_file() or not objects.is_dir():
        raise ValueError("complete archive index and objects directory are required")
    outside = bundle.parent.absolute()
    quarantine = outside / "local_sensitive_object_quarantine"
    require_plain(quarantine, outside)
    if quarantine.resolve().is_relative_to(bundle.resolve()):
        raise ValueError("quarantine must be outside the packaged bundle")
    contexts: dict[str, set[str]] = {}
    exclusions = []
    counts = Counter()
    for row in rows(index):
        counts["index_rows_before"] += 1
        logical = logical_path(row.get("logical_path"))
        object_path(objects, row.get("object"), row.get("sha256"))
        if excluded_logical(logical):
            exclusions.append({"logical_path": logical, "sha256": row["sha256"], "reason": "credential_or_environment_file_excluded"})
            continue
        # One payload may be referenced under multiple extensions. Apply each
        # distinct text interpretation so a JSON alias cannot escape redaction.
        suffix = Path(logical).suffix.lower()
        context = "payload" + suffix if suffix else PurePosixPath(logical).name
        contexts.setdefault(row["sha256"], set()).add(context)
    mapping = {}
    unknown = []
    for digest, interpretations in sorted(contexts.items()):
        source = object_path(objects, "objects/" + digest[:2] + "/" + digest, digest)
        if not source.is_file():
            raise ValueError("missing indexed CAS object: " + digest)
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("indexed CAS object SHA mismatch: " + digest)
        data = raw
        if "payload.jsonl" in interpretations:
            malformed = unknown_jsonl(raw)
            if malformed:
                unknown.append({"object_sha256": digest, "malformed_lines": malformed, "reason": "bad_jsonl_lines_preserved_with_text_only_scrub"})
        for interpretation in sorted(interpretations, key=lambda name: (not name.endswith(".json"), name)):
            data, _ = build.sanitized_bytes(Path(interpretation), data)
        new_digest = hashlib.sha256(data).hexdigest()
        changed = data != raw
        destination = object_path(objects, "objects/" + new_digest[:2] + "/" + new_digest, new_digest)
        if not destination.exists():
            destination.parent.mkdir(exist_ok=True)
            temporary = destination.with_name(destination.name + ".scrubbing.tmp")
            require_plain(temporary, objects)
            temporary.write_bytes(data)
            temporary.replace(destination)
        elif destination != source and hashlib.sha256(destination.read_bytes()).hexdigest() != new_digest:
            raise ValueError("existing replacement CAS object hash mismatch")
        mapping[digest] = {"sha256": new_digest, "object": "objects/" + new_digest[:2] + "/" + new_digest, "bytes": len(data), "changed": changed}
        counts["unique_objects_scanned"] += 1
        counts["unique_objects_changed"] += int(changed)
        if counts["unique_objects_scanned"] % 10000 == 0:
            print(json.dumps({"phase": "credential_scrub", "objects": counts["unique_objects_scanned"], "changed": counts["unique_objects_changed"]}), flush=True)
    temporary_index = index.with_name(index.name + ".scrubbing.tmp")
    referenced = set()
    with temporary_index.open("w", encoding="utf-8", newline="\n") as destination:
        for row in rows(index):
            logical = logical_path(row.get("logical_path"))
            if excluded_logical(logical):
                continue
            transformation = mapping[row["sha256"]]
            row.update({key: transformation[key] for key in ("sha256", "object", "bytes")})
            row["credential_redacted"] = bool(row.get("credential_redacted")) or transformation["changed"]
            # source_sha256/source_bytes continue to identify original source
            # material, not the transformed payload distributed in this bundle.
            destination.write(json.dumps(build.clean_value(row), ensure_ascii=False, separators=(",", ":")) + "\n")
            referenced.add(row["sha256"])
            counts["index_rows_after"] += 1
            counts["referenced_bytes_after"] += row["bytes"]
            counts["redacted_logical_files_after"] += int(row["credential_redacted"])
    backup = unique_outside(outside / "local_index_before_sanitize.jsonl")
    require_plain(backup, outside)
    if backup.resolve().is_relative_to(bundle.resolve()):
        raise ValueError("index backup must be outside bundle")
    shutil.copy2(index, backup)
    temporary_index.replace(index)
    quarantine.mkdir(exist_ok=True)
    interrupted_tail = archive / "interrupted_index_tail.bin"
    if interrupted_tail.exists():
        require_plain(interrupted_tail, archive)
        if not interrupted_tail.is_file():
            raise ValueError("interrupted index backup is not a regular file")
        target = unique_outside(quarantine / "interrupted_index_tail.bin")
        require_plain(target, quarantine)
        counts["quarantined_interrupted_index_tail_bytes"] += interrupted_tail.stat().st_size
        interrupted_tail.rename(target)
        counts["quarantined_interrupted_index_tails"] += 1
    for prefix in sorted(objects.iterdir()):
        if not prefix.is_dir() or linked(prefix) or not re.fullmatch(r"[a-f0-9]{2}", prefix.name):
            raise ValueError("refusing unexpected non-CAS entry in object store")
        for source in sorted(prefix.iterdir()):
            digest = source.name
            if not SHA.fullmatch(digest) or digest[:2] != prefix.name or not source.is_file():
                raise ValueError("refusing unexpected non-CAS entry in bucket")
            require_plain(source, objects)
            if digest in referenced:
                counts["unique_objects_after"] += 1
                counts["unique_bytes_after"] += source.stat().st_size
                continue
            # Only this run's generated CAS files move, and only after the new
            # atomic index is in place and proves that no logical row needs them.
            target = unique_outside(quarantine / digest[:2] / digest)
            require_plain(target, quarantine)
            target.parent.mkdir(exist_ok=True)
            counts["quarantined_object_bytes"] += source.stat().st_size
            source.rename(target)
            counts["quarantined_objects"] += 1
    unknown.extend(scrub_derived(bundle, index, counts))
    report = {
        "schema_version": "wrd-credential-scrub-v1",
        "completed_at_unix": int(time.time()),
        "status": "COMPLETE_WITH_UNKNOWN_TEXT_SCOPE" if unknown else "COMPLETE",
        "counts": dict(counts),
        "excluded_logical_files": exclusions,
        "unknown": unknown,
        "original_index_backup_outside_bundle": str(backup),
        "quarantined_generated_objects_outside_bundle": str(quarantine),
        "source_materials_modified": False,
        "claim": "Known credential patterns and structured keys scrubbed; this is not a claim of complete personal-data anonymization or of identifying every possible secret.",
    }
    write_json(bundle / "summary/credential_scrub.json", report)
    summary_path = bundle / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        if isinstance(summary, dict):
            archive_summary = summary.get("archive")
            if isinstance(archive_summary, dict):
                archive_summary.update({"logical_files": counts["index_rows_after"], "referenced_bytes": counts["referenced_bytes_after"], "redacted_logical_files": counts["redacted_logical_files_after"], "unique_objects": counts["unique_objects_after"], "unique_bytes": counts["unique_bytes_after"]})
            summary["credential_scrub"] = {"report": "summary/credential_scrub.json", "status": report["status"], "excluded_logical_files": len(exclusions), "changed_unique_objects": counts["unique_objects_changed"]}
            write_json(summary_path, summary)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        report = sanitize(arguments.bundle)
        print(json.dumps({"status": report["status"], "counts": report["counts"], "excluded_logical_files": len(report["excluded_logical_files"]), "unknown_scopes": len(report["unknown"])}), flush=True)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
