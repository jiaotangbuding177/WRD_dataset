"""Prepare the body-free 57-Actor-write assessment; never commit or push.

Frozen 32 payloads and their original manifest are copied unchanged. New
sidecars verify the two disjoint errata against the same actual v9 shards.
Only the two current model keys and existing AES key are read, in memory, for
exact-byte exclusion scans. Key values or fingerprints are never reported.
"""
from collections import Counter, defaultdict
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat

ROOT = Path(__file__).resolve().parents[3]
V10 = ROOT / 'output/20261027_wrd_main_v10'
SOURCE = V10 / 'execution_rescue_01'
OLD = V10 / 'prepare_ancestry_audit'
V9 = ROOT / 'output/20261026_wrd_dataset_v9'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE / 'assessment/20261027_actor_write_producers'
STAGING = V10 / 'execution_rescue_public_staging'
KEY = ROOT / 'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
BLOCK = 1048576
FORBIDDEN = {'private', 'private_credential_audit', 'credential_audit', '.git', '.claude', '.codex', '__pycache__'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(BLOCK), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def regular(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or path.is_symlink() or getattr(s, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
        raise ValueError('non_regular_or_reparse_file')


def safe(root, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or any(p.lower() in FORBIDDEN for p in rel.parts):
        raise ValueError('unsafe_payload_relative_path')
    if rel.suffix.lower() in {'.key', '.pem', '.pfx', '.p12', '.pyc'}:
        raise ValueError('private_or_cache_file_extension')
    path = root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('payload_path_escape')
    for parent in [root, *path.parents]:
        if not parent.exists() or not parent.resolve().is_relative_to(root.resolve()):
            continue
        s = parent.lstat()
        if parent.is_symlink() or getattr(s, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
            raise ValueError('reparse_parent')
    return path


def copy(source, name):
    regular(source)
    target = safe(STAGING, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    regular(target)
    assert digest(source) == digest(target)


def normalized_record(r, old, action):
    return {'episode_id': r['episode_id'], 'record_id': r['old_record_id'], 'split': r['old_split'],
        'shard': r['old_shard'], 'targets': r['target_ids_to_zero'] if old else r['target_ids_to_zero_on_future_import'],
        'supervised_tokens': r['old_supervised_tokens'],
        'input_sha256': r['old_input_ids_sha256_u32le'] if old else r['old_input_ids_sha256'],
        'spans_sha256': r['old_supervision_spans_sha256'] if old else r['old_spans_sha256'],
        'action': action, 'audit': 'previous26' if old else 'new39'}


def combine():
    previous_meta = load(OLD / 'V9_POSITIVE_LOSS_ERRATUM.json')
    new_meta = load(SOURCE / 'V9_AUX_FUTURE_IMPORT_ERRATUM.json')
    old_pins = {Path(r['path']).name: r for r in previous_meta['old_shard_pins'] if Path(r['path']).name.startswith('native_process.')}
    new_pins = {Path(r['path']).name: r for r in new_meta['old_shards']}
    assert set(old_pins) == set(new_pins) and len(old_pins) == 4
    for name in old_pins:
        assert old_pins[name]['sha256'] == new_pins[name]['sha256']
        assert old_pins[name]['bytes'] == new_pins[name]['bytes']
        actual = V9 / 'sft' / name
        regular(actual)
        assert digest(actual) == old_pins[name]['sha256'] and actual.stat().st_size == old_pins[name]['bytes']
    records = [normalized_record(r, True, 'confirmed_revoke') for r in rows(OLD / 'v9_confirmed_target_revocations.jsonl.gz')]
    records += [normalized_record(r, True, 'pending_hold') for r in rows(OLD / 'v9_pending_producer_targets.jsonl.gz')]
    records += [normalized_record(r, False, 'confirmed_revoke' if r['action'] == 'REVOKE_ON_FUTURE_IMPORT' else 'pending_hold') for r in new_meta['records']]
    wanted = {(r['shard'], r['record_id']): r for r in records}
    assert len(wanted) == len(records)
    checked = set()
    by_audit_action_split = defaultdict(Counter)
    owners = defaultdict(set)
    record_ids = defaultdict(set)
    episode_ids = defaultdict(set)
    for name in sorted(old_pins):
        for actual in rows(V9 / 'sft' / name):
            key = name, actual['id']
            if key not in wanted:
                continue
            r = wanted[key]
            assert actual['bank'] == 'native_process'
            assert r['episode_id'] == actual['episode_id'] and r['split'] == actual['split']
            assert actual['input_ids_sha256_u32le'] == r['input_sha256']
            assert actual['supervision_spans_sha256'] == r['spans_sha256']
            positive = {t['id'] for t in actual['targets'] if t.get('supervised_tokens', 0) > 0}
            assert positive == set(r['targets']) and len(positive) == len(r['targets'])
            assert actual['supervised_tokens'] == sum(hi - lo for lo, hi, _, _ in actual['supervision_spans']) == r['supervised_tokens']
            scope = r['audit'], r['action'], r['split']
            c = by_audit_action_split[scope]
            c['sequences'] += 1
            c['targets'] += len(positive)
            c['supervised_tokens'] += r['supervised_tokens']
            c['weighted_token_mass'] += sum((hi - lo) * w for lo, hi, _, w in actual['supervision_spans'])
            for owner in positive:
                assert owner not in owners[r['audit']]
                owners[r['audit']].add(owner)
            record_ids[r['audit']].add(r['record_id'])
            episode_ids[r['audit']].add(r['episode_id'])
            checked.add(key)
    assert checked == set(wanted)
    assert not owners['previous26'] & owners['new39']
    assert not record_ids['previous26'] & record_ids['new39']
    assert not episode_ids['previous26'] & episode_ids['new39']
    combined = defaultdict(Counter)
    for (audit, action, split), c in by_audit_action_split.items():
        combined[(action, split)].update(c)
    for action, expected_tokens in [('confirmed_revoke', 2198), ('pending_hold', 888)]:
        assert combined[(action, 'train')]['supervised_tokens'] == expected_tokens
        assert sum(c['supervised_tokens'] for (a, split), c in combined.items() if a == action) == expected_tokens
    by_audit = {}
    zero_stats = {'sequences': 0, 'targets': 0, 'supervised_tokens': 0, 'weighted_token_mass': 0.0}
    for audit in ['previous26', 'new39']:
        by_audit[audit] = {}
        for action in ['confirmed_revoke', 'pending_hold']:
            per_split = {split: {**zero_stats, **dict(by_audit_action_split.get((audit, action, split), Counter()))} for split in ['train', 'dev', 'test']}
            totals = Counter()
            for c in per_split.values():
                totals.update(c)
            by_audit[audit][action] = {'by_split': per_split, 'all_splits': dict(totals)}
    merged = {}
    for action in ['confirmed_revoke', 'pending_hold']:
        per_split = {split: {**zero_stats, **dict(combined.get((action, split), Counter()))} for split in ['train', 'dev', 'test']}
        totals = Counter()
        for c in per_split.values():
            totals.update(c)
        merged[action] = {'by_split': per_split, 'all_splits': dict(totals)}
    universe = {'bank': 'native_process', 'actual_shards': [{'path': 'sft/' + n, 'sha256': old_pins[n]['sha256'], 'bytes': old_pins[n]['bytes']} for n in sorted(old_pins)],
                'old_and_new_audits_bound_to_same_shard_bytes': True, 'shards_read_and_positive_owners_verified': len(old_pins),
                'all_audit_record_owners_disjoint': True, 'all_audit_target_ids_disjoint': True,
                'all_audit_episode_ids_disjoint': True, 'confirmed_and_pending_actions_not_interchangeable': True}
    combined_report = {'schema': 'wrd-v10-combined-old-v9-auxiliary-import-errata', 'status': 'PASS_SCOPED_COMBINATION_ONLY',
        'statistical_universe': universe, 'by_audit': by_audit, 'combined': merged,
        'all_affected_old_rows_are_train': True, 'affected_dev_and_test_positive_tokens': 0,
        'frozen_v9_train_sequences': 1660, 'frozen_v9_train_supervised_tokens': 403788,
        'frozen_v9_totals_not_overwritten_or_reclassified_by_this_sidecar': True,
        'is_a_complete_quality_or_lineage_certificate_for_the_rest_of_v9': False,
        'v10_active_banks_import_these_rows': False, 'v10_new_positive_loss_tokens': 0,
        'records': records, 'old_summary_pin': pin(OLD / 'V9_POSITIVE_LOSS_ERRATUM.json'),
        'new_erratum_pin': pin(SOURCE / 'V9_AUX_FUTURE_IMPORT_ERRATUM.json')}
    qa = {'status': 'PASS_SAME_ACTUAL_SHARDS_SPLITS_AND_DISJOINT_TARGET_IDS',
        'actual_old_v9_native_shards_read': len(old_pins), 'actual_affected_records_checked': len(records),
        'previous26_positive_target_ids_checked': len(owners['previous26']),
        'new39_positive_target_ids_checked': len(owners['new39']),
        'cross_audit_target_intersection': 0, 'cross_audit_record_intersection': 0,
        'cross_audit_episode_intersection': 0, 'train_equals_all_splits_for_this_limited_erratum': True,
        'combined': merged, 'old_v9_or_active_v10_files_modified': False,
        'is_an_updated_training_manifest': False, 'training_started': False}
    return combined_report, qa


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def scan(path, patterns):
    overlap = max(map(len, patterns), default=1) - 1
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as handle:
        tail = b''
        for block in iter(lambda: handle.read(BLOCK), b''):
            data = tail + block
            if any(pattern in data for pattern in patterns):
                return False
            tail = data[-overlap:] if overlap else b''
    return True


def main():
    if DEST.exists() or STAGING.exists():
        raise RuntimeError('refuse_existing_delivery_or_staging_directory')
    for target in [DEST, STAGING]:
        assert target.resolve().is_relative_to(ROOT.resolve())
    frozen_manifest = load(SOURCE / 'MANIFEST.json')
    assert frozen_manifest['payload_files'] == len(frozen_manifest['files']) == 32
    assert frozen_manifest['payload_bytes'] == 1412355
    assert digest(SOURCE / 'MANIFEST.json') == 'b836a5f5fd634a1145f63001318d05f686e8074a78f96ac6a2e729cb3b392610'
    STAGING.mkdir(parents=True)
    for row in frozen_manifest['files']:
        path = safe(SOURCE, row['path'])
        regular(path)
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
        copy(path, row['path'])
    copy(SOURCE / 'MANIFEST.json', 'MANIFEST.json')
    combined, combined_qa = combine()
    save(STAGING / 'COMBINED_V9_AUX_ERRATA.json', combined)
    save(STAGING / 'COMBINED_ERRATA_QA.json', combined_qa)
    for name in ['V9_POSITIVE_LOSS_ERRATUM.json', 'v9_confirmed_target_revocations.jsonl.gz', 'v9_pending_producer_targets.jsonl.gz']:
        copy(OLD / name, 'comparison_inputs/previous26/' + name)
    copy(Path(__file__), 'sourcecode_snapshots/package_execution_producer_audit.py')
    notes = '''# 57个旧业务write：任务producer审计交付

本包是审计资料。34个write确证保护producer，23个具体缺证，新增训练序列／正loss为0。v10 ACTIVE没有导入这些旧Actor；原始业务正文、私有原件和凭据未随本包发布。未启动模型、旧程序测试或训练。

冻结32载荷及原MANIFEST.json逐字节复制，原manifest SHA为b836a5f5fd634a1145f63001318d05f686e8074a78f96ac6a2e729cb3b392610。最终审计入口为producer57_extended_static/PRODUCER_AUDIT.json，最终QA为PRODUCER57_INDEPENDENT_QA_FINAL.json。早期时点报告和源码快照保留，不当作新样本。

新增sidecar把旧26 Actor与新39 Actor的两套勘误，逐条接回同样四个冻结v9 native_process分片（train16K／32K、dev16K、test16K），核对原数组／spans SHA、split及正owner。两套record、episode、target ID都不相交，因此这次可以相加；并非只凭两份摘要相加。

| 口径 | 已证保护：序列／目标／监督tokens | 缺证hold：序列／目标／监督tokens |
|---|---|---|
| 旧26审计，train | 21／36／1260 | 3／4／151 |
| 新39审计，train | 16／24／938 | 12／21／737 |
| 合并train | 37／60／2198 | 15／25／888 |
| 合并dev | 0／0／0 | 0／0／0 |
| 合并test | 0／0／0 | 0／0／0 |
| 合并all splits | 37／60／2198 | 15／25／888 |

本次受影响行恰好全部为train，因此train与all数值相同。2198是旧v9辅助正监督在未来导入时应撤销的数量；888是尚待来源闭合、应保持hold的数量，不能与已证保护混为一类。旧v9冻结train仍登记1660序列／403788监督tokens，本sidecar不覆盖它，也不把局部勘误当成剩余v9已经通过完整质量审核。

COMBINED_V9_AUX_ERRATA.json列出实际统计宇宙、分split统计及逐目标ID。comparison_inputs/previous26/给出旧勘误的原字节；新勘误已在冻结32载荷内。COMBINED_ERRATA_QA.json记录同分片与disjoint检查。PUBLIC_MANIFEST.json是本次公开交付清单；MANIFEST.json仍是冻结32载荷的原清单。

发布前对当前两份native模型key和本地AES key进行了内存中的exact-byte排除扫描，包含gzip解压内容；没有输出、记录指纹或打包密钥。已对生成器的body-free字段及源码快照作范围审查，并以本次引用的保护源标题／完整可读消息作额外精确串扫描；这不是对任意语义片段的形式化证明。科研AI标注成本UNKNOWN_NOT_ZERO。准备脚本不执行git add、commit或push，Git上传由主Agent统一完成。
'''
    (STAGING / 'DELIVERY_NOTES.md').write_text(notes, encoding='utf-8')
    credential_files = [V10 / 'runtime_preflight/private/model_consumer.json', V10 / 'runtime_preflight/private/model_upstream.json']
    key_values = [load(path)['api_key'] for path in credential_files]
    assert all(isinstance(value, str) and value for value in key_values)
    model_patterns = {value.encode('utf-8') for value in key_values}
    model_patterns.update(json.dumps(value, ensure_ascii=False)[1:-1].encode('utf-8') for value in key_values)
    aes = KEY.read_bytes()
    assert len(aes) == 32
    secret_patterns = model_patterns | {aes, aes.hex().encode('ascii'), base64.b64encode(aes)}
    audit = load(SOURCE / 'producer57_extended_static/PRODUCER_AUDIT.json')
    source_refs = {proof['source_id']: proof.get('original_title_source')
                   for episode in audit['episodes'] for producer in episode['matched_producers']
                   for proof in producer['earlier_protected_deliveries']}
    body_patterns = set()
    source_count = 0
    for sid, ref in source_refs.items():
        path = Path(ref['path']) if ref else ROOT / 'output/20261021_workflow_skill_library/sources' / sid / 'conversation.json'
        if not path.is_file():
            raise ValueError('protected_source_needed_for_exclusion_scan_missing')
        source = load(path)
        source_count += 1
        title = source.get('title')
        texts = [title] if isinstance(title, str) and len(title) >= 8 else []
        texts.extend(text for message in source.get('messages', []) for text in strings(message.get('content', '')) if len(text) >= 40)
        for text in texts:
            body_patterns.add(text.encode('utf-8'))
            body_patterns.add(json.dumps(text, ensure_ascii=False)[1:-1].encode('utf-8'))
    scanned = []
    for path in sorted(p for p in STAGING.rglob('*') if p.is_file()):
        regular(path)
        relative = str(path.relative_to(STAGING)).replace('\\', '/')
        safe(STAGING, relative)
        if not scan(path, secret_patterns):
            raise ValueError('credential_exact_bytes_found_packaging_stopped')
        if not scan(path, body_patterns):
            # No automatic replacement can silently preserve a frozen file's
            # identity. Stop; a separately declared projection is required.
            raise ValueError('protected_source_title_or_body_found_projection_required:' + relative)
        if path.suffix == '.gz':
            with path.open('rb') as handle:
                raw = handle.read()
            if any(pattern in raw for pattern in secret_patterns):
                raise ValueError('credential_exact_bytes_in_raw_gzip_container')
        scanned.append(relative)
    publication_qa = {'status': 'PASS_FROZEN_BYTES_SAME_UNIVERSE_AND_BODY_FREE_PUBLIC_SCOPE',
        'frozen_payload_files_copied_exactly': 32, 'frozen_manifest_copied_unchanged': True,
        'frozen_manifest_sha256': digest(SOURCE / 'MANIFEST.json'),
        'pre_QA_public_files_scanned': len(scanned), 'gzip_decompressed_files_scanned': sum(name.endswith('.gz') for name in scanned),
        'configured_model_key_files_read_only_in_memory': 2, 'local_AES_key_read_only_in_memory': True,
        'credential_exact_byte_matches': 0, 'key_values_or_key_fingerprints_serialized': False,
        'known_protected_source_records_used_only_for_exclusion_scan': source_count,
        'complete_protected_message_and_title_exact_matches': 0,
        'body_free_scope_review': 'Generated hashes/positions/counts and source-code helpers; no raw task prompt, protected title, business answer, original private record or authentication header is allowlisted.',
        'source_pattern_scan_is_not_a_semantic_fragment_exhaustiveness_claim': True,
        'all_regular_files_and_safe_relative_paths': True, 'old_v9_and_v10_frozen_files_modified': False,
        'new_positive_loss_tokens': 0, 'training_started': False,
        'git_add_commit_push_performed_by_packager': False, 'packager': pin(Path(__file__))}
    save(STAGING / 'PUBLICATION_QA.json', publication_qa)
    assert scan(STAGING / 'PUBLICATION_QA.json', secret_patterns) and scan(STAGING / 'PUBLICATION_QA.json', body_patterns)
    public_files = []
    for path in sorted(p for p in STAGING.rglob('*') if p.is_file()):
        relative = str(path.relative_to(STAGING)).replace('\\', '/')
        public_files.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': digest(path)})
    public = {'schema': 'wrd-v10-actor-write-producers-public-delivery',
        'status': 'AUDIT_ONLY_ZERO_NEW_TRAINING_TARGETS', 'files': public_files,
        'payload_files': len(public_files), 'payload_bytes': sum(row['bytes'] for row in public_files),
        'source_frozen_manifest_sha256': digest(SOURCE / 'MANIFEST.json'),
        'current_producer_result': {'confirmed_protected_writes': 34, 'missing_evidence_writes': 23, 'proven_clean_writes': 0},
        'new_execution_main_sequences': 0, 'new_supervised_tokens': 0,
        'combined_erratum': {'confirmed_revoke_train_and_all_tokens': 2198, 'pending_hold_train_and_all_tokens': 888, 'dev_test_tokens': 0},
        'is_training_manifest': False, 'training_started': False}
    save(STAGING / 'PUBLIC_MANIFEST.json', public)
    assert scan(STAGING / 'PUBLIC_MANIFEST.json', secret_patterns) and scan(STAGING / 'PUBLIC_MANIFEST.json', body_patterns)
    # Publish into this one user-authorized repository directory only. Do not
    # change the Git index, any root entrypoint or other agent-owned directory.
    DEST.mkdir(parents=True)
    for row in [*public_files, {'path': 'PUBLIC_MANIFEST.json', 'bytes': (STAGING / 'PUBLIC_MANIFEST.json').stat().st_size, 'sha256': digest(STAGING / 'PUBLIC_MANIFEST.json')}]:
        source = safe(STAGING, row['path'])
        target = safe(DEST, row['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        regular(target)
        assert target.stat().st_size == row['bytes'] and digest(target) == row['sha256']
    receipt = {'status': 'PREPARED_NOT_COMMITTED_OR_PUSHED',
        'destination': str(DEST), 'public_manifest_sha256': digest(DEST / 'PUBLIC_MANIFEST.json'),
        'public_payload_files': len(public_files), 'public_payload_bytes': public['payload_bytes'],
        'files_including_public_manifest': len(public_files) + 1,
        'bytes_including_public_manifest': public['payload_bytes'] + (DEST / 'PUBLIC_MANIFEST.json').stat().st_size,
        'frozen_32_and_original_manifest_exact_byte_copy': True,
        'credential_and_known_source_body_exact_matches': 0,
        'combined_errata_QA': combined_qa['status'], 'git_mutations_performed': False,
        'packager': pin(Path(__file__))}
    save(V10 / 'EXECUTION_PRODUCER_PUBLICATION_RECEIPT.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
