"""Read current-version actor costs, including failed attempts, without reruns.

Only the requested job and its explicit baseline-reuse chain are visited. Old
workflow versions remain in the full ledger but are not silently mixed here.
"""
from collections import OrderedDict
from copy import deepcopy
import json
import math
import os
from pathlib import Path


_CACHE = OrderedDict()
_LIMIT = 1024
_FIELDS = ('total_tokens', 'tokens', 'known_tokens', 'known_total_tokens',
           'known_measured_total_tokens', 'model_calls', 'calls', 'known_model_calls',
           'real_model_generations', 'known_distinct_native_generations',
           'unknown_calls', 'unknown_usage_calls', 'unknown_usage_generations',
           'measurement_status', 'complete')


def clear_cache():
    """Explicitly refresh after an offline ledger repair, not every poll."""
    _CACHE.clear()


def _read(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _first(*values):
    return next((value for value in values if _number(value)), None)


def _brief(job):
    result = job.get('result') or {}
    from .continuation import supplement
    usage = supplement(result)
    return {'id': job.get('id'), 'kind': job.get('kind'), 'attempt': job.get('attempt'),
            'status': job.get('status'), 'episode': job.get('episode'),
            'result': {key: result.get(key) for key in (*_FIELDS, 'episode_dir', 'episode',
                        'accounting', 'reused_from_job', 'status', 'dispatch_state', 'finished_at')},
            'usage': {key: usage.get(key) for key in _FIELDS}}


def _cost(result):
    from .continuation import supplement
    usage = supplement(result)
    accounting_ref = result.get('accounting')
    accounting = accounting_ref if isinstance(accounting_ref, dict) else _read(accounting_ref) if accounting_ref else {}
    total = _first(usage.get('total_tokens'), result.get('tokens'), result.get('total_tokens'), accounting.get('total_tokens'))
    known = _first(usage.get('known_total_tokens'), result.get('known_tokens'),
                   result.get('known_total_tokens'), accounting.get('known_measured_total_tokens'), total)
    calls = _first(usage.get('model_calls'), result.get('calls'), result.get('model_calls'),
                   accounting.get('real_model_generations'), usage.get('known_model_calls'),
                   accounting.get('known_distinct_native_generations'))
    unknown = _first(usage.get('unknown_usage_calls'), usage.get('unknown_calls'),
                     result.get('unknown_calls'), accounting.get('unknown_usage_generations'))
    explicit_not_started = result.get('dispatch_state') == 'not_started'
    if explicit_not_started and total in (None, 0) and calls in (None, 0) and known in (None, 0):
        return {'known_tokens': 0, 'total_tokens': 0, 'model_calls': 0, 'unknown_calls': 0,
                'unknown_count_is_lower_bound': False}
    measurement = str(usage.get('measurement_status') or accounting.get('measurement_status') or '').lower()
    incomplete = total is None or calls is None or measurement in ('partial', 'unknown', 'incomplete')
    unknown_lower_bound = unknown is None and incomplete
    unknown = int(unknown or 0)
    if incomplete and unknown == 0:
        unknown = 1
        unknown_lower_bound = True
    return {'known_tokens': known if known is not None else 0,
            'total_tokens': total if not incomplete and not unknown else None,
            'model_calls': calls, 'unknown_calls': unknown,
            'unknown_count_is_lower_bound': unknown_lower_bound}


def all_attempts(job, jobs, records_root):
    """Return costs for this actor version, deduplicated by native episode.

    `attempts` is a count; `attempt_details` supplies every episode and record
    path. Missing cost is unknown, including a missing earlier attempt. Stable
    job/attempt/status/cost summaries use the cache without directory scans.
    """
    if job.get('kind') != 'actor':
        raise ValueError('business_cost only accepts actor jobs')
    by_id = jobs if isinstance(jobs, dict) else {row['id']: row for row in jobs}
    chain, seen, warnings = [], set(), []
    current = job
    while current:
        jid = current['id']
        if jid in seen:
            warnings.append('baseline_reuse_cycle:' + jid)
            break
        if current.get('kind') != 'actor':
            warnings.append('baseline_reuse_target_not_actor:' + jid)
            break
        seen.add(jid)
        chain.append(current)
        target = (current.get('result') or {}).get('reused_from_job')
        if not target:
            break
        if target not in by_id:
            warnings.append('baseline_reuse_target_missing:' + str(target))
            break
        current = by_id[target]
    root = Path(records_root)
    key = (os.path.normcase(str(root.absolute())), json.dumps([_brief(row) for row in chain], sort_keys=True, ensure_ascii=False))
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return deepcopy(_CACHE[key])
    details = OrderedDict()

    def add(owner, result, attempt, record, fallback_episode=None):
        episode = result.get('episode_dir') or result.get('episode') or fallback_episode
        if not episode and result.get('accounting') and isinstance(result['accounting'], str):
            episode = str(Path(result['accounting']).parent)
        identity = os.path.normcase(os.path.normpath(str(episode))) if episode else owner['id'] + f':attempt_{attempt}'
        item = {'job_id': owner['id'], 'attempt': attempt, 'episode': str(episode) if episode else None,
                'record': record, 'record_line': 1, 'status': result.get('status') or owner.get('status'), **_cost(result)}
        # A current stored result may supplement its exact persisted episode;
        # it is never another model request merely because two copies exist.
        if identity in details:
            previous = details[identity]
            item['also_recorded_at'] = list(dict.fromkeys(previous.get('also_recorded_at', []) + [previous['record']]))
        details[identity] = item

    # Read actual baseline first; its copied reuse result is not a new attempt.
    for owner in reversed(chain):
        result = owner.get('result') or {}
        directory = root / owner['id']
        paths = sorted(directory.glob('attempt_*/result.json'), key=lambda p: int(p.parent.name.split('_')[-1]))
        found = set()
        for path in paths:
            attempt = int(path.parent.name.split('_')[-1])
            found.add(attempt)
            fallback = None
            if owner.get('episode'):
                fallback = str(Path(owner['episode']).parent / ('attempt_' + str(attempt)))
            add(owner, _read(path), attempt, str(path), fallback)
        attempt = int(owner.get('attempt') or 0)
        if result:
            result_episode = result.get('episode_dir') or result.get('episode')
            result_attempt = attempt
            if result_episode and Path(result_episode).name.startswith('attempt_'):
                try:
                    result_attempt = int(Path(result_episode).name.split('_')[-1])
                except ValueError:
                    pass
            add(owner, result, result_attempt, f"jobs[{owner['id']}].result", owner.get('episode'))
            # A running retry can still carry the previous terminal result.
            # That does not account for the new in-flight attempt.
            if result_attempt:
                found.add(result_attempt)
        for missing in set(range(1, attempt + 1)) - found:
            fallback = str(Path(owner['episode']).parent / ('attempt_' + str(missing))) if owner.get('episode') else None
            add(owner, {}, missing, str(directory / f'attempt_{missing}/result.json'), fallback)
        if not result and not paths and not attempt:
            add(owner, {}, 0, f"jobs[{owner['id']}].result", owner.get('episode'))
    values = list(details.values())
    unknown = sum(row['unknown_calls'] for row in values)
    calls_known = all(row['model_calls'] is not None for row in values)
    total_known = all(row['total_tokens'] is not None for row in values) and not warnings
    result = {'known_tokens': sum(row['known_tokens'] for row in values),
              'total_tokens': sum(row['total_tokens'] for row in values) if total_known else None,
              'model_calls': sum(row['model_calls'] for row in values) if calls_known else None,
              'known_model_calls': sum(row['model_calls'] or 0 for row in values),
              'unknown_calls': unknown or (1 if warnings else 0), 'attempts': len(values),
              'attempt_details': values, 'episodes': [row['episode'] for row in values],
              'warnings': warnings, 'scope': 'current_actor_job_and_explicit_reused_baseline'}
    _CACHE[key] = deepcopy(result)
    _CACHE.move_to_end(key)
    while len(_CACHE) > _LIMIT:
        _CACHE.popitem(last=False)
    return result
