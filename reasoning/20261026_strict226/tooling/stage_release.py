"""Synchronize confirmed-scope plan/entrypoints and byte manifest, no Git push."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
PLAN = ROOT / 'research/plans/20261025_wrd_reasoning_distillation_v4'
DEST = RELEASE / 'reasoning/20261026_strict226'
OUT = ROOT / 'output/20261026_wrd_strict226_expansion'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    policy = read(DEST / 'SCOPE_CONFIRMATION.json')
    assert policy['scope_question_pending'] is False
    assert read(DEST / 'FINAL_TRAINING_MANIFEST.json')['admitted_rows'] == 0
    qa = read(OUT / 'INDEPENDENT_RELEASE_QA.json')
    assert qa['status'] == 'PASS_FOR_FAIL_CLOSED_SCOPE_SUPPLEMENT_WITH_HISTORICAL_FINGERPRINT_LIMITS'
    assert qa['failures'] == []
    shutil.copyfile(OUT / 'INDEPENDENT_RELEASE_QA.json', DEST / 'INDEPENDENT_RELEASE_QA.json')
    v4_tooling = RELEASE / 'reasoning/20261025/tooling'
    for name in ('build_plan_artifacts.py', 'source_gate_profiles.py', 'publish_v4.py'):
        shutil.copyfile(ROOT / 'research/data_prep/wrd_reasoning_v4' / name, v4_tooling / name)
    tools = DEST / 'tooling'
    tools.mkdir(exist_ok=True)
    for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v5').glob('*.py')):
        shutil.copyfile(p, tools / p.name)
    provenance = read(PLAN / 'PROVENANCE.json')
    provenance.update(design_revision='5.0.29', change_id='ALG-20261026-02',
                      scope_confirmation='USER_CONFIRMED_KEEP_ORIGINAL226_ISOLATED_20261026',
                      baseline_v4_data_commit='5024f6143fe2ab7f5bf89fbdc73c1a430107bb85',
                      baseline_v4_final_commit='708bd77830006a81b99e3fdd44e0fe8f79b29218')
    provenance['research_source_head'] = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()
    provenance['research_source_head_does_not_include_uncommitted_script_edits'] = True
    provenance['design_sha256'] = {n: sha(ROOT / 'research/designs' / n) for n in ('A_B_MODULES.md', 'PIPELINE.md')}
    provenance['plan_files'] = [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size}
                               for p in sorted(PLAN.iterdir()) if p.is_file() and p.name != 'PROVENANCE.json']
    for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v4').glob('*.py')):
        if p.name in provenance['scientific_script_sha256']:
            provenance['scientific_script_sha256'][p.name] = sha(p)
    provenance['strict226_scientific_script_sha256'] = {p.name: sha(p) for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v5').glob('*.py'))}
    save(PLAN / 'PROVENANCE.json', provenance)
    public_plan = RELEASE / 'plans/20261025_reasoning_distillation'
    for p in PLAN.iterdir():
        if p.is_file():
            shutil.copyfile(p, public_plan / p.name)
    p = RELEASE / 'TRAINING_ENTRYPOINT.json'
    entry = read(p)
    entry.update(status='SOURCE_ISOLATION_CONFIRMED_FULL_AGENT_READINESS_INCOMPLETE',
                 scope_question_pending=False, user_confirmed_original226_isolation=True,
                 final_training_manifest='reasoning/20261026_strict226/FINAL_TRAINING_MANIFEST.json',
                 current_scope_audit='reasoning/20261026_strict226/README.md',
                 training_manifest_admitted_rows=0)
    save(p, entry)
    p = RELEASE / 'reasoning/20261025/DATA_ENTRYPOINT.json'
    entry = read(p)
    old = entry.pop('strict_phase_warmup_only', None)
    entry.pop('strict_phase_candidates_require_current_source_overlay', None)
    if old:
        entry['historical_v4_candidate_arrays_not_current_admission'] = old
    entry.update(scope_question_pending=False,
                 scope_confirmation='../20261026_strict226/SCOPE_CONFIRMATION.json',
                 current_source_visibility_overlay='../20261026_strict226/STRICT_SOURCE_VISIBILITY_OVERRIDES.json',
                 final_training_manifest='../20261026_strict226/FINAL_TRAINING_MANIFEST.json',
                 final_training_manifest_admitted_rows=0,
                 latest_zero_loss_review_candidates=[
                     '../20261026_strict226/data/public.direct_source_core32k.zero_loss.jsonl.gz',
                     '../20261026_strict226/data/public.direct_source_actor_aux32k.zero_loss.jsonl.gz'],
                 current_controlled_delta='../20261026_strict226/controlled/wrd-strict226-evidence-v5.tar.gz.aesgcm',
                 upstream_quality_admission_not_final_source_admission=True,
                 no_fallback_to_old_positive_spans=True)
    save(p, entry)
    for p in (RELEASE / 'README.md', RELEASE / 'reasoning/20261025/README.md'):
        text = p.read_text(encoding='utf-8-sig')
        prefix = ('**2026-10-26当前更正：用户确认原226继续隔离。** '
                  '[当前来源审计与补充](' + ('reasoning/20261026_strict226/README.md' if p.parent == RELEASE else '../20261026_strict226/README.md') +
                  ')；直接来源候选本地275窗、公开85窗，资源传递隔离仍待核，最终训练清单准入0。'
                  '旧数组/旧数量留作历史证据；当前公开候选正loss全部禁用，不启动训练。\n\n')
        if not text.startswith('**2026-10-26当前更正'):
            p.write_text(prefix + text, encoding='utf-8')
    # Main rolling manifest includes every changed/new payload and all old exact bytes.
    p = RELEASE / 'reasoning/20261025/MANIFEST.json'
    previous = read(p)
    previous_path = OUT / 'MANIFEST.baseline_708bd77.json'
    if not previous_path.exists():
        shutil.copyfile(p, previous_path)
    paths = {x['path'] for x in previous['files']}
    paths.update(str(p.relative_to(RELEASE)).replace('\\', '/') for p in DEST.rglob('*') if p.is_file())
    paths.update(str(p.relative_to(RELEASE)).replace('\\', '/') for p in public_plan.iterdir() if p.is_file())
    previous.update(schema_version='wrd-reasoning-public-rolling-manifest-v5',
                    latest_scope_confirmation='reasoning/20261026_strict226/SCOPE_CONFIRMATION.json',
                    latest_final_training_manifest='reasoning/20261026_strict226/FINAL_TRAINING_MANIFEST.json',
                    baseline_final_commit='708bd77830006a81b99e3fdd44e0fe8f79b29218')
    previous['files'] = [{'path': n, 'sha256': sha(RELEASE / n), 'bytes': (RELEASE / n).stat().st_size} for n in sorted(paths)]
    save(p, previous)
    print(json.dumps({'payload_files': len(previous['files']), 'payload_bytes': sum(x['bytes'] for x in previous['files']),
                      'manifest_sha256': sha(p), 'training_started': False}))


if __name__ == '__main__':
    main()
