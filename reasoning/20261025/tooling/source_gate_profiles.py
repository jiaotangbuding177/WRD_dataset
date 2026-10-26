"""Materialize strict direct-source profiles and preserve wider candidates.

Availability/catalog references are not called proven exposure. Pending-scope
records remain candidates; no implicit override of the protected-226 policy.
"""
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
    out = base / 'source_gated_profiles'
    out.mkdir(exist_ok=False)
    labels = {r['episode_id']: r for r in rows(base / 'controlled/native_source_split.labels.jsonl.gz')}
    correction_path = ROOT / 'output/20261026_wrd_strict226_expansion/STRICT_SOURCE_VISIBILITY_OVERRIDES.json'
    correction = json.loads(correction_path.read_text(encoding='utf-8')) if correction_path.is_file() else {'items': []}
    known_protected_body = {r['episode_id'] for r in correction['items']}
    counts, by_stage = Counter(), Counter()
    for scope in ('controlled', 'public'):
        for role in ('core32k', 'actor_aux32k'):
            source = base / 'curated_native' / (scope + '.' + role + '.jsonl.gz')
            with gzip.open(out / (scope + '.strict226.' + role + '.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as strict, \
                 gzip.open(out / (scope + '.scope_pending.' + role + '.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as pending, \
                 gzip.open(out / (scope + '.' + role + '.selection.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as select:
                for r in rows(source):
                    gate = labels[r['episode_id']]
                    eligible = gate.get('primary_source_scope_eligible') is True and r['episode_id'] not in known_protected_body
                    prefix = scope + ':' + role + ':'
                    counts[prefix + 'all_candidate_windows'] += 1
                    r['source_scope_gate'] = {
                        'label': gate['scope_label'], 'scope_label_sha256': digest(base / 'NATIVE_SOURCE_SPLIT_AUDIT.json'),
                        'protected_226_policy_overridden': False,
                        'actual_read_of_every_available_source_not_assumed': True,
                        'complete_transitive_dependency_independence_proven': False,
                    }
                    if eligible:
                        r['process_quality_silver'] = r.get('training_admitted') is True
                        r['training_manifest_admitted'] = False
                        r['training_admitted'] = False
                        r['training_admission_level'] = 'DIRECT_SOURCE_CANDIDATE_REQUIRES_VISIBILITY_OVERLAY_AND_RESOURCE_LINEAGE_REVIEW'
                        strict.write(js(r) + '\n')
                        counts[prefix + 'strict_windows'] += 1
                        counts[prefix + 'strict_processed_tokens'] += r['total_tokens']
                        counts[prefix + 'strict_supervised_tokens'] += r['supervised_tokens']
                        counts[prefix + 'strict_targets'] += sum(bool(t['owned_supervision_spans']) for t in r['targets'])
                        by_stage[scope + ':' + r['kind'] + ':windows'] += 1
                        by_stage[scope + ':' + r['kind'] + ':supervised_tokens'] += r['supervised_tokens']
                    else:
                        r['training_admitted'] = False
                        r['training_admission_level'] = 'SOURCE_SCOPE_PENDING_OR_PROTECTED_NOT_IN_STRICT_PROFILE'
                        pending.write(js(r) + '\n')
                        counts[prefix + 'scope_pending_windows'] += 1
                        counts[prefix + 'scope:' + gate['scope_label']] += 1
                    select.write(js({'id': r['id'], 'episode_id': r['episode_id'], 'source_record_sha256': hashlib.sha256(js(r).encode()).hexdigest(),
                                     'strict226_selected': eligible, 'scope_label': gate['scope_label'],
                                     'training_started': False}) + '\n')
    report = {'schema_version': 'wrd-source-gated-profiles-v4', 'counts': dict(counts), 'by_stage': dict(by_stage),
              'source_split_audit_sha256': digest(base / 'NATIVE_SOURCE_SPLIT_AUDIT.json'),
              'source_split_counts': json.loads((base / 'NATIVE_SOURCE_SPLIT_AUDIT.json').read_text(encoding='utf-8'))['counts'],
              'training_started': False, 'full_corpus_override_authorized': False,
              'user_confirmed_original226_isolation': True,
              'final_training_manifest_admitted_rows': 0,
              'strict_profile_is_not_complete_end_to_end_readiness': True,
              'note': 'Wider records retained as candidates; source availability alone is not asserted to be actual model exposure.'}
    (out / 'SOURCE_GATED_PROFILE_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js(report))


if __name__ == '__main__':
    main()
