"""Fresh remote Git blobs and only the new57 LFS entity; no credentials output.

Run after the reviewed commit and its LFS object have been pushed. This script
never pushes, checks out, executes payload code, or fetches legacy LFS packages.
"""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import os
import re
import subprocess

PREFIX = "dataset/20261101_increment57_offline/"
POINTER = re.compile(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?")


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def run(command, environment):
    # stdout may contain Git blobs and stderr may contain authenticated URLs.
    # Neither is echoed; callers emit only hashes, sizes and reviewed paths.
    result = subprocess.run(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError("GIT_SUBPROCESS_FAILED_EXIT_" + str(result.returncode))
    return result.stdout


def parse_pointer(data):
    match = POINTER.fullmatch(data)
    if match:
        return {"oid": match.group(1).decode("ascii"), "bytes": int(match.group(2))}
    return None


def validate_path(name):
    path = PurePosixPath(name)
    require(path.as_posix() == name and not path.is_absolute() and ".." not in path.parts, "UNSAFE_GIT_PATH")
    require(name and not any(ord(c) < 32 for c in name) and "," not in name and "\\" not in name, "UNSAFE_GIT_PATH_CHARACTERS")
    return name


def allowed_remote(url):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname == "github.com" and parsed.username is None and parsed.password is None,
            "REQUIRE_GITHUB_HTTPS_REMOTE_WITHOUT_EMBEDDED_CREDENTIALS")
    require(not parsed.query and not parsed.fragment and parsed.port is None and len(parsed.path.strip("/").split("/")) == 2,
            "UNEXPECTED_REMOTE_URL_SHAPE")
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", default="77ea6a8")
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-new-lfs-entities", type=int, default=1)
    parser.add_argument("--legacy-receipt", default="deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json")
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-fA-F]{7,40}", args.base) and re.fullmatch(r"[0-9a-fA-F]{7,40}", args.target), "COMMIT_HEX_REQUIRED")
    repo = args.repo.resolve()
    out = args.out.resolve()
    require(not out.exists() and not out.is_relative_to(repo), "FRESH_EXTERNAL_OUTPUT_DIRECTORY_REQUIRED")
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith(("GIT_TRACE", "GCM_TRACE")) or key in {
            "GIT_CURL_VERBOSE", "GIT_TRANSFER_TRACE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
            "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_LFS_STORAGE"
        }:
            environment.pop(key)
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    local = ["git", "-C", str(repo)]
    base = run(local + ["rev-parse", "--verify", args.base + "^{commit}"], environment).strip().decode("ascii")
    target = run(local + ["rev-parse", "--verify", args.target + "^{commit}"], environment).strip().decode("ascii")
    run(local + ["merge-base", "--is-ancestor", base, target], environment)
    remote_url = allowed_remote(run(local + ["remote", "get-url", "origin"], environment).decode("utf-8").strip())
    paths = [validate_path(p.decode("utf-8")) for p in run(local + ["diff", "--name-only", "--diff-filter=ACMR", "-z", base, target], environment).split(b"\x00") if p]
    require(paths and len(paths) == len(set(paths)), "NO_UNIQUE_CHANGED_FILES")
    local_blobs = {}
    new_pointers = {}
    for path in paths:
        mode = run(local + ["ls-tree", target, "--", path], environment).split(b" ", 1)[0]
        require(mode in {b"100644", b"100755"}, "CHANGED_NONREGULAR_FILE_NOT_SUPPORTED")
        body = run(local + ["cat-file", "blob", target + ":" + path], environment)
        pointer = parse_pointer(body)
        local_blobs[path] = {"sha256": digest(body), "bytes": len(body), "is_lfs_pointer": pointer is not None}
        if pointer:
            require(path.startswith(PREFIX) and path.endswith(".aesgcm"), "REFUSE_NON57_OR_NONAES_CHANGED_LFS_ENTITY")
            new_pointers[path] = pointer
    require(len(new_pointers) == args.expected_new_lfs_entities and args.expected_new_lfs_entities > 0,
            "UNEXPECTED_NEW57_LFS_ENTITY_COUNT")
    out.mkdir(parents=True, exist_ok=False)
    bare = out / "remote.git"
    storage = out / "fresh-lfs-storage"
    require(not bare.exists() and not storage.exists(), "REMOTE_OR_LFS_CACHE_NOT_FRESH")
    run(["git", "init", "--bare", str(bare)], environment)
    require(not (bare / "objects/info/alternates").exists(), "FRESH_BARE_MUST_NOT_REFERENCE_LOCAL_OBJECT_CACHE")
    git = ["git", "--git-dir=" + str(bare)]
    run(git + ["remote", "add", "origin", remote_url], environment)
    run(git + ["fetch", "--filter=blob:none", "--no-tags", "origin", target], environment)
    remote_target = run(git + ["rev-parse", "FETCH_HEAD^{commit}"], environment).strip().decode("ascii")
    require(remote_target == target, "REMOTE_TARGET_COMMIT_DIFFERS")
    checked = []
    for path in paths:
        body = run(git + ["cat-file", "blob", target + ":" + path], environment)
        actual = {"sha256": digest(body), "bytes": len(body), "is_lfs_pointer": parse_pointer(body) is not None}
        require(actual == local_blobs[path], "REMOTE_GIT_BLOB_MISMATCH")
        checked.append({"path": path, **actual})
    # Exact comma-separated paths only. No wildcard, pull, --all, --recent or
    # legacy05-11 include is used. Custom storage starts empty outside checkout.
    include = ",".join(sorted(new_pointers))
    run(git + ["-c", "lfs.storage=" + str(storage), "-c", "lfs.fetchrecentalways=false", "lfs", "fetch",
               "--include=" + include, "--exclude=", "origin", target], environment)
    entity_checks = []
    for path, pointer in sorted(new_pointers.items()):
        oid = pointer["oid"]
        entity = storage / "objects" / oid[:2] / oid[2:4] / oid
        require(entity.is_file() and entity.stat().st_size == pointer["bytes"] and file_sha(entity) == oid,
                "FRESH_REMOTE_LFS_ENTITY_HASH_OR_SIZE_MISMATCH")
        entity_checks.append({"path": path, "sha256": oid, "bytes": pointer["bytes"], "fresh_remote_download_verified": True})
    actual_objects = {p.name for p in (storage / "objects").rglob("*") if p.is_file()}
    require(actual_objects == {p["oid"] for p in new_pointers.values()}, "UNEXPECTED_OLD_OR_EXTRA_LFS_OBJECT_DOWNLOADED")
    legacy_path = repo / validate_path(args.legacy_receipt)
    require(legacy_path.is_file(), "LEGACY_REMOTE_PROOF_REFERENCE_REQUIRED")
    legacy_body = run(local + ["cat-file", "blob", target + ":" + args.legacy_receipt], environment)
    require(digest(legacy_body) == file_sha(legacy_path), "LEGACY_RECEIPT_LOCAL_FILE_DIFFERS_FROM_TARGET_COMMIT")
    report = {"schema": "wrd57-fresh-remote-git-blobs-and-new57-only-lfs-proof", "status": "PASS_FRESH_REMOTE_BLOBS_AND_ONLY_NEW57_LFS_ENTITY",
              "base_commit": base, "target_commit": target, "ordinary_files_verified": sum(not r["is_lfs_pointer"] for r in checked),
              "git_lfs_pointer_files_verified": len(new_pointers), "Git_blob_checks": checked, "new57_LFS_entities": entity_checks,
              "new57_LFS_bytes_downloaded": sum(r["bytes"] for r in entity_checks), "fresh_bare_repository": True,
              "fresh_external_lfs_storage": True, "GIT_LFS_SKIP_SMUDGE": True, "legacy_LFS_downloaded_this_verification": False,
              "legacy05_through11_remote_proof_reference": {"path": args.legacy_receipt, "sha256": digest(legacy_body), "re_downloaded_this_run": False},
              "credentials_or_signed_URLs_output": False, "push_performed": False, "training_started": False,
              "verifier_source_sha256": file_sha(Path(__file__))}
    (out / "REMOTE_VERIFICATION57.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "base_commit", "target_commit", "ordinary_files_verified",
          "git_lfs_pointer_files_verified", "new57_LFS_bytes_downloaded", "legacy_LFS_downloaded_this_verification", "training_started"]}))


if __name__ == "__main__":
    main()
