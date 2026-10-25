"""Conservative quality overlay on compiled teacher-silver process examples.

The originals and compiler results remain immutable. No model/tool execution.
Known prior AI rejections and invalid generated .py/.json writes are not positive
targets; unreviewed does not imply rejection. Silver is explicitly not gold.
"""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/data_prep/wrd_training_preflight'))
from prepare import review_map


def rows(p):
    op = gzip.open if p.suffix == '.gz' else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
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
    out = base / 'curated_native'
    out.mkdir(exist_ok=False)
    reviews = review_map(ROOT / 'output/20261025_wrd_training_preflight/local_review')
    errata = json.loads((ROOT / 'output/20261025_wrd_training_dataset/git_release/preflight/20261025/ANNOTATION_ERRATA.json').read_text(encoding='utf-8-sig'))
    for fix in errata['corrections']:
        if fix['id'] in reviews:
            reviews[fix['id']]['decision'] = fix['effective_semantic_decision']
    known_rejects = {i for i, r in reviews.items() if r['decision'] == 'reject'}
    assert len(known_rejects) == 61
    sources = {
        'controlled': ROOT / 'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz',
        'public': ROOT / 'output/20261025_wrd_fullchain_reaudit/public_projection/fullchain.native_sessions.jsonl.gz',
    }
    reports = {}
    for scope, source in sources.items():
        syntax_holds = {}
        for r in rows(source):
            for i, m in enumerate(r['messages']):
                if m.get('role') != 'assistant':
                    continue
                reasons = []
                for c in m.get('content', []) if isinstance(m.get('content'), list) else []:
                    if c.get('type') != 'toolCall' or c.get('name') != 'write':
                        continue
                    a = c.get('arguments', {})
                    if not isinstance(a, dict):
                        continue
                    path = str(a.get('path', a.get('file_path', '')))
                    body = a.get('content')
                    if not isinstance(body, str):
                        continue
                    try:
                        if path.lower().endswith('.py'):
                            ast.parse(body)
                        elif path.lower().endswith('.json'):
                            json.loads(body, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonstandard_constant')))
                    except (ValueError, SyntaxError, RecursionError):
                        reasons.append('generated_declared_python_or_json_not_parseable_requires_review')
                if reasons:
                    ident = hashlib.sha256((r['episode_id'] + ':' + str(i)).encode()).hexdigest()[:24]
                    syntax_holds[ident] = sorted(set(reasons))
        counts, phases, components = Counter(), Counter(), Counter()
        target_owners = set()
        handles = {name: gzip.open(out / (scope + '.' + name + '.jsonl.gz'), 'wt', encoding='utf-8', newline='\n')
                   for name in ('core32k', 'actor_aux32k', 'quality_target_overlay')}
        for name in ('full_stage_records.jsonl.gz', 'prefix32k_records.jsonl.gz'):
            p = base / ('native_compiled_' + scope + '_final') / name
            for original in rows(p):
                counts['compiled_records_seen'] += 1
                # Complete overlength stages are evidence, not truncated training rows.
                if original['total_tokens'] > 32768:
                    counts['overlength_complete_stages_not_selected'] += 1
                    continue
                spans = []
                for target in original['targets']:
                    identifier = target['id']
                    old = reviews.get(identifier)
                    why = []
                    if identifier in known_rejects:
                        why.append('prior_local_ai_reject_retained_as_hold_not_human_gold')
                    why.extend(syntax_holds.get(identifier, []))
                    if why and target.get('owned_supervision_spans'):
                        counts['targets_masked_by_quality_overlay'] += 1
                        counts['tokens_masked_by_quality_overlay'] += target['supervised_tokens']
                        handles['quality_target_overlay'].write(js({'id': identifier, 'episode_id': original['episode_id'],
                            'reasons': why, 'scope': scope, 'human_gold': False, 'source_not_modified': True}) + '\n')
                        target['quality_overlay'] = why
                        target['owned_supervision_spans'] = []
                        target['supervised_tokens'] = 0
                    elif target.get('owned_supervision_spans'):
                        if identifier in target_owners:
                            raise ValueError('duplicate target owner in selected windows')
                        target_owners.add(identifier)
                        target['review_level'] = 'prior_local_ai_' + old['decision'] if old else 'observed_teacher_silver_not_individually_semantically_reviewed'
                        spans.extend(target['owned_supervision_spans'])
                        phases[original['kind'] + ':targets'] += 1
                original['supervision_spans'] = sorted(spans)
                n = sum(b - a for a, b, *rest in spans)
                if not n:
                    counts['no_positive_targets_after_quality_overlay'] += 1
                    continue
                if original['kind'] not in {'screen', 'prepare', 'review', 'make', 'actor'}:
                    counts['historical_other_role_not_in_primary'] += 1
                    continue
                role = 'actor_aux32k' if original['kind'] == 'actor' else 'core32k'
                original['supervised_tokens'] = n
                original['supervised_tokens_by_component'] = dict(Counter())
                per = Counter()
                for a, b, component, weight in spans:
                    per[component] += b - a
                original['supervised_tokens_by_component'] = dict(per)
                original['supervision_spans_sha256'] = hashlib.sha256(js(spans).encode()).hexdigest()
                original['training_admitted'] = True
                original['training_admission_level'] = 'TEACHER_OBSERVED_PROTOCOL_SILVER_NOT_FULL_SEMANTIC_GOLD'
                original['quality_overlay_policy'] = 'prior_rejects_plus_generated_write_syntax_conservative_holds'
                original['full_autonomous_controller_demonstration'] = False
                original['scope_namespace'] = scope
                handles[role].write(js(original) + '\n')
                counts[role + ':windows'] += 1
                counts[role + ':processed_tokens'] += original['total_tokens']
                counts[role + ':supervised_tokens'] += n
                counts[role + ':owned_targets'] += sum(bool(t['owned_supervision_spans']) for t in original['targets'])
                counts[role + ':le16k_windows'] += original['total_tokens'] <= 16384
                counts[role + ':prefix_windows'] += not original['stage_complete_in_this_view']
                phases[original['kind'] + ':windows'] += 1
                phases[original['kind'] + ':supervised_tokens'] += n
                components.update({role + ':' + k: v for k, v in per.items()})
        for f in handles.values():
            f.close()
        reports[scope] = {'counts': dict(counts), 'by_stage': dict(phases), 'components': dict(components),
                          'generated_write_syntax_hold_ids': len(syntax_holds), 'source_sessions_sha256': digest(source),
                          'selected_target_owner_ids': len(target_owners), 'semantic_gold': 0}
    report = {'schema_version': 'wrd-curated-native-silver-v4', 'reports': reports, 'prior_effective_ai_reject_ids': 61,
              'timeout_erratum_applied': True, 'training_started': False,
              'readiness': 'PROCESS_SILVER_FOR_OFFLINE_SFT_PILOT_NOT_PROVEN_FULL_AUTONOMY',
              'note': 'Training-admitted means declared teacher-silver policy; unreviewed targets are not labelled semantic gold.'}
    (out / 'CURATED_NATIVE_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js({k: v['counts'] for k, v in reports.items()}))


if __name__ == '__main__':
    main()
