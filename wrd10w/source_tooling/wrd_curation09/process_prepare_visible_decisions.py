"""Exact recorded public process explanations in explicitly authored states.

These are assistant-visible text, never claimed as original internal reasoning.
Unsupported clauses are preserved in the target with precise loss0 exclusions.
No business call, program execution or full-pipeline success is manufactured.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261031_wrd_curation09/process'
DATA=ROOT/'output/20261027_wrd_main_v10'
RES=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
CAP=DATA/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def gzsave(p,data):
 with p.open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for x in data:f.write((js(x)+'\n').encode())
def blocks(m):
 c=m.get('content',[]);return [{'type':'text','text':c}]if isinstance(c,str)else c
def txt(m):return '\n'.join(x.get('text','')for x in blocks(m)if x.get('type')=='text')

SPECS={
 'fca1a71a04c939bcb69a4c3c':{'evidence':[2,8,16,18], 'purpose':'外部图片API多次返回404。当前授权的子任务是先确认本地HTML/SVG渲染环境并准备替代草案，不宣称已满足原指定生图模型的效果。请依据当前证据说明下一步。',
  'exclude':[('，该账号未开放images端点','404 does not establish an account-entitlement cause')],'extra_tools':[]},
 'a6989883529177f6a96f4f88':{'evidence':[2,12,14,16],'purpose':'当前未能确定用户账号；只依据已提供材料和已收检查结果决定下一步，不猜账号、不编造提交。','extra_tools':['ask_user']},
 '3550fb3e4c356079bee0247c':{'evidence':[2,10,12,14,16],'purpose':'本步决定是否具备发送前提以及需要向用户补问什么。不得发送到脱敏占位地址、猜凭据或声称已发出。','extra_tools':['ask_user']},
 '170528cfab8762d5526c9789':{'evidence':[2,4],'purpose':'已收到一份缺失附件错误和另一份实际可读的JSON原始需求。仅说明如何接续现有任务，不据缺失文件推断其内容已校对。',
  'exclude':[('内容一致。','The missing attachment cannot be compared to the available JSON')],'extra_tools':[]},
 'fd8b3c447135ba895972f7b3':{'evidence':[2,4,6,8],'purpose':'指定技能与参考目录在本环境未找到。请说明当前能采取的任务接续方式，不能冒称已读取或使用缺失技能。','extra_tools':[]},
 '45367ef84bf2439e17a581a1':{'evidence':[2,4],'purpose':'图像文件已提供，但原生模型读取反馈明确说像素被省略。请说明如何获取实际配色证据，不假装看到了图片。','extra_tools':[]},
 'fbd8c8b3768676770c9fa456':{'evidence':[2,6,14,16],'purpose':'已有本地动画脚本写入记录，但尚未完成渲染验收。请提出下一步有限验证，不把写入成功称为主逻辑已正确。',
  'exclude':[('主逻辑确认无误。','Writing code is not proof of its logic correctness')],'extra_tools':[]},
 'db4862de2e4caffd18773d62':{'evidence':[2,4,6],'include_prior_write':True,'purpose':'只依据实际源JSON与已写报告向用户说明数据缺口和本次交付。不得虚构财务指标；原草稿中的记录条数不是权威计数。',
  'exclude':[('约 70 条','Actual source JSON has 53 request records, not approximately70')],'extra_tools':[]},
 '5ba0217d85295ebfe61f85a3':{'evidence':[2,12,14,16,18,20],'include_prior_write':True,'purpose':'本次没有获得账号补充，报告草稿已写入。请如实说明未能完成数据拉取的原因和已交付内容；检查范围有限，不承诺补账号即能在确定时限完成。',
  'exclude':[('任务完成，','Only a deficiency report, not the requested data-backed summary, was delivered'),('已尽全部核查手段，','Finite recorded checks do not exhaust all possible checks'),('无任何 git/gitee 配置','Only the explicitly inspected locations/configurations were checked'),('| /workspace 及 ~/.openclaw 搜索凭据/令牌 | 无 |','Recorded commands do not prove exhaustive credential search across both trees'),('正常（HTTP 200），非网络原因','Homepage HTTP200 does not establish all API/network paths are working'),('下一步只需提供 Gitee 用户名（可选：访问令牌、多账号署名清单、入职时间），即可生成含真实提交数据的最终总结文档。','Actual access, repository scope and data quality remain untested')],'extra_tools':[]},
 'd03c86b1a2c0713fc3e3075f':{'evidence':[4,6,8],'purpose':'当前搜索工具返回不可用。只说明合法的替代检索方式；尚未获取定价，不生成价格结论。','extra_tools':['web_fetch']},
 'de7fc12e8ded00e51baf9105':{'evidence':[2,12,14,16,18],'purpose':'已做有限账号查找且本轮提问未获答复。请说明诚实的下一步，不伪造提交，也不把本轮未回复说成用户在所有渠道不可联系。',
  'exclude':[('用户也不可联系','No reply in this interaction is not proof of general unreachability')],'extra_tools':[]},
 '924074d354667c2741706dbc':{'evidence':[2,4,6],'purpose':'原附件路径不存在，但实际JSON已提供业务要求。只说明当前任务的接续方向，不声称合同条款已依法核验。','extra_tools':[]},
}

def main():
 assert not (OUT/'VISIBLE_DECISION_CANDIDATES12.jsonl.gz').exists()
 reservation=load(RES);reserved=set(reservation['reserved_source_ids']);held_components=set(reservation['reserved_source_scope_components'])
 scopes={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 owners={r['owner_id']:r for r in rows(OUT/'OWNER1321_EXACT_CONTENT.audit.jsonl.gz')if r['owner_id']in SPECS};assert set(owners)==set(SPECS)
 epids={r['episode_id']for r in owners.values()};contexts={c['episode_id']:c for c in rows(OUT/'ORIGINAL_CONTEXTS_343.audit.jsonl.gz')if c['episode_id']in epids}
 cap=load(CAP);toolreg={t['function']['name']:t for t in cap['tools']};core={'apply_patch','edit','exec','ls','process','read','write'}
 candidates=[];verdicts=[]
 for oid,spec in SPECS.items():
  row=owners[oid];context=contexts[row['episode_id']];idx=row['source_message_index'];m=row['target_message_original'];content=txt(m)
  assert len([b for b in blocks(m)if b.get('type')=='text'])==1 and content
  assert not set(row['source_ids'])&reserved
  assert all(scopes[s]['status']=='TRAIN'and scopes[s]['component_id']not in held_components for s in row['source_ids'])
  exclusions=[]
  for fragment,reason in spec.get('exclude',[]):
   assert content.count(fragment)==1,(oid,fragment)
   start=content.index(fragment);exclusions.append({'start':start,'end':start+len(fragment),'text':fragment,'text_sha256':h(fragment),'reason':reason})
  exclusions.sort(key=lambda z:z['start']);assert all(a['end']<=b['start']for a,b in zip(exclusions,exclusions[1:]))
  evidence=[]
  for i in spec['evidence']:
   assert i<idx;obs=context['messages'][i];assert obs['role']=='toolResult'
   evidence.append({'original_message_index':i,'tool_name':obs.get('toolName'),'tool_call_id':obs.get('toolCallId'),'message':obs,'text':txt(obs),'text_sha256':h(txt(obs))})
  priorwrite=[]
  if spec.get('include_prior_write'):
   for i,prior in enumerate(context['messages'][:idx]):
    for block in blocks(prior):
     if block.get('type')=='toolCall'and block.get('name')=='write':
      a=block['arguments'];priorwrite.append({'original_message_index':i,'tool_call_id':block['id'],'path':a.get('path'),'content':a.get('content'),'content_sha256':h(a.get('content',''))})
   assert priorwrite
  packet={'schema':'wrd09-visible-process-explanation-review-packet','owner':row,'original_context':context,'target_visible_text':content,
   'target_visible_text_sha256':h(content),'selected_pre_target_evidence':evidence,'prior_written_drafts':priorwrite,
   'unsupported_content_unicode_exclusions':exclusions,'new_state_instruction_authorship':'NEW_CURATOR_SCOPE_AND_DELEGATION',
   'not_original_internal_reasoning':True,'not_full_native_prompt_equivalence':True,'not_whole_skill_KEEP_gold':True}
  pp=OUT/'visible_decision_packets'/f'{oid}.json';save(pp,packet)
  task=txt(context['messages'][0]).split('用户任务：')[-1].strip()
  prompt='当前仅需依据现有任务和实际已收证据说明接续或收尾。'+spec['purpose']+'\n\n原始任务要求：\n'+task+'\n\n'
  for e in evidence:prompt+=f'已收到的原始工具反馈（原消息{e["original_message_index"]}，{e["tool_name"]}，未改写；仅表示该检查范围）：\n{e["text"]}\n\n'
  for w in priorwrite:prompt+=f'此前写入的报告草稿参数（原消息{w["original_message_index"]}；不是独立审核结论）：\n文件：{w["path"]}\n{w["content"]}\n\n'
  profile=core|set(spec['extra_tools']);tools=[t for t in cap['tools']if t['function']['name']in profile];assert len(tools)==len(profile)
  stage='D_local_missing_input_honest_response'if oid in{'db4862de2e4caffd18773d62','5ba0217d85295ebfe61f85a3'}else'B_visible_recovery_and_verification_decision'
  candidate={'schema_version':'wrd09-recorded-visible-process-text-functional-view-v1','id':'process09-visible-'+oid,'owner_id':oid,
   'bank':'process09_visible_control_text','stage':stage,'split':'train','source_ids':row['source_ids'],
   'source_group_id':'process09_'+h('|'.join(sorted(row['source_ids'])))[:20],'source_admission':'ADMIT','training_admitted':True,
   'root_main_admission':False,'requires_external_root_admission':True,'original226':False,'holdout12':False,
   'protected_sources_visible_prefix':False,'protected_source_ids':[],
   'annotation_provenance':'RECORDED_PUBLIC_ASSISTANT_TEXT_IN_NEW_EVIDENCE_GROUNDED_STATE; NOT_INTERNAL_R',
   'original_episode_id':row['episode_id'],'original_message_index':idx,'original_visible_text_sha256':h(content),
   'source_context':{'path':str(pp.resolve()),'bytes':pp.stat().st_size,'sha256':sha(pp)},
   'original_system_capture':context['system_capture_status'],'original_native_prompt_equivalence_claimed':False,
   'student_view':'EXPLICIT_CORE7_PLUS_NEEDED_NATIVE_TOOL_STATE_FOR_VISIBLE_EXPLANATION','actual_native_tool_dispatch':False,
   'original_recorded_tool_suffix_omitted_from_this_text_only_view':bool(row['actual_tool_names']),
   'loss_multiplier':0.25,'tools':tools,'tool_schema_provenance':{'path':str(CAP.resolve()),'sha256':sha(CAP)},
   'is_full_autonomous_execution_demonstration':False,'is_qualified_KEEP_demonstration':False,
   'credit':'Public local recovery/verification/clarification or honest subtask closure only; no whole pipeline autonomy or skill utility',
   'data_design_revision':'5.0.50','data_change_id':'ALG-20261031-02','curation_cost':'UNKNOWN_NOT_ZERO',
   'new_business_Teacher_Actor_calls':0,'training_started':False,'holdout_reservation_sha256':sha(RES),
   'teacher_original_R_supervised':False,'rationale_provenance':'ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD',
   'target_content_unicode_exclusions':exclusions,'output_content_provenance':'ONE_RECORDED_PUBLIC_TEXT_BLOCK_VERBATIM; unsupported spans loss0',
   'messages':[{'role':'system','content':'根据当前可见证据说明下一步或真实缺口，不把推测、草稿和工具退出码当业务正确性。'},
    {'role':'user','content':prompt},{'role':'assistant','content':content,'reasoning_content':''}],
   'supervision_message_indices':[2],'message_loss_mask':[0,0,1],'approved_components':['D']}
  candidates.append(candidate)
  verdicts.append({'owner_id':oid,'status':'SCOPED_PUBLIC_DECISION_TEXT_CANDIDATE_PENDING_ROOT_INDEPENDENT_REVIEW',
   'actual_before_evidence_indices':spec['evidence'],'excluded_ranges':exclusions,'whole_skill_utility_not_approved':True,
   'reasoning_field_positive':False,'text_not_rewritten':True})
 gzsave(OUT/'VISIBLE_DECISION_CANDIDATES12.jsonl.gz',candidates)
 save(OUT/'VISIBLE_DECISION_REVIEW12.json',{'status':'CANDIDATES_NOT_ADMISSION','records':verdicts,'targets':len(candidates),
  'original_visible_assistant_text_not_internal_reasoning':True,'new_R_positive':0,'original_R_positive':0,
  'new_qualified_KEEP_or_full_autonomy':0,'unsupported_spans':sum(len(x['excluded_ranges'])for x in verdicts),
  'script_sha256':sha(__file__),'reservation_sha256':sha(RES),'training_started':False})
 print(json.dumps({'candidates':len(candidates),'unsupported_spans':sum(len(x['excluded_ranges'])for x in verdicts),'new_R':0,'internal_R_claimed':False,'training_started':False}))
if __name__=='__main__':main()
