"""Import previous research work as data, without importing an old pipeline.

Only existing cards, skill files, task definitions and paid run receipts are read.
Importing does not launch work or change an old result.
"""
from pathlib import Path
import collections
import hashlib
import json


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, TypeError):
        return {}


def _ref(value):
    return value.get('path') if isinstance(value, dict) else value


def _skill(outputs):
    outputs = Path(outputs)
    direct = outputs / 'candidate' / 'skill'
    if (direct / 'SKILL.md').is_file():
        return str(direct)
    if (outputs / 'candidate' / 'SKILL.md').is_file():
        return str(outputs / 'candidate')
    candidate = outputs / 'candidate'
    if candidate.is_dir():
        choices = [p for p in candidate.iterdir() if p.is_dir() and (p / 'SKILL.md').is_file()]
        if len(choices) == 1:
            return str(choices[0])
    return None


def _run(episode, arm_record=None):
    episode = Path(episode)
    receipt = _read(episode / 'episode_receipt.json')
    account = _read(episode / 'accounting.json')
    if not receipt and not episode.exists():
        return None
    arm_record = arm_record or {}
    delivery_path = _ref(arm_record.get('delivery_report'))
    delivery = _read(delivery_path) if delivery_path else {}
    status = receipt.get('status', 'UNKNOWN')
    measured = account.get('complete', account.get('full_measurement_gate', False))
    return {
        'episode': str(episode), 'status': status,
        'complete': status == 'COMPLETED', 'usage_complete': bool(measured),
        'dispatched': (episode / 'dispatch_claim.json').is_file() or (episode / 'meter_start.json').is_file(),
        'receipt': str(episode / 'episode_receipt.json') if receipt else None,
        'accounting': str(episode / 'accounting.json') if account else None,
        'tokens': account.get('known_measured_total_tokens', account.get('total_tokens')),
        'input_tokens': account.get('known_measured_input_tokens', account.get('total_input_tokens')),
        'output_tokens': account.get('known_measured_output_tokens', account.get('total_output_tokens')),
        'calls': account.get('real_model_generations', account.get('complete_usage_generations')),
        'complete_calls': account.get('complete_usage_generations'),
        'unknown_calls': account.get('unknown_usage_generations'),
        'seconds': receipt.get('seconds'), 'error': receipt.get('error'),
        'outputs': str(episode / 'workspace' / 'outputs'),
        'delivery_status': delivery.get('status'), 'delivery_report': delivery_path,
        'native_read_report': _ref(arm_record.get('native_read_report')),
        'native_resource_report': _ref(arm_record.get('native_resource_report')),
        'legacy': True,
    }


def _decisions(body):
    values = body.get('decisions', []) if isinstance(body, dict) else []
    if isinstance(values, list):
        return values
    return []


def _usage(out, native_roots):
    """One cost row per original episode; old reconciliation fills missing usage."""
    rows = {}
    def key(path):
        return str(Path(path).absolute()).replace('\\', '/').lower()
    for native in native_roots:
        if not native.is_dir():
            continue
        for ep in native.iterdir():
            if not ep.is_dir():
                continue
            receipt, a = _read(ep / 'episode_receipt.json'), _read(ep / 'accounting.json')
            if not receipt and not a and not (ep / 'meter_start.json').is_file():
                continue
            rows[key(ep)] = {
                'episode': str(ep), 'status': receipt.get('status', 'UNKNOWN'),
                'known_tokens': a.get('known_measured_total_tokens', a.get('total_tokens')),
                'model_calls': a.get('real_model_generations', a.get('known_distinct_native_generations')),
                'unknown_calls': a.get('unknown_usage_generations'),
                'complete': bool(a.get('full_measurement_gate', a.get('complete', False))),
                'accounting': str(ep / 'accounting.json') if a else None,
                'old_snapshot_used': False,
            }
    progress = _read(out / 'progress.json')
    # Both summaries contain per-episode records. Merge those identities rather
    # than adding whole old/new batch totals, which would charge duplicates.
    for group_index, group in enumerate(('new_usage', 'prior_usage')):
        for old in progress.get(group, {}).get('episodes', []):
            if not isinstance(old, dict):
                continue
            receipt = _ref(old.get('original_receipt_pin'))
            if old.get('phase') == 'NO_DISPATCH_EVIDENCE':
                continue
            if receipt:
                ep = Path(receipt).parent
            elif old.get('id') and group_index < len(native_roots):
                ep = native_roots[group_index] / old['id']
            else:
                continue
            k = key(ep)
            # Some historical recovery reused an episode directory. A different
            # saved meter-start file identifies its prior paid session. Keep
            # that bill as its own row instead of losing it to newer usage.
            old_starts = {e.get('original_start_pin', {}).get('sha256')
                for e in old.get('raw_cost_evidence', []) if isinstance(e, dict)} - {None}
            start = ep / 'meter_start.json'
            current_start = hashlib.sha256(start.read_bytes()).hexdigest() if start.is_file() else None
            prior_session = bool(old_starts and current_start and current_start not in old_starts)
            if prior_session:
                k += '#previous-meter-start:' + sorted(old_starts)[0]
            r = rows.setdefault(k, {'episode': str(ep), 'status': old.get('original_terminal_status', 'UNKNOWN'),
                'known_tokens': None, 'model_calls': None, 'unknown_calls': None, 'complete': False,
                'accounting': None, 'old_snapshot_used': False})
            if prior_session:
                r['historical_paid_session'] = True
                r['meter_start_identity'] = sorted(old_starts)
            candidates = {'known_tokens': old.get('known_tokens'), 'model_calls': old.get('distinct_calls'),
                'unknown_calls': old.get('unknown_calls')}
            for field, value in candidates.items():
                if isinstance(value, (int, float)) and (r[field] is None or value > r[field]):
                    r[field] = value
                    r['old_snapshot_used'] = True
    episodes = sorted(rows.values(), key=lambda r: r['episode'].lower())
    return {
        'known_tokens': sum(r['known_tokens'] or 0 for r in episodes),
        'model_calls': sum(r['model_calls'] or 0 for r in episodes),
        'unknown_calls': sum(r['unknown_calls'] or 0 for r in episodes),
        'episodes': episodes, 'episode_count': len(episodes),
        'episodes_without_token_measurement': sum(r['known_tokens'] is None for r in episodes),
        'episodes_without_call_measurement': sum(r['model_calls'] is None for r in episodes),
        'episodes_without_unknown_measurement': sum(r['unknown_calls'] is None for r in episodes),
        'cash_cost': None,
        'counting': 'One absolute episode path once; distinct historical meter-start sessions retained separately. Actual accounting with per-episode old reconciliation as a lower-bound supplement. Missing values remain null; no cash estimate.',
    }


def import_legacy(config):
    root = Path(config.get('root', config.get('project_root', 'D:/skillloop')))
    out = Path(config.get('legacy_output', root / 'output/20261021_workflow_library_v10'))
    native_roots = [Path(p) for p in config.get('legacy_native_roots', [
        'E:/skillloop_runs/w10/native_episodes', 'E:/skillloop_runs/w9/native_episodes'])]
    bindings_path = Path(config.get('source_bindings', root / 'output/20261021_workflow_skill_library/source_bindings.json'))
    bindings = _read(bindings_path)
    if not isinstance(bindings, dict):
        bindings = {}
    # A per-source decision is usable even when another source made its batch fail.
    # Missing/contradictory decisions remain pending; no old gate is called.
    bodies = []
    for directory in (out / 'screens', out / 'partial_screen159'):
        if directory.is_dir():
            for p in directory.glob('*/result.json'):
                d = _read(p)
                bodies.append(d)
                if isinstance(d.get('body'), dict):
                    bodies.append(d['body'])
    for directory in native_roots:
        if directory.is_dir():
            for p in directory.glob('screen_*/workspace/outputs/screen.json'):
                bodies.append(_read(p))
    # The initial 163 previews were screened before the w10 batches.
    for old in (root / 'output/20261021_workflow_library_v9', root / 'output/20261021_workflow_library_parallel4_recovery1'):
        if (old / 'screens').is_dir():
            bodies.extend(_read(p) for p in (old / 'screens').glob('*/result.json'))
    actions = collections.defaultdict(set)
    for body in bodies:
        for d in _decisions(body):
            if not isinstance(d, dict):
                continue
            sid, action = d.get('source_id'), d.get('action')
            evidence = d.get('evidence_message_ids', d.get('message_ids'))
            if sid in bindings and action in ('reuse', 'no_value', 'defer', 'new') and isinstance(evidence, list) and evidence:
                actions[sid].add(action)
    # These 163 sources were already handled before the later 40 batches were
    # formed. Their saved source list prevents charging for the same screening.
    prior_screened = set(_read(out / 'fullscan_queue.json').get('previously_screened_ids', []))
    screened = sorted((set(s for s, a in actions.items() if len(a) == 1) | prior_screened) & set(bindings))

    cards = {p.stem: _read(p) for p in (out / 'cards').glob('*.json')}
    markers = {p.stem: _read(p) for p in (out / 'resource_ready').glob('*.json')}
    routes, runs = [], []
    for sid, card in sorted(cards.items()):
        marker = markers.get(sid, {})
        skill = marker.get('skill_root')
        if skill and not (Path(skill) / 'SKILL.md').is_file():
            skill = None
        dev = out / 'w' / sid / 'development'
        tasks = _read(dev / 'fixed_development_tasks.json').get('cases', [])
        if not isinstance(tasks, list):
            tasks = []
        row = {
            'id': sid, 'name': card.get('name', sid), 'category': card.get('category', 'OTHER'),
            'source_ids': card.get('source_ids', []),
            'steps': card.get('route_signature', {}).get('steps', []),
            'route_signature': card.get('route_signature', {}), 'value_plan': card.get('value_plan', {}),
            'existing_skill_root': skill, 'resource_ready': bool(skill and marker),
            'previous_episode': None, 'previous_feedback': None, 'candidate_skill_root': None,
            'existing_tasks': tasks, 'existing_runs': {}, 'legacy_card': str(out / 'cards' / f'{sid}.json'),
            'legacy_jobs': {}, 'previous_making_runs': [],
            'lane': _read(out / 'lane_assignments' / f'{sid}.json').get('lane', marker.get('lane')),
            'prepared_tasks_output': None, 'prepared_tasks': [], 'prepared_floor_output': None,
        }
        for native in native_roots:
            outputs = native / f'{sid}_devprep' / 'workspace' / 'outputs'
            for name in ('development_tasks.json', 'tasks.json'):
                path = outputs / name
                if path.is_file():
                    row['prepared_tasks_output'] = str(path)
                    prepared = _read(path)
                    row['prepared_tasks'] = prepared.get('cases', []) if isinstance(prepared, dict) else []
                    floor = outputs / 'delivery_floor.json'
                    row['prepared_floor_output'] = str(floor) if floor.is_file() else None
                    break
            if row['prepared_tasks_output']:
                break
        for kind in ('generate', 'development', 'recover'):
            p = out / 'jobs' / f'{kind}_{sid}_result.json'
            d = _read(p)
            if d:
                row['legacy_jobs'][kind] = {'path': str(p), 'status': d.get('status'), 'error': d.get('error'), 'reasons': d.get('reasons')}
        for native in reversed(native_roots):
            for attempt in range(1, 4):
                episode = native / f'{sid}__make{attempt}'
                run = _run(episode)
                if run is None:
                    continue
                row['previous_making_runs'].append(run)
                candidate = _skill(episode / 'workspace' / 'outputs')
                if candidate:
                    row['previous_episode'] = str(episode)
                    row['candidate_skill_root'] = candidate
                    feedback = out / 'w' / sid / f'r{attempt}' / 'evaluation.json'
                    if feedback.is_file():
                        row['previous_feedback'] = str(feedback)
        if skill and not row['previous_episode']:
            evaluation = _read(_ref(marker.get('evaluation')))
            row['previous_episode'] = evaluation.get('episode')
            row['previous_feedback'] = _ref(marker.get('evaluation'))
        for case in tasks:
            cid = case.get('id', case.get('case_id'))
            if not cid:
                continue
            row['existing_runs'][cid] = {}
            for arm in ('no_skill', 'workflow'):
                arm_record = _read(dev / 'arms' / f'{cid}_{arm}.json')
                receipt_path = _ref(arm_record.get('receipt'))
                candidates = [Path(receipt_path).parent] if receipt_path else []
                candidates.extend(native / f'{sid}_{cid}_{arm}' for native in native_roots)
                run = next((r for path in candidates if (r := _run(path, arm_record)) is not None), None)
                if run:
                    run.update({'route_id': sid, 'case_id': cid, 'arm': arm})
                    row['existing_runs'][cid][arm] = run
                    runs.append(run)
        routes.append(row)
    usage = _usage(out, native_roots)
    return {
        'bindings': bindings, 'routes': routes, 'screened_source_ids': screened, 'legacy_runs': runs,
        'legacy_usage': usage,
        'summary': {
            'bindings': len(bindings), 'routes': len(routes), 'resource_ready': sum(r['resource_ready'] for r in routes),
            'screened_sources': len(screened), 'ambiguous_screen_sources': sorted(s for s, a in actions.items() if len(a) > 1),
            'business_runs': len(runs), 'complete_business_runs': sum(r['complete'] for r in runs),
            'unknown_business_runs': sum(not r['complete'] for r in runs),
            'billing_incomplete_business_runs': sum(not r['usage_complete'] for r in runs),
            'completion_definition': 'COMPLETED Actor results are reused regardless of missing usage; billing completeness is reported separately and never dispatches a repeat.',
            'performance_proven': 0, 'old_frozen_flags_not_performance_proof': True,
            'source_bindings': str(bindings_path), 'legacy_output': str(out),
        },
    }


def recover_pending_routes(config, known_routes):
    """Recover paid route proposals, not another screening or execution layer.

    Same IDs share one candidate. Only actual ``merge/target_id`` decisions
    redirect an ID; proposal_ids are retained as history, never used as aliases.
    The caller decides how to join these candidates to its ordinary queue.
    """
    root = Path(config.get('root', config.get('project_root', 'D:/skillloop')))
    out = Path(config.get('legacy_output', root / 'output/20261021_workflow_library_v10'))
    natives = [Path(p) for p in config.get('legacy_native_roots', [
        'E:/skillloop_runs/w10/native_episodes', 'E:/skillloop_runs/w9/native_episodes'])]
    if isinstance(known_routes, dict):
        known_ids = set(known_routes)
        known = list(known_routes.values())
    else:
        known = list(known_routes)
        known_ids = {r.get('id') if isinstance(r, dict) else r for r in known}
    known_sources = {s for r in known if isinstance(r, dict) for s in r.get('source_ids', [])}

    def unique(values):
        rows, seen = [], set()
        for value in values:
            key = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                rows.append(value)
                seen.add(key)
        return rows

    cards, decisions, mappings = collections.defaultdict(list), [], []
    screens = set()
    for native in natives:
        for path in sorted(native.glob('screen_*/workspace/outputs/screen.json')):
            screens.add(str(path))
            body = _read(path)
            for card in body.get('cards', []):
                if isinstance(card, dict) and card.get('id'):
                    cards[card['id']].append({'path': str(path), 'card': card})
            decisions.extend({'path': str(path), **d} for d in body.get('decisions', []) if isinstance(d, dict))
        for path in sorted(native.glob('resolve_screen_*/workspace/outputs/resolution.json')):
            mappings.extend({'path': str(path), **d} for d in _read(path).get('decisions', []) if isinstance(d, dict))
    for path in sorted((out / 'resolution').glob('*/result.json')):
        body = _read(path)
        mappings.extend({'path': str(path), **r['decision']} for r in body.get('merged_evidence', [])
                        if isinstance(r, dict) and isinstance(r.get('decision'), dict))
    mappings = unique(mappings)
    reuse = collections.defaultdict(list)
    for d in decisions:
        if d.get('action') == 'reuse' and d.get('route_id'):
            reuse[d['route_id']].append(d)
    raw_sources = {s for rows in cards.values() for row in rows for s in row['card'].get('source_ids', [])}
    candidates, merges = [], []
    for cid, records in sorted(cards.items()):
        if cid in known_ids:
            continue
        first = records[0]['card']
        related = [m for m in mappings if (m.get('id') or m.get('candidate_id')) == cid]
        targets = sorted({m['target_id'] for m in related
                          if m.get('action') == 'merge' and m.get('target_id') in known_ids})
        sources = sorted({s for row in records for s in row['card'].get('source_ids', [])} |
                         {d['source_id'] for d in reuse.get(cid, []) if d.get('source_id')})
        sig = first.get('route_signature') or {}
        value = first.get('value_plan') or {}
        resources = [{k: r[k] for k in ('id', 'kind', 'operation', 'input_contract', 'output_contract', 'applicability') if k in r}
                     for r in value.get('resources', []) if isinstance(r, dict)]
        row = {
            'id': cid, 'name': first.get('name', cid), 'category': first.get('category', 'OTHER'),
            'source_ids': sources, 'steps': sig.get('steps', []), 'route_signature': sig,
            'value_plan': {'reusable_steps': value.get('reusable_steps', []), 'resources': resources},
            'conditions': unique([v for r in records for v in r['card'].get('conditions', [])]),
            'conflicts': unique([v for r in records for v in r['card'].get('conflicts', [])]),
            'source_evidence': unique([v for r in records for v in r['card'].get('source_evidence', [])]),
            'raw_card_paths': sorted({r['path'] for r in records}), 'resolution_records': related,
            'reuse_source_ids': sorted({d['source_id'] for d in reuse.get(cid, []) if d.get('source_id')}),
        }
        if len(targets) == 1:
            row['target_id'] = targets[0]
            merges.append(row)
        else:
            row['resolved_targets'] = targets
            candidates.append(row)
    news = [d for d in decisions if d.get('action') == 'new']
    no_card = unique([d for d in news if d.get('source_id') not in raw_sources | known_sources])
    deferred = unique([d for d in decisions if d.get('action') == 'defer'])
    reuse_links = [{'route_id': target, 'source_ids': sorted({d['source_id'] for d in rows if d.get('source_id')}),
                    'decisions': rows, 'existing_route': target in known_ids}
                   for target, rows in sorted(reuse.items())]
    return {
        'summary': {
            'raw_screen_files': len(screens), 'raw_card_occurrences': sum(map(len, cards.values())),
            'raw_unique_candidate_ids': len(cards), 'candidate_count': len(candidates),
            'explicit_merge_count': len(merges), 'new_decisions': len(news),
            'new_without_cards': len(no_card), 'deferred_sources': len(deferred),
            'reuse_decisions': sum(map(len, reuse.values())),
            'reuse_to_existing_routes': sum(len(rows) for target, rows in reuse.items() if target in known_ids),
            'reuse_to_pending_candidates': sum(len(rows) for target, rows in reuse.items() if target not in known_ids and target in cards),
            'reuse_to_missing_routes': sum(len(rows) for target, rows in reuse.items() if target not in known_ids and target not in cards),
            'source_screening_is_not_resource_completion': True,
        },
        'candidates': candidates, 'explicit_merges': merges,
        'new_without_cards': no_card, 'deferred_sources': deferred, 'reuse_links': reuse_links,
    }
