"""Combine source/outcome/AI-review and privacy overlays without editing sources."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    out = base / 'curated_reasoning'
    out.mkdir(exist_ok=False)
    review = json.loads((base / 'SSE_SEMANTIC_SAMPLE_REVIEW.json').read_text(encoding='utf-8'))
    semantic_holds = {r['id'] for r in review['sample_reviews']
                      if r['process_disposition'] == 'needs_context_and_data_faithfulness_boundary'}
    sse_allowed = {r['id'] for r in rows(base / 'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz')}
    outcomes = {r['id']: r for r in rows(base / 'controlled/sse_action_outcome.labels.jsonl.gz')}
    scope_by_run = {r['run_path']: r for r in rows(base / 'controlled/raw_scope_review.by_run.jsonl.gz')}
    counts = Counter()
    with gzip.open(out / 'controlled.original_reasoning32k.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as target:
        for r in rows(base / 'raw_reasoning_evolution_final/historical_original_reasoning_records.jsonl.gz'):
            counts['controlled_source_pairs'] += 1
            if r['id'] in semantic_holds:
                counts['semantic_boundary_hold_pairs'] += 1
                continue
            if r['total_tokens'] > 32768 or not r['supervised_tokens']:
                counts['overlength_or_zero_loss_not_selected'] += 1
                continue
            r['training_admitted'] = True
            r['training_admission_level'] = 'SOURCE_AND_EXECUTION_COMPATIBLE_HISTORICAL_TEACHER_SILVER'
            r['source_role_audit_pending'] = False
            r['source_scope_review_sha256'] = digest(base / 'RAW_SCOPE_REVIEW.json')
            r['semantic_sample_review_applied_not_full_semantic_gold'] = True
            target.write(js(r) + '\n')
            counts['controlled_positive_pairs32k'] += 1
            counts['controlled_processed_tokens'] += r['total_tokens']
            counts['controlled_supervised_tokens'] += r['supervised_tokens']
            counts['controlled_reasoning_positive_pairs'] += bool(r['original_reasoning_characters'])
            counts['controlled_reasoning_tokens'] += r['supervised_tokens_by_component'].get('R', 0)
            counts['controlled_reasoning_boundary_tokens'] += r['supervised_tokens_by_component'].get('R_BOUNDARY_MIXED', 0)
    public = out / 'public'
    public.mkdir()
    handles = {k: gzip.open(public / (k + '.pairs.jsonl.gz'), 'wt', encoding='utf-8', newline='\n')
               for k in ('sse_core', 'historical_generation', 'historical_actor_aux')}
    with gzip.open(out / 'PUBLIC_SCOPE_QUALITY_INDEX.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as index:
        for source_scope in ('sse', 'raw'):
            p = base / 'reasoning_privacy_projection/local_restricted' / (source_scope + '.cleaned_all.jsonl.gz')
            for r in rows(p):
                reasons = []
                role = None
                if source_scope == 'sse':
                    if r['id'] not in sse_allowed:
                        reasons.append('historical_formal_source_or_unmapped')
                    if r['id'] in outcomes and outcomes[r['id']]['definite_negative_action']:
                        reasons.append('original_execution_rejected_positive_action')
                    if r['id'] in semantic_holds:
                        reasons.append('semantic_data_faithfulness_boundary_pending')
                    role = 'sse_core'
                else:
                    original_scope = scope_by_run.get(r.get('run_path'), {})
                    if original_scope.get('reviewed_scope') != 'source_proven_learning_development_candidate':
                        reasons.append('source_scope_not_confirmed_nonformal')
                    role = 'historical_generation' if r['role_scope'] == 'historical_skill_generation_candidate' else 'historical_actor_aux'
                if not r.get('publication_approved'):
                    reasons.append('privacy_projection_hold')
                allowed = not reasons
                counts['public_projection_rows_examined'] += 1
                if allowed:
                    r['source_role_audit_pending'] = False
                    r['source_scope_review_sha256'] = digest(base / 'RAW_SCOPE_REVIEW.json')
                    r['semantic_approved'] = False
                    r['training_admitted'] = False
                    r['candidate_tier'] = 'source-proven privacy-transformed teacher silver requires exact template compilation'
                    r['current_native_runtime_equivalence_claimed'] = False
                    if source_scope == 'sse':
                        r['original_action_outcome'] = outcomes[r['id']]['original_status']
                        r['original_finish_ready_is_not_current_skill_retain'] = True
                    handles[role].write(js(r) + '\n')
                    counts['public:' + role + ':pairs'] += 1
                    counts['public:' + role + ':reasoning_pairs'] += bool(r.get('original_reasoning_characters'))
                for why in reasons:
                    counts['hold:' + why] += 1
                index.write(js({'id': r['id'], 'source_scope': source_scope, 'role': role,
                                'public_source_and_quality_candidate': allowed,
                                'hold_reasons': reasons}) + '\n')
    for h in handles.values():
        h.close()
    report = {'schema_version': 'wrd-curated-reasoning-v4', 'counts': dict(counts),
              'source_scope_sha256': digest(base / 'RAW_SCOPE_REVIEW.json'),
              'action_outcome_sha256': digest(base / 'SSE_ACTION_OUTCOME_AUDIT.json'),
              'semantic_sample_sha256': digest(base / 'SSE_SEMANTIC_SAMPLE_REVIEW.json'),
              'semantic_hold_ids': sorted(semantic_holds),
              'source_original_records_modified': False, 'training_started': False,
              'human_gold': 0, 'historical_conditions_not_current_native_equivalence': True}
    (out / 'CURATED_REASONING_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js(report))


if __name__ == '__main__':
    main()
