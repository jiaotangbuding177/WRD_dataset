"""Automatic missing-stage continuation inside the sole persistent pipeline.

No business executor, model probes, repeated paid verdict or admission gate.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def resource_revision_budget(app, route, jobs):
    """User cap counts distinct resource revisions, not retries or evidence work."""
    limit = app.config.get('max_resource_revisions')
    used = sum(j['kind'] == 'make' and j['id'] != 'make__' + route['id']
               and (j.get('attempt', 0) > 0 or j['status'] in ('pending', 'running'))
               for j in jobs)
    return used, limit, limit is not None and used >= int(limit)


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def supplement(result, episode=None):
    """Overlay a proven exact provider receipt without altering old results."""
    ep = episode or result.get('episode_dir') or result.get('episode')
    if not ep:
        return result.get('usage') or {}
    ep = Path(ep)
    receipt = read(ep/'usage_supplement.json', {})
    original = result.get('usage') or {}
    value = receipt.get('usage') or {}
    raw = ep/'native_events.jsonl'
    if (receipt.get('schema') != 'native-provider-usage-supplement-v1'
            or value.get('measurement_status') != 'complete' or not raw.is_file()
            or receipt.get('source_sha256') != hashlib.sha256(raw.read_bytes()).hexdigest()
            or value.get('known_total_tokens', -1) < original.get('known_total_tokens', 0)):
        return original
    if original.get('total_tokens') is not None:
        return original
    return value


def evidence_receipts(jobs):
    out = []
    for j in jobs:
        if j.get('episode'):
            f = Path(j['episode'])/'usage_supplement.json'
            if f.is_file():
                out.append((str(f), hashlib.sha256(f.read_bytes()).hexdigest()))
    return out


def repair_request(review, root):
    """Use the existing verdict; legacy prose needs a concrete existing resource."""
    root = Path(root)
    structured = review.get('next_step') or {}
    forbidden = ('上限', '最多调用', '提前收尾', '超出即交付', '硬限制', '改运行环境',
                 '只暴露一条', '重跑基线', '重跑无技能', '先增加核验', '新增门禁')
    def prohibited(text):
        # A warning NOT to alter the experiment is not a request to alter it.
        # Remove only explicitly negated directives, not the rest of a clause:
        # a subsequent positive instruction must still be rejected.
        terms = r'(?:硬调用上限|调用上限|提前收尾|硬限制|改运行环境|重跑基线|重跑无技能|新增门禁|先增加核验)'
        negative = r'(?:不得|不要|禁止|避免|不)(?:新增|增加|引入|设置|采用|使用)?' + terms
        text = re.sub(negative + r'(?:[、或和及]' + terms + r')*', '', text)
        return any(x in text for x in forbidden)
    if structured.get('action') and structured.get('action') != 'repair_resource':
        return []
    if structured.get('action') == 'repair_resource':
        items = structured.get('repairs', [])
    else:
        items = []
        files = {p.name:p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        for note in review.get('repair_notes', []):
            if not isinstance(note, str) or prohibited(note):
                continue
            evidence_only = ('补做一次','补一次真实','补充候选技能的真实业务','若可取得',
                '补来源比对','无法比对是否原样','补充来源或比对','未经本轮业务','若该公共技能后续可用',
                '从未在真实任务中运行','若原技能库可得')
            if any(v in note for v in evidence_only):
                continue
            if not any(v in note for v in ('错误','失败','缺陷','重复','字段','参数','转义','退出码',
                    '丢失','不支持','不一致','强制','默认','过宽','编码','语法','缺少','未说明','无法生成',
                    '误用','截断','反复','全文读取','两次','各做了一次')):
                continue
            # A request to beat a number or rewrite prose alone is no repair plan.
            names = re.findall(r'[A-Za-z_][A-Za-z0-9_.-]*\.(?:py|js|json|html|md|txt|yaml|yml)', note)
            targets = sorted({files[n] for n in names if n in files})
            if not targets or not any(x in note for x in ('修', '补', '改', '增加', '合并', '默认', '入口')):
                continue
            items.append({'targets':targets, 'issue':note, 'change':note,
                          'replaced_work':'复用现成资源消除评审中具体反复操作',
                          'evidence_refs':review.get('evidence_refs', [])})
    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get('issue','')) + str(item.get('change',''))
        targets = item.get('targets') or []
        if (not text.strip() or not item.get('change') or not item.get('replaced_work')
                or not item.get('evidence_refs') or prohibited(text)):
            continue
        try:
            if not targets or any(not (root/t).resolve().is_relative_to(root.resolve())
                                  or not (root/t).is_file() for t in targets):
                continue
        except (TypeError, OSError):
            continue
        # Issue identity ignores changed metrics/numbers, not changed resources.
        canonical = re.sub(r'\d+(?:[,.]\d+)*', '#', text)
        valid.append({**item, 'identity':digest({'targets':sorted(targets), 'change':canonical})[:20]})
    return valid


def recover_evidence(app, route, jobs, all_jobs=None):
    from .business_cost import all_attempts, clear_cache
    from . import native
    active = set(route.get('active_case_ids', []))
    episodes = set()
    # The scheduler already read the full queue. Never decode that table again
    # for each historical Actor while merely checking missing receipts.
    snapshot = all_jobs if all_jobs is not None else app.state.jobs()
    by_id = snapshot if isinstance(snapshot,dict) else {j['id']:j for j in snapshot}
    for j in jobs:
        if j['kind'] != 'actor' or (active and j['case_id'] not in active):
            continue
        costs = all_attempts(j, by_id, app.out/'records')
        episodes.update(x['episode'] for x in costs['attempt_details']
                        if x.get('episode') and x.get('total_tokens') is None)
    fingerprint = []
    for ep in sorted(episodes):
        f = Path(ep)/'native_events.jsonl'
        fingerprint.append((ep, f.stat().st_mtime_ns, f.stat().st_size) if f.is_file() else (ep,None,None))
    sig = digest(fingerprint)
    state = route.setdefault('automatic_continuation', {})
    if state.get('evidence_signature') == sig:
        return False
    recovered = []
    for ep in episodes:
        f = Path(ep)/'native_events.jsonl'
        if not f.is_file():
            continue
        raw = f.read_bytes()
        value = native._usage(raw, event_file_present=True)
        if value['measurement_status'] != 'complete':
            continue
        target = Path(ep)/'usage_supplement.json'
        app_write(target, {'schema':'native-provider-usage-supplement-v1',
            'source_sha256':hashlib.sha256(raw).hexdigest(), 'usage':value,
            'at':datetime.now().astimezone().isoformat(), 'inference_calls_added':0})
        recovered.append(str(target))
    state.update(evidence_signature=sig, evidence_checked_at=datetime.now().astimezone().isoformat(),
        evidence_recovered=recovered, evidence_missing_episodes=len(episodes)-len(recovered),
        evidence_status='recovered' if recovered else 'blocked_original_usage_missing')
    app.state.route(route)
    if recovered:
        clear_cache()
    return bool(recovered)


def app_write(path, value):
    # Use the sole pipeline's existing atomic writer, not another queue.
    import pipeline
    pipeline.write(path,value)


def watch_materials(app, route, jobs):
    """Wake a blocked preparation only for newly available declared real input."""
    from . import recall
    follow = route.get('selection_repair') or {}
    review = route.get('value_review') or {}
    if follow.get('status') != 'blocked_inputs' and review.get('decision') != 'defer':
        return False
    learned = set(route.get('learning_source_ids',route.get('source_ids',[])))
    source_ids = {v.get('source_id') for v in route.get('blocked_inputs',[]) if isinstance(v,dict)}
    source_ids.update(route.get('development_source_ids',[]))
    source_ids.update(c.get('source_id') for c in route.get('tasks',[]))
    files = []
    for sid in sorted(s for s in source_ids if s and s not in learned):
        for item in recall.source_materials(app.bindings.get(sid,{}))[0]:
            path = Path(item['path']);stat = path.stat()
            files.append((sid,str(path),stat.st_size,stat.st_mtime_ns))
    state = route.setdefault('automatic_continuation',{})
    previous = state.get('input_files')
    state['input_files'] = files
    app.state.route(route)
    if previous is None or not files or digest(previous)==digest(files):
        return False  # Establish baseline; never repeat an old full search.
    additions = [f for f in files if list(f) not in previous and f not in previous]
    if not additions:
        return False
    identity = digest(additions)[:16]
    old = route.get('selection_repair')
    if old:
        route.setdefault('selection_repair_history',[]).append(old)
    reason = '仅核对这次新到的真实独立材料来源:'+','.join(sorted({f[0] for f in additions}))+'.复用旧准备/排除理由，仅补新文件能否完成原委托，不重复全库已核条目。'
    key = app.state.enqueue('prepare',route['id'],{'full_catalog':True,
        'selection_repair':'automatic-input-'+identity,'repair_scope':reason,
        'previous_reason':route.get('task_note',''),'previous_case_decisions':route.get('case_decisions',[])},
        route['lane'],'automatic-input-'+identity)
    route['selection_repair'] = {'id':'automatic-input-'+identity,'reselect':True,
        'repair':False,'status':'preparing','prepare_job':key,'reason':reason}
    state['input_status']='new_real_input_queued'
    app.state.route(route)
    return True


def automatic_followup(app, route, jobs, all_jobs=None):
    if any(j['status'] in ('pending','running','unknown','held','maintenance') for j in jobs):
        return False
    if route.get('library_status') in ('retained','rejected') or not route.get('skill_root'):
        return False
    if watch_materials(app, route, jobs):
        return True
    follow = route.get('selection_repair') or {}
    if follow.get('status') in ('waiting','preparing','making','trial','reviewing'):
        return False  # Let an explicit or still-unsettled continuation finish first.
    review = route.get('value_review') or {}
    if review.get('decision') not in ('revise','defer'):
        return False
    if review.get('decision') == 'defer':
        recover_evidence(app, route, jobs, all_jobs)
    used, limit, exhausted = resource_revision_budget(app, route, jobs)
    if exhausted:
        route['resource_revision_policy'] = {'limit':limit, 'used':used,
            'resource_repair_closed':True, 'reason':'用户限定最多4轮资源修订，不发第5轮；缺证据与缺输入仍单独补齐。'}
        if review.get('decision') == 'revise':
            route['library_status'] = 'rejected'
            route['make_status'] = '不入库：已到用户资源修订上限，未证明减负'
        app.state.route(route)
        return False
    if app.config.get('resource_revision_mode') == 'evidence_inputs_only':
        route['resource_revision_policy'] = {'limit':limit, 'used':used,
            'resource_repair_paused':True, 'reason':'用户本轮只补证据和独立输入，不再开启下一轮资源修订。'}
        app.state.route(route)
        return False
    requests = repair_request(review, route['skill_root'])
    history = route.setdefault('automatic_continuation', {}).setdefault('repairs', {})
    new = [x for x in requests if x['identity'] not in history]
    if not new:
        state = route['automatic_continuation']
        state['repair_status'] = 'no_new_concrete_resource_plan'
        app.state.route(route)
        return False
    identity = digest(sorted(x['identity'] for x in new))[:16]
    feedback = app.out/'automatic_continuation'/route['id']/identity/'feedback.json'
    app_write(feedback, {'prior_review':{k:v for k,v in review.items() if k!='repair_notes'},
        'repair_notes':[x['change'] for x in new], 'resource_repairs':new,
        'instruction':'只沿这些具体资源问题局修，不改真实任务/预算/原生环境、不写本题答案、不硬限调用或提前交付。'
        '完整复现公开程序、用法准确；同字节不重做业务，无实质问题返回未变化，制作记录留包外。'})
    old = route.get('selection_repair')
    if old:
        route.setdefault('selection_repair_history',[]).append(old)
    campaign = 'automatic-resource-' + identity
    key = app.state.enqueue('make',route['id'],{'selection_repair':campaign,
        'previous':{'skill_root':route['skill_root'],'feedback':str(feedback),
                    'making_jobs':[j for j in jobs if j['kind']=='make']}},route['lane'],campaign)
    route['selection_repair'] = {'id':campaign, 'reselect':False,'repair':True,
        'status':'making','make_job':key,'reason':'既有评审具体资源缺陷自动接续',
        'created_at':datetime.now().astimezone().isoformat()}
    for item in new:
        history[item['identity']] = {'job':key,'feedback':str(feedback),'targets':item['targets']}
    route['automatic_continuation']['repair_status']='queued'
    app.state.route(route)
    return True
