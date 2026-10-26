"""Copy this census and exact hashes to the existing Git delivery checkout.

This packages address/statistical evidence, not the original workspace bodies.
It never starts a model, training, a production session or a Git push.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "output/20261026_wrd_raw_census_v7"
TARGET = ROOT / "output/20261025_wrd_training_dataset/git_release/census/20261026"


def main():
    summary = json.loads((SOURCE / "SUMMARY.json").read_text(encoding="utf-8"))
    review = json.loads((SOURCE / "REVIEW.json").read_text(encoding="utf-8"))
    assert not summary["training_started"]
    assert review.get("status") in {"PASS", "PASS_WITH_LIMITED_SCOPE"} and review.get("failure_count") == 0, "The independent census review must bind the final report."
    pins = {Path(item["path"]).name: item for item in review["reviewed_artifact_pins"]}
    for name in ["RAW_DATA_LOCATIONS.md", "SUMMARY.json", "ROOTS_ALL.csv"]:
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == pins[name]["sha256"], "Review does not bind current artifact: " + name
    TARGET.mkdir(parents=True, exist_ok=True)
    payload = []
    for source in sorted(SOURCE.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        if "partial_allocated_attempt1" in relative.parts or source.name in {"MANIFEST.json", "REMOTE_GIT_VERIFICATION.json", "LOCAL_PUBLICATION_PREPARATION.json"}:
            continue
        target = TARGET / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        payload.append(target)
    for source in sorted(Path(__file__).parent.glob("*.py")):
        target = TARGET / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        payload.append(target)
    artifacts = [{"path": str(path.relative_to(TARGET)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in payload]
    manifest = {
        "schema_version": "wrd-v7-census-delivery-manifest",
        "scope": "Original addresses, stat indexes, lineage references, old export coverage audit and review. Not a new admitted SFT dataset.",
        "payload_files": len(artifacts),
        "payload_bytes": sum(x["bytes"] for x in artifacts),
        "files": artifacts,
        "original_bodies_are_not_reuploaded_by_this_census_package": True,
        "partial_allocated_attempt1_preserved_in_original_workspace_not_in_this_package": True,
        "original226_training_boundary_unchanged": True,
        "training_started": False,
        "scripts_reproduction_environment": "Original D:/skillloop layout and original D/E source paths; scripts preserve the exact original research environment and are not portable launch configs.",
        "review_status_as_recorded": review.get("status"),
    }
    (TARGET / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {"target": str(TARGET), "payload_files": len(artifacts), "payload_bytes": manifest["payload_bytes"], "manifest_sha256": hashlib.sha256((TARGET / "MANIFEST.json").read_bytes()).hexdigest(), "training_started": False}
    (SOURCE / "LOCAL_PUBLICATION_PREPARATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
