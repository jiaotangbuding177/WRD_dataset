"""Add missing-source work to the existing queue, without another runner.

This prepares ordinary screen inputs. It never runs a model, changes an
existing job, or edits a skill. PID 29412 can consume the appended jobs with
its already-loaded recovery task builder.
"""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3


def _read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, TypeError):
        return default


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def _old_decisions(config, db):
    decisions = {}
    for base in config['legacy_native_roots']:
        for path in sorted(Path(base).glob('screen_*/workspace/outputs/screen.json')):
            for row in (_read(path, {}) or {}).get('decisions', []):
                if isinstance(row, dict) and row.get('source_id'):
                    decisions[row['source_id']] = {**row, 'record': str(path)}
    out = Path(config['output'])
    # Only the four completed, original discovery jobs. Supplement results are
    # separate so preparing the same work again cannot create a new paid pass.
    original_ids = ('screen__6083616fab97', 'screen__c78d5348877a',
                    'screen__legacy-route-continuation', 'screen__legacy-deferred-continuation')
    for job_id in original_ids:
        for path in sorted((out / 'records' / job_id).glob('screen_attempt_*.json')):
            for row in (_read(path, {}) or {}).get('model_output', {}).get('decisions', []):
                if isinstance(row, dict) and row.get('source_id'):
                    decisions[row['source_id']] = {**row, 'record': str(path)}
    return decisions


def _old_groups(root):
    groups, holds = defaultdict(list), defaultdict(list)
    path = root / 'output/20261021_workflow_library_v2/candidate_directory.json'
    for row in (_read(path, {}) or {}).get('proposals', []):
        for sid in row.get('source_ids', []):
            groups[sid].append({'proposal_id': row.get('proposal_id'), 'record': str(path),
                                'meaning': '旧主题提议，不视为已证明的同路线或已淘汰'})
    base = root / 'output/20261021_workflow_library_parallel4_recovery1/route_reviews'
    for path in sorted(base.glob('*/checked_cards.json')):
        value = _read(path, {}) or {}
        for row in value.get('cards', []):
            for sid in row.get('source_ids', []):
                holds[sid].append({'candidate_id': row.get('id'), 'status': 'old_card', 'record': str(path)})
        for item in value.get('holds', []):
            row = item.get('raw_card', {})
            for sid in row.get('source_ids', []):
                holds[sid].append({'candidate_id': row.get('id'), 'status': 'old_hold',
                                   'reason': item.get('reason'), 'record': str(path),
                                   'steps': (row.get('route_signature') or {}).get('steps', [])})
    return groups, holds


def prepare_recheck(app, plan_path):
    """Append only an explicitly selected old-rule review to the same queue.

    The saved plan is written before enqueueing, so a repeated command after
    interruption fills missing rows with the same IDs. Existing attempts and
    source processed flags are never reset. This function does not run models.
    """
    plan = _read(plan_path)
    rows = plan.get('sources', []) if isinstance(plan, dict) else plan
    if not isinstance(rows, list) or not rows:
        raise ValueError('定向补查计划需要非空sources列表或来源记录列表。')
    selected = {}
    for row in rows:
        row = {'source_id': row} if isinstance(row, str) else row
        sid = row.get('source_id') if isinstance(row, dict) else None
        if sid not in app.bindings:
            raise ValueError(f'定向补查来源不在当前真实来源表中：{sid}')
        selected[sid] = row
    folder = app.out / 'coverage/rechecks'
    key = hashlib.sha256('\n'.join(sorted(selected)).encode()).hexdigest()[:16]
    manifest_path = folder / (key + '.json')
    manifest = _read(manifest_path)
    if not manifest:
        previous = [_read(path, {}) or {} for path in sorted(folder.glob('*.json'))]
        covered = {sid for item in previous for job in item.get('jobs', []) for sid in job['source_ids']}
        pending = sorted(set(selected) - covered)
        members = defaultdict(list)
        for route in app.state.routes():
            for sid in route.get('source_ids', []):
                members[sid].append(route['id'])
        notes = {}
        for sid in pending:
            binding = app.bindings[sid]
            source = binding.get('conversation') or {}
            source_path = source.get('path') if isinstance(source, dict) else source
            conversation = _read(source_path, {}) or {}
            requests = []
            for message in conversation.get('messages', []):
                if message.get('role') == 'user':
                    content = message.get('content', '')
                    requests.append({'message_id': message.get('id'),
                                     'text': content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)})
            notes[sid] = {
                'source_id': sid, 'action': 'recheck_old_constraint',
                'reason': '仅补查已识别的旧限制影响，旧判断作为历史保留；不是从零重跑，也不是要求必须新增技能。',
                'uncovered_work': {
                    'prior_decision': selected[sid], 'existing_route_ids': members.get(sid, []),
                    'all_user_requests_in_order': requests,
                    'scope': '逐条看完整用户请求，再按需读真实工具动作和原文，允许同一会话有多条局部路线。'
                             '不再要求同批第二来源；不能以多主题无共同主路线整体淘汰。'
                             '先与已有路线按实际步骤和资源用途归并，业务内容差异作为输入变化；'
                             '新增交付物不否定可复用的主要步骤。只有实际可替代重复规划、代码或材料处理的路线才保留候选。'
                             '相同路线复用现有候选/资源，不重复制作；不同小路线分别保留来源与条件。'
                             '缺材料、账号或尚不能确认价值用defer并写具体缺件，不能据此认定没有复用价值。'
                             '确无可替代工作才no_value。此阶段不制作技能、不运行业务、不预定保留结论。',
                },
            }
        active = Counter(j['lane'] for j in app.state.jobs() if j['status'] in ('pending', 'running', 'unknown'))
        lanes = sorted(range(int(app.config.get('workers', 8))), key=lambda lane: (active[lane], lane))
        jobs = []
        size = int(app.config.get('screen_batch_size', 16))
        for index, offset in enumerate(range(0, len(pending), size)):
            batch = pending[offset:offset + size]
            route_id = 'constraint-recheck-' + hashlib.sha256('\n'.join(batch).encode()).hexdigest()[:16]
            payload = {'source_ids': batch, 'coverage_phase': 'old_constraint_recheck',
                       'recovery': {'candidates': [], 'new_without_cards': [notes[sid] for sid in batch],
                                    'continuation_type': 'old_constraint_recheck'}}
            jobs.append({'job_id': 'screen__' + route_id, 'route_id': route_id, 'source_ids': batch,
                         'lane': lanes[index % len(lanes)], 'payload': payload})
        manifest = {'created_at': datetime.now().astimezone().isoformat(), 'input_plan': str(Path(plan_path)),
                    'requested_source_ids': sorted(selected), 'source_ids': pending, 'jobs': jobs,
                    'reused_source_ids': sorted(set(selected) & covered), 'prior_decisions': list(selected.values()),
                    'model_calls_by_preparation': 0, 'existing_jobs_modified': 0}
        _write(manifest_path, manifest)
    # Also finish enqueueing an earlier overlapping plan interrupted after its
    # manifest was persisted. INSERT OR IGNORE preserves all paid attempts.
    for path in sorted(folder.glob('*.json')):
        saved = _read(path, {}) or {}
        for job in saved.get('jobs', []):
            app.state.enqueue('screen', job['route_id'], job['payload'], job['lane'])
    result = status(app)
    result['recheck_manifest'] = str(manifest_path)
    return result


def _recheck_state(app, jobs):
    rows, source_ids, decisions = {}, set(), {}
    for path in sorted((app.out / 'coverage/rechecks').glob('*.json')):
        for row in (_read(path, {}) or {}).get('jobs', []):
            rows[row['job_id']] = row
            source_ids.update(row['source_ids'])
    counts, costs = Counter(), {'known_tokens': 0, 'model_calls': 0, 'unknown_calls': 0}
    for jid, row in rows.items():
        job = jobs.get(jid, {})
        answered = set()
        records = app.out / 'records' / jid
        for path in sorted(records.glob('screen_attempt_*.json'), key=lambda p: int(p.stem.rsplit('_', 1)[-1])):
            for decision in (_read(path, {}) or {}).get('model_output', {}).get('decisions', []):
                if isinstance(decision, dict) and decision.get('source_id') in row['source_ids']:
                    answered.add(decision['source_id'])
                    decisions[decision['source_id']] = {**decision, 'record': str(path)}
        remaining = len(set(row['source_ids']) - answered)
        state = job.get('status', 'not_enqueued')
        counts['answered'] += len(answered)
        counts[state] += remaining
        for path in records.glob('attempt_*/result.json'):
            usage = (_read(path, {}) or {}).get('usage', {})
            costs['known_tokens'] += usage.get('total_tokens') or usage.get('known_total_tokens') or 0
            costs['model_calls'] += usage.get('model_calls') or usage.get('known_model_calls') or 0
            costs['unknown_calls'] += usage.get('unknown_calls') or usage.get('unknown_usage_calls') or 0
    result = {'sources': len(source_ids), 'jobs': len(rows), 'answered': len(decisions),
              'pending': counts['pending'] + counts['not_enqueued'], 'running': counts['running'],
              'terminal_unanswered': sum(counts[s] for s in ('done', 'failed', 'unknown', 'held', 'superseded')),
              'decisions': dict(Counter(d.get('action', 'unknown') for d in decisions.values())),
              'recorded_costs': costs}
    return result, decisions


def prepare(app):
    """Idempotently enqueue focused completion; do not start a second runner."""
    out = app.out / 'coverage'
    manifest_path = out / 'manifest.json'
    existing = _read(manifest_path)
    if existing:
        return status(app)
    config, root = app.config, Path(__file__).resolve().parents[2]
    with app.state.connect() as db:
        decisions = _old_decisions(config, db)
    bindings = app.bindings
    routes = app.state.routes()
    original_routes = {r['id'] for r in routes}
    members = defaultdict(list)
    for route in routes:
        for sid in route.get('source_ids', []):
            members[sid].append(route['id'])
    prior = set((_read(Path(config['legacy_output']) / 'fullscan_queue.json', {}) or {}).get('previously_screened_ids', []))
    prior_missing = sorted((prior - set(decisions)) - set(members))
    groups, holds = _old_groups(root)
    _write(out / 'original_50_routes.json', routes)
    _write(out / 'original_jobs.json', app.state.jobs())

    # Restore only explicit paid links. Transaction reads the freshest route
    # and changes source_ids alone; no skills, tasks, judgments or budgets.
    restored = []
    with app.state.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for sid, decision in decisions.items():
            target = decision.get('route_id')
            if sid in members or sid not in bindings or decision.get('action') != 'reuse' or target not in original_routes:
                continue
            row = db.execute('SELECT payload FROM routes WHERE id=?', (target,)).fetchone()
            route = json.loads(row[0])
            source_ids = sorted(set(route.get('source_ids', [])) | {sid})
            db.execute("UPDATE routes SET payload=json_set(payload,'$.source_ids',json(?)) WHERE id=?",
                       (json.dumps(source_ids), target))
            members[sid].append(target)
            restored.append({'source_id': sid, 'route_id': target, 'record': decision['record']})
    _write(out / 'restored_links.json', restored)

    excluded = {sid for sid, d in decisions.items() if d.get('action') == 'no_value' and sid in bindings}
    notes, conversations = {}, {}
    for sid, binding in bindings.items():
        if sid in excluded:
            continue
        source = binding.get('conversation') or {}
        path = source.get('path') if isinstance(source, dict) else source
        conversation = _read(path, {}) or {}
        users = []
        for message in conversation.get('messages', []):
            if message.get('role') != 'user':
                continue
            content = message.get('content', '')
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            users.append({'message_id': message.get('id'), 'text_preview': text[:1200],
                          'truncated': len(text) > 1200})
        conversations[sid] = {'user_messages': len(users), 'messages': len(conversation.get('messages', []))}
        old = decisions.get(sid, {})
        notes[sid] = {
            'source_id': sid, 'action': old.get('action', 'prior_screened_without_per_source_decision'),
            'reason': '这是用户授权的缺漏补判，不代表此前已判new。已有主路线和历史结论保留，不从零重筛。'
                      '只核对尚未确认的局部工作路线；没有复用价值才明确no_value，暂缺输入或不确定用defer，不能当淘汰。',
            'uncovered_work': {
                'old_action': old.get('action'), 'old_reason': old.get('reason'),
                'old_record': old.get('record'), 'existing_route_ids': members.get(sid, []),
                'old_proposals': groups.get(sid, []), 'old_candidate_records': holds.get(sid, []),
                'all_user_requests_in_order': users,
                'scope': '这些请求覆盖整条会话，而非旧预览的前四个。先复用原判断，再检查后续需求、关键工具/动作、'
                         '纠正后新增或不同的小路线。上面的截断内容及必要工具轨迹从该source完整conversation读取。'
                         '同一来源可以有多个不同工作流，分别写入routes并重复引用source_id；decisions只记本来源的补漏结论。'
                         '有具体可替代公共工作的单来源也可新增；不要求同批两条，不要求本阶段就具备附件或资源。'
                         '缺材料记录conditions，后续制作时再复现。只有实际步骤与资源用途相同才merge_into，'
                         '不要只凭公司报告/Excel/图片等大类名硬合并，不要因增加一个产物就否定共同主路线。'
                         '主要路线不同的小路线应独立保留；不为增加数量拆分内容变化。'
                         '新增使用不同id；既有50候选不删除、不重写。此次只整理遗漏路线，不制作程序或运行企业业务。',
            },
        }
    _write(out / 'prior_117_dispositions.json', [
        {'source_id': sid, 'physical_line': bindings[sid].get('physical_line'),
         'old_proposals': groups.get(sid, []), 'old_candidate_records': holds.get(sid, []),
         'current_disposition': '待补判，旧主题提议已找回' if groups.get(sid) else '待补判，未找到旧主题提议'}
        for sid in prior_missing])

    unresolved = set(notes) - set(members)
    phases = [
        ('prior117', prior_missing),
        ('deferred_or_skipped', sorted(unresolved - set(prior_missing))),
        ('mapped_long', sorted(s for s in notes if s in members and conversations[s]['user_messages'] > 4)),
        ('mapped_other', sorted(s for s in notes if s in members and conversations[s]['user_messages'] <= 4)),
    ]
    # Do not put supplementary screen work in a lane with any original pending
    # or active task. Existing screen priority would otherwise delay that task.
    busy = {j['lane'] for j in app.state.jobs() if j['status'] in ('pending', 'running', 'unknown')}
    lanes = [lane for lane in range(8) if lane not in busy]
    if not lanes:
        _write(out / 'prepared_waiting_for_idle_lanes.json', {'reason': '原任务占用全部通道；不抢占', 'source_count': len(notes)})
        return {'status': 'prepared_waiting_for_idle_lanes', 'source_count': len(notes)}
    jobs, index = [], 0
    size = int(config.get('screen_batch_size', 16))
    for phase, source_ids in phases:
        for offset in range(0, len(source_ids), size):
            batch = source_ids[offset:offset + size]
            lane = lanes[index % len(lanes)]
            key = 'coverage-' + phase + '-' + hashlib.sha256('\n'.join(batch).encode()).hexdigest()[:10]
            # Existing recovery builder preserves uncovered_work, so this also
            # works in PID 29412 without hot reload or executor modifications.
            payload = {'source_ids': batch, 'recovery': {
                'candidates': [], 'new_without_cards': [notes[sid] for sid in batch],
                'continuation_type': 'coverage_completion'}, 'coverage_phase': phase}
            job_id = app.state.enqueue('screen', key, payload, lane)
            jobs.append({'job_id': job_id, 'phase': phase, 'source_ids': batch, 'lane': lane})
            index += 1
    manifest = {
        'created_at': datetime.now().astimezone().isoformat(), 'original_runner': app.state.meta('owner'),
        'total_sources': len(bindings), 'explicit_no_value_excluded': len(excluded),
        'supplement_sources': len(notes), 'prior_117_restored_to_old_proposals': sum(bool(groups.get(sid)) for sid in prior_missing),
        'restored_link_count': len(restored), 'phase_sources': {k: len(v) for k, v in phases},
        'long_conversations': sum(v['user_messages'] > 4 for v in conversations.values()),
        'original_route_ids': sorted(original_routes), 'jobs': jobs, 'lanes': lanes,
        'model_calls_by_preparation': 0, 'existing_jobs_modified': 0,
        'task_builder': 'existing screen recovery, explicit uncovered_work notes; no live reload',
    }
    _write(manifest_path, manifest)
    app.state.meta('coverage_completion', {'manifest': str(manifest_path), 'sources': len(notes), 'jobs': len(jobs)})
    return status(app)


def status(app):
    manifest = _read(app.out / 'coverage/manifest.json', {}) or {}
    jobs = {j['id']: j for j in app.state.jobs()}
    phases = defaultdict(Counter)
    completed, in_progress, pending, terminal_unanswered = set(), set(), set(), set()
    dispositions = {}
    costs = {'known_tokens': 0, 'model_calls': 0, 'unknown_calls': 0}
    for row in manifest.get('jobs', []):
        job = jobs.get(row['job_id'], {})
        state = job.get('status', 'not_enqueued')
        phases[row['phase']][state] += len(row['source_ids'])
        for path in (app.out / 'records' / row['job_id']).glob('attempt_*/result.json'):
            usage = (_read(path, {}) or {}).get('usage', {})
            costs['known_tokens'] += usage.get('total_tokens') or usage.get('known_total_tokens') or 0
            costs['model_calls'] += usage.get('model_calls') or usage.get('known_model_calls') or 0
            costs['unknown_calls'] += usage.get('unknown_calls') or usage.get('unknown_usage_calls') or 0
        answered = set()
        # Partial answers remain useful even when a later omitted-item followup
        # fails. Completion means an actual answer, never just job termination.
        for path in sorted((app.out / 'records' / row['job_id']).glob('screen_attempt_*.json')):
            value = _read(path, {}) or {}
            for decision in value.get('model_output', {}).get('decisions', []):
                if isinstance(decision, dict) and decision.get('source_id') in row['source_ids']:
                    # A merged route may list sources from other batches. Only
                    # explicit answers for this batch count as completion.
                    answered.add(decision['source_id'])
                    dispositions[decision['source_id']] = decision
        completed.update(answered)
        if state == 'running':
            in_progress.update(row['source_ids'])
        elif state == 'pending':
            pending.update(row['source_ids'])
        elif state in ('failed', 'unknown', 'done'):
            terminal_unanswered.update(set(row['source_ids']) - answered)
    recheck, recheck_decisions = _recheck_state(app, jobs)
    effective = _old_decisions(app.config, None)
    effective.update(dispositions)
    effective.update(recheck_decisions)
    _write(app.out / 'coverage/latest_source_dispositions.json', list(effective.values()))
    _write(app.out / 'coverage/targeted_recheck_status.json', recheck)
    routes = app.state.routes()
    result = {'updated_at': datetime.now().astimezone().isoformat(), 'runner': app.state.meta('owner'),
              'total_sources': manifest.get('total_sources'), 'supplement_sources': manifest.get('supplement_sources'),
              'completed_sources': len(completed), 'in_progress_sources': len(in_progress), 'pending_sources': len(pending),
              'terminal_unanswered_sources': len(terminal_unanswered),
              'completion_percent': round(100 * len(completed) / manifest['supplement_sources'], 2) if manifest.get('supplement_sources') else 0,
              'phases': dict(phases), 'restored_links': manifest.get('restored_link_count'),
              'prior117_old_proposals_restored': manifest.get('prior_117_restored_to_old_proposals'),
              'original_candidates': len(manifest.get('original_route_ids', [])),
              'new_candidates': len({r['id'] for r in routes} - set(manifest.get('original_route_ids', []))),
              'library_states': dict(Counter(r.get('library_status', 'not_generated') for r in routes)),
              'supplement_decisions': dict(Counter(v.get('action', 'unknown') for v in dispositions.values())),
              'targeted_recheck': recheck,
              'effective_source_decisions': dict(Counter(v.get('action', 'unknown') for sid, v in effective.items() if sid in app.bindings)),
              'supplement_recorded_costs': costs,
              'in_flight_costs_not_finalized': sum(jobs.get(v['job_id'], {}).get('status') == 'running' for v in manifest.get('jobs', [])),
              'jobs': dict(Counter(j['status'] for j in jobs.values()))}
    _write(app.out / 'coverage/latest_dispositions.json', list(dispositions.values()))
    _write(app.out / 'coverage/status.json', result)
    lines = [
        '# 补漏进度', '', f"快照时间：{result['updated_at']}", '',
        '实际在途与队列继续由[原实时页面](../progress.html)显示。此文件是运行coverage-status时的来源统计快照。', '',
        '补漏和价值筛查由当前同一管道、同一队列执行；实际主管身份看原实时页面。', '',
        f"原117条去向找回 {result['prior117_old_proposals_restored']}/117；明确漏关联已恢复 {result['restored_links']}/5。找回提议不等于已通过语义判断。", '',
        f"补判已回答 {result['completed_sources']}/{result['supplement_sources']}（{result['completion_percent']}%）；在途 {result['in_progress_sources']}；待办 {result['pending_sources']}；终态未回答 {result['terminal_unanswered_sources']}。", '',
        '| 范围 | 来源数 | 已完成批次所含来源 | 在途 | 待办 | 失败或未知 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    labels = {'prior117': '117条旧去向补判', 'deferred_or_skipped': '暂缓或曾跳过',
              'mapped_long': '已有路线中的长会话', 'mapped_other': '其他已有路线来源'}
    for phase, counts in phases.items():
        lines.append(f"| {labels.get(phase, phase)} | {sum(counts.values())} | {counts['done']} | {counts['running']} | {counts['pending']} | {counts['failed'] + counts['unknown']} |")
    lines += ['', '表中批次完成量与上方实际回答量分开，局部漏答不冒充完成。', '',
              f"原候选 {result['original_candidates']}，新增候选 {result['new_candidates']}；全库状态：{json.dumps(result['library_states'], ensure_ascii=False)}。候选不等于有效技能。", '',
              f"原903条补漏和旧204条排除口径保留；另针对旧限制影响定向补查{recheck['sources']}条，已回答{recheck['answered']}，待办{recheck['pending']}，在途{recheck['running']}，终态未回答{recheck['terminal_unanswered']}。新决定单列并更新全来源去向，不改写旧决定。", '',
              '其余保留原判断和已有资源，只补遗漏；同一来源可有多个小路线，缺材料先记录条件。所有候选仍需可靠资源、真实使用与交付达线、业务Token和调用下降才保留。', '',
              f"补漏初筛已收齐账单：{costs['known_tokens']:,} Token / {costs['model_calls']:,} 次调用；另有{result['in_flight_costs_not_finalized']}个初筛会话在途，费用尚未结清。新候选的制作和业务费用由原总账记录，不能把此处初筛小计当全链路费用。", '',
              '查询：`python pipeline.py coverage-status`。准备命令`python pipeline.py complete-coverage`可重复执行，只读取同一清单，不重复排队或调用模型。', '',
              '[117条旧去向](prior_117_dispositions.json) / [5条关联依据](restored_links.json) / [58批任务清单](manifest.json) / [补判决定](latest_dispositions.json)', '']
    (app.out / 'coverage/补漏进度.md').write_text('\n'.join(lines), encoding='utf-8')
    return result
