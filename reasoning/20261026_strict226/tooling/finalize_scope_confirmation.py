"""Apply the human-confirmed original226 boundary; offline, no training entrypoint.

Old evidence/arrays remain unchanged. New candidate projections fail closed and
the final training manifest is deliberately empty until lineage review passes.
"""
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_strict226_expansion'
V4 = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
PLAN = ROOT / 'research/plans/20261025_wrd_reasoning_distillation_v4'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE / 'reasoning/20261026_strict226'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    review = read(OUT / 'VISIBILITY_REVIEW.json')
    override = read(OUT / 'STRICT_SOURCE_VISIBILITY_OVERRIDES.json')
    prefix = read(OUT / 'prefixes/PREFIX_RECOVERY_REPORT.json')
    qa = read(OUT / 'prefixes/INDEPENDENT_PREFIX_QA.json')
    assert review['actual_safe_new_training_admissions'] == 0
    assert len(override['items']) == 1
    assert prefix['proved_initial_discovery_prefix_episodes'] == 9
    # The QA schema is independent; require an explicit successful status.
    assert qa.get('status') == 'PASS_FOR_NARROW_INITIAL_DISCOVERY_PREFIX_ONLY', 'independent prefix QA not complete'
    assert qa.get('failures') == [], 'independent prefix QA has failures'
    DEST.mkdir(exist_ok=False)
    hold = {x['episode_id'] for x in override['items']}
    policy = {
        'schema_version': 'wrd-original226-human-confirmed-scope-v5',
        'confirmed_date': '2026-10-26',
        'user_decision': '继续隔离原226来源，保留原评测边界',
        'original_evaluation_boundary_retained': True,
        'protected_original_sources': 226,
        'protected_source_body_answer_feedback_and_derived_resource_may_train': False,
        'protected_sources_may_select_checkpoints_or_calibrate_thresholds': False,
        'later_evolution_relabel_overrides_original_boundary': False,
        'scope_question_pending': False,
        'quality_silver_is_not_final_source_admission': True,
        'absence_of_source_id_match_is_not_an_isolation_proof': True,
        'final_training_manifest_admitted_rows': 0,
        'full_autonomous_target_training_ready': False,
        'training_started': False,
    }
    save(OUT / 'SCOPE_CONFIRMATION.json', policy)
    manifest = dict(policy, schema_version='wrd-final-training-admission-manifest-v5',
                    admitted_datasets=[], admitted_parent_samples=[], admitted_rows=0,
                    reason='Transitive resource/source isolation and full-chain coverage remain unproven; no implicit fallback to older entrypoints.',
                    recommended_dataset=None, training_execution_authorized=False)
    save(OUT / 'FINAL_TRAINING_MANIFEST.json', manifest)
    counts, by_stage = {}, {}
    for scope in ('controlled', 'public'):
        for role in ('core32k', 'actor_aux32k'):
            key = scope + ':' + role
            c, stages = Counter(), Counter()
            source = V4 / 'source_gated_profiles' / (scope + '.strict226.' + role + '.jsonl.gz')
            output = []
            for r in rows(source):
                c['v4_baseline_windows'] += 1
                if r['episode_id'] in hold:
                    c['newly_proven_protected_body_windows_removed'] += 1
                    c['removed_candidate_supervised_tokens'] += r['supervised_tokens']
                    continue
                c['current_direct_source_candidate_windows'] += 1
                c['candidate_supervised_tokens_before_disabled_loss'] += r['supervised_tokens']
                c['processed_input_tokens'] += r['total_tokens']
                c['candidate_owned_targets'] += sum(bool(t['owned_supervision_spans']) for t in r['targets'])
                c['le16k_candidate_windows'] += int(r['total_tokens'] <= 16384)
                c['le32k_candidate_windows'] += int(r['total_tokens'] <= 32768)
                stages[r['kind'] + ':windows'] += 1
                stages[r['kind'] + ':candidate_supervised_tokens'] += r['supervised_tokens']
                if scope == 'public':
                    r = deepcopy(r)
                    r['candidate_original_supervision_spans'] = r['supervision_spans']
                    r['candidate_original_supervised_tokens'] = r['supervised_tokens']
                    r['candidate_original_supervised_tokens_by_component'] = r['supervised_tokens_by_component']
                    r['candidate_original_supervision_spans_sha256'] = r['supervision_spans_sha256']
                    r['candidate_original_targets'] = deepcopy(r['targets'])
                    r['supervision_spans'] = []
                    r['supervised_tokens'] = 0
                    r['supervised_tokens_by_component'] = {}
                    r['supervision_spans_sha256'] = hashlib.sha256(b'[]').hexdigest()
                    for t in r['targets']:
                        t['owned_supervision_spans'] = []
                        t['supervised_tokens'] = 0
                    r['process_quality_silver'] = True
                    r['training_admitted'] = False
                    r['training_manifest_admitted'] = False
                    r['training_admission_level'] = 'DIRECT_SOURCE_CANDIDATE_ONLY_FINAL_MANIFEST_EMPTY_V5'
                    r['current_source_policy'] = '../SCOPE_CONFIRMATION.json'
                    r['current_visibility_overlay'] = '../STRICT_SOURCE_VISIBILITY_OVERRIDES.json'
                    r['current_training_manifest'] = '../FINAL_TRAINING_MANIFEST.json'
                    output.append(r)
            counts[key], by_stage[key] = dict(c), dict(stages)
            if scope == 'public':
                p = DEST / 'data' / ('public.direct_source_' + role + '.zero_loss.jsonl.gz')
                p.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(p, 'wt', encoding='utf-8', newline='\n') as f:
                    for r in output:
                        f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    report = {
        'schema_version': 'wrd-strict226-confirmed-candidate-reconciliation-v5',
        'status': 'SOURCE_BOUNDARY_CONFIRMED_FINAL_TRAINING_MANIFEST_EMPTY',
        'counts': counts, 'by_stage': by_stage,
        'new_controlled_generic_prefixes': {'windows': 9, 'targets': 9, 'supervised_tokens': 279,
            'processed_input_tokens': 40103, 'le16k_windows': 9, 'public_windows': 0,
            'domain_full_stage_or_complete_task_increment': 0},
        'new_visibility_positive_evolution_context_candidates': 91,
        'new_observed_context_candidates_are_episodes_not_extra_independent_sources': True,
        'original_structured_decision_candidate_records': 119,
        'structured_decisions_overlap_the_same_parent_episodes_and_are_not_extra_tasks': True,
        'final_training_manifest_admitted_rows': 0,
        'no_new_field_annotations_fabricated': True,
        'no_new_teacher_actor_judge_or_native_runs': True,
        'training_started': False,
        'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in
            [OUT / 'VISIBILITY_REVIEW.json', OUT / 'STRICT_SOURCE_VISIBILITY_OVERRIDES.json',
             OUT / 'prefixes/PREFIX_RECOVERY_REPORT.json', OUT / 'prefixes/INDEPENDENT_PREFIX_QA.json']},
        'baseline_v4_preserved_as_historical_evidence_not_current_admission': True,
    }
    assert counts['controlled:core32k']['current_direct_source_candidate_windows'] == 275
    assert counts['controlled:core32k']['candidate_supervised_tokens_before_disabled_loss'] == 476418
    assert counts['public:core32k']['current_direct_source_candidate_windows'] == 85
    save(OUT / 'DIRECT_SOURCE_CANDIDATE_REPORT.json', report)
    # All new controlled material is delivered. No key is included in the tar.
    encryption_dir = OUT / 'encrypted_delivery'
    encryption_dir.mkdir(exist_ok=False)
    members = {}
    for p in sorted((OUT / 'controlled').glob('*.gz')):
        members['visibility/' + p.name] = p
    for name in ('controlled.jsonl.gz', 'public.jsonl.gz', 'PREFIX_RECOVERY_REPORT.json', 'INDEPENDENT_PREFIX_QA.json'):
        members['prefixes/' + name] = OUT / 'prefixes' / name
    for name in ('SCOPE_CONFIRMATION.json', 'FINAL_TRAINING_MANIFEST.json', 'VISIBILITY_REVIEW.json',
                 'STRICT_SOURCE_VISIBILITY_OVERRIDES.json', 'DIRECT_SOURCE_CANDIDATE_REPORT.json'):
        members['reports/' + name] = OUT / name
    inner = {'schema_version': 'wrd-strict226-controlled-delta-manifest-v5', 'contains_key': False,
             'files': [{'path': n, 'bytes': p.stat().st_size, 'sha256': sha(p)} for n, p in members.items()]}
    plain = encryption_dir / 'wrd-strict226-evidence-v5.tar.gz'
    with tarfile.open(plain, 'w:gz') as tf:
        for n, p in members.items():
            tf.add(p, arcname=n, recursive=False)
        data = (json.dumps(inner, ensure_ascii=False, indent=2) + '\n').encode()
        info = tarfile.TarInfo('MANIFEST.json')
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    helper_path = ROOT / 'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py'
    spec = importlib.util.spec_from_file_location('wrd_encryption', helper_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cipher = encryption_dir / 'wrd-strict226-evidence-v5.tar.gz.aesgcm'
    key = V4 / 'local_delivery_key/wrd-reasoning-v4.key'
    encryption = module.encrypt(plain, cipher, key, reuse_key=True)
    with cipher.open('rb') as f:
        f.read(8)
        nonce = f.read(12)
    for old in (RELEASE / 'reasoning/20261025/controlled').glob('*.aesgcm'):
        with old.open('rb') as f:
            f.read(8)
            assert f.read(12) != nonce
    encryption.update(schema_version='wrd-strict226-encrypted-delta-v5',
                      members_including_manifest=len(members) + 1,
                      reused_local_key_with_new_distinct_nonce=True,
                      tar_member_hashes_and_sizes=inner['files'],
                      training_started=False)
    save(OUT / 'CONTROLLED_DELTA_ENCRYPTION_REPORT.json', encryption)
    for name in ('SCOPE_CONFIRMATION.json', 'FINAL_TRAINING_MANIFEST.json', 'VISIBILITY_REVIEW.json',
                 'STRICT_SOURCE_VISIBILITY_OVERRIDES.json', 'DIRECT_SOURCE_CANDIDATE_REPORT.json',
                 'CONTROLLED_DELTA_ENCRYPTION_REPORT.json'):
        shutil.copyfile(OUT / name, DEST / name)
    for name in ('PREFIX_RECOVERY_REPORT.json', 'INDEPENDENT_PREFIX_QA.json'):
        shutil.copyfile(OUT / 'prefixes' / name, DEST / name)
    (DEST / 'controlled').mkdir()
    shutil.copyfile(cipher, DEST / 'controlled' / cipher.name)
    data = read(PLAN / 'DATA_REPORT.json')
    data['strict226_scope_confirmation'] = policy
    data['v5_current_direct_source_candidate_reconciliation'] = report
    data['current_source_visibility_review'] = review
    save(PLAN / 'DATA_REPORT.json', data)
    config = read(PLAN / 'TRAINING_PLAN.json')
    config['data_profiles']['scope_confirmation_date'] = '2026-10-26'
    config['data_profiles']['current_candidate_reconciliation'] = '../../reasoning/20261026_strict226/DIRECT_SOURCE_CANDIDATE_REPORT.json'
    config['data_profiles']['final_training_manifest'] = '../../reasoning/20261026_strict226/FINAL_TRAINING_MANIFEST.json'
    save(PLAN / 'TRAINING_PLAN.json', config)
    readiness = read(PLAN / 'READINESS.json')
    readiness['current_candidate_core_windows_controlled_public'] = [275, 85]
    readiness['current_candidate_core_supervised_tokens_before_disabled_loss_controlled_public'] = [476418, 198769]
    readiness['new_generic_discovery_prefixes_do_not_solve_domain_coverage'] = 9
    readiness['source_scope_confirmation'] = '../../reasoning/20261026_strict226/SCOPE_CONFIRMATION.json'
    save(PLAN / 'READINESS.json', readiness)
    print(json.dumps({'candidate_core_controlled': 275, 'candidate_core_public': 85,
                      'new_generic_prefixes': 9, 'final_admitted_rows': 0,
                      'encrypted_delta_bytes': cipher.stat().st_size, 'training_started': False}))


if __name__ == '__main__':
    main()
