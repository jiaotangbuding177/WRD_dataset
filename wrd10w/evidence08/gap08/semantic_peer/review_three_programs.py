"""Read-only independent semantic review of original writers, no execution.

The factual findings below are literal source/output comparisons. They do not
use a writer's completed status as evidence of task correctness or skill value.
"""
from pathlib import Path
import ast,hashlib,json,zipfile,xml.etree.ElementTree as ET

ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261030_wrd_gap08/corpus/first6';OUT=Path(__file__).resolve().parent
GROUPS=['ep_13db0415403c12c60e2b','ep_42d23f25933caada98b1','ep_530653bde445b02636f4']
def H(b):return hashlib.sha256(b).hexdigest()
def J(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def P(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def tx(m):
 c=m.get('content','');return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def excerpt(s,needle):
 i=s.find(needle);assert i>=0,needle;return {'start':i,'end':i+len(needle),'text':needle,'text_SHA256':H(needle.encode())}
def point(code,lineno,col):
 ls=code.splitlines(keepends=True);return sum(map(len,ls[:lineno-1]))+len(ls[lineno-1].encode()[:col].decode())
def node_range(code,n):return {'start':point(code,n.lineno,n.col_offset),'end':point(code,n.end_lineno,n.end_col_offset),'coordinate':'Original write.arguments.content Unicode codepoints; half-open; includes full statement or function','start_line':n.lineno,'end_line':n.end_lineno}
def add_problem(out,code,tree,needle,why,evidence,kind='REQUIRES_ZERO_LOSS_UNLESS_EXPLICIT_NEW_CORRECTED_TARGET'):
 found=[n for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and needle in n.value];assert len(found)==1,(needle,len(found));n=found[0]
 # Give an exact complete literal mask and the more conservative containing
 # statement. A list assignment can hold many unrelated valid facts, so its
 # full assignment is not the mandatory minimum exclusion.
 parents={id(c):p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)};p=n
 while not isinstance(p,ast.stmt):p=parents[id(p)]
 r=node_range(code,n);sr=node_range(code,p);s=code[r['start']:r['end']]
 out.append({'disposition':kind,'code_range':r,'containing_statement_range_conservative_optional':sr,'code_text_SHA256':H(s.encode()),'literal_problem_excerpt':needle,'reason':why,'original_source_evidence':evidence,'target_execution_success_does_not_resolve_this':True})

def main():
 OUT.mkdir(exist_ok=True);results=[]
 for eid in GROUPS:
  gp=BASE/eid/'GROUP.json';g=J(gp);ctx=g['original_context'];ms=ctx['messages'];resources=g['source_and_resource_proofs'];files=resources['frozen_input_final_output_objects'];inp=next(x for x in files if x['record']['role']=='workspace_input');ip=Path(inp['actual_copied_object']['path']);assert P(ip)==inp['actual_copied_object'];source=J(ip);source_text='\n'.join(x['text'] for x in source['requests'])
  outputs=[]
  for f in files:
   p=Path(f['actual_copied_object']['path']);assert P(p)==f['actual_copied_object']
   if f['record']['role']=='workspace_output' and f['record']['logical_path'].endswith('.docx'):
    with zipfile.ZipFile(p) as z:xml=ET.fromstring(z.read('word/document.xml'))
    outputs.append({'artifact':P(p),'logical_path':f['record']['logical_path'],'actual_XML_text':''.join(x.text or '' for x in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))})
  for t in g['original_targets_with_feedback']:
   cp=Path(t['original_code_file']['path']);raw=cp.read_bytes();code=raw.decode('utf8');assert P(cp)==t['original_code_file'];target=ms[t['message_index']];call=next(c for c in target['content'] if c.get('type')=='toolCall' and c['id']==t['tool_call_id']);assert call['arguments']['content']==code and call['arguments']['path']==t['native_path'];tree=ast.parse(code)
   problems=[];facts=[];functions=[{'name':n.name,'original_code_range':node_range(code,n),'body_SHA256':H(code[node_range(code,n)['start']:node_range(code,n)['end']].encode()),'credit':'BOUNDED_PYTHON_DOCX_RESOURCE_CONSTRUCTION_ONLY_NOT_BUSINESS_EVALUATION_OR_SKILL_KEEP'} for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
   if eid==GROUPS[0]:
    add_problem(problems,code,tree,'主导解决产品开发过程中的技术难题','Source only assigns solving technical problems; 主导 adds lead responsibility despite explicit no substantive scope changes.',excerpt(source_text,'解决产品开发过程中的技术难题'))
    add_problem(problems,code,tree,'编写并维护各类技术文档','Source assigns writing documentation; maintaining it adds a duty despite explicit no substantive scope changes.',excerpt(source_text,'编写技术文档'))
    facts=[{'source_anchor':excerpt(source_text,x),'literal_in_code':x in code} for x in ['8年以上','轨道巡检机器人','轮式机器人','四足机器人','防爆认证','矿用安标','SolidWorks','AutoCAD','ANSYS']]
    decision='CONDITIONAL_FULL_WRITER_WITH_TWO_RESPONSIBILITY_STATEMENTS_ZERO_LOSS; alternatively new corrected target must declare new authorship and repeat CPU/content QA'
   elif eid==GROUPS[1] and 'gen_docs' in t['native_path']:
    add_problem(problems,code,tree,'健康咨询Agent服务超5万用户零投诉','Source narrows the reported zero complaints to 医疗安全投诉. General zero complaints overstates the evidence.',excerpt(source_text,'未发生一起医疗安全投诉'))
    add_problem(problems,code,tree,'薪资预期显著高于其他候选人','Source gives prior/current salary19K base+14K annual bonus and says expected salary negotiable. It does not establish a higher current expectation than all other candidates.',excerpt(source_text,'期望薪资可根据岗位职责与面试情况合理确定'))
    add_problem(problems,code,tree,'已按用户决定安排终面','User selected 左 for interview and separately corrected that final-round advancement had not been confirmed; selecting whom to interview does not establish final-round scheduling.',excerpt(source_text,'目前还没明确进入终面'))
    add_problem(problems,code,tree,'用户已确认仅面左，本报告附其面试提纲','The selection of 左 is grounded, but paragraph discusses next-round/final-round progression as already settled; retain source correction and do not teach confirmed progression.',excerpt(source_text,'目前还没明确进入终面'))
    facts=[{'source_anchor':excerpt(source_text,x),'code_status':'SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED'} for x in ['这是王的面试总结','这是徐的面试纪要','期望薪资为14K','80%SOP覆盖','核心模块稳定性达99%','孙静静期望年包20万以上']]
    decision='CONDITIONAL_WRITER_A_ONLY_WITH_FOUR_BUSINESS_STATEMENTS_ZERO_LOSS; ranking and hiring judgments remain historical proposals, not verified business outcomes'
   elif eid==GROUPS[1]:
    add_problem(problems,code,tree,'终面原约张江双子塔A塔现场','Original interview summary proposed an onsite final round, later user correction says no final-round confirmation. Current delegated task asks online within30min; it does not prove an appointment or confirmed final-round progression.',excerpt(source_text,'目前还没明确进入终面'))
    facts=[{'source_anchor':excerpt(source_text,'时间30分钟内'),'planned_section_minutes':[3,10,6,4,5,2],'sum':30,'credit':'PROPOSED_SCHEDULE_MATCHES_BOUND; no observed interview timing'}, {'new_policy_not_original_factual_requirement':{'score_weights':[30,25,15,15,15],'recommended_threshold':3.8,'minimum_0_to_1_score':3},'credit':'EXPLICIT_NEW_PROPOSED_HEURISTIC_ONLY_NO_EMPIRICAL_HIRING_VALIDATION'}]
    decision='CONDITIONAL_FULL_OUTLINE_WRITER_A_ONLY_WITH_APPOINTMENT_STATEMENT_ZERO_LOSS; label questions/weights/threshold as proposed design'
   else:
    add_problem(problems,code,tree,'除为备份数据所必需的下载、复制外','Literal source allows download for backup as an exception; revision adds copying to the exception. This changes authorization content and cannot receive factual/legal correctness credit merely because rendering succeeded.',excerpt(source_text,'除下载数据备份外，禁止对软件进行反向工程、复制或修改'))
    add_problem(problems,code,tree,'包括数据丢失、业务中断或生产损失等','Original liability examples include personal injury or production loss. Revision substitutes data loss/business interruption and drops personal injury; this is a substantive unsupported change, independent of legal validity.',excerpt(source_text,'包括人身伤害或生产损失'))
    add_problem(problems,code,tree,'将优先依据企业已有的制度与流程文件','Original explicitly prioritizes compiled evidence atoms. General existing documents remove that original evidence-control requirement without source support.',excerpt(source_text,'优先引用已编译的证据原子'))
    add_problem(problems,code,tree,'以下仅保留原始文本中与「我的分享」相关的现存内容','Existing sharing fragment is preserved, but assigning it to missing section6 is an unverified structural inference; source/user says section6 absent and do not invent it. Keep as unplaced fragment or explicitly mark proposed placement.',excerpt(ms[0]['content'],'不得臆造或补写缺失内容'))
    add_problem(problems,code,tree,'支持多种调度类型，可按需设置周期选项','Source specifies three schedule types but omits their names. Omitting the supported count is not necessary to avoid inventing names; this is a completeness loss rather than proof there are not3.',excerpt(source_text,'支持三种调度类型'))
    add_problem(problems,code,tree,'未虚构任何内容','Global factual correctness claim is too broad given substantive content changes identified in this same writer. Mask this self-certification; successful file generation or PDF text extraction cannot certify it.',excerpt(ms[0]['content'],'一律以所提供文本为准'))
    facts=[{'source_anchor':excerpt(source_text,x),'literal_in_code':x in code} for x in ['17 个内置智能体','不超过 100MB','最多 5 个'] if x in source_text]
    decision='CONDITIONAL_WRITER_A_ONLY_WITH_SIX_STATEMENTS_ZERO_LOSS; prefer generic docx builder extraction if semantic mask/compiler boundary cannot be shown'
   actualtext=''.join(x['actual_XML_text'] for x in outputs)
   for p in problems:p['problem_excerpt_persisted_in_some_frozen_output_XML']=p['literal_problem_excerpt'] in actualtext
   observed_execs=[{'message_index':i,'tool_result_text_SHA256':H(tx(m).encode()),'visible_text_prefix':tx(m)[:180]} for i,m in enumerate(ms) if m.get('role')=='toolResult' and m.get('toolName')=='exec' and i>t['message_index']]
   results.append({'episode_id':eid,'source_ids':resources['source_ids'],'source_statuses':resources['source_current_statuses'],'target_owner_id':t['original_target_id'],'original_code':P(cp),'characters':len(code),'target_code_equals_original_write_argument':True,'group':P(gp),'source_packet':P(ip),'original_system_status':resources['original_system_status'],'native_target_is_not_equivalent_new_prompt':True,'decision':decision,'positive_credit_only':'Original complete code retained; any training input adaptation is explicit NEW_FUNCTIONAL_COMMISSION. Original R0; new rationale if any must be new-authored and independently masked. Component A only. No skill KEEP, pipeline controller or autonomous closed-loop credit.','mandatory_zero_loss_code_ranges':problems,'candidate_reusable_functions':functions,'source_grounding_checks':facts,'actual_later_exec_results_for_audit_not_input':observed_execs,'frozen_docx_outputs':[{'artifact':x['artifact'],'logical_path':x['logical_path'],'XML_text_SHA256':H(x['actual_XML_text'].encode())} for x in outputs],'no_new_program_or_Agent_execution_in_this_review':True,'visual_QA_or_business_outcome_not_proved_by_docx_XML_or_pdftotext':True})
 report={'schema':'wrd-gap08-independent-three-program-semantic-review-v2','status':'CONDITIONAL_SCOPED_A_RESOURCE_CREDIT; NO_WHOLE_BUSINESS_SUCCESS_ADMISSION','reviewer':'scheduled_batch24','independent_from_candidate_preparer':True,'read_full_original_programs':4,'episodes':3,'findings':results,'mandatory_zero_loss_literals':sum(len(x['mandatory_zero_loss_code_ranges']) for x in results),'function_definition_proposals_not_independent_original_tasks':sum(len(x['candidate_reusable_functions']) for x in results),'new_business_Teacher_Actor_or_old_Agent_calls':0,'no_training':True,'AI_curation_and_offline_processing_cost':'UNKNOWN_NOT_ZERO','supersedes_preserved_first_review':P(OUT/'THREE_PROGRAM_SEMANTIC_QA.json'),'corrections_from_first_review':['Mandatory masks now target complete offending literals; containing statement ranges remain optional conservative masks, avoiding unrelated facts in a list being hidden.','Old no_model_calls=true meant no new business Teacher/Actor but was too broad: AI curation did occur and cost is unknown, not zero.'],'program':P(__file__)}
 p=OUT/'THREE_PROGRAM_SEMANTIC_QA02.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'report':P(p),'status':report['status'],'zero_loss_literals':report['mandatory_zero_loss_literals']}))

if __name__=='__main__':main()
