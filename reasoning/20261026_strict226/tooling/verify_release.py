"""Incremental remote Git/LFS verification after an explicit final push.

Writing or importing this file does not access the network. The parent must
explicitly invoke --commit FULL_SHA after uploading the final release. Reuse
the prior independent bare repository and LFS object cache; request LFS fetch
only for reasoning/20261026_strict226/**. Never read a decryption key, decrypt
ciphertext, initialize an empty cache, or overwrite any v4 verification report.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
V4 = ROOT / "output/20261025_wrd_reasoning_recovery_v4"
OUT = ROOT / "output/20261026_wrd_strict226_expansion"
LOCAL = ROOT / "output/20261025_wrd_training_dataset/git_release"
BARE = V4 / "outputv4remote_verify.git"
CACHE = V4 / "outputv4remote_lfs_empty"
OLD_RECEIPT = V4 / "REMOTE_GIT_VERIFICATION.final_708bd77.json"
REPORT = OUT / "REMOTE_GIT_VERIFICATION.json"
PROGRESS = OUT / "REMOTE_GIT_VERIFICATION_PROGRESS.json"
MANIFEST_PATH = "reasoning/20261025/MANIFEST.json"
NEW_PREFIX = "reasoning/20261026_strict226/"
LFS_INCLUDE = NEW_PREFIX + "**"
REMOTE = "https://github.com/jiaotangbuding177/WRD_dataset.git"
BRANCH = "codex/wrd-training-data-20261025"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
POINTER = re.compile(rb"version https://git-lfs.github.com/spec/v1\r?\n"
                     rb"oid sha256:([a-f0-9]{64})\r?\nsize ([0-9]+)\r?\n?\Z")


class VerificationFailure(RuntimeError):
    """Only fixed, non-sensitive error codes may leave subprocess boundaries."""


def require(condition, code):
    if not condition:
        raise VerificationFailure(code)


def bsha(value):
    return hashlib.sha256(value).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def environment():
    env = dict(os.environ)
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return env


def sanitized_git_failure(returncode, stderr):
    # Never print raw git/LFS stderr: it may contain authentication or signed
    # storage URLs. Categories are from a closed, literal allow-list.
    text = stderr.decode("utf-8", errors="replace").lower()
    categories = [word for word in ("authentication", "authorization", "bandwidth", "quota",
        "403", "404", "429", "timeout", "could not resolve", "tls") if word in text]
    return "git_failed_code_" + str(returncode) + "_categories_" + ",".join(categories)


def git(*args, local=False, timeout=120):
    command = ["git", "-C", str(LOCAL)] if local else ["git", "--git-dir", str(BARE)]
    try:
        result = subprocess.run(command + list(args), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=environment(), timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise VerificationFailure("git_command_timeout") from None
    if result.returncode:
        raise VerificationFailure(sanitized_git_failure(result.returncode, result.stderr))
    return result.stdout


def valid_manifest_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\x00" in value or "\n" in value or "\r" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or ".." in path.parts or ".git" in path.parts:
        return False
    # The manifest is a payload index; keys must never be an indexed payload.
    return path.suffix.lower() != ".key" and "local_delivery_key" not in path.parts


def parse_manifest(blob):
    manifest = json.loads(blob.decode("utf-8-sig"))
    require(isinstance(manifest, dict) and isinstance(manifest.get("files"), list), "manifest_files_schema_invalid")
    require(manifest.get("local_key_intentionally_excluded") is True, "manifest_key_exclusion_not_declared")
    require(manifest.get("training_started") is False, "manifest_training_scope_changed")
    seen = set()
    for row in manifest["files"]:
        require(isinstance(row, dict) and valid_manifest_path(row.get("path")), "unsafe_manifest_payload_path")
        require(row["path"] != MANIFEST_PATH and row["path"] not in seen, "duplicate_or_self_indexed_manifest_path")
        require(isinstance(row.get("sha256"), str) and HEX64.fullmatch(row["sha256"]) is not None, "invalid_manifest_payload_sha256")
        require(type(row.get("bytes")) is int and row["bytes"] >= 0, "invalid_manifest_payload_size")
        seen.add(row["path"])
    require(bool(seen), "empty_manifest_not_accepted")
    return manifest


def cached_object(oid):
    require(HEX64.fullmatch(oid) is not None, "unsafe_lfs_object_id")
    return CACHE / "objects" / oid[:2] / oid[2:4] / oid


def cache_object_ids():
    objects = CACHE / "objects"
    return {p.name for p in objects.glob("*/*/*") if p.is_file() and HEX64.fullmatch(p.name)} if objects.is_dir() else set()


def local_preflight(commit):
    require(BARE.is_dir() and CACHE.is_dir(), "existing_v4_bare_and_cache_required")
    require(OLD_RECEIPT.is_file(), "existing_v4_final_receipt_required")
    require(git("remote", "get-url", "origin").decode().strip() == REMOTE, "bare_origin_does_not_match_expected_repository")
    require(git("remote", "get-url", "origin", local=True).decode().strip() == REMOTE, "checkout_origin_does_not_match_expected_repository")
    configured_storage = git("config", "--local", "--get", "lfs.storage").decode().strip()
    require(Path(configured_storage).resolve() == CACHE.resolve(), "bare_lfs_storage_does_not_reuse_v4_cache")
    local_head = git("rev-parse", "HEAD", local=True).decode().strip()
    require(local_head == commit, "local_checkout_head_not_explicit_final_commit")
    status = git("status", "--porcelain", "--untracked-files=all", local=True)
    require(not status.strip(), "local_release_checkout_not_clean")
    local_manifest_blob = (LOCAL / MANIFEST_PATH).read_bytes()
    require(git("show", commit + ":" + MANIFEST_PATH, local=True) == local_manifest_blob,
            "local_manifest_worktree_differs_from_committed_blob")
    manifest = parse_manifest(local_manifest_blob)
    previous = json.loads(OLD_RECEIPT.read_text(encoding="utf-8-sig"))
    require(previous.get("status") == "PASS" and isinstance(previous.get("verified_files"), list), "prior_verification_receipt_not_pass")
    previous_commit = previous.get("remote_commit")
    require(isinstance(previous_commit, str) and HEX40.fullmatch(previous_commit) is not None, "prior_receipt_commit_invalid")
    previous_lfs = {r["path"]: r for r in previous["verified_files"]
                    if r.get("verified") is True and "lfs" in r.get("kind", "").lower()}
    require(bool(previous_lfs), "prior_verified_lfs_payload_index_empty")
    return manifest, local_manifest_blob, previous_commit, previous_lfs


def fetch_incremental_lfs(commit, previous_ids):
    # Do not broaden this include to reasoning/** or the old v4 prefix.
    command = ["git", "--git-dir", str(BARE), "lfs", "fetch",
               "--include=" + LFS_INCLUDE, "--exclude=", "origin", commit]
    start = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment())
    while True:
        try:
            _stdout, stderr = process.communicate(timeout=20)
            break
        except subprocess.TimeoutExpired:
            current = cache_object_ids()
            progress = {"phase": "restricted_incremental_lfs_fetch_running",
                "elapsed_seconds": round(time.monotonic() - start, 1),
                "new_complete_cached_objects": len(current - previous_ids),
                "include": LFS_INCLUDE, "key_accessed": False,
                "raw_credentials_or_signed_urls_logged": False}
            save(PROGRESS, progress)
            print(json.dumps(progress), flush=True)
            if time.monotonic() - start > 3600:
                process.terminate()
                try:
                    process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                raise VerificationFailure("restricted_incremental_lfs_fetch_one_hour_timeout")
    if process.returncode:
        raise VerificationFailure(sanitized_git_failure(process.returncode, stderr))


def verify(commit):
    manifest, local_manifest_blob, previous_commit, previous_lfs = local_preflight(commit)
    # This fetch transfers Git metadata/blobs only, with smudging disabled.
    git("fetch", "--depth=1", "--no-tags", "origin", BRANCH)
    fetched = git("rev-parse", "FETCH_HEAD").decode().strip()
    require(fetched == commit, "remote_branch_head_not_expected_final_commit")
    server_manifest_blob = git("show", commit + ":" + MANIFEST_PATH)
    require(server_manifest_blob == local_manifest_blob, "remote_manifest_blob_not_equal_committed_local_manifest")
    server_manifest = parse_manifest(server_manifest_blob)
    require(server_manifest == manifest, "remote_manifest_decoded_values_differ")
    # The old commit is already present in the reused bare repository. Do not
    # fetch old LFS data or create a second independent 739 MB download.
    git("cat-file", "-e", previous_commit + "^{commit}")
    changed = {p.decode("utf-8") for p in git("diff", "--name-only", "-z", previous_commit, commit).split(b"\0") if p}
    indexed = {r["path"] for r in manifest["files"]}
    require(changed <= indexed | {MANIFEST_PATH}, "changed_release_paths_missing_from_manifest")
    files = []; lfs = []; counts = Counter()
    before_ids = cache_object_ids()
    for row in manifest["files"]:
        path = row["path"]
        blob = git("show", commit + ":" + path)
        pointer = POINTER.fullmatch(blob)
        git_blob_sha256 = bsha(blob)
        if pointer:
            oid = pointer.group(1).decode("ascii")
            size = int(pointer.group(2))
            require(oid == row["sha256"] and size == row["bytes"], "remote_lfs_pointer_not_equal_manifest_payload_identity")
            old = previous_lfs.get(path)
            reuses_old = old is not None and old.get("sha256") == oid and old.get("bytes") == size
            require(reuses_old or path.startswith(NEW_PREFIX), "new_or_changed_lfs_payload_outside_authorized_incremental_prefix")
            if reuses_old:
                cached = cached_object(oid)
                require(cached.is_file() and cached.stat().st_size == size, "previously_verified_lfs_object_missing_or_wrong_size")
                # Rehash actual cache bytes, do not rely only on a receipt.
                require(digest(cached) == oid, "previously_verified_lfs_cached_object_sha256_mismatch")
                counts["reused_old_lfs_payloads"] += 1
                counts["reused_old_lfs_payload_bytes"] += size
            else:
                counts["new_prefix_lfs_payloads"] += 1
                counts["new_prefix_lfs_payload_bytes"] += size
            lfs.append({"path": path, "sha256": oid, "bytes": size,
                        "remote_git_blob_sha256": git_blob_sha256,
                        "remote_git_blob_bytes": len(blob),
                        "reuses_prior_cold_remote_verified_object": reuses_old,
                        "object_present_before_incremental_fetch": oid in before_ids})
            counts["lfs_pointer_payloads"] += 1
        else:
            require(len(blob) == row["bytes"] and git_blob_sha256 == row["sha256"], "remote_ordinary_git_blob_not_equal_manifest")
            files.append({"path": path, "sha256": row["sha256"], "bytes": len(blob),
                "kind": "ordinary_git_blob", "remote_git_blob_sha256": git_blob_sha256,
                "remote_git_blob_bytes": len(blob), "verified": True})
            counts["normal_git_payloads"] += 1
    save(PROGRESS, {"phase": "all_remote_blobs_and_lfs_pointers_verified",
        "commit": commit, "counts": dict(counts), "lfs_fetch_include": LFS_INCLUDE,
        "cipher_key_accessed": False, "raw_credentials_or_signed_urls_logged": False})
    print(json.dumps({"phase": "remote_git_blobs_and_lfs_pointers_pass", "counts": dict(counts)}), flush=True)
    # Git LFS skips objects already present. The include rule confines any
    # missing-object request to the newly authorized prefix only.
    fetch_incremental_lfs(commit, before_ids)
    for row in lfs:
        cached = cached_object(row["sha256"])
        require(cached.is_file() and cached.stat().st_size == row["bytes"], "remote_lfs_real_object_missing_or_wrong_size")
        require(digest(cached) == row["sha256"], "remote_lfs_real_object_sha256_mismatch")
        files.append({**row, "kind": "reused_cold_verified_lfs_object_rehashed" if row["reuses_prior_cold_remote_verified_object"]
            else "new_prefix_remote_lfs_real_object", "verified": True})
        counts["lfs_real_objects_verified"] += 1
        counts["lfs_real_object_bytes_verified"] += row["bytes"]
    new_ids = cache_object_ids() - before_ids
    allowed_new_ids = {r["sha256"] for r in lfs if r["path"].startswith(NEW_PREFIX)}
    require(new_ids <= allowed_new_ids, "lfs_fetch_added_objects_outside_incremental_manifest_prefix")
    require(len(files) == len(manifest["files"]), "verified_payload_file_count_not_equal_dynamic_manifest")
    advertised = git("ls-remote", "--heads", "origin", BRANCH).decode().strip().split()
    require(len(advertised) == 2 and advertised[0] == commit and advertised[1] == "refs/heads/" + BRANCH,
            "remote_branch_head_changed_or_not_expected")
    local_head = git("rev-parse", "HEAD", local=True).decode().strip()
    status = git("status", "--porcelain", "--untracked-files=all", local=True)
    require(local_head == commit and not status.strip(), "local_release_changed_during_verification")
    result = {"schema_version": "wrd-v5-incremental-remote-git-lfs-verification",
        "status": "PASS", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "remote": REMOTE, "branch": BRANCH, "remote_commit": commit,
        "manifest_path": MANIFEST_PATH, "manifest_sha256": bsha(server_manifest_blob),
        "payload_files": len(manifest["files"]), "files_including_manifest": len(manifest["files"]) + 1,
        "payload_bytes": sum(r["bytes"] for r in manifest["files"]), "counts": dict(counts),
        "verified_files": sorted(files, key=lambda r: r["path"]),
        "manifest_normal_git_blob": {"sha256": bsha(server_manifest_blob), "bytes": len(server_manifest_blob), "verified": True},
        "previous_verified_commit": previous_commit,
        "previous_verification_receipt_path": str(OLD_RECEIPT.relative_to(ROOT)),
        "previous_verification_receipt_sha256": digest(OLD_RECEIPT),
        "incremental_changed_paths": sorted(changed),
        "incremental_changed_paths_all_indexed": True,
        "existing_v4_bare_repository_and_lfs_cache_reused": True,
        "previous_lfs_objects_rehashed_without_redownload_request": True,
        "lfs_fetch_include": LFS_INCLUDE, "old_v4_lfs_prefix_fetch_requested": False,
        "new_complete_lfs_cache_object_count": len(new_ids),
        "new_complete_lfs_cache_object_bytes": sum(cached_object(oid).stat().st_size for oid in new_ids),
        "cache_delta_confined_to_new_manifest_prefix_oids": True,
        "remote_branch_head_rechecked_after_readback": advertised[0],
        "local_git_release_head": local_head, "local_git_release_worktree_clean": True,
        "all_remote_payload_bytes_equal_dynamic_manifest": True,
        "cipher_verification": "ciphertext SHA/size only; no decryption or key access",
        "decryption_key_read_or_accessed": False, "training_started": False,
        "raw_credentials_or_signed_urls_logged": False, "script_sha256": digest(Path(__file__))}
    save(REPORT, result)
    print(json.dumps({key: result[key] for key in ("status", "remote_commit", "manifest_sha256",
        "payload_files", "files_including_manifest", "payload_bytes", "counts")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="Full final pushed commit SHA; running this command authorizes network verification.")
    args = parser.parse_args()
    require(HEX40.fullmatch(args.commit) is not None, "full_lowercase_40_character_commit_required")
    try:
        verify(args.commit)
    except Exception as exc:
        # Unknown exceptions emit their type only. No raw subprocess, URL,
        # authentication, exception repr, source body, or environment is saved.
        code = str(exc) if isinstance(exc, VerificationFailure) else "verification_exception_" + type(exc).__name__
        failure = {"schema_version": "wrd-v5-incremental-remote-git-lfs-verification", "status": "FAIL",
            "expected_commit": args.commit, "failure_code": code,
            "decryption_key_read_or_accessed": False, "training_started": False,
            "raw_credentials_or_signed_urls_logged": False, "script_sha256": digest(Path(__file__))}
        save(REPORT, failure)
        print(json.dumps(failure), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
