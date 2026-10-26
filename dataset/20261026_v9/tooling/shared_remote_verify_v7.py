"""Read back the explicitly pushed census commit, including real LFS bytes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "output/20261025_wrd_training_dataset/git_release"
OUT = ROOT / "output/20261026_wrd_raw_census_v7"
V4 = ROOT / "output/20261025_wrd_reasoning_recovery_v4"
BARE = V4 / "outputv4remote_verify.git"
CACHE = V4 / "outputv4remote_lfs_empty"
PREFIX = "census/20261026/"
REMOTE = "https://github.com/jiaotangbuding177/WRD_dataset.git"
BRANCH = "codex/wrd-training-data-20261025"
PRIOR = "9e7fa8c58a831b1e37544c92dff9d9723508b406"
POINTER = re.compile(rb"version https://git-lfs.github.com/spec/v1\r?\noid sha256:([a-f0-9]{64})\r?\nsize ([0-9]+)\r?\n?\Z")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def git(*arguments, local=False, timeout=180):
    command = ["git", "-c", "http.sslBackend=openssl", "-c", "http.sslVersion=tlsv1.2", "-c", "http.version=HTTP/1.1"]
    command += ["-C", str(LOCAL)] if local else ["--git-dir", str(BARE)]
    environment = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    result = subprocess.run(command + list(arguments), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=environment)
    if result.returncode:
        # Avoid recording raw stderr, which may contain signed LFS URLs.
        raise RuntimeError("remote_git_command_failed_" + str(result.returncode))
    return result.stdout


def verify(commit):
    assert re.fullmatch(r"[a-f0-9]{40}", commit)
    assert git("remote", "get-url", "origin").decode().strip() == REMOTE
    assert Path(git("config", "--local", "--get", "lfs.storage").decode().strip()).resolve() == CACHE.resolve()
    assert git("rev-parse", "HEAD", local=True).decode().strip() == commit
    assert not git("status", "--porcelain", "--untracked-files=all", local=True).strip()
    git("fetch", "--depth=1", "--no-tags", "origin", BRANCH)
    assert git("rev-parse", "FETCH_HEAD").decode().strip() == commit
    path = PREFIX + "MANIFEST.json"
    blob = git("show", commit + ":" + path)
    assert blob == (LOCAL / path).read_bytes()
    manifest = json.loads(blob)
    assert manifest["training_started"] is False
    assert manifest["original226_training_boundary_unchanged"] is True
    changed = {value.decode("utf-8") for value in git("diff", "--name-only", "-z", PRIOR, commit).split(b"\0") if value}
    root_paths = {"README.md", "TRAINING_ENTRYPOINT.json", ".gitattributes"}
    manifest_paths = {PREFIX + row["path"] for row in manifest["files"]}
    assert len(manifest_paths) == manifest["payload_files"]
    assert changed <= manifest_paths | {path} | root_paths
    rows, lfs = [], []
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        assert not relative.is_absolute() and ".." not in relative.parts and "\\" not in item["path"]
        name = PREFIX + item["path"]
        stored = git("show", commit + ":" + name)
        pointer = POINTER.fullmatch(stored)
        if pointer:
            oid = pointer.group(1).decode("ascii")
            size = int(pointer.group(2))
            assert oid == item["sha256"] and size == item["bytes"]
            lfs.append({"path": name, "sha256": oid, "bytes": size})
        else:
            assert len(stored) == item["bytes"] and hashlib.sha256(stored).hexdigest() == item["sha256"]
            rows.append({"path": name, "sha256": item["sha256"], "bytes": len(stored), "kind": "ordinary_git_blob", "verified": True})
    print(json.dumps({"phase": "remote_manifest_blobs_and_pointers_verified", "ordinary_files": len(rows), "lfs_payloads": len(lfs)}), flush=True)
    git("lfs", "fetch", "--include=" + PREFIX + "**", "--exclude=", "origin", commit, timeout=1800)
    for item in lfs:
        oid = item["sha256"]
        source = CACHE / "objects" / oid[:2] / oid[2:4] / oid
        assert source.is_file() and source.stat().st_size == item["bytes"] and digest(source) == oid
        rows.append({**item, "kind": "remote_lfs_real_object_rehashed", "verified": True})
    root_verified = []
    for name in sorted(root_paths & changed):
        stored = git("show", commit + ":" + name)
        assert stored == (LOCAL / name).read_bytes()
        root_verified.append({"path": name, "bytes": len(stored), "sha256": hashlib.sha256(stored).hexdigest()})
    advertised = git("ls-remote", "--heads", "origin", BRANCH).decode().split()
    assert advertised == [commit, "refs/heads/" + BRANCH]
    assert not git("status", "--porcelain", "--untracked-files=all", local=True).strip()
    receipt = {"schema_version": "wrd-v7-remote-census-readback", "status": "PASS", "verified_at_utc": datetime.now(timezone.utc).isoformat(), "remote": REMOTE, "branch": BRANCH, "remote_commit": commit, "manifest_path": path, "manifest_sha256": hashlib.sha256(blob).hexdigest(), "payload_files": len(rows), "payload_bytes": sum(row["bytes"] for row in rows), "ordinary_git_payloads": len(rows) - len(lfs), "lfs_real_objects_verified": len(lfs), "lfs_real_object_bytes_verified": sum(row["bytes"] for row in lfs), "changed_paths": sorted(changed), "root_metadata_verified": root_verified, "verified_files": rows, "old_training_payloads_changed": False, "training_started": False}
    (OUT / "REMOTE_GIT_VERIFICATION.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key not in {"verified_files", "changed_paths", "root_metadata_verified"}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    verify(parser.parse_args().commit)
