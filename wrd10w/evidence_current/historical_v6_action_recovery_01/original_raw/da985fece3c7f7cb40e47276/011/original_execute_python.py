import json, os, hashlib, openpyxl

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

cases = [('original_recovery','inputs/dev_request.json')]
for c in json.load(open('inputs/development_cases.json', encoding='utf-8')):
    if c['valid_input']: cases.append((c['id'], c['request']))

summary = []
for cid, reqp in cases:
    outroot = os.path.abspath(f'outputs/report_repair_tests/{cid}')
    req = json.load(open(reqp, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(reqp))
    in_path = os.path.normpath(os.path.join(base, req['input_workbook']))
    report_path = os.path.normpath(os.path.join(outroot, req['report_file']))
    out_path = os.path.normpath(os.path.join(outroot, req['output_workbook']))
    rep = json.load(open(report_path, encoding='utf-8'))
    ok = {}
    ok['schema_version'] = rep['schema_version'] == 'data_field_mask_report_v1'
    ok['input_sha'] = rep['input_sha256'] == sha(in_path)
    ok['output_sha'] = rep['output_sha256'] == sha(out_path)
    ok['masking'] = rep['masking'] == req['masking']
    t = rep['totals']
    ok['totals_identity'] = t['changed_cells']+t['unchanged_text_cells']+t['blank_cells']+t['non_text_cells']+t['formula_cells'] == t['selected_cells']
    ok['all_checks_pass'] = all(c['status']=='PASS' for c in rep['checks'])
    ok['n_checks'] = len(rep['checks'])
    c5, c6 = rep['checks'][5], rep['checks'][6]
    assert c5['name']=='types_and_tables_preserved' and c6['name']=='counting_identity'
    wb_in = openpyxl.load_workbook(in_path, data_only=False)
    wb_out = openpyxl.load_workbook(out_path, data_only=False)
    tc, tm, tdi = 0, 0, {}
    for title in wb_in.sheetnames:
        wi, wo = wb_in[title], wb_out[title]
        for row in wi.iter_rows():
            for cell in row:
                tc += 1
                if cell.data_type != wo[cell.coordinate].data_type: tm += 1
        tdi[title] = {tn: (wi.tables[tn].ref) for tn in wi.tables}
    tdo = {title: {tn: (wb_out[title].tables[tn].ref) for tn in wb_out[title].tables} for title in wb_in.sheetnames}
    e5 = c5['evidence']
    ok['check5_recompute'] = (isinstance(e5, dict) and e5['cells_compared']==tc and e5['type_mismatch_cells']==tm
        and e5['table_definition_count']==sum(len(v) for v in tdi.values())
        and e5['table_definitions_identical']==(tdi==tdo)
        and e5['input_sha256']==rep['input_sha256'] and e5['output_sha256']==rep['output_sha256']
        and os.path.normpath(e5['output_workbook'])==out_path and os.path.normpath(e5['input_workbook'])==in_path)
    e6 = c6['evidence']
    ok['check6_recompute'] = (isinstance(e6, dict) and e6['totals']==t
        and e6['sum_of_components']==e6['selected_cells'] and e6['identity_holds'] is True
        and e6['sum_of_components']==t['selected_cells'])
    ok['input_unchanged_check'] = rep['checks'][3]['name']=='input_unchanged' and rep['checks'][3]['status']=='PASS'
    summary.append({'id': cid, **ok})
    print(cid, 'ALL_OK' if all(ok.values()) else f'FAIL:{[k for k,v in ok.items() if not v]}', 'selected=', t['selected_cells'])
json.dump(summary, open('work/verification_pass.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)