"""Recall development sources from complete original user requests.

Ranking supplies manageable batches to the existing task preparer; it does not
decide whether a task matches a workflow, reject a partial workflow, or create
tasks.  Callers keep the original user requests and attachments unchanged.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


# Exporter boilerplate is not a business request and occurs in nearly every
# conversation.  In particular, its word "回复" must not rank every source as
# an email-reply task.  The original text is never changed on disk or returned
# to the task preparer through this module.
_PREFIX = re.compile(r"^\s*(?:\[[^\]\n]{1,100}\]\s*)?请使用中文回复[，,]?除非用户明确使用其他语言[。.]?\s*")
_WORDS = re.compile(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*|[\u3400-\u9fff]+", re.I)
_STOP = {
    "this", "that", "with", "from", "have", "into", "then", "the", "and", "for",
    "或者", "以及", "一个", "可以", "需要", "不要", "根据", "进行", "相关", "当前",
    "用户", "每次", "直接", "已有", "输出", "输入", "结果", "文件", "内容", "说明",
    "使用", "处理", "步骤", "路线", "工作", "流程", "通用", "保存", "返回", "路径",
    "替代", "复用", "完成", "要求", "材料", "信息", "方面", "什么", "这个", "我们",
}
_STEP_FIELDS = ("operation", "action", "method", "tools", "input_types", "output_types")
_GENERAL_OPERATIONS = {
    "阅读", "全文", "起草", "润色", "导出", "格式", "成文", "整理", "归纳", "指定",
    "结合", "重新", "组织", "提供", "附件", "语言", "模板", "固定", "结构", "记录",
}


def _strings(value):
    """Read semantic values, not JSON keys, paths, evidence, or old reviews."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for key in _STEP_FIELDS:
            if key in value:
                yield from _strings(value[key])


def _tokens(text):
    terms = []
    for match in _WORDS.finditer(text.lower()):
        word = match.group()
        if "\u3400" <= word[0] <= "\u9fff":
            # Overlapping short phrases avoid a heavyweight segmenter and work
            # with both terse Chinese requests and mixed Chinese/English JD.
            for size in (2, 3, 4):
                for start in range(len(word) - size + 1):
                    term = word[start:start + size]
                    if term not in _STOP:
                        terms.append(term)
        elif word not in _STOP:
            terms.append(word)
            if "-" in word or "_" in word:
                terms.extend(part for part in re.split(r"[-_]", word) if part not in _STOP)
    return terms


def _content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_content(v) for v in value)
    if isinstance(value, dict):
        # Multimodal messages often carry text alongside a file/image URL.  A
        # file name or serialized protocol key is not user intent.
        return _content(value.get("text", value.get("content", "")))
    return ""


def _path(value):
    if isinstance(value, dict):
        return value.get("path") or (value.get("pin") or {}).get("path")
    return str(value) if value else None


def source_materials(binding):
    """Resolve only the real files explicitly attached to this source.

    This is input wiring, not filename search or a new admission check. A
    source's unavailable/reconstructed bytes remain unavailable. An alternate
    pin path is usable only when it is an exact, existing declared path.
    """
    available, unavailable = [], []
    for number, material in enumerate(binding.get("materials", []), 1):
        if not material.get("eligible_real_input"):
            continue
        paths = [material.get("path"), (material.get("pin") or {}).get("path")]
        path = next((Path(value) for value in paths if value and Path(value).is_file()), None)
        if path is None:
            unavailable.append(_path(material) or material.get("relative_path", "unknown"))
            continue
        available.append({"path": str(path.resolve()), "filename": path.name, "number": number})
    return available, unavailable


@dataclass(frozen=True)
class _Request:
    source_id: str
    message_id: str
    request_index: int
    start: int
    end: int
    length: int
    request_chars: int


@dataclass
class _Corpus:
    sources: tuple[str, ...]
    requests: list[_Request]
    postings: dict
    mean_length: float


def _binding_signature(bindings):
    rows = []
    for source_id, binding in bindings.items():
        path = _path(binding.get("conversation"))
        if not path:
            continue
        try:
            candidate = Path(path)
            stat = candidate.stat()
            if candidate.is_file():
                rows.append((str(source_id), str(candidate.resolve()), stat.st_size, stat.st_mtime_ns))
        except OSError:
            continue
    return tuple(sorted(rows))


@lru_cache(maxsize=2)
def _index(signature):
    requests, postings, readable = [], defaultdict(list), []
    for source_id, path, _size, _mtime in signature:
        try:
            conversation = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError):
            continue
        readable.append(source_id)
        user_index = 0
        for message in conversation.get("messages", []):
            if message.get("role") != "user":
                continue
            text = _content(message.get("content", ""))
            prefix = _PREFIX.match(text)
            first = prefix.end() if prefix else 0
            # Every request is indexed in full.  Overlapping windows bound
            # length normalisation so a brief late request is not drowned by
            # an earlier 20,000-character knowledge-graph export.
            # Separate paragraphs keep a short actual delegation from being
            # length-penalised together with the letter/reference below it.
            spans = []
            cursor = first
            for paragraph in re.split(r"(\n\s*\n)", text[first:]):
                if paragraph.strip():
                    for offset in range(0, len(paragraph), 240):
                        spans.append((cursor + offset, min(cursor + offset + 320, cursor + len(paragraph))))
                cursor += len(paragraph)
            for start, end in spans:
                counts = Counter(_tokens(text[start:end]))
                if not counts:
                    continue
                doc_id = len(requests)
                requests.append(_Request(source_id, str(message.get("id", user_index)),
                                         user_index, start, end, sum(counts.values()), len(text) - first))
                for term, count in counts.items():
                    postings[term].append((doc_id, count))
            user_index += 1
    mean = sum(request.length for request in requests) / max(1, len(requests))
    return _Corpus(tuple(readable), requests, dict(postings), mean)


def _query(route):
    weights = defaultdict(float)
    for key, weight in (("name", 6.0), ("steps", 0.8), ("reuse_reason", 0.4)):
        for value in _strings(route.get(key)):
            # Split connective words before extracting Chinese phrases, so
            # "阅读与回复" does not invent a rare high-IDF concept "读与".
            value = re.sub(r"[与和及的按为从并对中时后前]", " ", value)
            for phrase in sorted(_STOP | _GENERAL_OPERATIONS, key=len, reverse=True):
                if not phrase.isascii():
                    value = value.replace(phrase, " ")
            for term in set(_tokens(value)):
                weights[term] += weight
    if not weights:
        for term in set(_tokens(str(route.get("id", "")))):
            weights[term] = 1.0
    return weights


def _explicit(route):
    sources = []
    for key in ("task_source_ids", "development_source_ids", "candidate_source_ids"):
        value = route.get(key, [])
        sources.extend([value] if isinstance(value, str) else value or [])
    for task in route.get("available_tasks", []) or []:
        if isinstance(task, dict) and task.get("source_id"):
            sources.append(task["source_id"])
    return list(dict.fromkeys(sources))


def rank_source_details(route, bindings):
    """Return ranked source metadata, retaining every readable non-learning source.

    `requests` identifies the best original user messages and offsets for a
    readable candidate summary.  It is evidence for recall, not a matching
    verdict; the preparer can inspect the entire original user projection.
    """
    corpus = _index(_binding_signature(bindings))
    learned = set(route.get("learning_source_ids", route.get("source_ids", [])) or [])
    readable = set(corpus.sources) - learned
    explicit = [source_id for source_id in _explicit(route) if source_id in readable]
    query = _query(route)
    scores, matches = defaultdict(float), defaultdict(set)
    count = len(corpus.requests)
    for term, weight in query.items():
        posting = corpus.postings.get(term, [])
        if not posting:
            continue
        idf = min(4.0, math.log1p((count - len(posting) + 0.5) / (len(posting) + 0.5)))
        # Adjacent Chinese ngrams are correlated; discount the longer ones
        # slightly instead of tripling the influence of an identical phrase.
        weight *= 1.0 if term.isascii() or len(term) == 2 else 0.3
        for doc_id, frequency in posting:
            request = corpus.requests[doc_id]
            if request.source_id not in readable:
                continue
            length_factor = 0.3 + 0.7 * request.length / max(1.0, corpus.mean_length)
            # Repeated paragraphs/knowledge exports do not represent repeated
            # delegations.  Bound local TF as well as total source aggregation.
            frequency = min(frequency, 3)
            score = weight * idf * frequency * 2.2 / (frequency + 1.2 * length_factor)
            scores[doc_id] += score
            matches[doc_id].add(term)
    per_source = defaultdict(list)
    for doc_id, score in scores.items():
        request = corpus.requests[doc_id]
        # Independent concepts together are more useful than a rare accidental
        # bigram alone.  Correlated nested ngrams count only once; this is a
        # relevance boost, never an admission rule or exclusion threshold.
        independent = [term for term in matches[doc_id]
                       if not any(term != other and term in other for other in matches[doc_id])]
        score *= 1.0 + 0.3 * min(3, max(0, len(independent) - 1))
        score /= 1.0 + 0.1 * math.log1p(request.request_chars / 320)
        per_source[request.source_id].append((score, doc_id))
    result = []
    for source_id in readable:
        top = sorted(per_source[source_id], reverse=True)[:3]
        # A conversation with more messages must not gain relevance just by
        # being longer: rank by its best actual request/window, not their sum.
        result.append({
            "source_id": source_id,
            "score": round(top[0][0], 6) if top else 0.0,
            "explicit": source_id in explicit,
            "requests": [{
                "message_id": corpus.requests[doc_id].message_id,
                "request_index": corpus.requests[doc_id].request_index,
                "char_start": corpus.requests[doc_id].start,
                "char_end": corpus.requests[doc_id].end,
                "score": round(score, 6),
                "matched_terms": sorted(matches[doc_id]),
            } for score, doc_id in top],
        })
    priority = {source_id: index for index, source_id in enumerate(explicit)}
    result.sort(key=lambda row: (0, priority[row["source_id"]]) if row["explicit"]
                else (1, -row["score"], row["source_id"]))
    return result


def rank_sources(route, bindings):
    """All readable non-learning source IDs; explicit choices stay first."""
    return [row["source_id"] for row in rank_source_details(route, bindings)]


def select_sources(route, bindings, seen=(), limit=12):
    """Next small batch; previous zero-case sources are not sent again."""
    if limit <= 0:
        return []
    seen = set(seen or ())
    return [source_id for source_id in rank_sources(route, bindings)
            if source_id not in seen][:limit]


def build_catalog(bindings, workdir):
    """Write the complete user-only search catalog for one prepare session.

    No assistant answers or reconstructed examples enter the catalog. Native
    tools can search the compact per-request JSONL and
    read a source's complete original projection when useful.  The material
    manifest identifies only that source's existing real inputs; it does not
    silently bind the entire corpus's attachments into a business task. Real
    attachments are readable in this preparation session even when a source
    was not in the short ranked batch; the later actor receives only fixtures
    explicitly selected for its own source.

    The return value uses the pipeline's ordinary resource schema.  A caller
    can mount its `resources` unchanged, or reuse the two path values in its
    own input manifest.  Generating this local catalog never calls a model.
    """
    directory = Path(workdir) / "recall_catalog"
    directory.mkdir(parents=True, exist_ok=True)
    requests_path = directory / "user_requests.jsonl"
    materials_path = directory / "source_materials.json"
    projection_dir = directory / "sources"
    projection_dir.mkdir(exist_ok=True)
    sources, request_count, material_resources = [], 0, {}
    with requests_path.open("w", encoding="utf-8", newline="\n") as stream:
        for source_id, path, _size, _mtime in _binding_signature(bindings):
            try:
                conversation = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, ValueError):
                continue
            binding = bindings[source_id]
            requests = []
            for message in conversation.get("messages", []):
                if message.get("role") != "user":
                    continue
                row = {"id": message.get("id"), "text": _content(message.get("content", ""))}
                request_index = len(requests)
                requests.append(row)
                stream.write(json.dumps({"source_id": source_id, "message_id": row["id"],
                                         "request_index": request_index, "text": row["text"]},
                                        ensure_ascii=False) + "\n")
                request_count += 1
            name = re.sub(r"[^\w.-]+", "_", source_id).strip("._") or "source"
            projection = projection_dir / (name + ".json")
            projection.write_text(json.dumps({"source_id": source_id, "requests": requests},
                                              ensure_ascii=False) + "\n", encoding="utf-8")
            materials, unavailable = source_materials(binding)
            for material in materials:
                # Multiple sources can refer to the very same exported file.
                # Copy that exact path once, retaining each source's explicit
                # association. Never infer an association from a filename.
                key = str(Path(material["path"]).resolve())
                if key not in material_resources:
                    name_part = re.sub(r"[^\w.-]+", "_", material["filename"]).strip("._") or "file"
                    mount = f"inputs/recall_materials/{len(material_resources) + 1:04d}/{name_part}"
                    material_resources[key] = {"path": material["path"], "mount": mount}
                resource = material_resources[key]
                material.update({"mount": resource["mount"],
                                 "native_path": "/workspace/" + resource["mount"]})
            sources.append({
                "source_id": source_id,
                "original_line": binding.get("physical_line"),
                "title": conversation.get("title", ""),
                "category": conversation.get("task_category", ""),
                "user_input": "/workspace/inputs/recall_catalog/sources/" + name + ".json",
                "materials": materials,
                "unavailable_materials": unavailable,
                "limitations": binding.get("limitations", []),
            })
    materials_path.write_text(json.dumps({"sources": sources}, ensure_ascii=False) + "\n", encoding="utf-8")
    total_bytes = sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())
    return {
        "resources": [{"path": str(directory.resolve()), "mount": "inputs/recall_catalog"},
                      *material_resources.values()],
        "requests_path": str(requests_path.resolve()),
        "materials_path": str(materials_path.resolve()),
        "native_requests_path": "/workspace/inputs/recall_catalog/user_requests.jsonl",
        "native_materials_path": "/workspace/inputs/recall_catalog/source_materials.json",
        "source_count": len(sources), "request_count": request_count, "bytes": total_bytes,
        "material_file_count": len(material_resources),
        "material_bytes": sum(Path(row["path"]).stat().st_size for row in material_resources.values()),
    }
