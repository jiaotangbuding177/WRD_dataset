"""Validate, stream-package, and safely unpack an offline WRD training bundle.

This tool never invokes a model, executes archived programs, or changes sources.
Only Python's standard library is required. Run ``python delivery.py --help``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import time
import zlib


FORMAT = "wrd-training-package-v1"
PART_BYTES = 256 * 1024 * 1024
BLOCK_BYTES = 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
WINDOWS_DEVICE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    temporary.replace(path)


def strict_json(text: str) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError("non-JSON numeric constant: " + value)

    return json.loads(text, parse_constant=reject_constant)


def safe_relative(value: object) -> str:
    """Check POSIX archive paths, including Windows drive/ADS/device pitfalls."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("path must be a nonempty POSIX relative path")
    value = value[:-1] if value.endswith("/") else value
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("absolute, empty, or traversal path component")
    if any(":" in part or part.endswith((" ", ".")) or WINDOWS_DEVICE.fullmatch(part) for part in parts):
        raise ValueError("unsafe Windows path component")
    if PurePosixPath(value).is_absolute():
        raise ValueError("absolute path is forbidden")
    return value


def under(root: Path, relative: object) -> Path:
    relative = safe_relative(relative)
    target = root.joinpath(*relative.split("/"))
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("path resolves outside requested directory")
    return target


def is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def entries(root: Path):
    """Walk deterministically without following links or silently losing files."""
    def on_error(error: OSError) -> None:
        raise error

    for directory, folders, files in os.walk(root, followlinks=False, onerror=on_error):
        folders.sort()
        files.sort()
        base = Path(directory)
        for name in folders:
            path = base / name
            if is_link(path):
                raise ValueError("symbolic links or reparse points are forbidden: " + str(path))
            yield path, True
        for name in files:
            path = base / name
            if is_link(path) or not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError("only regular files can be packaged: " + str(path))
            yield path, False


def file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(BLOCK_BYTES):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


class PartWriter(io.RawIOBase):
    """Write one continuous compressed stream into bounded files."""

    def __init__(self, dist: Path, part_bytes: int = PART_BYTES):
        super().__init__()
        if part_bytes <= 0:
            raise ValueError("part size must be positive")
        self.dist = dist
        self.part_bytes = part_bytes
        self.parts: list[dict] = []
        self.handle = None
        self.digest = None
        self.size = 0
        self.total_bytes = 0

    def writable(self) -> bool:
        return True

    def _finish(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.parts.append({"path": "dist/" + self.path.name, "bytes": self.size, "sha256": self.digest.hexdigest()})
            self.handle = None

    def write(self, data) -> int:
        if self.closed:
            raise ValueError("write to closed part stream")
        view = memoryview(data)
        original_size = len(view)
        while view:
            if self.handle is None:
                self.path = self.dist / f"wrd-training-bundle-v1.tar.gz.part{len(self.parts) + 1:04d}"
                self.handle = self.path.open("xb")
                self.digest = hashlib.sha256()
                self.size = 0
            take = min(len(view), self.part_bytes - self.size)
            block = view[:take]
            self.handle.write(block)
            self.digest.update(block)
            self.size += take
            self.total_bytes += take
            view = view[take:]
            if self.size == self.part_bytes:
                self._finish()
        return original_size

    def close(self) -> None:
        if not self.closed:
            self._finish()
        super().close()


class PartReader(io.RawIOBase):
    """Read verified parts as a single stream without joining them on disk."""

    def __init__(self, paths: list[Path]):
        super().__init__()
        self.paths = iter(paths)
        self.handle = None

    def readable(self) -> bool:
        return True

    def readinto(self, destination) -> int:
        view = memoryview(destination)
        done = 0
        while done < len(view):
            if self.handle is None:
                path = next(self.paths, None)
                if path is None:
                    break
                self.handle = path.open("rb")
            got = self.handle.readinto(view[done:])
            if got:
                done += got
            else:
                self.handle.close()
                self.handle = None
        return done

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None
        super().close()


def require_empty(path: Path) -> None:
    if path.exists() and (not path.is_dir() or is_link(path) or any(path.iterdir())):
        raise ValueError("destination must not exist or must be an empty directory: " + str(path))


def package(bundle: Path, release: Path, *, part_bytes: int = PART_BYTES) -> dict:
    bundle, release = bundle.absolute(), release.absolute()
    if not bundle.is_dir() or is_link(bundle):
        raise ValueError("bundle must be an existing real directory")
    if release.resolve().is_relative_to(bundle.resolve()) or bundle.resolve().is_relative_to(release.resolve()):
        raise ValueError("bundle and release directories must not contain each other")
    require_empty(release)
    release.mkdir(parents=True, exist_ok=True)
    dist = release / "dist"
    dist.mkdir()
    files = directories = size = 0
    writer = PartWriter(dist, part_bytes)
    try:
        with gzip.GzipFile(filename="", fileobj=writer, mode="wb", compresslevel=3, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT, dereference=True) as archive:
                for path, is_directory in entries(bundle):
                    relative = safe_relative(path.relative_to(bundle).as_posix())
                    info = archive.gettarinfo(str(path), arcname=relative)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.pax_headers = {}
                    if is_directory:
                        archive.addfile(info)
                        directories += 1
                    else:
                        before = path.stat()
                        with path.open("rb") as source:
                            archive.addfile(info, source)
                        after = path.stat()
                        if info.size != before.st_size or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                            raise ValueError("bundle changed while packaging: " + relative)
                        files += 1
                        size += info.size
                    archive.members.clear()
                    if files and files % 10000 == 0 and not is_directory:
                        print(json.dumps({"phase": "package", "files": files, "input_bytes": size, "compressed_bytes": writer.total_bytes}), flush=True)
    finally:
        writer.close()
    for name in ("README.md", "DATA_CARD.md", "PLAN.md", "summary.json", "VALIDATION.json"):
        source = bundle / name
        if source.is_file():
            shutil.copy2(source, release / name)
    scripts = Path(__file__).resolve().parent
    tools = release / "tools"
    tools.mkdir()
    # Copy the complete resource tree too: native schemas and their provenance
    # are required to interpret the historical messages without guessing tools.
    for source, directory in entries(scripts):
        if directory or "__pycache__" in source.parts or source.suffix in (".pyc", ".pyo"):
            continue
        target = tools / source.relative_to(scripts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (release / ".gitattributes").write_text("dist/* filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")
    (release / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.cache/\n.venv/\nunpacked/\n", encoding="utf-8")
    manifest = {
        "format": FORMAT,
        "compression": "gzip",
        "container": "tar",
        "part_bytes": part_bytes,
        "bundle_files": files,
        "bundle_directories": directories,
        "bundle_bytes": size,
        "compressed_bytes": writer.total_bytes,
        "parts": writer.parts,
        "unpack": "python tools/delivery.py unpack --release . --output ../wrd-training-unpacked",
        "note": "Concatenated parts form one tar.gz stream; keep this manifest and all parts together. The original bundle is not modified.",
    }
    json_write(release / "package_manifest.json", manifest)
    return manifest


def unpack(release: Path, output: Path) -> dict:
    release, output = release.absolute(), output.absolute()
    require_empty(output)
    manifest = strict_json((release / "package_manifest.json").read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise ValueError("unsupported package manifest")
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("manifest has no parts")
    paths = []
    for number, part in enumerate(parts, 1):
        if not isinstance(part, dict):
            raise ValueError("invalid part record")
        expected_name = f"dist/wrd-training-bundle-v1.tar.gz.part{number:04d}"
        if part.get("path") != expected_name or not SHA256.fullmatch(str(part.get("sha256", ""))):
            raise ValueError("part order, path, or digest is invalid")
        path = under(release, part["path"])
        if not path.is_file() or is_link(path):
            raise ValueError("missing or linked part: " + expected_name)
        digest, size = file_digest(path)
        if size != part.get("bytes") or digest != part["sha256"]:
            raise ValueError("part SHA256/size mismatch: " + expected_name)
        paths.append(path)
        print(json.dumps({"phase": "verify_part", "part": number, "parts": len(parts), "bytes": size}), flush=True)
    if sum(part["bytes"] for part in parts) != manifest.get("compressed_bytes"):
        raise ValueError("compressed size total mismatch")
    output.mkdir(parents=True, exist_ok=True)
    root = output.resolve()
    files = directories = size = 0
    seen = set()
    with PartReader(paths) as source:
        with gzip.GzipFile(fileobj=source, mode="rb") as compressed:
            with tarfile.open(fileobj=compressed, mode="r|") as archive:
                for member in archive:
                    relative = safe_relative(member.name)
                    key = relative.casefold() if os.name == "nt" else relative
                    if key in seen:
                        raise ValueError("duplicate tar member: " + relative)
                    seen.add(key)
                    if not (member.isdir() or member.isfile()):
                        raise ValueError("links, devices, and special tar entries are forbidden: " + relative)
                    target = under(root, relative)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        directories += 1
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        extracted = archive.extractfile(member)
                        if extracted is None:
                            raise ValueError("tar file has no data: " + relative)
                        written = 0
                        with extracted, target.open("xb") as destination:
                            while block := extracted.read(BLOCK_BYTES):
                                destination.write(block)
                                written += len(block)
                        if written != member.size:
                            raise ValueError("tar member truncated: " + relative)
                        files += 1
                        size += written
                    archive.members.clear()
            # Consume the gzip trailer too, validating CRC and stream length.
            while compressed.read(BLOCK_BYTES):
                pass
    if files != manifest.get("bundle_files") or size != manifest.get("bundle_bytes") or directories != manifest.get("bundle_directories"):
        raise ValueError("unpacked file, directory, or byte count differs from manifest")
    return {"status": "PASS", "files": files, "directories": directories, "bytes": size, "output": str(output)}


def validate(bundle: Path) -> dict:
    bundle = bundle.absolute()
    if not bundle.is_dir() or is_link(bundle):
        raise ValueError("bundle must be an existing real directory")
    errors: list[dict] = []
    error_count = 0
    counts = {"index_rows": 0, "unique_objects": 0, "object_bytes": 0, "jsonl_files": 0, "jsonl_gzip_files": 0, "jsonl_rows": 0, "retained_skill_files": 0}

    def error(code: str, path: object, detail: object = "") -> None:
        nonlocal error_count
        error_count += 1
        if len(errors) < 1000:
            errors.append({"code": code, "path": str(path), "detail": str(detail)[:300]})

    logical_seen = set()
    object_expectations = {}
    index = bundle / "archive/file_index.jsonl"
    try:
        with index.open(encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                try:
                    row = strict_json(line)
                    if not isinstance(row, dict):
                        raise ValueError("index row is not an object")
                    logical = safe_relative(row.get("logical_path"))
                    if logical in logical_seen:
                        raise ValueError("duplicate logical_path")
                    logical_seen.add(logical)
                    relative = safe_relative(row.get("object"))
                    digest = row.get("sha256")
                    size = row.get("bytes")
                    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                        raise ValueError("invalid sha256")
                    if type(size) is not int or size < 0:
                        raise ValueError("bytes must be a nonnegative integer")
                    if relative != "objects/" + digest[:2] + "/" + digest:
                        raise ValueError("object path does not match content-addressed SHA256")
                    expectation = (digest, size)
                    if relative in object_expectations and object_expectations[relative] != expectation:
                        raise ValueError("conflicting object size or digest")
                    object_expectations[relative] = expectation
                    counts["index_rows"] += 1
                except (ValueError, TypeError, KeyError) as failure:
                    error("index_row", "archive/file_index.jsonl:" + str(line_number), failure)
    except (OSError, UnicodeError) as failure:
        error("index_read", index.relative_to(bundle), failure)
    actual_objects = set()
    objects = bundle / "archive/objects"
    if not objects.is_dir():
        error("objects_missing", "archive/objects")
    try:
        for path, directory in entries(objects):
            if directory:
                continue
            relative = path.relative_to(bundle / "archive").as_posix()
            actual_objects.add(relative)
            expected = object_expectations.get(relative)
            if expected is None:
                error("unreferenced_object", relative)
                continue
            digest, size = file_digest(path)
            counts["unique_objects"] += 1
            counts["object_bytes"] += size
            if (digest, size) != expected:
                error("object_mismatch", relative, "actual SHA256 or byte length differs from index")
            if counts["unique_objects"] % 10000 == 0:
                print(json.dumps({"phase": "validate_objects", "objects": counts["unique_objects"]}), flush=True)
    except (OSError, ValueError) as failure:
        error("objects_read", "archive/objects", failure)
    for missing in sorted(set(object_expectations) - actual_objects):
        error("missing_object", missing)
    verification = bundle / "catalog/retained_skills_verification.json"
    try:
        record = strict_json(verification.read_text(encoding="utf-8-sig"))
        expected = record["sha256"]
        if not isinstance(expected, dict) or len(expected) != 154 or record.get("expected_files") != 154 or record.get("actual_files") != 154 or record.get("matches_original_manifest") is not True:
            error("retained_manifest", verification.relative_to(bundle), "expected verified 154-file original manifest")
        retained_root = bundle / "skills/retained29"
        actual = {}
        for path, directory in entries(retained_root):
            if directory:
                continue
            relative = safe_relative(path.relative_to(retained_root).as_posix())
            actual[relative] = file_digest(path)[0]
        counts["retained_skill_files"] = len(actual)
        if actual != expected:
            error("retained_skills_mismatch", "skills/retained29", "file set or SHA256 differs from retained skill manifest")
        if len(actual) != 154:
            error("retained_files_count", "skills/retained29", len(actual))
    except (OSError, ValueError, TypeError, KeyError) as failure:
        error("retained_read", verification.relative_to(bundle), failure)
    try:
        for path, directory in entries(bundle):
            if directory or not path.name.lower().endswith((".jsonl", ".jsonl.gz")):
                continue
            counts["jsonl_files"] += 1
            compressed = path.name.lower().endswith(".jsonl.gz")
            counts["jsonl_gzip_files"] += int(compressed)
            try:
                source_file = gzip.open(path, mode="rt", encoding="utf-8-sig") if compressed else path.open(encoding="utf-8-sig")
                with source_file as source:
                    for line_number, line in enumerate(source, 1):
                        try:
                            strict_json(line)
                            counts["jsonl_rows"] += 1
                        except (ValueError, TypeError) as failure:
                            error("jsonl_parse", path.relative_to(bundle).as_posix() + ":" + str(line_number), failure)
            except (OSError, UnicodeError, EOFError, zlib.error) as failure:
                error("jsonl_read", path.relative_to(bundle), failure)
    except (OSError, ValueError) as failure:
        error("bundle_walk", bundle, failure)
    report = {"format": "wrd-training-validation-v1", "status": "PASS" if not error_count else "FAIL", "validated_at_unix": int(time.time()), "counts": counts, "error_count": error_count, "errors": errors, "errors_truncated": error_count > len(errors), "new_model_calls": 0}
    json_write(bundle / "VALIDATION.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("package", help="stream a complete bundle into 256 MiB Git LFS parts")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--release", type=Path, required=True)
    p = commands.add_parser("unpack", help="verify every part before safe streaming extraction")
    p.add_argument("--release", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("validate", help="check object archive, retained skill bytes, and every JSONL")
    p.add_argument("--bundle", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "package":
            result = package(arguments.bundle, arguments.release)
            printable = {key: value for key, value in result.items() if key != "parts"}
            printable["parts"] = len(result["parts"])
        elif arguments.command == "unpack":
            result = printable = unpack(arguments.release, arguments.output)
        else:
            result = validate(arguments.bundle)
            printable = {key: value for key, value in result.items() if key != "errors"}
        print(json.dumps(printable, ensure_ascii=False), flush=True)
        return 1 if result.get("status") == "FAIL" else 0
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError, EOFError) as failure:
        print(json.dumps({"status": "FAIL", "error": str(failure)}, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
