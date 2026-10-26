"""Freeze a small, reproducible stratified qualitative review queue.

Excerpts support only bounded local judgements, never population quality rates.
"""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_quality_v8"
SOURCE = ROOT / "output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz"


def flatten(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    pieces = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            pieces.append(block.get("text", ""))
        elif block.get("type") == "toolCall":
            pieces.append(json.dumps({"tool": block.get("name"), "arguments": block.get("arguments")}, ensure_ascii=False))
    return "\n".join(pieces)


def shortened(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit * 3 // 4] + "\n[EXCERPT_NOT_FULL_CONTENT]\n" + text[-limit // 4:]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grouped = defaultdict(list)
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            grouped[row["kind"]].append(row)
    chosen = []
    for kind in ["screen", "prepare", "make", "actor", "review", "legacy"]:
        pool = sorted(grouped[kind], key=lambda row: hashlib.sha256(("v8-semantic-20261026/" + row["episode_id"]).encode()).hexdigest())
        selected, routes = [], set()
        for row in pool:
            if row["route_id"] in routes:
                continue
            routes.add(row["route_id"])
            selected.append(row)
            if len(selected) == 3:
                break
        for row in selected:
            messages = row["messages"]
            assistants = [(i, m) for i, m in enumerate(messages) if m.get("role") == "assistant" and flatten(m)]
            finals = [(i, m) for i, m in assistants if any(b.get("type") == "text" for b in m.get("content", []) if isinstance(b, dict))]
            writes = [(i, m) for i, m in assistants if any(b.get("type") == "toolCall" and b.get("name") in {"write", "edit", "apply_patch"} for b in m.get("content", []) if isinstance(b, dict))]
            points = []
            for label, point in [("last_write_or_edit", writes[-1] if writes else None), ("last_visible_text", finals[-1] if finals else assistants[-1] if assistants else None)]:
                if point:
                    i, message = point
                    points.append({"label": label, "target_message_index": i, "source_event_line": row.get("source_event_lines", [])[i] if len(row.get("source_event_lines", [])) > i else None, "target_characters": len(flatten(message)), "target_excerpt": shortened(flatten(message), 2200), "preceding_message_excerpt": shortened(flatten(messages[i - 1]), 1100) if i else "", "following_message_excerpt": shortened(flatten(messages[i + 1]), 850) if i + 1 < len(messages) else ""})
            chosen.append({"episode_id": row["episode_id"], "old_kind_not_gold": kind, "route_id": row["route_id"], "status": row["status"], "native_verified": row["native_verified"], "source_ids": row["source_ids"], "source_event_archive_path": row["archive_path"], "messages": len(messages), "initial_user_excerpt": shortened(flatten(messages[0]), 1500), "points": points, "review_scope": "Selected local windows only; no full-episode semantic correctness assertion."})
    with (OUT / "SEMANTIC_SAMPLE_WINDOWS.jsonl").open("w", encoding="utf-8") as handle:
        for row in chosen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (OUT / "SEMANTIC_SAMPLE_PROTOCOL.json").write_text(json.dumps({"sampling": "3 distinct routes per old stage, deterministic SHA ordering seed v8-semantic-20261026; local last-write/last-visible windows", "cases": len(chosen), "no_global_quality_rate_inferred": True, "source_path": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "training_started": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(chosen), "by_old_stage": {k: sum(x["old_kind_not_gold"] == k for x in chosen) for k in grouped}}))


if __name__ == "__main__":
    main()
