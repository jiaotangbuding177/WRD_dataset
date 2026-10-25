"""Assemble only plans, aggregate metadata, and a pre-existing public projection.

This performs no Git/network operation and never copies controlled row bodies.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    root = Path(__file__).resolve().parents[3]
    plan = root / 'research/plans/20261025_wrd_fullchain_distillation'
    audit = root / 'output/20261025_wrd_fullchain_reaudit'
    repo = root / 'output/20261025_wrd_training_dataset/git_release'
    dest = repo / 'fullchain/20261025'
    public_plan = repo / 'plans/20261025_fullchain_distillation'
    if dest.exists() or public_plan.exists():
        raise ValueError('new release paths required')
    assert json.loads((plan / 'TRAINING_PLAN.json').read_text(encoding='utf-8'))['execution_authorized'] is False
    allowed = ['README.md', 'ANNOTATION_GUIDE.md', 'CONTENT_AND_MASK.md', 'DATA_LEDGER.json',
               'EVALUATION_AND_COST.md', 'LITERATURE.md', 'TRAINING_PLAN.json']
    src_session = audit / 'public_projection/fullchain.native_sessions.jsonl.gz'
    previous = root / 'output/20261025_wrd_training_preflight/prepared_gated/public/support/canonical_native_episodes.jsonl.gz'
    assert sha(src_session) == sha(previous)
    provenance = {'schema_version': 'wrd-fullchain-plan-provenance-v3', 'design_revision': '5.0.26',
                  'change_id': 'ALG-20261025-12', 'training_started': False,
                  'files': [{'path': n, 'sha256': sha(plan / n), 'bytes': (plan / n).stat().st_size} for n in allowed],
                  'design_file_sha256': {p.name: sha(p) for p in
                      [root / 'research/designs/A_B_MODULES.md', root / 'research/designs/PIPELINE.md']},
                  'research_source_head': None, 'software_execution_environment': 'offline CPU dataset analysis only'}
    save(plan / 'PROVENANCE.json', provenance)
    validation = {'schema_version': 'wrd-fullchain-plan-static-validation-v3',
                  'status': 'PASS_STATIC_PLAN_AND_PROJECTION_NOT_TRAINING_READINESS',
                  'json_parses': True, 'core_nonempty_count': 19728, 'all_nonempty_count': 32014,
                  'source_report_hashes_checked': True, 'source_reports_unchanged': True,
                  'public_projection_session_bytes_match_previous_release_input': True,
                  'projection_target_messages_match_parent_sessions': True,
                  'independent_content_and_link_review': 'completed; count, causality, schema and masking clarifications applied',
                  'training_trainer_implemented': False, 'full_semantic_admission_completed': False,
                  'new_fullchain_token_masks_compiled': False, 'training_started': False}
    ledger = json.loads((plan / 'DATA_LEDGER.json').read_text(encoding='utf-8'))
    for n, expected in ledger['source_reports_sha256'].items():
        assert sha(audit / n) == expected
    sessions = {}
    with gzip.open(src_session, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            r = json.loads(line)
            sessions[r['episode_id']] = r['messages']
    count = 0
    with gzip.open(audit / 'public_projection/assistant_targets.native.jsonl.gz', 'rt', encoding='utf-8-sig') as f:
        for line in f:
            r = json.loads(line)
            m = sessions[r['episode_id']][r['target_message_index']]
            target = {k: v for k, v in m.items() if k not in {'timestamp', 'details'}}
            assert r['completion_native'] == [target] and r['training_admitted'] is False
            count += 1
    assert len(sessions) == 1051 and count == 17513
    save(plan / 'PLAN_VALIDATION.json', validation)
    public_plan.mkdir(parents=True)
    for n in allowed + ['PROVENANCE.json', 'PLAN_VALIDATION.json']:
        shutil.copy2(plan / n, public_plan / n)
    (dest / 'candidates').mkdir(parents=True)
    (dest / 'tooling').mkdir()
    for p in (audit / 'public_projection').glob('*.gz'):
        shutil.copy2(p, dest / 'candidates' / p.name)
    for n in ['audit.py', 'link_audit.py', 'content_audit.py', 'plan_artifacts.py', 'publish_plan.py']:
        shutil.copy2(Path(__file__).parent / n, dest / 'tooling' / n)
    save(dest / 'DATA_LEDGER.json', ledger)
    controlled = []
    for directory in ['controlled_master', 'controlled_linkage']:
        for p in sorted((audit / directory).glob('*')):
            if p.is_file():
                controlled.append({'local_relative_path': directory + '/' + p.name, 'sha256': sha(p),
                                   'bytes': p.stat().st_size, 'body_in_this_public_release': False})
    save(dest / 'CONTROLLED_RECOVERY_INVENTORY.json', {
        'schema_version': 'wrd-controlled-recovery-inventory-v3', 'files': controlled,
        'scope': 'body-free inventory; controlled texts require privacy processing before public release',
        'publication_permission_and_local_training_admission_separate': True})
    save(dest / 'PUBLIC_PROJECTION.json', {
        'source': 'previously privacy-cleared whole-session projection from preflight/20261025',
        'sessions': 1051, 'assistant_candidate_positions': 17513, 'training_admitted_by_this_export': 0,
        'same_old_session_gzip_sha256': sha(src_session),
        'no_new_controlled_body_copied': True, 'existing_projection_reuse_is_not_a_new_absolute_privacy_guarantee': True,
        'training_ready': False, 'training_started': False})
    (dest / 'README.md').write_text(
        '# 全阶段候选恢复与全流程蒸馏计划\n\n'
        '此前93条只属于旧技术诊断子集，完整主训练数据尚在审核建设。\n\n'
        '[详细训练计划](../../plans/20261025_fullchain_distillation/README.md) · [数据计数](DATA_LEDGER.json)\n\n'
        '本次提供既有已清理1051会话的完整原生记录、17513助手候选及真实末条定位；'
        '包含企业语义正文，来源与原公开清理投影一致。所有新增候选均未由本次导出判为训练正例。'
        '完整受控范围1763会话、32342助手位置；19728为沉淀角色非空候选，不是合格独立任务数。\n\n'
        '候选用session_ref及session_line_1based定位本目录candidates中的完整会话，'
        'prompt_messages_range_exclusive是历史前缀范围，completion_native是该位置真实输出。'
        '目标/整场成败/公开状态各自保留，不能整包直接送入SFT。\n\n'
        'CONTROLLED_RECOVERY_INVENTORY只公开受控文件SHA/大小/相对位置，不含新增受控正文。'
        '派生标签15104行、151修订配对的正文仍在本地处理，不假称已经全部公开。'
        'tooling是离线只读盘点/组装脚本，不是原生业务Agent执行器或训练启动器。\n', encoding='utf-8')
    old_entry = repo / 'TRAINING_ENTRYPOINT.json'
    shutil.copy2(old_entry, dest / 'TRAINING_ENTRYPOINT.before_fullchain_correction.json')
    old = json.loads(old_entry.read_text(encoding='utf-8-sig'))
    save(old_entry, {'schema_version': 'wrd-training-entrypoint-v3',
                    'status': 'FULLCHAIN_MAIN_CORPUS_UNDER_CONSTRUCTION_NOT_TRAINING_READY',
                    'recommended_dataset': None, 'main_training_manifest': None,
                    'fullchain_plan': 'plans/20261025_fullchain_distillation/README.md',
                    'fullchain_public_candidates': 'fullchain/20261025/candidates/assistant_targets.native.jsonl.gz',
                    'public_candidate_positions': 17513, 'core_controlled_nonempty_candidates': 19728,
                    'legacy_diagnostic_subset': {'short': old['recommended_dataset'], 'short_records': 32,
                                                 'long_only': old['additional_16k_to_32k_only'], 'long_records': 61,
                                                 'total': 93, 'use_as_main_training_corpus': False},
                    'training_ready': False, 'training_execution_authorized': False,
                    'training_started': False, 'is_launch_config': False})
    readme = repo / 'README.md'
    old_readme = readme.read_text(encoding='utf-8-sig')
    readme.write_text('# WRD 全流程蒸馏数据与训练计划\n\n'
                      '**最新：已扩至全阶段候选；完整主训练集正在审核，尚未训练。旧93条仅作诊断。**\n\n'
                      '[详细训练算法、数据量与验收计划](plans/20261025_fullchain_distillation/README.md) · '
                      '[新增1051会话／17513候选](fullchain/20261025/README.md) · '
                      '[当前入口状态](TRAINING_ENTRYPOINT.json)\n\n'
                      '新计划覆盖A归纳筛选、B工作流资源、C双臂试做与反馈修订、D封装冻结。'
                      '完整母表19728个沉淀角色非空位置及11683个Actor非空位置仍需全量准入和共同mask编译；'
                      '下列旧统计仅对旧make/screen子集有效。\n\n---\n\n## 历史子集交付记录\n\n' + old_readme,
                      encoding='utf-8')
    attrs = repo / '.gitattributes'
    with attrs.open('a', encoding='utf-8', newline='\n') as f:
        f.write('plans/20261025_fullchain_distillation/** -text\nfullchain/** -text\nfullchain/**/*.jsonl.gz filter=lfs diff=lfs merge=lfs -text\n')
    paths = [p for d in [dest, public_plan] for p in d.rglob('*') if p.is_file()]
    paths += [readme, old_entry, attrs]
    manifest = {'schema_version': 'wrd-fullchain-public-manifest-v3', 'training_started': False,
                'contains_new_controlled_row_bodies': False,
                'files': [{'path': str(p.relative_to(repo)).replace('\\', '/'), 'sha256': sha(p),
                           'bytes': p.stat().st_size} for p in sorted(paths)]}
    save(dest / 'MANIFEST.json', manifest)
    print(json.dumps({'files': len(paths) + 1, 'payload_bytes': sum(x['bytes'] for x in manifest['files']),
                      'public_candidates': count, 'training_started': False}))


if __name__ == '__main__':
    main()
