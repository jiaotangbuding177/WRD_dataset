import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
ler = fb['previous_validation'].get('learning_evidence_review')
open('work_ler.json','w',encoding='utf-8').write(json.dumps(ler, ensure_ascii=False, indent=1))
diags = fb['development_case_diagnostics']
lines=[]
for d in diags:
    lines.append(f"=== {d['id']} passed={d.get('passed')} exit={d.get('exit_code')}")
    for c in d.get('failed_or_unknown_checks', []):
        lines.append(f" check {c['id']} pass={c.get('pass')} status={c.get('status')} crit={c.get('critical')}")
        ev=c.get('evidence')
        if ev: lines.append(' ev='+json.dumps(ev,ensure_ascii=False))
    if d.get('stderr'): lines.append(' stderr='+d['stderr'][:400])
open('work_diags.txt','w',encoding='utf-8').write('\n'.join(lines))
print('written')
print(open('work_diags.txt',encoding='utf-8').read()[:3000])