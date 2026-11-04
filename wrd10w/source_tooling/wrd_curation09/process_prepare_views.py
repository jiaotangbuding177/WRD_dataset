"""Prepare explicitly authored functional views, not historical prompt equivalents.

The four complete code resources and one real local edit remain candidates until
independent resource QA and root admission. Unknown business literals are exact
zero-loss exclusions. No source programs or model weights are executed here.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import ast,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261031_wrd_curation09/process'
DATA=ROOT/'output/20261027_wrd_main_v10'
RESERVATION=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
CAP=DATA/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(t):return hashlib.sha256(t.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def gzsave(p,data):
 with p.open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for r in data:f.write((js(r)+'\n').encode())
def blocks(m):
 c=m.get('content',[]);return [{'type':'text','text':c}]if isinstance(c,str)else c
def text(m):return '\n'.join(x.get('text','')for x in blocks(m)if isinstance(x,dict)and x.get('type')=='text')
def offset(code,node):
 lines=code.splitlines(keepends=True)
 start=sum(len(x)for x in lines[:node.lineno-1])+len(lines[node.lineno-1].encode()[:node.col_offset].decode())
 end=sum(len(x)for x in lines[:node.end_lineno-1])+len(lines[node.end_lineno-1].encode()[:node.end_col_offset].decode())
 return start,end
def exclusion(code,node,reason):
 start,end=offset(code,node);return {'start':start,'end':end,'text':code[start:end],'text_sha256':hs(code[start:end]),'reason':reason}
def merge(ranges,code):
 out=[]
 for r in sorted(ranges,key=lambda r:(r['start'],r['end'])):
  if out and r['start']<=out[-1]['end']:
   q=out[-1];q['end']=max(q['end'],r['end']);q['text']=code[q['start']:q['end']];q['text_sha256']=hs(q['text']);q['reason']+='; '+r['reason']
  else:out.append(dict(r))
 return out
def cjk(v):return bool(re.search('[\u3400-\u9fff]',v))

def main():
 assert not (OUT/'FUNCTIONAL_CANDIDATES05.jsonl.gz').exists(),'preserve prior candidates'
 reservation=load(RESERVATION);held_sources=set(reservation['reserved_source_ids']);held_groups=set(reservation['reserved_source_scope_components'])
 scopes={s['source_id']:s for s in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 tools=[t for t in load(CAP)['tools']if t['function']['name']in{'apply_patch','edit','exec','ls','process','read','write'}];assert len(tools)==7
 cases=[
 ('0f1603b601613eac2fecb014','B_complete_inline_html_slide_renderer','/workspace/tmp/gen_slides.py','先实现可在本地重复运行的36页HTML排版和截图子资源，使用真实来源中的固定画面文字；本步不调用外部生图或vision服务。最终整套生图构图与PDF交付仍需另外验收。'),
 ('b1be5b288ae637de175154a5','B_complete_inline_org_chart_renderer','/workspace/tmp/org_chart.py','先实现组织架构图的本地图形绘制子资源，用于后续Word嵌入。岗位配置是待核的设计提案；本步只负责绘图代码，不宣称治理、医疗器械或财务职责安排已获业务批准。'),
 ('43280ee97c7e5a3da3c9053c','B_complete_inline_xlsx_export_resource','/workspace/tmp/build_plan.py','先制作可重开的Excel排版和导出子资源。客户提供的事项、时间和费用保留；法律、税务、监管、开户及汇率结论均属未校准内容，不能仅据生成成功宣称正确，本步只授导出实现信用。'),
 ('45444e97188d392abd301d94','B_complete_inline_docx_export_resource','/workspace/tmp_make_contract.py','先制作Word合同排版和导出的本地子资源。兼职关系类型及条款合法性仍须另核，本步不将草稿法律正文当作已验证规范；只实现文档机制。'),
 ]
 candidates=[];reviews=[];ranges_by_owner={}
 def base(owner,packet,stage):
  row=packet['owner'];sources=row['source_ids'];assert sources and not set(sources)&held_sources
  assert all(scopes[s]['status']=='TRAIN'and scopes[s]['component_id']not in held_groups for s in sources)
  return {'schema_version':'wrd09-explicit-functional-process-view-v1','id':'process09-'+owner,'owner_id':owner,
   'bank':'process09_inline_resource_and_real_edit','stage':stage,'split':'train','source_ids':sources,
   'source_group_id':'process09_'+hs('|'.join(sorted(sources)))[:20],'source_admission':'ADMIT','training_admitted':True,
   'root_main_admission':False,'requires_external_root_admission':True,'original226':False,'holdout12':False,
   'protected_sources_visible_prefix':False,'protected_source_ids':[],
   'annotation_provenance':'NEW_FUNCTIONAL_SUBTASK_DELEGATION_WITH_RECORDED_CODE_OR_ACTION_NOT_ORIGINAL_PROMPT_EQUIVALENCE',
   'original_episode_id':row['episode_id'],'original_message_index':row['source_message_index'],
   'source_context':{'path':str((OUT/'packets'/f'{owner}.json').resolve()),'bytes':(OUT/'packets'/f'{owner}.json').stat().st_size,'sha256':sha(OUT/'packets'/f'{owner}.json')},
   'original_system_capture':packet['original_context']['system_capture_status'],'original_native_prompt_equivalence_claimed':False,
   'student_view':'EXPLICIT_CORE7_STATE_SUBTASK_DELEGATION','actual_native_tool_dispatch':False,
   'original_recorded_action_owner':owner,'loss_multiplier':0.25,'tools':tools,
   'tool_schema_provenance':{'path':str(CAP.resolve()),'sha256':sha(CAP)},
   'is_full_autonomous_execution_demonstration':False,'is_qualified_KEEP_demonstration':False,
   'credit':'Bounded local resource mechanism or exact text-label repair; no whole skill utility, business correctness, legal validity or visual-gold claim',
   'data_design_revision':'5.0.50','data_change_id':'ALG-20261031-02','curation_cost':'UNKNOWN_NOT_ZERO',
   'new_business_Teacher_Actor_calls':0,'training_started':False,
   'holdout_reservation_sha256':sha(RESERVATION),'teacher_original_R_supervised':False,'rationale_provenance':'NO_ORIGINAL_R_SUPERVISED_IN_THIS_VIEW'}
 def finish(r,prompt,call):
  r.update(messages=[{'role':'system','content':'依据当前明确子任务、真实来源和可见文件使用工具。保留未知和失败；没有证据时不宣称业务正确。'},
   {'role':'user','content':prompt},{'role':'assistant','content':'','reasoning_content':'','tool_calls':[call]}],
   supervision_message_indices=[2],message_loss_mask=[0,0,1],approved_components=['A'],target_tool_call_id=call['id'])
  candidates.append(r)
 for owner,stage,path,delegation in cases:
  packet=load(OUT/'packets'/f'{owner}.json');row=packet['owner'];c=packet['original_context'];idx=row['source_message_index']
  program=row['literal_inline_programs'][0];code=Path(program['path']).read_text(encoding='utf-8');assert hs(code)==program['text_sha256']
  tree=ast.parse(code);ex=[]
  if owner=='45444e97188d392abd301d94':
   allowed={'宋体','黑体','楷体','兼职人员聘用合同','（媒体、广告行业适用）'}
   for node in ast.walk(tree):
    if isinstance(node,ast.Constant)and isinstance(node.value,str)and cjk(node.value)and node.value not in allowed and not node.value.startswith('/workspace/'):
     ex.append(exclusion(code,node,'UNVERIFIED_LEGAL_BODY_RELATION_TYPE_OR_CLAUSE; preserve raw content but no positive business/legal loss'))
  elif owner=='43280ee97c7e5a3da3c9053c':
   notes=next(n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='notes'for t in n.targets))
   # The entire original advice/currency-estimate data block is left visible but untrained.
   ex.append(exclusion(code,notes.value,'UNVERIFIED_REGULATORY_TAX_DIRECTOR_AND_CURRENCY_NARRATIVE; no legal/financial content credit'))
   for node in ast.walk(tree):
    if isinstance(node,ast.Constant)and isinstance(node.value,str)and any(x in node.value for x in ['约1周','文件公证/核证费用','一般免开户费','股东亦可按银行要求陪同','面签当天完成','每年缴纳公司年费，续期注册代理']):
     ex.append(exclusion(code,node,'UNVERIFIED_ADDED_TIMING_FEE_OR_PROCEDURE_NOT_SOURCE_FACT'))
   height=next(n for n in ast.walk(tree)if isinstance(n,ast.Assign)and 'ws.row_dimensions[row].height = max(30, nlines * 15 + 20)'in(ast.get_source_segment(code,n)or''))
   ex.append(exclusion(code,height,'ROW_HEIGHT_FROM_NEWLINES_ONLY_DOES_NOT_VERIFY_WRAPPED_LONG_TEXT_VISIBILITY'))
  elif owner=='b1be5b288ae637de175154a5':
   fonts={'宋体','黑体','楷体'}
   for node in ast.walk(tree):
    if isinstance(node,ast.Constant)and isinstance(node.value,str)and cjk(node.value)and node.value not in fonts and not node.value.startswith('/workspace/'):
     ex.append(exclusion(code,node,'UNVALIDATED_ORGANIZATION_PROPOSAL_LABELS_NOT_ASSERTED_BUSINESS_OR_REGULATORY_OPTIMUM'))
  else:
   page19=next(n for n in tree.body if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='P'and isinstance(n.value.args[0],ast.Constant)and n.value.args[0].value==19)
   ex.append(exclusion(code,page19.value.args[1],'MATRIX_REGION_SEMANTIC_ASSIGNMENT_NOT_SEPARATELY_VALIDATED'))
  ex=merge(ex,code);ranges_by_owner[owner]=ex
  original_task=text(c['messages'][0]).split('用户任务：')[-1].strip()
  delivered=[]
  for mi,m in enumerate(c['messages'][:idx]):
   if m.get('role')=='toolResult'and m.get('toolName')=='read'and len(text(m))>150:
    delivered.append({'original_message_index':mi,'text':text(m)})
  # XLSX source-only read was recorded through exec; include exact source/user metadata output.
  if owner=='43280ee97c7e5a3da3c9053c':delivered.append({'original_message_index':2,'text':text(c['messages'][2])})
  resource_text='\n\n'.join(f'来源材料（原消息{x["original_message_index"]}，逐字）：\n{x["text"]}'for x in delivered)
  prompt=('当前工作目录为 /workspace，Python及已安装的本地文档/绘图/Chromium工具可用。当前子资源文件为 '+path+'。\n'+delegation+
   '\n\n原始需求（只用于保留事实与约束，本步不声称已完成整项交付）：\n'+original_task+'\n\n'+resource_text+
   '\n\n请将本步完整程序写入上述路径；不执行外部业务操作、不新增交付格式。外部服务与剩余预算未知。')
  r=base(owner,packet,stage);r['target_code_unicode_exclusions']=ex;r['target_original_code_sha256']=hs(code)
  r['output_content_provenance']='VERBATIM_CODE_EXTRACTED_FROM_RECORDED_EXEC_HEREDOC; new write projection, old exec args/feedback in audit'
  r['source_material_messages_provided_in_new_state']=[{'message_index':x['original_message_index'],'text_sha256':hs(x['text'])}for x in delivered]
  call={'id':'process09-write-'+owner,'type':'function','function':{'name':'write','arguments':{'path':path,'content':code}}}
  finish(r,prompt,call)
  reviews.append({'owner_id':owner,'semantic_review':'COMPLETE_CODE_READ; scoped mechanism candidate only','excluded_unicode_ranges':len(ex),'excluded_characters':sum(x['end']-x['start']for x in ex),
   'original_feedback_preserved':row['immediate_original_tool_feedback'],'required_root_QA':'Run exact resource in fixed CPU container, reopen/render output and test stated local contract; no model/agent call or whole business-gold inference'})
 # Exactly recorded five-label repair. Source before is recovered from prior write, not later filesystem.
 owner='890556c82086d7fd1b896de3';packet=load(OUT/'packets'/f'{owner}.json');r=base(owner,packet,'B_real_local_html_label_repair')
 target=packet['owner']['target_message_original'];call0=next(b for b in blocks(target)if b.get('type')=='toolCall');args=deepcopy(call0['arguments']);path=args['path']
 before=None
 for m in packet['state_before_target']:
  for b in blocks(m):
   if b.get('type')=='toolCall'and b.get('name')=='write'and b.get('arguments',{}).get('path')==path:before=b['arguments']['content']
 assert before is not None;after=before
 for edit in args['edits']:
  assert after.count(edit['oldText'])==1;after=after.replace(edit['oldText'],edit['newText'])
 assert before.count(' b<b id=')==5 and after.count(' b<b id=')==0
 repair=OUT/'real_edit'/owner;repair.mkdir(parents=True,exist_ok=True);(repair/'before.html').write_bytes(before.encode());(repair/'after.html').write_bytes(after.encode())
 r['exact_repair_versions']={'before_sha256':hs(before),'after_sha256':hs(after),'five_label_typo_only':True,'whole_physics_or_visual_quality_not_approved':True}
 r['output_content_provenance']='RECORDED_NATIVE_EDIT_ARGUMENTS_VERBATIM; explicit new state, not original prompt equivalence'
 prompt='当前文件 '+path+' 的完整内容如下。仅移除五个stat读数标签中误入普通文本的字母b，保留<b>标签和其它程序。物理模型与整体视觉正确性尚未验收，本步不改变它们。请用精确编辑完成该排版纠错。\n\n```html\n'+before+'\n```'
 call={'id':call0['id'],'type':'function','function':{'name':'edit','arguments':args}}
 finish(r,prompt,call);reviews.append({'owner_id':owner,'semantic_review':'VERBATIM_EXACT_FIVE_LABEL_TYPO_REPAIR; not physics or final visual gold','exact_before_sha256':hs(before),'exact_after_sha256':hs(after),'required_root_QA':'Independent before/after exact edit diff and DOM text check'})
 gzsave(OUT/'FUNCTIONAL_CANDIDATES05.jsonl.gz',candidates)
 save(OUT/'FUNCTIONAL_CODE_EXCLUSIONS.json',{'schema':'wrd09-unicode-code-literal-exclusions','ranges_by_owner':ranges_by_owner,'new_R_tokens':0})
 save(OUT/'SEMANTIC_REVIEW05.json',{'status':'SCOPED_FUNCTIONAL_CANDIDATES_PENDING_ROOT_RESOURCE_QA_AND_COMPILATION','records':reviews,'targets':len(candidates),'not_full_autonomous_or_qualified_KEEP':True,'training_started':False,'new_business_calls':0,'reservation_sha256':sha(RESERVATION),'script_sha256':sha(__file__)})
 print(json.dumps({'functional_candidates':len(candidates),'new_original_R':0,'new_authored_R':0,'code_exclusion_ranges':sum(len(x)for x in ranges_by_owner.values()),'business_model_calls':0,'training_started':False}))
if __name__=='__main__':main()
