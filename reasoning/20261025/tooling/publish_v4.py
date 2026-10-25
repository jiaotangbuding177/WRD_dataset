"""Assemble reviewed public projections plus encrypted controlled archives.

Never copies a local key, plaintext archive, mapping, or controlled plaintext.
No Git/network or training action is performed by this assembly script.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def candidate_without_positive_loss(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, 'wt', encoding='utf-8', newline='\n') as f:
        for r in rows(source):
            r['candidate_supervision_spans'] = r.pop('supervision_spans')
            r['candidate_supervised_tokens'] = r['supervised_tokens']
            r['supervised_tokens'] = 0
            r['supervised_tokens_by_component'] = {}
            r['supervision_spans'] = []
            r['supervision_spans_sha256'] = hashlib.sha256(b'[]').hexdigest()
            for t in r['targets']:
                t['candidate_owned_supervision_spans'] = t.pop('owned_supervision_spans')
                t['owned_supervision_spans'] = []
                t['supervised_tokens'] = 0
            r['training_admitted'] = False
            r['candidate_only_all_positive_loss_disabled'] = True
            f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')


def main():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    local_plan = ROOT / 'research/plans/20261025_wrd_reasoning_distillation_v4'
    repo = ROOT / 'output/20261025_wrd_training_dataset/git_release'
    dest = repo / 'reasoning/20261025'
    plan = repo / 'plans/20261025_reasoning_distillation'
    if dest.exists() or plan.exists():
        raise ValueError('new v4 release directories required')
    for report in ('ENCRYPTED_DELIVERY_INDEPENDENT_QA.json', 'ENCRYPTED_EVIDENCE_INDEPENDENT_QA.json'):
        q = json.loads((base / 'encrypted_delivery' / report).read_text(encoding='utf-8'))
        assert q['status'] == 'PASS'
    dest.mkdir(parents=True)
    plan.mkdir(parents=True)
    for p in local_plan.iterdir():
        if p.suffix in {'.md', '.json'}:
            copy(p, plan / p.name)
    transfers = {
        'source_gated_profiles/public.strict226.core32k.jsonl.gz': 'data/strict226_core32k.jsonl.gz',
        'source_gated_profiles/public.strict226.actor_aux32k.jsonl.gz': 'data/strict226_actor_aux32k.jsonl.gz',
        'public_reasoning_compiled_final/common16k.jsonl.gz': 'data/original_reasoning16k.jsonl.gz',
        'public_reasoning_compiled_final/common32k_long_only.jsonl.gz': 'data/original_reasoning32k_long_only.jsonl.gz',
        'public_reasoning_compiled_final/over32k.jsonl.gz': 'evidence/original_reasoning_over32k_not_training.jsonl.gz',
        'public_actor_aux_compiled/common16k.jsonl.gz': 'data/historical_actor_aux16k.jsonl.gz',
        'public_actor_aux_compiled/common32k_long_only.jsonl.gz': 'data/historical_actor_aux32k_long_only.jsonl.gz',
        'curated_reasoning/public/sse_core.pairs.jsonl.gz': 'sources/sse_core.pairs.jsonl.gz',
        'curated_reasoning/public/historical_generation.pairs.jsonl.gz': 'sources/historical_generation.pairs.jsonl.gz',
        'curated_reasoning/public/historical_actor_aux.pairs.jsonl.gz': 'sources/historical_actor_aux.pairs.jsonl.gz',
        'controller_views/public.controller_decisions.jsonl.gz': 'annotations/derived_policy_candidates_not_gold.jsonl.gz',
        'encrypted_delivery/wrd-controlled-records-v4.tar.gz.aesgcm': 'controlled/wrd-controlled-records-v4.tar.gz.aesgcm',
        'encrypted_delivery/wrd-controlled-evidence-v4.tar.gz.aesgcm': 'controlled/wrd-controlled-evidence-v4.tar.gz.aesgcm',
        'CAUSAL_TEMPLATE.json': 'protocol/CAUSAL_TEMPLATE.json',
    }
    for src, target in transfers.items():
        copy(base / src, dest / target)
    for role in ('core32k', 'actor_aux32k'):
        candidate_without_positive_loss(base / 'source_gated_profiles' / ('public.scope_pending.' + role + '.jsonl.gz'),
                                        dest / 'candidates' / ('scope_pending.' + role + '.zero_loss.jsonl.gz'))
    reports = ['curated_native/CURATED_NATIVE_REPORT.json', 'curated_reasoning/CURATED_REASONING_REPORT.json',
               'source_gated_profiles/SOURCE_GATED_PROFILE_REPORT.json',
               'public_reasoning_compiled_final/PUBLIC_REASONING_COMPILATION_REPORT.json',
               'public_actor_aux_compiled/PUBLIC_REASONING_COMPILATION_REPORT.json',
               'PUBLIC_REASONING_DATA_VALIDATION.json', 'COMPILED_DATA_INDEPENDENT_QA.entrypoints.json',
               'encrypted_delivery/ENCRYPTED_DELIVERY_REPORT.json',
               'encrypted_delivery/ENCRYPTED_EVIDENCE_REPORT.json',
               'encrypted_delivery/ENCRYPTED_DELIVERY_INDEPENDENT_QA.json',
               'encrypted_delivery/ENCRYPTED_EVIDENCE_INDEPENDENT_QA.json']
    for src in reports:
        p = base / src
        name = p.name if 'public_actor_aux_compiled' not in src else 'PUBLIC_ACTOR_AUX_COMPILATION_REPORT.json'
        copy(p, dest / 'reports' / name)
    # Preserve source layout for the scientific recovery scripts. They expect
    # original workspace paths; token arrays and decryption are portable.
    for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v4').glob('*.py')):
        copy(p, dest / 'tooling' / p.name)
    for n in ('raw_source_discovery.py', 'recover_raw_reasoning.py', 'raw_reasoning_pairs_audit.py',
              'recover_original_sse_reasoning.py', 'recover_historical_native.py', 'label_sse_source_splits.py',
              'audit_sse_action_outcomes.py', 'write_sse_semantic_sample_review.py', 'raw_scope_review_v4.py'):
        p = ROOT / 'research/data_prep/wrd_training_fullchain' / n
        if p.is_file():
            copy(p, dest / 'tooling/recovery' / n)
    for n in ('privacy.py', 'publication_gate.py', 'prepare.py', 'audit_structure.py'):
        copy(ROOT / 'research/data_prep/wrd_training_preflight' / n, dest / 'tooling/prior_dependencies' / n)
    save(dest / 'DATA_ENTRYPOINT.json', {
        'schema_version': 'wrd-reasoning-data-entrypoint-v4',
        'full_target_training_ready': False, 'training_execution_authorized': False, 'training_started': False,
        'recommended_full_agent_training_dataset': None,
        'scope_question_pending': 'retain original226, or use all legacy sources and build entirely new independent evaluation',
        'strict_phase_warmup_only': ['data/strict226_core32k.jsonl.gz', 'data/original_reasoning16k.jsonl.gz',
                                   'data/original_reasoning32k_long_only.jsonl.gz'],
        'strict_profile_not_claimed_sufficient_for_full_goal': True,
        'optional_actor_loss_budget_max_fraction': 0.1,
        'controlled_complete_archive': 'controlled/wrd-controlled-records-v4.tar.gz.aesgcm',
        'controlled_full_evidence': 'controlled/wrd-controlled-evidence-v4.tar.gz.aesgcm',
        'local_key_not_in_git': True,
        'wider_candidate_positive_loss_disabled': True,
        'do_not_combine_public_and_controlled_duplicate_views': True,
        'tokenizer_assets': '../../preflight/20261025/tokenizer_assets/',
        'causal_template': 'protocol/CAUSAL_TEMPLATE.json'})
    (dest / 'README.md').write_text(
        '# WRD原始思考与过程数据v4\n\n'
        '[训练计划](../../plans/20261025_reasoning_distillation/README.md) · '
        '[实际数据报告](../../plans/20261025_reasoning_distillation/DATA_REPORT.json) · '
        '[就绪与缺口](../../plans/20261025_reasoning_distillation/READINESS.json) · '
        '[解密与加载](../../plans/20261025_reasoning_distillation/DATA_LOADING_AND_DELIVERY.md)\n\n'
        '找回67份原SSE思考1301758字符；完整原请求/响应/工具/修订证据同时保全。'
        '受控原件与原始source_objects用AES256GCM交付，随机钥匙只留用户本机；'
        '不再只有受控数据的SHA或索引。公开另有去标识来源与实际input_ids/监督span。\n\n'
        '本包是可核验过程silver与原件，完整自主训练尚未就绪：原226范围待确认、'
        '严格层A/取题覆盖不足、原生高层闭环/模板接线与新独立评测未验证。'
        '候选目录全部正loss禁用；正式/失败/未决原件不因归档而获训练许可。'
        '未训练、未加载权重、未跑GPU。\n', encoding='utf-8')
    copy(repo / 'TRAINING_ENTRYPOINT.json', dest / 'TRAINING_ENTRYPOINT.before_v4.json')
    save(repo / 'TRAINING_ENTRYPOINT.json', {
        'schema_version': 'wrd-training-entrypoint-v4',
        'status': 'ORIGINAL_REASONING_RECOVERED_FULL_AGENT_READINESS_PENDING',
        'recommended_dataset': None, 'full_training_readiness': 'plans/20261025_reasoning_distillation/READINESS.json',
        'detailed_plan': 'plans/20261025_reasoning_distillation/README.md',
        'data_entrypoint': 'reasoning/20261025/DATA_ENTRYPOINT.json',
        'controlled_originals_available_encrypted': True, 'local_key_not_in_repository': True,
        'legacy_93_are_diagnostic_only': True,
        'training_ready': False, 'training_execution_authorized': False, 'training_started': False,
        'is_launch_config': False})
    readme = repo / 'README.md'
    old = readme.read_text(encoding='utf-8-sig')
    readme.write_text('# WRD 原始思考、完整过程数据与训练计划\n\n'
        '**v4：找回原SSE思考并实际编译，未启动训练。**\n\n'
        '[调研与新计划](plans/20261025_reasoning_distillation/README.md) · '
        '[真实数据与完整加密原件](reasoning/20261025/README.md) · '
        '[当前就绪与限制](plans/20261025_reasoning_distillation/READINESS.json)\n\n'
        '完整母本/原思考/响应/工具过程/来源与失败证据已加密交付，钥匙留本机；'
        '公开投影提供实际数组和loss span。原226训练范围尚待明确，严格层不能冒充足量覆盖完整自主目标，'
        '候选正loss禁用；旧93不是主训练集。\n\n---\n\n' + old, encoding='utf-8')
    with (repo / '.gitattributes').open('a', encoding='utf-8', newline='\n') as f:
        f.write('reasoning/** -text\nreasoning/**/*.jsonl.gz filter=lfs diff=lfs merge=lfs -text\n'
                'reasoning/**/*.aesgcm filter=lfs diff=lfs merge=lfs -text\n'
                'plans/20261025_reasoning_distillation/** -text\n/.gitignore -text\n')
    with (repo / '.gitignore').open('a', encoding='utf-8', newline='\n') as f:
        f.write('\n# Local decryption and privacy secrets never belong in Git\n**/local_delivery_key/\n**/*.key\n'
                '**/privacy_hmac_salt.bin\n**/privacy_private_mapping.json\n')
    files = [p for p in plan.iterdir() if p.is_file()]
    provenance = {'schema_version': 'wrd-reasoning-plan-provenance-v4',
        'design_revision': '5.0.28', 'change_id': 'ALG-20261026-01',
        'research_source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'design_sha256': {p.name: sha(p) for p in [ROOT / 'research/designs/A_B_MODULES.md', ROOT / 'research/designs/PIPELINE.md']},
        'plan_files': [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(files)],
        'scientific_script_sha256': {p.name: sha(p) for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v4').glob('*.py'))},
        'training_started': False}
    save(plan / 'PROVENANCE.json', provenance)
    save(local_plan / 'PROVENANCE.json', provenance)
    manifest_files = [p for directory in (dest, plan) for p in directory.rglob('*') if p.is_file()]
    manifest_files += [repo / p for p in ('README.md', 'TRAINING_ENTRYPOINT.json', '.gitattributes', '.gitignore')]
    manifest = {'schema_version': 'wrd-reasoning-public-manifest-v4', 'training_started': False,
                'contains_controlled_plaintext': False, 'encrypted_controlled_data_present': True,
                'local_key_intentionally_excluded': True,
                'files': [{'path': str(p.relative_to(repo)).replace('\\', '/'), 'sha256': sha(p),
                           'bytes': p.stat().st_size} for p in sorted(manifest_files)]}
    save(dest / 'MANIFEST.json', manifest)
    print(json.dumps({'payload_files': len(manifest_files), 'payload_bytes': sum(r['bytes'] for r in manifest['files']),
                      'manifest_sha256': sha(dest / 'MANIFEST.json'), 'full_training_ready': False}))


if __name__ == '__main__':
    main()
