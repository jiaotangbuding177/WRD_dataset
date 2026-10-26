"""Independent exact protected-text and attachment check of positive arrays.

CPU tokenizer decode only. Long exact overlaps are evidence for review, not a
claim that absence of a match proves semantic independence or resolves lineage.
"""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
SEQ = ROOT / 'output/20261026_wrd_sequences_v6'
OUT = ROOT / 'output/20261026_wrd_lineage_v6'
DEC = json.JSONDecoder()


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def norm(v):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', v))


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def leaf_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for child in v.values():
            yield from leaf_strings(child)
    elif isinstance(v, list):
        for child in v:
            yield from leaf_strings(child)


def nested_texts(text):
    yield text
    pos = 0
    while pos < len(text):
        match = re.search(r'[\[{]', text[pos:])
        if not match:
            break
        start = pos + match.start()
        try:
            obj, end = DEC.raw_decode(text, start)
        except ValueError:
            pos = start + 1
            continue
        yield from leaf_strings(obj)
        pos = end


def main():
    helper = ROOT / 'research/data_prep/wrd_training_fullchain/raw_scope_review_v4.py'
    spec = importlib.util.spec_from_file_location('prior_exact_formal_inventory', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    all_texts, _, inputs, original_refs = module.formal_inventory()
    contracts = [p for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl') if p.parent.parent.name in {
        'enterprise_split_v9_20261010', 'enterprise_input_closed_v11_20261012',
        'enterprise_original_inputs_v10_20261011', 'enterprise_final_delivery_v8_20261010'}]
    original226 = {json.loads(line)['session_id'] for p in contracts for line in p.open(encoding='utf-8-sig') if line.strip()}
    assert len(original226) == 226
    allowed_sid_hashes = {hashlib.sha256(sid.encode()).hexdigest() for sid in original226}
    protected = {text: [r for r in refs if r.get('session_id_sha256') in allowed_sid_hashes or r['source_file'].endswith('tasks250.json')]
                 for text, refs in all_texts.items()}
    protected = {text: refs for text, refs in protected.items() if refs}
    patterns = {text: refs for text, refs in protected.items() if len(text) >= 128}
    attachment_sha = set()
    for source in inputs:
        p = ROOT / source['path']
        if source.get('fixed_current_250'):
            values = json.loads(p.read_text(encoding='utf-8-sig'))
            attachment_sha.update(a['sha256'] for item in values for a in item.get('resources', []) if isinstance(a, dict) and a.get('sha256'))
        else:
            for line in p.open(encoding='utf-8-sig'):
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get('session_id') in original226:
                    attachment_sha.update(a['sha256'] for a in item.get('attachments', []) if a.get('sha256'))
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets/primary_14b',
                                               local_files_only=True, trust_remote_code=False)
    hits, checked = [], []
    for bank in ('native_core', 'actor_aux', 'reasoning'):
        path = SEQ / 'controlled' / ('admitted.' + bank + '32k.jsonl.gz')
        if not path.is_file():
            continue
        count = 0
        for row in rows(path):
            if not row.get('supervised_tokens'):
                continue
            rendered = tokenizer.decode(row['input_ids'], skip_special_tokens=False)
            candidates = list(dict.fromkeys(norm(t) for t in nested_texts(rendered) if len(t) >= 128))
            for pattern, refs in patterns.items():
                if any(pattern in candidate for candidate in candidates if len(candidate) >= len(pattern)):
                    hits.append({'bank': bank, 'row_id': row['id'], 'episode_id': row.get('episode_id'),
                                 'source_original_pair_id': row.get('source_original_pair_id'),
                                 'protected_text_normalized_sha256': hashlib.sha256(pattern.encode()).hexdigest(),
                                 'normalized_characters': len(pattern), 'protected_evidence_references': refs,
                                 'business_body_exported': False})
            count += 1
        checked.append({'bank': bank, 'rows': count, 'file_sha256': sha(path)})
    resource_hits, resource_count = [], 0
    for name in ('admitted.resource_closure.index.jsonl.gz', 'admitted.reasoning_resource_closure.index.jsonl.gz'):
        path = SEQ / 'controlled' / name
        if not path.is_file():
            continue
        for node in rows(path):
            digest = node.get('sha256') or (node.get('file_identity') or {}).get('sha256')
            resource_count += 1
            if digest in attachment_sha:
                resource_hits.append({'index': name, 'node_id': node.get('node_id'), 'sha256': digest,
                                      'requires_shared_attachment_identity_review': True})
    result = {'schema_version': 'wrd-v6-exact-protected-content-attachment-check',
              'status': 'PASS_EXACT_CHECKS_ONLY' if not hits and not resource_hits else 'REVIEW_EXACT_OVERLAPS_REQUIRED',
              'positive_arrays_checked': checked, 'protected_inventory_sources': inputs,
              'original_protected_contract_source_ids': len(original226),
              'additional_current_formal250_kept_isolated': True,
              'protected_normalized_body_patterns': len(patterns),
              'short_common_texts_not_used_as_substring_provenance': len(protected) - len(patterns),
              'minimum_normalized_characters_for_exact_substring_evidence': 128,
              'protected_attachment_hashes': len(attachment_sha), 'positive_resource_index_records_checked': resource_count,
              'exact_body_overlaps': hits, 'exact_attachment_hash_overlaps': resource_hits,
              'semantic_near_duplicate_independence_proven_by_this_check': False,
              'absence_of_match_does_not_replace_resource_lineage': True,
              'training_started': False, 'model_weights_loaded': False, 'gpu_used': False,
              'business_api_called': False, 'script_sha256': sha(Path(__file__))}
    p = OUT / 'EXACT_PROTECTED_CONTENT_CHECK.json'
    if p.is_file():
        history = OUT / 'history/exact_scope_checks'
        history.mkdir(parents=True, exist_ok=True)
        prior = history / (sha(p) + '.json')
        if not prior.exists():
            shutil.copyfile(p, prior)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'rows': sum(x['rows'] for x in checked),
                      'body_overlaps': len(hits), 'attachment_overlaps': len(resource_hits)}))


if __name__ == '__main__':
    main()
