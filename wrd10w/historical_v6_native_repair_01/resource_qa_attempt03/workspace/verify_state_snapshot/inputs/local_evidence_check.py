"""Finite, local resource QA helper. It is not an Agent or tool dispatcher.

Re-open actual old-case outputs and recompute the local report evidence. Never
imports the candidate program, changes its inputs, or treats PASS as full skill
quality. Intended CLI runs in the frozen Linux image under /workspace.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import openpyxl

FIELDS=['selected_cells','changed_cells','unchanged_text_cells','blank_cells','non_text_cells','formula_cells']

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table_defs(wb):
    return {ws.title:{name:{'ref':ws.tables[name].ref,'style_name':ws.tables[name].tableStyleInfo.name if ws.tables[name].tableStyleInfo else None}
            for name in ws.tables}for ws in wb}

def verify_case(cid,reqp,meta,valid):
    reqp=Path(reqp).resolve();req=load(reqp);root=Path(meta['output_root']).resolve()
    source=(reqp.parent/req['input_workbook']).resolve()
    output=(root/req['output_workbook']).resolve();report=(root/req['report_file']).resolve()
    assert source.is_file(),(cid,'missing_input')
    assert meta['exit_code']==(0 if valid else 2),(cid,'exit_code')
    if not valid:
        assert not output.exists() and not report.exists(),(cid,'invalid_case_wrote_deliverable')
        return {'id':cid,'valid':False,'exit_code':2,'no_workbook_or_report':True}
    assert output.is_file()and report.is_file(),(cid,'missing_deliverable')
    assert output.is_relative_to(root.parent)and report.is_relative_to(root.parent),(cid,'escaped_case_root')
    rep=load(report);a=openpyxl.load_workbook(source,data_only=False);b=openpyxl.load_workbook(output,data_only=False)
    assert a.sheetnames==b.sheetnames,(cid,'sheet_names_or_order')
    selected={};counter={f:0 for f in FIELDS}
    for spec in req['worksheets']:
        ws=a[spec['name']];headers=[c.value for c in ws[spec['header_row']]]
        for name in spec['columns']:
            hits=[i+1 for i,v in enumerate(headers)if v==name];assert len(hits)==1,(cid,'ambiguous_header')
            for n in range(spec['data_start_row'],spec['data_end_row']+1):
                cell=ws.cell(n,hits[0]);key=(ws.title,cell.coordinate);assert key not in selected,(cid,'overlapping_target')
                value=cell.value;want=value;counter['selected_cells']+=1
                if cell.data_type=='f':counter['formula_cells']+=1
                elif value is None or value=='':counter['blank_cells']+=1
                elif not isinstance(value,str):counter['non_text_cells']+=1
                else:
                    m=req['masking'];left,right=m['prefix_chars'],m['suffix_chars']
                    if len(value)>left+right:want=value[:left]+m['replacement']+(value[-right:]if right else'')
                    counter['changed_cells'if want!=value else'unchanged_text_cells']+=1
                selected[key]=want
    type_count=0;type_mismatches=0
    for ws in a:
        other=b[ws.title];assert (ws.max_row,ws.max_column)==(other.max_row,other.max_column),(cid,'dimensions')
        for row in ws:
            for cell in row:
                got=other[cell.coordinate];key=(ws.title,cell.coordinate);want=selected.get(key,cell.value)
                assert got.value==want or(want==''and got.value is None),(cid,'cell_value',ws.title,cell.coordinate)
                type_count+=1;type_mismatches+=cell.data_type!=got.data_type
    assert type_mismatches==0,(cid,'storage_type_changed')
    ta,tb=table_defs(a),table_defs(b);assert ta==tb,(cid,'table_name_ref_or_style_name_changed')
    assert rep['schema_version']=='data_field_mask_report_v1'and rep['masking']==req['masking'],(cid,'report_contract')
    assert rep['input_sha256']==sha(source)and rep['output_sha256']==sha(output),(cid,'report_hash')
    assert rep['totals']==counter,(cid,'independently_recounted_totals')
    assert sum(counter[k]for k in FIELDS[1:])==counter['selected_cells'],(cid,'totals_identity')
    # Bind the exact evidence object to its check name, never mix fields from
    # another failure/check object to satisfy one assertion.
    checks={c['name']:c for c in rep['checks']};assert len(checks)==len(rep['checks']),(cid,'duplicate_check_name')
    c5=checks['types_and_tables_preserved'];c6=checks['counting_identity']
    assert c5['status']=='PASS'and c6['status']=='PASS',(cid,'local_check_status')
    e5,e6=c5['evidence'],c6['evidence'];assert isinstance(e5,dict)and isinstance(e6,dict),(cid,'evidence_not_structured')
    assert Path(e5['input_workbook']).resolve()==source and Path(e5['output_workbook']).resolve()==output,(cid,'check5_paths')
    assert e5['input_sha256']==sha(source)and e5['output_sha256']==sha(output),(cid,'check5_hashes')
    assert e5['cells_compared']==type_count and e5['type_mismatch_cells']==type_mismatches,(cid,'check5_cell_counts')
    assert e5['table_definition_count']==sum(len(x)for x in ta.values())and e5['table_definitions_identical']is True,(cid,'check5_tables')
    assert e6['totals']==counter and e6['sum_of_components']==sum(counter[k]for k in FIELDS[1:]),(cid,'check6_components')
    assert e6['selected_cells']==counter['selected_cells']and e6['identity_holds']is True,(cid,'check6_selected_identity')
    a.close();b.close()
    return {'id':cid,'valid':True,'exit_code':0,'report':str(report),'report_sha256':sha(report),
        'output_sha256':sha(output),'selected_cells':counter['selected_cells'],'recomputed_local_evidence':True,
        'claim_scope':'FINITE_CELL_VALUES_COUNTS_TYPES_TABLE_REF_AND_STYLE_NAME_NOT_VISUAL_OR_COST_BENEFIT'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',required=True);ap.add_argument('--baseline',required=True)
    ap.add_argument('--meta-root',required=True);ap.add_argument('--report',required=True);args=ap.parse_args()
    cases=[('original_recovery',args.baseline,True)]+[(c['id'],c['request'],c['valid_input'])for c in load(args.cases)]
    results=[];failures=[];paths=set()
    for cid,req,valid in cases:
        try:
            meta=load(Path(args.meta_root)/cid/'run_meta.json');obj=verify_case(cid,req,meta,valid)
            if valid:
                rep=Path(obj['report']).resolve();assert rep not in paths,(cid,'two_cases_share_report');paths.add(rep)
            results.append(obj)
        except Exception as exc:failures.append({'case_id':cid,'error_type':type(exc).__name__,'error':str(exc)})
    report={'status':'PASS'if not failures else'FAIL','valid_cases':sum(v for _,_,v in cases),'invalid_cases':sum(not v for _,_,v in cases),
        'case_results':results,'failures':failures,'full_visual_quality_or_skill_retention_proven':False}
    dest=Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'valid_cases':report['valid_cases'],'invalid_cases':report['invalid_cases'],'failure_count':len(failures)},ensure_ascii=False))
    return bool(failures)
if __name__=='__main__':raise SystemExit(main())
