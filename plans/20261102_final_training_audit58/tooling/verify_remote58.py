"""Cold v58 Git blobs and one official LFS batch entity, never a push.

Use --ordinary-only for the later receipt commit. Existing offline proof and
old payloads are references only; no ls-tree -l or broad git-lfs fetch is used.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re

GIT_HELPER_SHA = "a941396216372c584cad8167dd9d05cfbaeb22dcb01f20ac2baacedcb5354da1"
BATCH_HELPER_SHA = "ec171b1270e19122a0021d40413688d40a463f8f94604b54764e4edf9d629c1f"
NATIVE_ENTITY = "dataset/20261102_v58_protocol_mask/controlled/wrd-v58-protocol-mask.tar.gz.aesgcm"
ALLOWED_PREFIXES = ("plans/20261102_final_training_audit58/", "dataset/20261102_v58_protocol_mask/", "deliveries/20261102_final_training_audit58/")
ALLOWED_ROOT = {"README.md", "TRAINING_ENTRYPOINT.json", ".gitattributes"}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def pinned_module(path, expected, name):
    require(sha(path) == expected, "TRUSTED_VERIFIER_SOURCE_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", default="7283f2e9a788b6b08355230e951ffcefdab3a910")
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ordinary-only", action="store_true")
    parser.add_argument("--cipher-sha256")
    parser.add_argument("--cipher-bytes", type=int)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-fA-F]{7,40}", args.base) and re.fullmatch(r"[0-9a-fA-F]{7,40}", args.target), "COMMIT_HEX_REQUIRED")
    if args.ordinary_only:
        require(args.cipher_sha256 is None and args.cipher_bytes is None, "NO_ENTITY_ARGUMENTS_FOR_RECEIPT_ONLY")
    else:
        require(args.cipher_sha256 is not None and re.fullmatch(r"[0-9a-f]{64}", args.cipher_sha256) and args.cipher_bytes and args.cipher_bytes > 0, "EXACT_REVIEWED_ENTITY_PIN_REQUIRED")
    repo, out = args.repo.resolve(), args.out.resolve()
    require(not out.exists() and not out.is_relative_to(repo), "FRESH_EXTERNAL_OUTPUT_REQUIRED")
    helper = pinned_module(repo / "plans/20261101_increment57/tooling/verify_remote57.py", GIT_HELPER_SHA, "reviewed57_cold_git_helpers")
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("GIT_TRACE", "GCM_TRACE")) or key in {"GIT_CURL_VERBOSE", "GIT_TRANSFER_TRACE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_LFS_STORAGE"}:
            env.pop(key)
    env.update(GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    local = ["git", "-C", str(repo)]
    base = helper.run(local + ["rev-parse", "--verify", args.base + "^{commit}"], env).strip().decode("ascii")
    target = helper.run(local + ["rev-parse", "--verify", args.target + "^{commit}"], env).strip().decode("ascii")
    helper.run(local + ["merge-base", "--is-ancestor", base, target], env)
    require(not helper.run(local + ["diff", "--name-only", "--diff-filter=D", base, target], env).strip(), "NO_DELETIONS_IN_NATIVE_DELIVERY")
    remote = helper.allowed_remote(helper.run(local + ["remote", "get-url", "origin"], env).decode().strip())
    require(remote.rstrip("/").removesuffix(".git") == "https://github.com/jiaotangbuding177/WRD_dataset", "PINNED_BATCH_ENDPOINT_REPOSITORY_REQUIRED")
    paths = [helper.validate_path(p.decode("utf-8")) for p in helper.run(local + ["diff", "--name-only", "--diff-filter=ACMR", "-z", base, target], env).split(b"\0") if p]
    require(paths and len(paths) == len(set(paths)), "NONEMPTY_UNIQUE_CHANGED_PATHS_REQUIRED")
    require(all(p in ALLOWED_ROOT or p.startswith(ALLOWED_PREFIXES) for p in paths), "OUTSIDE_V58_DELIVERY_ALLOWLIST")
    out.mkdir(parents=True, exist_ok=False)
    bare = out / "remote.git"
    helper.run(["git", "init", "--bare", str(bare)], env)
    require(not (bare / "objects/info/alternates").exists(), "NO_LOCAL_GIT_OBJECT_CACHE_ALLOWED")
    git = ["git", "--git-dir=" + str(bare)]
    for key, value in [("gc.auto", "0"), ("maintenance.auto", "false")]:
        helper.run(git + ["config", key, value], env)
    helper.run(git + ["remote", "add", "origin", remote], env)
    helper.run(git + ["fetch", "--filter=blob:none", "--no-tags", "origin", target], env)
    require(helper.run(git + ["rev-parse", "FETCH_HEAD^{commit}"], env).strip().decode() == target, "REMOTE_COMMIT_MISMATCH")
    checks, pointers = [], []
    for path in paths:
        mode = helper.run(local + ["ls-tree", target, "--", path], env).split(b" ", 1)[0]
        require(mode in {b"100644", b"100755"}, "CHANGED_NONREGULAR_FILE_REJECTED")
        expected = helper.run(local + ["cat-file", "blob", target + ":" + path], env)
        actual = helper.run(git + ["cat-file", "blob", target + ":" + path], env)
        require(expected == actual, "COLD_REMOTE_BLOB_MISMATCH")
        pointer = helper.parse_pointer(actual)
        checks.append({"path": path, "sha256": hashlib.sha256(actual).hexdigest(), "bytes": len(actual), "is_lfs_pointer": pointer is not None})
        if pointer:
            require(not args.ordinary_only and path == NATIVE_ENTITY, "REFUSE_OLD_OR_UNEXPECTED_LFS_ENTITY")
            require(pointer["oid"] == args.cipher_sha256 and pointer["bytes"] == args.cipher_bytes, "NEW_ENTITY_POINTER_DIFFERS_FROM_REVIEWED_PINS")
            pointers.append({"entity": path, "sha256": pointer["oid"], "bytes": pointer["bytes"]})
    require(len(pointers) == (0 if args.ordinary_only else 1), "UNEXPECTED_NEW_ENTITY_COUNT")
    downloads, wire_bytes = [], 0
    if pointers:
        batch = pinned_module(repo / "deliveries/20261101_full_data_and_plan/tooling/verify_remote_entities55.py", BATCH_HELPER_SHA, "reviewed55_official_lfs_batch")
        batch.REPO = repo
        fresh = out / "fresh-official-lfs-batch"
        fresh.mkdir(exist_ok=False)
        auth = batch.credential()
        try:
            downloaded = batch.download(pointers[0], auth, fresh)
        finally:
            del auth
        downloaded.pop("local_file", None)
        downloads.append(downloaded)
        wire_bytes = batch.WIRE_BYTES
    legacy = []
    for path in ["deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json", "deliveries/20261101_increment57_offline/REMOTE_VERIFICATION.json", "deliveries/20261101_increment57_native/REMOTE_VERIFICATION.json"]:
        body = helper.run(local + ["cat-file", "blob", target + ":" + path], env)
        legacy.append({"path": path, "sha256": hashlib.sha256(body).hexdigest(), "re_downloaded_this_run": False})
    report = {"schema": "wrd58-final-audit-fresh-git-blobs-and-single-official-lfs-batch-v1", "status": "PASS_FRESH_REMOTE_ORDINARY_RECEIPT_BLOBS" if args.ordinary_only else "PASS_FRESH_REMOTE_BLOBS_AND_ONLY_V58_FULL_LFS_ENTITY",
              "base_commit": base, "target_commit": target, "ordinary_files_verified": sum(not r["is_lfs_pointer"] for r in checks), "git_lfs_pointer_files_verified": len(pointers), "Git_blob_checks": checks,
              "new_v58_LFS_entities": downloads, "new_v58_LFS_bytes_downloaded": sum(r["downloaded_file_bytes"] for r in downloads), "actual_wire_bytes": wire_bytes,
              "fresh_bare_repository": True, "fresh_external_download_directory": True, "local_LFS_cache_used": False, "GIT_LFS_SKIP_SMUDGE": True,
              "official_LFS_batch_endpoint_used": bool(pointers), "only_reviewed_v58_OID_requested": bool(pointers), "legacy_LFS_downloaded_this_verification": False,
              "legacy_remote_proof_references": legacy, "credential_source": "GCM via git credential fill, process memory only, official GitHub batch only" if pointers else "Normal Git GCM, no explicit credential access",
              "credentials_or_signed_URLs_output": False, "pinned_Git_helper_sha256": GIT_HELPER_SHA, "pinned_official_batch_helper_sha256": BATCH_HELPER_SHA, "verifier_source_sha256": sha(__file__),
              "push_performed": False, "training_started": False}
    (out / "REMOTE_VERIFICATION58.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "target_commit", "ordinary_files_verified", "git_lfs_pointer_files_verified", "new_v58_LFS_bytes_downloaded", "actual_wire_bytes", "training_started"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # HTTP errors may include signed URLs; never output exception text.
        print(json.dumps({"status": "REMOTE_CHECK_FAILED", "error_class": type(exc).__name__}))
        raise SystemExit(1)
