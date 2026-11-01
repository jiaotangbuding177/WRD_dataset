"""Cold Git proof plus one official LFS batch download using pinned55 code.

Avoids git-lfs ls-tree -l walking every missing blob in a partial clone. The
original CLI attempt is retained separately; only a completed download is PASS.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re

HELPER_SHA = "a941396216372c584cad8167dd9d05cfbaeb22dcb01f20ac2baacedcb5354da1"
BATCH_SHA = "ec171b1270e19122a0021d40413688d40a463f8f94604b54764e4edf9d629c1f"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned_module(path, expected, name):
    require(sha(path) == expected, "TRUSTED_VERIFIER_SOURCE_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", default="77ea6a8")
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-fA-F]{7,40}", args.base) and re.fullmatch(r"[0-9a-fA-F]{7,40}", args.target), "COMMIT_HEX_REQUIRED")
    repo, out = args.repo.resolve(), args.out.resolve()
    require(not out.exists() and not out.is_relative_to(repo), "FRESH_EXTERNAL_OUTPUT_REQUIRED")
    helper = pinned_module(Path(__file__).with_name("verify_remote57.py"), HELPER_SHA, "reviewed57_remote_git_helpers")
    batch = pinned_module(repo / "deliveries/20261101_full_data_and_plan/tooling/verify_remote_entities55.py", BATCH_SHA, "reviewed55_official_LFS_download")
    batch.REPO = repo
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("GIT_TRACE", "GCM_TRACE")) or key in {"GIT_CURL_VERBOSE", "GIT_TRANSFER_TRACE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_LFS_STORAGE"}:
            env.pop(key)
    env.update(GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    local = ["git", "-C", str(repo)]
    base = helper.run(local + ["rev-parse", "--verify", args.base + "^{commit}"], env).strip().decode("ascii")
    target = helper.run(local + ["rev-parse", "--verify", args.target + "^{commit}"], env).strip().decode("ascii")
    helper.run(local + ["merge-base", "--is-ancestor", base, target], env)
    remote = helper.allowed_remote(helper.run(local + ["remote", "get-url", "origin"], env).decode().strip())
    require(remote.rstrip("/").removesuffix(".git") == "https://github.com/jiaotangbuding177/WRD_dataset", "PINNED_BATCH_ENDPOINT_REPOSITORY_REQUIRED")
    paths = [helper.validate_path(p.decode("utf-8")) for p in helper.run(local + ["diff", "--name-only", "--diff-filter=ACMR", "-z", base, target], env).split(b"\0") if p]
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
        local_body = helper.run(local + ["cat-file", "blob", target + ":" + path], env)
        remote_body = helper.run(git + ["cat-file", "blob", target + ":" + path], env)
        require(local_body == remote_body, "COLD_REMOTE_BLOB_MISMATCH")
        pointer = helper.parse_pointer(remote_body)
        checks.append({"path": path, "sha256": hashlib.sha256(remote_body).hexdigest(), "bytes": len(remote_body), "is_lfs_pointer": pointer is not None})
        if pointer:
            require(path.startswith(helper.PREFIX) and path.endswith(".aesgcm"), "REFUSE_OLD_OR_NON57_LFS_ENTITY")
            pointers.append({"entity": path, "sha256": pointer["oid"], "bytes": pointer["bytes"]})
    require(len(pointers) == 1, "REQUIRE_EXACTLY_ONE_NEW57_ENTITY")
    fresh = out / "fresh-official-lfs-batch"
    fresh.mkdir(exist_ok=False)
    # Existing reviewed code requests only this single verified pointer OID from
    # GitHub's official batch endpoint, then validates ranges, full SHA and size.
    auth = batch.credential()
    downloaded = batch.download(pointers[0], auth, fresh)
    del auth
    downloaded.pop("local_file", None)
    legacy = "deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json"
    legacy_body = helper.run(local + ["cat-file", "blob", target + ":" + legacy], env)
    report = {"schema": "wrd57-fresh-remote-blobs-and-single-official-lfs-batch-download", "status": "PASS_FRESH_REMOTE_GIT_BLOBS_AND_ONLY_NEW57_FULL_LFS_ENTITY",
              "base_commit": base, "target_commit": target, "ordinary_files_verified": sum(not r["is_lfs_pointer"] for r in checks),
              "git_lfs_pointer_files_verified": 1, "Git_blob_checks": checks, "new57_LFS_entities": [downloaded],
              "new57_LFS_bytes_downloaded": downloaded["downloaded_file_bytes"], "actual_wire_bytes": batch.WIRE_BYTES,
              "fresh_bare_repository": True, "fresh_external_download_directory": True, "local_LFS_cache_used": False,
              "official_LFS_batch_endpoint_used": True, "only_new57_OID_requested": True, "GIT_LFS_SKIP_SMUDGE": True,
              "legacy_LFS_downloaded_this_verification": False,
              "legacy05_through11_remote_proof_reference": {"path": legacy, "sha256": hashlib.sha256(legacy_body).hexdigest(), "re_downloaded_this_run": False},
              "initial_git_lfs_CLI_attempt": "ABORTED_BEFORE_ANY_LFS_ENTITY_BYTES_PARTIAL_CLONE_LS_TREE_SIZE_WALK_NOT_PASS",
              "credential_source": "GCM via git credential fill; process memory only; official GitHub batch only",
              "credentials_or_signed_URLs_output": False, "pinned_Git_helper_sha256": HELPER_SHA, "pinned_official_batch_helper_sha256": BATCH_SHA,
              "verifier_source_sha256": sha(Path(__file__)), "push_performed": False, "training_started": False}
    (out / "REMOTE_VERIFICATION57.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "target_commit", "ordinary_files_verified", "new57_LFS_bytes_downloaded", "actual_wire_bytes", "legacy_LFS_downloaded_this_verification", "training_started"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Exceptions from HTTP libraries can contain signed URLs; emit class only.
        print(json.dumps({"status": "REMOTE_CHECK_FAILED", "error_class": type(exc).__name__}))
        raise SystemExit(1)
