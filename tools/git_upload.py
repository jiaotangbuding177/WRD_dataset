"""Upload a verified WRD release to the explicitly authorized private repository.

The script operates only in --release, never in the original research checkout.
GitHub credentials stay in memory; signed LFS transfer URLs are never printed.
There is no force push, deletion, repository creation, or automatic fallback.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


REPOSITORY = "jiaotangbuding177/WRD_dataset"
REMOTE = "https://github.com/" + REPOSITORY + ".git"
DEFAULT_BRANCH = "codex/wrd-training-data-20261025"
FORMAT = "wrd-training-package-v1"
SHA = re.compile(r"[a-f0-9]{64}\Z")


class UploadError(Exception):
    def __init__(self, code: int, stage: str, message: str):
        super().__init__(message)
        self.code = code
        self.stage = stage


def digest(path: Path) -> tuple[str, int]:
    value = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
            size += len(block)
    return value.hexdigest(), size


def run(arguments: list[str], directory: Path, *, input_text: str | None = None) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_LFS_FORCE_PROGRESS": "0"})
    # Capture output rather than echoing it: external errors may contain private
    # author addresses or temporary signed object-store URLs.
    return subprocess.run(arguments, cwd=directory, input=input_text, text=True,
                          encoding="utf-8", errors="replace", capture_output=True, env=environment)


def git(directory: Path, arguments: list[str], *, code: int = 4, stage: str = "local_git", allowed=(0,)) -> subprocess.CompletedProcess:
    result = run(["git", *arguments], directory)
    if result.returncode not in allowed:
        raise UploadError(code, stage, "Git command failed: " + " ".join(arguments[:3]) + "; exit=" + str(result.returncode) + ". Local release and Git/LFS files are preserved.")
    return result


def credentials(directory: Path) -> str:
    result = run(["git", "credential", "fill"], directory,
                 input_text="protocol=https\nhost=github.com\n\n")
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or not fields.get("password"):
        raise UploadError(3, "authentication", "No existing GitHub GCM credential is available; no upload attempted.")
    pair = fields.get("username", "") + ":" + fields["password"]
    return "Basic " + base64.b64encode(pair.encode()).decode()


def request_json(url: str, authorization: str, *, body: dict | None = None, lfs: bool = False):
    content_type = "application/vnd.git-lfs+json" if lfs else "application/vnd.github+json"
    headers = {"Authorization": authorization, "User-Agent": "WRD-private-dataset-uploader", "Accept": content_type}
    raw = None
    if body is not None:
        headers["Content-Type"] = content_type
        raw = json.dumps(body).encode()
    request = urllib.request.Request(url, data=raw, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as failure:
        raise UploadError(3 if not lfs else 6, "repository_api" if not lfs else "lfs_remote_verification",
                          "Authenticated endpoint returned HTTP " + str(failure.code) + "; no credential or transfer URL is logged.") from None
    except (OSError, ValueError) as failure:
        raise UploadError(3 if not lfs else 6, "repository_api" if not lfs else "lfs_remote_verification",
                          "Authenticated endpoint could not be read; exception type=" + type(failure).__name__) from None


def verify_release(release: Path) -> tuple[dict, str]:
    if not release.is_dir() or release.is_symlink():
        raise UploadError(2, "release_verification", "Release must be an existing real directory.")
    manifest_path = release / "package_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise UploadError(2, "release_verification", "Complete package_manifest.json is required.") from None
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or not isinstance(manifest.get("parts"), list) or not manifest["parts"]:
        raise UploadError(2, "release_verification", "Unsupported or empty package manifest.")
    total = 0
    expected_files = set()
    for number, part in enumerate(manifest["parts"], 1):
        expected = f"dist/wrd-training-bundle-v1.tar.gz.part{number:04d}"
        if not isinstance(part, dict) or part.get("path") != expected or not SHA.fullmatch(str(part.get("sha256", ""))):
            raise UploadError(2, "release_verification", "Invalid or unordered part metadata.")
        path = release / expected
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(release.resolve()):
            raise UploadError(2, "release_verification", "Missing or linked release part.")
        actual, size = digest(path)
        if actual != part["sha256"] or size != part.get("bytes"):
            raise UploadError(2, "release_verification", "Release part digest or size differs from manifest: part " + str(number))
        total += size
        expected_files.add(path.resolve())
        print(json.dumps({"stage": "part_verified", "part": number, "parts": len(manifest["parts"]), "bytes": size}), flush=True)
    if total != manifest.get("compressed_bytes"):
        raise UploadError(2, "release_verification", "Compressed total does not match manifest.")
    actual_files = {path.resolve() for path in (release / "dist").rglob("*") if path.is_file()}
    if actual_files != expected_files:
        raise UploadError(2, "release_verification", "dist contains files not listed in the manifest.")
    return manifest, digest(manifest_path)[0]


def remote_head(release: Path, branch: str, expected: str, *, code=6) -> None:
    result = git(release, ["ls-remote", "--heads", "origin", "refs/heads/" + branch], code=code, stage="remote_ref_verification")
    heads = [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
    if heads != [expected]:
        raise UploadError(code, "remote_ref_verification", "Remote branch does not match the local uploaded commit.")


def check_download_action(action: dict) -> str:
    href = action.get("href")
    if not isinstance(href, str) or urllib.parse.urlsplit(href).scheme != "https":
        raise UploadError(6, "lfs_remote_verification", "LFS download action is missing a secure transfer URL.")
    headers = dict(action.get("header", {}))
    headers["User-Agent"] = "WRD-private-dataset-uploader"
    try:
        with urllib.request.urlopen(urllib.request.Request(href, headers=headers, method="HEAD"), timeout=60) as response:
            if response.status in (200, 204, 206):
                return "HEAD_confirmed"
    except urllib.error.HTTPError as failure:
        # Some signed storage URLs bind the GET method, so HEAD is not valid.
        if failure.code not in (400, 403, 405, 501):
            raise UploadError(6, "lfs_remote_verification", "Remote LFS object HEAD returned HTTP " + str(failure.code)) from None
    except OSError:
        raise UploadError(6, "lfs_remote_verification", "Remote LFS object HEAD could not be checked.") from None
    headers["Range"] = "bytes=0-0"
    try:
        with urllib.request.urlopen(urllib.request.Request(href, headers=headers), timeout=60) as response:
            if response.status not in (200, 206) or len(response.read(1)) != 1:
                raise UploadError(6, "lfs_remote_verification", "Remote LFS object did not serve the verification byte.")
        return "GET_first_byte_confirmed_HEAD_method_unavailable"
    except urllib.error.HTTPError as failure:
        raise UploadError(6, "lfs_remote_verification", "Remote LFS verification read returned HTTP " + str(failure.code)) from None
    except OSError:
        raise UploadError(6, "lfs_remote_verification", "Remote LFS verification read could not complete.") from None


def verify_remote_lfs(manifest: dict, authorization: str) -> dict:
    objects = [{"oid": part["sha256"], "size": part["bytes"]} for part in manifest["parts"]]
    verified = []
    for start in range(0, len(objects), 100):
        batch = objects[start:start + 100]
        response = request_json(REMOTE + "/info/lfs/objects/batch", authorization,
                                body={"operation": "download", "transfers": ["basic"], "objects": batch, "hash_algo": "sha256"}, lfs=True)
        returned = {item.get("oid"): item for item in response.get("objects", []) if isinstance(item, dict)}
        for requested in batch:
            item = returned.get(requested["oid"], {})
            action = item.get("actions", {}).get("download")
            if item.get("error") or item.get("size") != requested["size"] or not isinstance(action, dict):
                raise UploadError(6, "lfs_remote_verification", "Remote LFS batch did not confirm an expected object and byte length.")
            method = check_download_action(action)
            verified.append({**requested, "availability": method})
    return {"status": "PASS", "objects": verified, "object_count": len(verified), "bytes": sum(item["size"] for item in verified), "full_objects_redownloaded": False, "signed_urls_stored_or_logged": False}


def upload(release: Path, branch: str) -> dict:
    release = release.absolute()
    manifest, manifest_sha = verify_release(release)
    if release.resolve() == Path("D:/skillloop").resolve():
        raise UploadError(2, "release_verification", "The original research checkout is not a release directory.")
    authorization = credentials(release)
    repo = request_json("https://api.github.com/repos/" + REPOSITORY, authorization)
    if repo.get("full_name", "").lower() != REPOSITORY.lower() or repo.get("private") is not True or repo.get("permissions", {}).get("push") is not True or repo.get("archived"):
        raise UploadError(3, "private_repository_guard", "Target must be the authorized private, writable, unarchived repository.")
    git(release, ["check-ref-format", "--branch", branch])
    local_git = release / ".git"
    if local_git.exists():
        if not local_git.is_dir() or local_git.is_symlink():
            raise UploadError(4, "local_git", "Existing .git must be a local directory, never a worktree pointer.")
        current = git(release, ["branch", "--show-current"]).stdout.strip()
        if current != branch:
            raise UploadError(4, "local_git", "Existing release repository is on a different branch; it is preserved.")
    else:
        git(release, ["init", "-b", branch])
    top = git(release, ["rev-parse", "--show-toplevel"]).stdout.strip()
    if Path(top).resolve() != release.resolve():
        raise UploadError(4, "local_git", "Git top-level directory is not the isolated release directory.")
    origin = git(release, ["remote", "get-url", "origin"], allowed=(0, 2))
    if origin.returncode == 2:
        git(release, ["remote", "add", "origin", REMOTE])
    elif origin.stdout.strip().removesuffix(".git") != REMOTE.removesuffix(".git"):
        raise UploadError(4, "local_git", "Existing release origin is not the authorized private repository.")
    owner = repo.get("owner", {})
    login = owner.get("login", "jiaotangbuding177")
    for key, fallback in (("user.name", login), ("user.email", str(owner.get("id", "")) + "+" + login + "@users.noreply.github.com")):
        existing = git(release, ["config", "--get", key], allowed=(0, 1))
        if not existing.stdout.strip():
            git(release, ["config", "--local", key, fallback])
    # Isolate hooks and transfer endpoints from any inherited global settings.
    # No global hook directory or unrelated LFS endpoint is modified or used.
    git(release, ["config", "--local", "core.hooksPath", (local_git / "hooks").as_posix()])
    git(release, ["config", "--local", "lfs.url", REMOTE + "/info/lfs"])
    git(release, ["config", "--local", "lfs.pushurl", REMOTE + "/info/lfs"])
    git(release, ["lfs", "install", "--local"])
    for part in manifest["parts"]:
        attributes = git(release, ["check-attr", "filter", "--", part["path"]]).stdout.strip()
        if not attributes.endswith(": filter: lfs"):
            raise UploadError(4, "local_lfs", "Every dist part must be covered by the LFS filter before staging.")
    git(release, ["add", "--all", "--", "."])
    for part in manifest["parts"]:
        pointer = git(release, ["show", ":" + part["path"]]).stdout
        if "version https://git-lfs.github.com/spec/v1" not in pointer or "oid sha256:" + part["sha256"] not in pointer.splitlines() or "size " + str(part["bytes"]) not in pointer.splitlines():
            raise UploadError(4, "local_lfs", "Staged file is not the expected verified LFS pointer.")
    changed = git(release, ["diff", "--cached", "--quiet", "--exit-code"], allowed=(0, 1))
    if changed.returncode:
        git(release, ["commit", "-m", "Deliver WRD training dataset and verified offline preparation tools"])
    data_commit = git(release, ["rev-parse", "HEAD"]).stdout.strip()
    git(release, ["lfs", "fsck"], stage="local_lfs_fsck")
    print(json.dumps({"stage": "push_data", "parts": len(manifest["parts"]), "bytes": manifest["compressed_bytes"]}), flush=True)
    git(release, ["push", "-u", "origin", branch], code=5, stage="push_data")
    remote_head(release, branch, data_commit)
    lfs = verify_remote_lfs(manifest, authorization)
    receipt = {
        "schema_version": "wrd-private-upload-receipt-v1",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/" + REPOSITORY,
        "repository_private": True,
        "remote_ref": "refs/heads/" + branch,
        "data_commit": data_commit,
        "data_commit_matches_remote": True,
        "package_manifest_sha256": manifest_sha,
        "git_push": "SUCCESS",
        "git_lfs_pre_push": "SUCCESS",
        "local_lfs_fsck": "PASS",
        "remote_lfs": lfs,
        "note": "The receipt is committed separately. The final receipt commit is reported by the CLI after its remote reference is verified; this file cannot contain its own commit hash.",
    }
    receipt_path = release / "UPLOAD_RECEIPT.json"
    temporary = release / "UPLOAD_RECEIPT.json.tmp"
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(receipt_path)
    git(release, ["add", "--", "UPLOAD_RECEIPT.json"], code=7, stage="receipt_commit")
    git(release, ["commit", "-m", "Record private upload and remote LFS availability verification"], code=7, stage="receipt_commit")
    git(release, ["push", "origin", branch], code=7, stage="receipt_push")
    final_head = git(release, ["rev-parse", "HEAD"], code=7, stage="receipt_commit").stdout.strip()
    remote_head(release, branch, final_head, code=7)
    return {"status": "UPLOADED_AND_VERIFIED", "repository": receipt["repository"], "repository_private": True, "branch": branch, "data_commit": data_commit, "final_head": final_head, "remote_lfs_objects": lfs["object_count"], "remote_lfs_bytes": lfs["bytes"], "package_manifest_sha256": manifest_sha, "receipt": str(receipt_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    arguments = parser.parse_args()
    try:
        result = upload(arguments.release, arguments.branch)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except UploadError as failure:
        print(json.dumps({"status": "FAILED_RELEASE_PRESERVED", "stage": failure.stage, "exit_code": failure.code, "error": str(failure)}), file=sys.stderr, flush=True)
        return failure.code
    except (OSError, ValueError, TypeError, KeyError) as failure:
        # Do not print exception strings from network/process libraries: they can
        # include URLs. Root may inspect local state and choose a manual fallback.
        print(json.dumps({"status": "FAILED_RELEASE_PRESERVED", "stage": "unexpected_local_error", "exit_code": 8, "exception_type": type(failure).__name__}), file=sys.stderr, flush=True)
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
