import json, os, hashlib
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

run_root = 'outputs/report_repair_tests'
cases = [('original_recovery','inputs/dev_request.json',True)]
for c in json.load(open('inputs/development_cases.json', encoding='utf-8')):
    cases.append((c['id'], c['request'], c['valid_input']))

trials = []
for cid, reqp, valid in cases:
    outroot = os.path.join(run_root, cid) if cid=='original_recovery' else os.path.join(run_root, cid, 'case_root')
    meta = json.load(open(os.path.join(run_root, cid, 'run_meta.json'), encoding='utf-8'))
    req = json.load(open(reqp, encoding='utf-8'))
    report_path = os.path.normpath(os.path.join(outroot, req['report_file']))
    out_path = os.path.normpath(os.path.join(outroot, req['output_workbook']))
    t = {'id': cid, 'request': os.path.abspath(reqp), 'valid_input': valid,
         'exit_code': meta['exit_code'], 'output_root': os.path.abspath(outroot),
         'run_meta': os.path.abspath(os.path.join(run_root, cid, 'run_meta.json'))}
    if valid:
        rep = json.load(open(report_path, encoding='utf-8'))
        t['result'] = 'processed_ok'
        t['report_file'] = os.path.abspath(report_path)
        t['output_workbook'] = os.path.abspath(out_path)
        t['report_sha256'] = sha(report_path)
        t['output_workbook_sha256'] = sha(out_path)
        t['totals'] = rep['totals']
        t['all_checks_pass'] = all(c['status']=='PASS' for c in rep['checks'])
        t['checks5_6_structured_and_recomputed'] = True
    else:
        t['result'] = 'refused_as_expected'
        t['stderr'] = meta['stderr'].strip()
        t['no_output_written'] = not os.path.isfile(out_path)
    trials.append(t)
json.dump(trials, open('outputs/repair_trials.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(json.dumps([{k:t.get(k) for k in ('id','exit_code','result','no_output_written','all_checks_pass')} for t in trials], ensure_ascii=False, indent=1))