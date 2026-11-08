"""Write the three human-facing outputs of the single workflow pipeline."""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _number(value):
    return f"{value:,}" if isinstance(value, (int, float)) and not isinstance(value, bool) else "未记全"


def _plain(value):
    labels = {
        "pending": "待处理", "running": "正在运行", "completed": "会话完成",
        "failed": "失败，记录保留", "unknown": "状态不明，记录保留",
        "ready": "资源已提供", "published": "资源已提供", "skipped": "已跳过",
        "resource_ready": "资源已提供", "imported": "已复用原结果", "accepted": "已交付",
        "held": "未完成，记录保留", "error": "发生错误，记录保留", "done": "已完成",
        "make": "制作技能", "screen": "整理会话路线", "prepare": "准备真实任务",
        "no_skill": "无技能任务", "workflow": "使用技能任务", "stopped": "已停止",
        "not_evaluated": "已执行，交付待查看",
        "review": "复用价值筛选",
        "superseded": "旧记录保留，待业务完成后合并评审",
    }
    text = str(value or "尚无记录")
    return labels.get(text.lower(), text)


def _skill_file(route):
    root = route.get("skill_root")
    if not root:
        return None
    path = Path(root)
    return path if path.name == "SKILL.md" else path / "SKILL.md"


def _arm(arm):
    if arm is None:
        return "尚未运行"
    current = f"{_number(arm.get('tokens'))} Token / {_number(arm.get('calls'))} 次调用 / {_plain(arm.get('status'))}"
    attempts = arm.get("all_attempts")
    if not isinstance(attempts, dict):
        return current
    total, known = attempts.get("total_tokens"), attempts.get("known_tokens")
    unknown = attempts.get("unknown_calls")
    if isinstance(total, (int, float)) and not isinstance(total, bool) and unknown == 0:
        tokens = f"{_number(total)} Token"
    elif isinstance(known, (int, float)) and not isinstance(known, bool):
        tokens = f"至少 {_number(known)} Token，总量未记全"
    else:
        tokens = "Token 未记全"
    return ("当前结果记录：" + current + "\n本版全部业务尝试（含失败）："
            f"{tokens} / {_number(attempts.get('model_calls'))} 次调用；"
            f"{_number(attempts.get('attempts'))} 次尝试，{_number(unknown)} 次用量未记全")


def _selection_progress(route):
    progress = route.get("selection_progress") or {}
    labels = {
        "continuing": "本次接续中", "awaiting_independent_input": "缺独立试用输入",
        "repair_parked": "已修过，当前暂存", "evidence_pending": "待补业务证据",
        "retained": "保留", "rejected": "明确不保留",
    }
    label = progress.get("label") or labels.get(progress.get("state")) or "接续状态未记录"
    reason = progress.get("reason")
    return label + ("：" + str(reason) if reason else "")


def _performance_note(route):
    performance = route.get("performance") or {}
    if not performance:
        return "含失败的业务总开销尚未逐项确认"
    pair = performance.get("completed_pair_reduced")
    all_attempts = performance.get("all_attempts_reduced")
    if all_attempts is True:
        return "本版全部业务尝试（含失败）的 Token 与调用均下降"
    if pair is True:
        return "成功对照下降，含失败未证净省"
    if pair is False:
        return "当前完成对照未实现 Token 与调用双降"
    return "业务开销证据未齐，暂不判断减负"


def _campaign_count(value):
    if isinstance(value, list):
        return _number(len(value))
    if isinstance(value, dict):
        return _number(value.get("total", value.get("count")))
    return _number(value)


def _atomic(path, text):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_view(out: Path, snapshot: dict) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    esc = lambda value: html.escape(str(value), quote=True)
    runner = snapshot.get("runner") or {}
    conversations = snapshot.get("conversations") or {}
    counts = snapshot.get("counts") or {}
    routes = snapshot.get("routes") or []
    jobs = snapshot.get("jobs") or []
    updated = str(snapshot.get("updated_at") or "未记录")
    service_state = snapshot.get('services') or {}
    service_labels = {'ready':'正常，可接新任务','starting':'启动中','unchecked':'等待检查',
        'busy_wait':'等原会话结束后恢复','backoff':'等待恢复','http_unavailable':'接口不可达',
        'launch_blocked':'托管异常，已停新派发','blocked_owner':'端口被其他进程占用',
        'draining_temporary_host':'原会话收尾中','migrating_idle_host':'正在迁移空闲服务',
        'migration_wait':'等待迁移','launch_failed':'启动失败','stopped':'已停止'}
    service_rows = []
    for row in service_state.get('services',[]):
        born = datetime.fromtimestamp(row['birth'],timezone(timedelta(hours=8))).strftime('%m-%d %H:%M:%S') if row.get('birth') else '—'
        code = row.get('exit_code') if row.get('exit_code_known') else '未记录'
        service_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in (
            row.get('lane'),row.get('port'),row.get('pid') or '—',born,
            service_labels.get(row.get('status'),row.get('status','未检查')),
            row.get('error') or '—',code))+'</tr>')
    process = f"进程 {runner.get('pid') or '未记录'}，{'存活' if runner.get('alive') else '未在运行'}，{_plain(runner.get('status'))}"
    total, screened = conversations.get("total"), conversations.get("screened")
    percent = f"（{screened / total:.1%}）" if isinstance(total, (int, float)) and total and isinstance(screened, (int, float)) else ""
    summary = f"初步判断已覆盖 {_number(screened)} / {_number(total)} 条会话 {percent}；尚待初步判断 {_number(conversations.get('remaining'))} 条。"
    summary += f" 已生成候选资源包 {_number(counts.get('generated', counts.get('published')))}，在跑 {_number(counts.get('active'))}，待处理 {_number(counts.get('pending'))}，执行失败 {_number(counts.get('failed'))}，状态不明 {_number(counts.get('unknown'))}。"
    summary += f" 当前保留 {_number(counts.get('published'))}；每项是否包含失败成本、是否还在接续，见下表。未审完不算通过。"
    repair = snapshot.get("selection_repair") or {}
    continuation = snapshot.get('legacy_continuation') or {}
    continuation_note = "初步判断覆盖不代表技能制作与业务任务已完成。旧候选会沿原判断接续，不重新筛选全部会话。"
    if continuation:
        continuation_note += f" 原暂缺条件的会话 {_number(continuation.get('deferred_sources', continuation.get('deferred_count')))} 条单独保留，不充当已生成技能。"
    rows, comparison_rows, md = [], [], ["# 候选技能与资源目录", "", f"数据更新时间：{updated}", "", process, "", summary, "", "只有资源可可靠复用、交付达到底线且实际减负，才应最终保留。未确认的候选照常保留文件和费用。", ""]
    for route in routes:
        name = route.get("name") or route.get("id") or "未命名路线"
        skill = _skill_file(route)
        link = f'<a href="{esc(skill.absolute().as_uri())}">打开 SKILL.md</a><br><small>{esc(skill)}</small>' if skill else "尚无技能目录"
        selection = _selection_progress(route)
        performance = _performance_note(route)
        rows.append(f"<tr><td>{esc(name)}<br><small>{esc(route.get('id', ''))}</small></td><td>{esc(route.get('category', ''))}</td><td>{esc(_plain(route.get('make_status')))}</td><td>{esc(selection)}<br><small>{esc(performance)}</small></td><td>{esc(_number(route.get('task_count')))}</td><td>{link}</td></tr>")
        md.extend([f"## {str(name).replace(chr(10), ' ')}", "", f"制作状态：{_plain(route.get('make_status'))}；真实任务数：{_number(route.get('task_count'))}。", "", f"接续情况：{selection}。", "", f"业务成本：{performance}。", ""])
        if skill:
            md.extend([f"[查看技能](<{skill.as_posix()}>)", ""])
        else:
            md.extend(["尚无技能目录。", ""])
        comparisons = route.get("comparison") or []
        if comparisons:
            md.extend(["| 任务 | 无技能 | 使用技能 |", "|---|---|---|"])
        for comparison in comparisons:
            case_id = str(comparison.get("case_id", "未命名任务"))
            plain, workflow = _arm(comparison.get("no_skill")), _arm(comparison.get("workflow"))
            scope = comparison.get("scope_note") or ""
            comparison_rows.append(f"<tr><td>{esc(name)}</td><td>{esc(case_id)}<br><small>{esc(scope)}</small></td><td>{esc(plain).replace(chr(10), '<br>')}</td><td>{esc(workflow).replace(chr(10), '<br>')}</td></tr>")
            md.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in (case_id, plain, workflow)) + " |")
        md.append("")
    job_rows = []
    for job in jobs:
        job_rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in (
            job.get("route_id") or job.get("id", ""), _plain(job.get("kind")),
            _plain(job.get("status")), job.get("lane") if job.get("lane") is not None else "—",
            job.get("error") or job.get("episode") or "—")) + "</tr>")
    cost_rows = []
    for key, label in (("legacy", "此前记录"), ("new", "本链路新增")):
        cost = (snapshot.get("costs") or {}).get(key) or {}
        cost_rows.append(f"<tr><td>{label}</td><td>{esc(_number(cost.get('known_tokens')))}</td><td>{esc(_number(cost.get('model_calls')))}</td><td>{esc(_number(cost.get('unknown_calls')))}</td></tr>")
    def table(headers, body, empty):
        return "<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>" + ("".join(body) or f'<tr><td colspan="{len(headers)}">{esc(empty)}</td></tr>') + "</tbody></table>"
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="5"><meta name="viewport" content="width=device-width,initial-scale=1"><title>工作流技能生成进度</title><style>body{font:16px/1.65 system-ui,sans-serif;max-width:1450px;margin:30px auto;padding:0 20px;color:#172536;background:#f7f9fb}section{background:white;border:1px solid #dde4eb;border-radius:10px;padding:18px;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #e3e8ee;overflow-wrap:anywhere}th{background:#edf2f7}small,.note{color:#5b6877}h1,h2{line-height:1.3}a{color:#125caa}code{overflow-wrap:anywhere}</style>'
    page += f"<h1>工作流技能生成进度</h1><p>数据更新时间：{esc(updated)}</p><section><strong>{esc(process)}</strong><p>{esc(runner.get('message') or '')}</p><p>{esc(summary)}</p><p>并发上限：{esc(_number(snapshot.get('workers')))}。当前实际在跑数量以任务记录为准。</p></section>"
    page += "<p class=note>当前展示候选资源，不是有效技能库。入库仍须符合原路线：确实替代公共工作、资源可靠、原生试用交付达标并实际减负。取消外部冗余核验不等于取消价值筛选。所有失败和未记全用量保留。</p>"
    page += '<p class=note>' + esc(continuation_note) + '</p>'
    reconciliation = repair.get("retention_reconciliation") or {}
    if reconciliation:
        page += f"<p class=note>原保留记录 {_number(reconciliation.get('original_retained'))} 个；计入本版全部业务尝试（含失败）后，仍有完整减负证据 {_number(reconciliation.get('including_failed_attempts_retained'))} 个。原评审原文与失败费用保留，页面口径更正不改写历史结果。</p>"
    if repair.get("id"):
        progress_counts = repair.get("counts") or {}
        repair_rows = []
        for key, label in (("source_rechecks", "补查遗漏会话判断"), ("task_reselections", "补找独立试用任务"), ("resource_repairs", "沿真实来源局部修复资源")):
            repair_rows.append(f"<tr><td>{label}</td><td>{esc(_campaign_count(repair.get(key)))}</td></tr>")
        progress = "；".join(f"{label} {_number(progress_counts.get(key))}" for key, label in (
            ("pending", "待处理"), ("running", "正在运行"), ("done", "已完成"),
            ("failed", "失败保留"), ("unknown", "状态不明")))
        page += f"<section><h2>本次补漏、补题与局部修复</h2><p>{esc(_plain(repair.get('status')))}；开始时间：{esc(repair.get('started_at') or '尚未记录')}</p><p>{esc(progress)}</p>"
        page += table(["接续工作", "计划数量"], repair_rows, "尚无接续记录")
        page += '<p class=note>复用已有判断、候选和业务结果。缺输入、正在修、已修后暂存分别列示；完成接续不等于已经证明技能减负。原负例、失败与费用继续保留。</p></section>'
    if service_state:
        page += '<section><h2>模型服务是否可用</h2>'
        page += f"<p><strong>{esc(service_state.get('message') or '')}</strong><br>检查时间：{esc(service_state.get('checked_at') or '未记录')}</p>"
        page += table(['通道','端口','进程号','进程启动时间','状态','说明','最近退出码'],service_rows,'正在启动服务')
        page += '<p class=note>服务失联只暂停对应通道的新派发；在途任务先收尾。接口可达不等于业务成功。</p></section>'
    page += "<section><h2>当前任务</h2>" + table(["路线", "正在做什么", "状态", "通道", "结果目录或原因"], job_rows, "当前没有任务记录") + "</section>"
    page += "<section><h2>候选技能和资源目录</h2>" + table(["工作路线", "类别", "制作状态", "现在卡在哪里 / 减负口径", "真实任务数", "候选入口"], rows, "尚无路线记录") + "</section>"
    page += "<section><h2>两组实际开销和交付</h2><p class=note>只计执行器做业务任务：当前完成尝试与本版全部尝试（含失败）分开显示，不能把前者当作全部实际支出。旧版本与不匹配的旧任务留作历史，不冒充新版收益；原本匹配的负例不得删去。制作、准备和评审开销另在累计账中保留。未运行、已知下界和总量未记全分别显示。</p>" + table(["工作路线", "任务", "无技能", "使用技能"], comparison_rows, "还没有两组业务结果") + "</section>"
    page += "<section><h2>模型开销</h2>" + table(["来源", "已知 Token", "已记录模型调用", "用量未记全调用"], cost_rows, "暂无开销记录") + f"<p class=note>此前数字为本次导入的 w9/w10 记录，其他更早原账单仍原样保留，未冒充全项目总额。现金费用没有可靠记录，不换算成零。结果与失败记录保存在 {esc(out / 'records')}。</p></section></html>"
    _atomic(out / "status.json", json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    _atomic(out / "progress.html", page)
    _atomic(out / "技能目录.md", "\n".join(md))
