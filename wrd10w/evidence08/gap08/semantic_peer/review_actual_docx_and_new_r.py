"""Independent read-only inspection of actual artifacts and5 authored R inputs.

No program, Agent, model or training is run here. Root's execution result is
checked against actual DOCX XML and exact original/revised source identities.
"""
from pathlib import Path
from collections import Counter
import ast,gzip,hashlib,json,zipfile,sys,xml.etree.ElementTree as ET

ROOT=Path('D:/skillloop');OUT=Path(__file__).resolve().parent;WORK=ROOT/'output/20261030_wrd_gap08/semantic_root/docx_source_corrections/workspace';BANK=ROOT/('output/20261030_wrd_gap08/process_bank03/candidate17.jsonl.gz' if '--bank03' in sys.argv else 'output/20261030_wrd_gap08/process_bank02/candidate17.jsonl.gz')
def H(b):return hashlib.sha256(b).hexdigest()
def C(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def P(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def J(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def Z(p):return [json.loads(x) for x in gzip.open(p,'rt',encoding='utf-8-sig')]
def save(n,x):p=OUT/n;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return P(p)
def docx_text(p):
 with zipfile.ZipFile(p) as z:xml=ET.fromstring(z.read('word/document.xml'))
 return ''.join(n.text or '' for n in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
def arg(t):
 a=t['function']['arguments'];return json.loads(a) if isinstance(a,str) else a
def fieldspan(s,needle):
 i=s.find(needle);assert i>=0,needle;return {'start':i,'end':i+len(needle),'text_SHA256':H(needle.encode())}

def main():
 proposals=J(OUT/'SOURCE_GROUNDED_CORRECTION_PROPOSALS.json');root_result=J(WORK/'RESULT.json');got={x['owner']:x for x in root_result['results']};results=[]
 for e in proposals['programs']:
  owner=e['original_owner_id'];r=got[owner];program=WORK/'programs'/(owner+'.py');assert P(program)['sha256']==e['proposed_program']['sha256'];raw=Path(e['original_program']['path']).read_bytes().decode('utf8');current=program.read_bytes().decode('utf8')
  for c in e['changes']:assert raw.count(c['oldText'])==1;raw=raw.replace(c['oldText'],c['newText'],1)
  assert raw==current;ast.parse(current)
  dp=WORK/r['docx'].removeprefix('/workspace/');pdf=WORK/r['pdf'].removeprefix('/workspace/');assert P(dp)['sha256']==r['docx_SHA256'] and pdf.read_bytes().startswith(b'%PDF-');dt=docx_text(dp);checks=[]
  for c in e['changes']:
   new=c['newText'];old=c['oldText'];problem=c['original_finding']['literal_problem_excerpt']
   if '\n' in new:
    a=ast.parse(new);parts=[n.value for n in ast.walk(a) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
   else:parts=[new]
   assert parts and all(x in dt for x in parts);assert problem not in dt
   checks.append({'source_finding':c['original_finding']['reason'],'original_source_evidence':c['original_finding']['original_source_evidence'],'newText_SHA':H(new.encode()),'required_new_XML_text_parts':parts,'all_new_parts_present_in_actual_docx_XML':True,'unsupported_original_phrase_absent':True,'specific_source_literal_or_explicit_unknown_credit_only':True})
  results.append({'owner':owner,'actual_program':P(program),'program_exact_proposal_and_only_declared_changes':True,'actual_docx':P(dp),'actual_docx_XML_text_SHA':H(dt.encode()),'actual_pdf':P(pdf),'PDF_pages_root_receipt_only':r['pages'],'changes_independently_rechecked_in_XML':checks,'source_external_business_truth':'NOT_TESTED_OR_CLAIMED','hiring_rankings_and_thresholds':'Retained historical/proposed judgments; these corrections do not validate their empirical correctness.','legal_effect':'Literal original authorization/liability wording restored; enforceability/validity not assessed.','full_visual_quality_Q':'NOT_ASSESSED; root viewed four first pages only, not all-page independent visual Q.'})
 docxqa={'schema':'wrd-gap08-actual-docx-source-corrections-independent-QA-v1','status':'PASS_4_ACTUAL_DOCX_XML_AND_13_SOURCE_GROUNDED_CORRECTIONS_SCOPED_ONLY','independent_from_runtime_runner':True,'correction_proposal_author_is_same_reviewer':True,'runtime_already_done_by_root_not_repeated':True,'actual_programs':4,'actual_generated_docx':4,'source_corrections':sum(len(x['changes_independently_rechecked_in_XML']) for x in results),'inputs':[P(WORK/'RESULT.json'),P(OUT/'SOURCE_GROUNDED_CORRECTION_PROPOSALS.json')],'results':results,'new_native_tool_dispatch':False,'new_business_Teacher_Actor_calls':0,'AI_curation_cost':'UNKNOWN_NOT_ZERO','training':False}
 dqp=save('ACTUAL_CORRECTED_DOCX_INDEPENDENT_QA.json',docxqa)
 rows=Z(BANK);selected=[r for r in rows if r['messages'][-1].get('reasoning_content')];assert len(rows)==17 and len(selected)==5
 proposal_by={e['original_owner_id']:e for e in proposals['programs']};reviews=[];findings=[]
 for r in selected:
  ms=r['messages'];i=len(ms)-1;t=ms[-1];reason=t['reasoning_content'];call=t['tool_calls'][0];a=arg(call);path=a['path'];prefix=json.dumps(ms[:-1],ensure_ascii=False);path_locs=[]
  for j,m in enumerate(ms[:-1]):
   s=m.get('content','') or ''
   if isinstance(s,str) and path in s:path_locs.append({'message_index':j,'field':'content',**fieldspan(s,path)})
   for k,c in enumerate(m.get('tool_calls',[])):
    if arg(c).get('path')==path:path_locs.append({'message_index':j,'field':'tool_calls/'+str(k)+'/function/arguments/path','exact_value':path})
  assert r['actual_native_tool_dispatch'] is False and r['teacher_original_R_supervised'] is False and r['rationale_provenance']=='NEW_AUTHORED_SCOPED_RATIONALE' and r['approved_components']==['R','A'];assert r['supervision_message_indices']==[i] and r['message_loss_mask']==[0]*i+[1]
  # Root receipts reside in metadata, never in input messages.
  assert 'PASS_FOUR_CORRECTED_PROGRAMS' not in prefix and 'actual_resource_QA' not in prefix and 'qualified_skill' not in prefix
  if r['id'].startswith('gap08-new-source-correction-'):
   original=r['original_writer_owner'];e=proposal_by[original];program=Path(e['original_program']['path']).read_bytes().decode('utf8');priorwrites=[]
   for j,m in enumerate(ms[:-1]):
    for c in m.get('tool_calls',[]):
     ca=arg(c)
     if c['function']['name']=='write' and ca.get('path')==path and ca.get('content')==program:priorwrites.append(j)
   assert len(priorwrites)==1 and path_locs;assert len(a['edits'])==len(e['changes'])
   for x,y in zip(a['edits'],e['changes']):assert x['oldText']==y['oldText'] and x['newText']==y['newText'] and program.count(x['oldText'])==1
   anchors={'befe257a688eb74361966e52':['不改变岗位事实内容','解决产品开发过程中的技术难题','编写技术文档'], '50a3b236baa2f7324e247fba':['未发生一起医疗安全投诉','期望薪资可根据岗位职责与面试情况合理确定','目前还没明确进入终面'], 'c9753a249f6f08a9c7726efa':['线上面试','目前还没明确进入终面'], 'f78b5c3163c5516f9b7db22a':['除下载数据备份外','包括人身伤害或生产损失','已编译的证据原子','支持三种调度类型','不得臆造或补写缺失内容']}[original]
   located=[]
   for needle in anchors:
    hits=[{'message_index':j,'field':'content',**fieldspan(m['content'],needle)} for j,m in enumerate(ms[:-1]) if isinstance(m.get('content'),str) and needle in m['content']];assert hits,needle;located.append({'anchor':needle,'actual_prefix_locations':hits})
   rationale_assessment='Grounded in actual prefix original source facts/corrections and visible erroneous current code; proposes precise source-restoring edits, no statement that future rerun succeeds.'
   extra={'source_fact_anchors':located,'visible_current_full_original_program_write_index':priorwrites[0],'exact_declared_edit_count':len(a['edits']),'whole_program_one_tool_edit_target':True,'new_CORRECTED_program_or_after_run_results_in_input':False}
  else:
   up=ms[1]['content'];before=J(r['actual_resource_QA']['path']);bp=Path(r['necessary_before_resource']['path']);rawcode=bp.read_bytes().decode('utf8');code=rawcode.replace('\r\n','\n');assert code in up and before['before_actual_size']==[2000,500];assert '2000×500' in up and '520' in up
   new=code
   for x in a['edits']:assert new.count(x['oldText'])==1;new=new.replace(x['oldText'],x['newText'],1)
   actual_new=Path(before['actual_new_resource']['path']);assert P(actual_new)['sha256']==before['actual_new_resource']['sha256'] and new==actual_new.read_text(encoding='utf8');rationale_assessment='Reasoning describes fixed500 viewport vs clip520 and requests PNG-size verification after edit; based on pre-fix measured dimensions, without claiming post-fix success.'
   extra={'necessary_before_code':P(bp),'before_size_receipt':P(r['actual_resource_QA']['path']),'before_size_2000x500_in_input':True,'current_input_code_equals_before_after_explicit_CRLF_to_LF':True,'before_input_LF_text_SHA':H(code.encode()),'before_physical_CRLF_bytes_not_claimed_identical_to_visible_LF_text':True,'target_edit_produces_actually_retested_new_resource_after_CRLF_to_LF':True,'actual_new_resource':P(actual_new),'after_repair_PNG_size_or_PASS_in_input':False}
   if not path_locs:findings.append({'id':r['id'],'severity':'REQUIRES_INPUT_CORRECTION_AND_RECOMPILE','message_index':1,'field':'content','missing_information':'Exact existing file path is absent from whole input while target directly edits it. OUT directory does not identify render_overlays.py.','required_prefix_addition':'文件：/workspace/tmp/archery/render_overlays.py（当前完整内容如下）。\n','target_path':path,'reasoning_itself_can_be_retained':True,'old_raw_bank':P(BANK)})
  reviews.append({'id':r['id'],'source_ids':r['source_ids'],'target_message_index':i,'R_SHA':H(reason.encode()),'R_characters':len(reason),'R_original_teacher_credit':0,'R_new_authored_credit':True,'reasoning_assessment':rationale_assessment,'tool_path_observable':bool(path_locs),'visible_path_locations':path_locs,'native_dispatch_or_original_autonomous_demonstration':False,'future_resource_QA_metadata_not_serialized_to_model_messages':True,**extra})
 result={'schema':'wrd-gap08-new-R-input-causality-QA-v1','status':'REQUIRES_VIEWPORT_FILENAME_INPUT_AND_RECOMPILE' if findings else 'PASS_5_NEW_AUTHORED_R_INPUT_CAUSALITY_SCOPED','raw_bank':P(BANK),'rows17':17,'new_authored_R_targets':5,'new_R_characters':sum(x['R_characters'] for x in reviews),'original_R_targets':0,'reviews':reviews,'findings':findings,'no_different_execution_or_quality_credit_from_metadata':True,'new_business_Teacher_Actor_calls':0,'AI_curation_cost':'UNKNOWN_NOT_ZERO','training':False,'script':P(__file__)}
 nqp=save('NEW_R_INPUT_CAUSALITY_QA02.json' if '--bank03' in sys.argv else 'NEW_R_INPUT_CAUSALITY_QA01.json',result);print(json.dumps({'docx_QA':dqp,'newR_QA':nqp,'newR_status':result['status'],'findings':len(findings)}))

if __name__=='__main__':main()
