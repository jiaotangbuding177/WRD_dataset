"""Explicit state-conditioned resource/repair SFT views, CPU tokenizers only.

The original complete transcripts and wrong code remain in audit. New states,
new source-preserving repairs and original recorded actions have separate tags.
No constructed view is called an original native prompt or autonomous episode.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
import argparse,gzip,hashlib,importlib.util,json,os,subprocess,sys
os.environ.update(USE_TORCH='0',USE_TF='0',TOKENIZERS_PARALLELISM='false',CUDA_VISIBLE_DEVICES='-1')
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261030_wrd_gap08/process_bank02'
DATA=ROOT/'output/20261027_wrd_main_v10'
FIRST=ROOT/'output/20261030_wrd_gap08/corpus/first6'
CAP=DATA/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'
PEER=ROOT/'output/20261030_wrd_gap08/semantic_peer'
HTML=ROOT/'output/20261030_wrd_gap08/semantic_peer_html'
SEM=ROOT/'output/20261030_wrd_gap08/semantic_root'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(t):return hashlib.sha256(t.encode('utf-8')).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def write_rows(p,rs):
 p.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:
  for r in rs:f.write(js(r)+'\n')
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def normalized(m):
 role=m['role'];blocks=m.get('content',[])
 if isinstance(blocks,str):txt=blocks;blocks=[]
 else:txt='\n'.join(b.get('text','') for b in blocks if isinstance(b,dict)and b.get('type')=='text')
 if role=='toolResult':
  if any(b.get('type')=='image'for b in blocks if isinstance(b,dict)):
   txt+='\n[此文本状态没有提供原图像像素；图像内容不据此视为已核验。]'
  return {'role':'tool','tool_call_id':m.get('toolCallId'),'content':txt}
 if role=='assistant':
  r={'role':'assistant','content':txt,'reasoning_content':''}
  calls=[]
  for b in blocks:
   if isinstance(b,dict)and b.get('type')=='toolCall':
    args=b.get('arguments',{});args=json.loads(args)if isinstance(args,str)else args
    calls.append({'id':b['id'],'type':'function','function':{'name':b['name'],'arguments':args}})
  if calls:r['tool_calls']=calls
  return r
 return {'role':'user','content':txt}


def prepare():
 OUT.mkdir(parents=True,exist_ok=False)
 assert load(SEM/'docx_source_corrections/workspace/RESULT.json')['status'].startswith('PASS')
 assert load(SEM/'overlay_viewport_repair/workspace/RESULT.json')['status'].startswith('PASS')
 assert load(HTML/'PEER.json')['status'].startswith('PASS')
 source_scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 cap=load(CAP);tools=[t for t in cap['tools']if t['function']['name']in {'apply_patch','edit','exec','ls','process','read','write'}]
 assert len(tools)==7
 refs=load(FIRST/'FIRST6_ACTUAL_GROUPS.json')['groups']
 groups={r['episode_id']:load(FIRST/r['episode_id']/'GROUP.json')for r in refs}
 current=load(DATA/'TRAINING_MANIFEST.json')
 occupied_owners=set();occupied_calls=set()
 for f in current['actual_train_files']:
  for r in rows(DATA/f['path']):
   occupied_owners.add(r['original_record_metadata'].get('owner_id',r['id']))
   for t in r['targets']:
    if any(s[2]=='A'for s in t['owned_supervision_spans']):
     occupied_calls.update(c['id']for c in r['messages'][t['message_index']].get('tool_calls',[]))
 excludes=defaultdict(list)
 for r in load(PEER/'THREE_PROGRAM_SEMANTIC_QA02.json')['findings']:
  for x in r['mandatory_zero_loss_code_ranges']:
   excludes[r['target_owner_id']].append({'start':x['code_range']['start'],'end':x['code_range']['end'],'reason':x['reason'],'text_sha256':x['code_text_SHA256']})
 for x in load(HTML/'MANDATORY_LOSS0_SPANS.json')['spans']:
  excludes[x['original_target_id']].append({'start':x['start'],'end':x['end'],'reason':x['reason'],'text_sha256':x['span_sha256_utf8']})
 made=[];held=[]
 def state(g,idx):
  original=g['original_context']['messages'];task=str(original[0]['content']).split('用户任务：')[-1].strip()
  prompt=('当前工作目录为 /workspace，Python、Node及既有文档/媒体工具可用。以下材料和此前操作记录来自当前任务。'
          '工具反馈可能包含失败或未证实判断；以实际内容和用户要求为准。仅提供所列工具；外部服务与剩余预算未知。\n\n'+task)
  messages=[{'role':'system','content':'根据当前任务、可见文件和实际工具反馈操作。保留用户纠正；没有证据时明确未知，不把文件生成或退出码等同内容正确。'},
            {'role':'user','content':prompt}]
  messages += [normalized(m)for m in original[1:idx]]
  return messages
 def base(g,owner,index,kind):
  sources=g['source_and_resource_proofs']['source_ids'];assert all(source_scope[s]['status']=='TRAIN'for s in sources)
  assert owner not in occupied_owners
  return {'schema_version':'wrd-gap08-functional-resource-view-v1','id':'gap08-'+owner,'owner_id':owner,
   'bank':'gap08_resource_and_repair_process','stage':kind,'split':'train','source_ids':sources,
   'source_group_id':'gap08_component_'+hs('|'.join(sorted(sources)))[:20],
   'source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,'requires_external_root_admission':True,
   'original226':False,'holdout12':False,'protected_sources_visible_prefix':False,'protected_source_ids':[],
   'annotation_provenance':'NEW_FUNCTIONAL_STATE_WITH_PRECISE_RECORDED_ACTION_OR_DECLARED_NEW_CORRECTION',
   'original_episode_id':g['original_context']['episode_id'],'original_message_index':index,
   'source_context':pin(FIRST/g['original_context']['episode_id']/'GROUP.json'),
   'original_system_capture':g['original_context']['system_capture_status'],
   'original_native_prompt_equivalence_claimed':False,'student_view':'EXPLICIT_CORE7_FUNCTIONAL_STATE_NOT_FULL53_ORIGINAL_INPUT',
   'actual_native_tool_dispatch':False,'original_action_if_present_remains_recorded_native_not_new_dispatch':True,
   'loss_multiplier':0.25,'tool_schema_provenance':{'path':str(CAP.resolve()),'sha256':sha(CAP)},'tools':tools,
   'is_full_autonomous_execution_demonstration':False,'is_qualified_KEEP_demonstration':False,
   'credit':'Scoped resource implementation or source-preserving local repair; no whole skill utility/decision gold',
   'data_design_revision':'5.0.48','data_change_id':'ALG-20261030-02','curation_cost':'UNKNOWN_NOT_ZERO',
   'new_business_Teacher_Actor_calls':0,'training_started':False}
 def finish(r,messages,call,rationale='',allowed=None):
  assert call['id']not in occupied_calls
  messages=deepcopy(messages)+[{'role':'assistant','content':'','reasoning_content':rationale,'tool_calls':[call]}]
  r.update(messages=messages,supervision_message_indices=[len(messages)-1],
           message_loss_mask=[0]*(len(messages)-1)+[1],approved_components=allowed or ['A'],
           rationale_provenance='NEW_AUTHORED_SCOPED_RATIONALE'if rationale else'NO_ORIGINAL_R_IN_THIS_VIEW',
           target_tool_call_id=call['id'],teacher_original_R_supervised=False)
  made.append(r)
 for ep,g in groups.items():
  for t in g['original_targets_with_feedback']:
   owner=t['original_target_id'];code=Path(t['original_code_file']['path']).read_text(encoding='utf-8')
   if any(e['start']==0 and e['end']==len(code)for e in excludes[owner]):
    held.append({'owner':owner,'reason':'WHOLE_ORIGINAL_TEST_HARNESS_KNOWN_BAD','original':t['original_code_file']});continue
   r=base(g,owner,t['message_index'],'B_resource_implementation_from_execution_auxiliary')
   r['target_code_unicode_exclusions']=excludes[owner];r['target_original_code_sha256']=hs(code)
   r['original_recorded_action_owner']=owner;r['output_content_provenance']='RECORDED_NATIVE_WRITE_CONTENT_VERBATIM_WITH_EXACT_NEGATIVE_MASKS'
   for x in excludes[owner]:assert hs(code[x['start']:x['end']])==x['text_sha256']
   call=normalized(t['original_message'])['tool_calls'][0]
   assert call['function']['arguments']['content']==code
   finish(r,state(g,t['message_index']),call)
 # Real historical repair actions, supplied with complete necessary current
 # file state. These are new prompts, not claims of original system capture.
 for ep,index,version in [
  ('ep_4aadd96d99f2c07543c7',17,'versions/game_test_v1.js'),
  ('ep_4aadd96d99f2c07543c7',31,'versions/ep_4aadd96d99f2c07543c7_31_before.html'),
  ('ep_4d412dca2c57480536e7',65,'versions/ep_4d412dca2c57480536e7_65_before.py'),
  ('ep_4d412dca2c57480536e7',83,'versions/ep_4d412dca2c57480536e7_83_before.py')]:
  g=groups[ep];original_owner=hs(ep+':'+str(index))[:24];owner='state-repair-'+original_owner;r=base(g,owner,index,'B_verified_local_repair_new_functional_state')
  original=g['original_context']['messages'];call=normalized(original[index])['tool_calls'][0]
  p=SEM/'qa/workspace'/version;before=p.read_text(encoding='utf-8')
  goals={17:'当前Playwright测试脚本出现 Identifier chromium has already been declared，脚本全文如下。请最小修复变量重复声明并重新运行本地测试。',
   31:'当前横版游戏在camX=0时向右侧生成runner的坐标落在地面空隙，局部实际检查得到0个runner。请让附近存在可用地面时仍能生成runner，保留其它玩法。',
   65:'当前合成程序实际报 Invalid stream specifier: vbase，overlay分支消费了已经用过的流标签。请最小修复filtergraph连接；先处理这个局部问题，不宣称完整视频质量已通过。',
   83:'请把当前字幕脚本末尾的弓箭emoji改为脚本内联矢量图，减少对emoji字体的依赖。保留文案与其它样式；这里只处理字符图形，不代表整体视频已经验收。'}
  messages=[{'role':'system','content':'只依据当前明确提供的文件、要求与实际局部反馈操作；未提供的历史图像、音频和视觉服务返回不作已验证前提。'},
    {'role':'user','content':goals[index]+'\n当前相关文件全文：\n'+before}]
  r['actual_recorded_repair_call_id']=call['id'];r['original_recorded_action_owner']=original_owner
  call['id']='gap08_projection_'+original_owner
  r['original_prefix_admission']='HOLD_OR_INCOMPLETE_NOT_IMPORTED; only clean original program plus independently checked functional state used'
  r['necessary_before_resource']=pin(p)
  if index==17:
   html_source=FIRST/ep/'874f734c5198497a8a3cda31.html'
   r['other_available_current_file']={'native_path':'/workspace/outputs/contra.html',**pin(html_source)}
   messages[1]['content']+='\n\n测试所需的游戏页面已存在于 /workspace/outputs/contra.html，可在本地访问；本次只修改测试脚本的重复声明。'
  r['before_resource_identity']='LF_CANONICAL_TEXT_OF_QA_DERIVATIVE; raw recorded edits and original bytes separately retained'
  r['output_content_provenance']='INDEPENDENTLY_VERIFIED_NEW_ACTION_PROJECTION_MATCHING_RECORDED_REPAIR_ARGUMENTS; original prefix remains held'
  finish(r,messages,call)
 proposals=load(PEER/'SOURCE_GROUNDED_CORRECTION_PROPOSALS.json')
 for p in proposals['programs']:
  original_owner=p['original_owner_id']
  ep,g,t=next((ep,g,t)for ep,g in groups.items()for t in g['original_targets_with_feedback']if t['original_target_id']==original_owner)
  owner='new-source-correction-'+original_owner;r=base(g,owner,t['message_index'],'B_new_source_preservation_repair')
  messages=state(g,t['message_index']+1)
  messages += [normalized(x['message'])for x in t['actual_feedback']]
  messages.append({'role':'user','content':'请再将当前程序中的内容与上面的原始材料及用户纠正逐项核对。保留正确排版和代码，只改有原文依据的事实偏移；未确认的安排和缺失章节明确标注，不自行补全。'})
  args={'path':t['native_path'],'edits':[{k:c[k]for k in ['oldText','newText']}for c in p['changes']]}
  call={'id':'gap08_'+hs(owner)[:24],'type':'function','function':{'name':'edit','arguments':args}}
  rationale={'befe257a688eb74361966e52':'原任务明确不改变职责事实。原文是解决技术问题和编写文档，新增主导责任或维护义务超出了材料。仅恢复这两处原文表述，保留其余排版。',
   '50a3b236baa2f7324e247fba':'录音中的医疗安全投诉范围不能扩成所有投诉，原薪资也不等于已确认的期望薪资。用户选择面试不代表已经安排终面。按原始范围修订，未确认的安排保持待核实。',
   'c9753a249f6f08a9c7726efa':'当前委托要求线上提纲，但历史记录另有尚未明确进入终面的纠正。可以准备提纲，不能把旧的现场提议写成已经确认的预约。',
   'f78b5c3163c5516f9b7db22a':'这里只校正对原文的保真，不判断条款法律效力。恢复原授权例外、责任列举和证据原子要求；保留明确的三种调度数量，缺失章节和片段归属标明未知，撤掉全局无虚构自证。'}[original_owner]
  r.update(output_content_provenance='NEW_AUTHORED_SOURCE_GROUNDED_LITERAL_EDITS_ACTUALLY_RESOURCE_RETESTED',
    correction_proposal=pin(PEER/'SOURCE_GROUNDED_CORRECTION_PROPOSALS.json'),
    actual_resource_QA=pin(SEM/'docx_source_corrections/workspace/RESULT.json'),
    original_writer_owner=original_owner,do_not_train_corrected_whole_write_alongside_this_repair=True)
  finish(r,messages,call,rationale,['R','A'])
 # Newly discovered screenshot clipping, distinct from the old emoji repair.
 ep='ep_4d412dca2c57480536e7';g=groups[ep];owner='new-overlay-viewport-repair';r=base(g,owner,None,'B_new_actual_viewport_repair')
 before=SEM/'overlay_viewport_repair/before.py'
 messages=[{'role':'system','content':'根据当前文件和实际反馈修订。不要把局部测试通过当作整个视频质量已确认。'},
  {'role':'user','content':'当前字幕PNG生成脚本如下。实际检查发现胜利字幕的预期clip高度为520，生成PNG只有2000×500；其它两张为2000×300。请定位并最小修复截图高度问题，保留已有文本与SVG。\n\n'+before.read_text(encoding='utf-8')}]
 call={'id':'gap08_'+hs(owner)[:24],'type':'function','function':{'name':'edit','arguments':load(SEM/'overlay_viewport_repair/NEW_NATIVE_EDIT_ARGUMENTS.json')}}
 r.update(output_content_provenance='NEW_AUTHORED_SCHEMA_SHAPED_EDIT_ACTUALLY_APPLIED_AND_RESOURCE_RETESTED',
  actual_resource_QA=pin(SEM/'overlay_viewport_repair/REPAIR_EVIDENCE.json'),
  necessary_before_resource=pin(before))
 finish(r,messages,call,'脚本的视口固定为500高，而短字幕要求截取520高。已有尺寸反馈说明裁切受视口限制。按当前卡片高度先调整视口，再设置内容并截图；修后仍需核对实际PNG尺寸。',['R','A'])
 assert len(made)==17 and len(held)==1
 write_rows(OUT/'candidate17.jsonl.gz',made);save(OUT/'HELD_ORIGINAL_BAD_WRITER.json',held)
 save(OUT/'PREPARATION.json',{'status':'ACTUAL17_NEW_STATE_VIEWS_PENDING_COMPILE_AND_ROOT_ADMISSION','records':len(made),'writer_views':8,'recorded_repairs':4,'new_source_preserving_repairs':4,'new_viewport_repair':1,'original_R_new_tokens':0,
  'unconditional_full_native_autonomy':False,'new_business_Teacher_Actor_calls':0,'training_started':False,
  'actual_current_manifest_before':pin(DATA/'TRAINING_MANIFEST.json'),'script':pin(Path(__file__))})
 print(js({'prepared':len(made),'held':len(held)}))


def prune():
 work=OUT/'compiled01';report=load(work/'COMPILATION_REPORT.json');src=module('gap08_compiler',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py')
 compiler=src.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
 dest=OUT/'compiled02';dest.mkdir(exist_ok=False);buckets=defaultdict(list);all_ex=[]
 for ref in report['files']:
  for row in rows(work/ref['path']):
   meta=row['original_record_metadata'];reg=meta.get('target_code_unicode_exclusions',[])
   if reg:
    kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map,enable_thinking=False)
    rendered=compiler.plain_compiled.render(messages=row['messages'],tools=row['tools'],documents=None,add_generation_prompt=False,**kwargs)
    encoded=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
    assert encoded['input_ids']==row['input_ids'];offs=encoded['offset_mapping']
    i=meta['supervision_message_indices'][0];target=next(t for t in row['targets']if t['message_index']==i)
    call=row['messages'][i]['tool_calls'][0];args=call['function']['arguments'];a,b=target['rendered_assistant_span']
    candidates=[];decoder=json.JSONDecoder()
    for pos in range(a,b):
     if rendered[pos]!='{':continue
     try:v,end=decoder.raw_decode(rendered[pos:b])
     except ValueError:continue
     if v==args:candidates.append((pos,pos+end))
    assert len(candidates)==1,candidates
    start,end=candidates[0];serialized=rendered[start:end];code=args['content'];ec=json.dumps(code,ensure_ascii=False)
    assert ec in serialized;content_start=start+serialized.index(ec)+1
    meta['serialized_tool_argument_rendered_span']={'start':start,'end':end,'text_sha256':hs(serialized)}
    ranges=[]
    for x in reg:
     ca,cb=x['start'],x['end'];assert hs(code[ca:cb])==x['text_sha256']
     lo=content_start+len(json.dumps(code[:ca],ensure_ascii=False))-2
     hi=content_start+len(json.dumps(code[:cb],ensure_ascii=False))-2
     expected=json.dumps(code[ca:cb],ensure_ascii=False)[1:-1];assert rendered[lo:hi]==expected
     ranges.append({'start':lo,'end':hi,'text':expected,'text_sha256':hs(expected),'message_index':i,
       'field':'serialized_tool_arguments','subfield':'content','tool_call_id':call['id'],'reason':x['reason']})
    meta['target_excluded_rendered_ranges']=ranges
    spans=[];components=Counter()
    for lo,hi,c,w in row['supervision_spans']:
     for token in range(lo,hi):
      x,y=offs[token]
      if any(x<r['end']and y>r['start']for r in ranges):continue
      if spans and spans[-1][1]==token and spans[-1][2:]==[c,w]:spans[-1][1]=token+1
      else:spans.append([token,token+1,c,w])
      components[c]+=1
    row['supervision_spans']=spans;row['supervised_tokens_by_component']=dict(components);row['supervised_tokens']=sum(components.values());row['supervision_spans_sha256']=hs(js(spans))
    target['owned_supervision_spans']=spans;target['supervised_tokens']=row['supervised_tokens']
    all_ex += [{'id':row['id'],**r}for r in ranges]
   bucket='16k'if row['total_tokens']<=16384 else'32k';buckets[bucket].append(row)
 files=[];counts=Counter();stages=defaultdict(Counter);banks=defaultdict(Counter)
 for bucket,rs in buckets.items():
  name='gap08_resource_and_repair_process.train.'+bucket+'.jsonl.gz';write_rows(dest/name,rs);files.append({'path':name,'bytes':(dest/name).stat().st_size,'sha256':sha(dest/name)})
  for row in rs:
   for c in [counts,stages[row['stage']],banks[row['bank']]]:
    c.update(sequences=1,targets=1,input_tokens=row['total_tokens'],supervised_tokens=row['supervised_tokens'],**{bucket+'_sequences':1,'train_sequences':1,'train_supervised_tokens':row['supervised_tokens']})
    for k,v in row['supervised_tokens_by_component'].items():c['component_'+k]+=v
 with gzip.open(dest/'held.jsonl.gz','wt',encoding='utf-8'):pass
 (dest/'CAUSAL_TEMPLATE.json').write_bytes((work/'CAUSAL_TEMPLATE.json').read_bytes())
 report.update(counts=dict(counts),stages={k:dict(v)for k,v in stages.items()},banks={k:dict(v)for k,v in banks.items()},files=files,
   held_file={'path':'held.jsonl.gz','bytes':(dest/'held.jsonl.gz').stat().st_size,'sha256':sha(dest/'held.jsonl.gz')},
   exact_excluded_code_ranges=len(all_ex),pre_pruning_report=pin(work/'COMPILATION_REPORT.json'),script_sha256=sha(__file__))
 save(dest/'COMPILATION_REPORT.json',report);save(OUT/'EXACT_ZERO_RANGES.json',all_ex)
 assert counts['sequences']==17 and len(all_ex)==22
 print(js({'counts':dict(counts),'negative_ranges':len(all_ex),'full_pipeline_ready':False}))


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['prepare','compile','prune']);a=ap.parse_args()
 if a.operation=='prepare':prepare()
 elif a.operation=='compile':raise SystemExit(subprocess.call([sys.executable,str(ROOT/'research/data_prep/wrd_main_v10/compile_main.py'),'--input',str(OUT/'candidate17.jsonl.gz'),'--output',str(OUT/'compiled01')]))
 else:prune()
