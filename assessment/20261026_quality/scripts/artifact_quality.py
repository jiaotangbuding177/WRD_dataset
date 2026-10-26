"""Static checks of all 29 retained artifacts; no generated code is executed."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_quality_v8"
INDEX = ROOT / "output/20261026_wrd_raw_census_v7/skills29"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    packages, checks, imports = [], Counter(), Counter()
    for source in sorted(INDEX.glob("*.json")):
        graph = json.loads(source.read_text(encoding="utf-8"))
        folder = Path(graph["final_frozen_skill_root"])
        row = {"skill_id": graph["skill_id"], "frozen_root": str(folder), "files": [], "resource_path_mentions": []}
        for item in graph["final_files"]:
            path = Path(item["frozen_skill_file"])
            data = path.read_bytes()
            entry = {"relative_path": item["relative_path"], "bytes": len(data), "source_sha256": hashlib.sha256(data).hexdigest(), "hash_equal_final_manifest": hashlib.sha256(data).hexdigest() == item["sha256"]}
            checks["files"] += 1
            checks["manifest_hash_equal"] += entry["hash_equal_final_manifest"]
            if path.suffix.lower() in {".md", ".py", ".json", ".txt", ".yaml", ".yml", ".sh", ".js"}:
                try:
                    text = data.decode("utf-8-sig")
                    entry["utf8_decodable"] = True
                except UnicodeDecodeError:
                    text = ""
                    entry["utf8_decodable"] = False
                if path.suffix.lower() == ".py":
                    checks["python_files"] += 1
                    try:
                        tree = ast.parse(text, filename=item["relative_path"])
                        entry["python_ast_syntax"] = "pass"
                        checks["python_syntax_pass"] += 1
                        modules = set()
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                modules.update(alias.name.split(".")[0] for alias in node.names)
                            if isinstance(node, ast.ImportFrom) and node.module:
                                modules.add(node.module.split(".")[0])
                        entry["imported_modules_not_environment_validation"] = sorted(modules)
                        imports.update(modules)
                    except SyntaxError as error:
                        entry["python_ast_syntax"] = "fail"
                        entry["syntax_error"] = {"line": error.lineno, "message": error.msg}
                        checks["python_syntax_fail"] += 1
                if path.suffix.lower() == ".json":
                    checks["json_files"] += 1
                    try:
                        json.loads(text)
                        entry["json_parse"] = "pass"
                        checks["json_parse_pass"] += 1
                    except json.JSONDecodeError as error:
                        entry["json_parse"] = "fail"
                        entry["json_error_line"] = error.lineno
                        checks["json_parse_fail"] += 1
                if path.name == "SKILL.md":
                    row["homepage_characters"] = len(text)
                    header = re.match(r"\A---\s*\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
                    row["has_frontmatter"] = bool(header)
                    if header:
                        front = header.group(1)
                        row["frontmatter_name_field_present"] = bool(re.search(r"(?m)^name\s*:\s*\S", front))
                        row["frontmatter_description_field_present"] = bool(re.search(r"(?m)^description\s*:\s*\S", front))
                    # Exact file-like mentions only. Directories, globs and optional
                    # prose are not rejected by this bounded path existence check.
                    mentioned = set(re.findall(r"\b(?:scripts|templates|references|assets)/[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+", text))
                    for name in sorted(mentioned):
                        row["resource_path_mentions"].append({"mentioned_relative_path": name, "exists_in_frozen_package": (folder / name).is_file()})
                    row["headings"] = [line.strip()[:180] for line in text.splitlines() if line.startswith("#")]
                    row["homepage_source_path"] = str(path)
            row["files"].append(entry)
        packages.append(row)
    paths = [item for package in packages for item in package["resource_path_mentions"]]
    result = {"schema_version": "wrd-v8-retained-artifact-static-quality", "scope": "All 29 retained frozen packages, all 154 manifest files; static parser/path checks only, no runtime or semantic quality certification.", "retained_packages": len(packages), "counts": dict(checks), "homepages_with_frontmatter": sum(row["has_frontmatter"] for row in packages), "exact_resource_path_mentions": len(paths), "missing_exact_resource_mentions": [dict(skill_id=row["skill_id"], **item) for row in packages for item in row["resource_path_mentions"] if not item["exists_in_frozen_package"]], "imported_module_file_counts_not_dependency_availability": dict(imports), "packages": packages, "generated_scripts_executed": False, "runtime_replay_done": False, "training_started": False, "new_model_calls": 0}
    (OUT / "ARTIFACT_STATIC_QUALITY.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"retained_packages": len(packages), "counts": dict(checks), "resource_path_mentions": len(paths), "missing_exact_mentions": len(result["missing_exact_resource_mentions"])}))


if __name__ == "__main__":
    main()
