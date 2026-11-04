"""Independent five-row compatible-R provenance/state/full-token-mask audit.

No author point_state/CausalCompiler/span-selection code is imported. Uses
two separate local HF tokenizers and independently reconstructs every label,
weight and component from rendered character geometry. No model is loaded.
"""
from pathlib import Path
from collections import Counter,defaultdict
from array import array
from copy import deepcopy
import gzip,hashlib,json,os,re,sys
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'reasoning_semantic10'
DATA=ROOT/'output/20261027_wrd_main_v10';OLD=DATA/'runtime_preflight/episodes'
RAW=OUT/'ROOT_APPROVED_STAGING.raw.jsonl.gz';COMPILED=OUT/'compiled02'
HEADER='<|im_start|>assistant\n';OPEN='<think>\n';CLOSE='\n</think>\n\n';END='<|im_end|>\n'

def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip():yield json.loads(line)
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def verify(ref):
 p=Path(ref['path']);actual=pin(p);assert actual==ref,('FILE_PIN_MISMATCH',str(p));return p
def save(name,v):(OUT/name).write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def u32sha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return h(a.tobytes())
def text(m):return m.get('content','')if isinstance(m.get('content'),str)else''.join(b.get('text','')for b in m.get('content',[])if b.get('type')=='text')

_stream_cache={}
def sse(ref):
 p=verify(ref)
 if ref['sha256']in _stream_cache:return _stream_cache[ref['sha256']]
 reasoning=[];visible=[];calls={};ids=set();chunks=0
 for line in p.read_text(encoding='utf-8-sig').splitlines():
  if not line.startswith('data:'):continue
  body=line[5:].strip()
  if not body or body=='[DONE]':continue
  event=json.loads(body);ids.add(event.get('id'));chunks+=1
  for choice in event.get('choices',[]):
   assert choice.get('index',0)==0
   delta=choice.get('delta',{})
   if isinstance(delta.get('reasoning_content'),str):reasoning.append(delta['reasoning_content'])
   if isinstance(delta.get('content'),str):visible.append(delta['content'])
   for c in delta.get('tool_calls',[])or[]:
    state=calls.setdefault(c['index'],{'id':'','type':'function','function':{'name':'','arguments':''}})
    if c.get('id'):state['id']+=c['id']
    if c.get('type'):assert c['type']=='function'
    for key in ['name','arguments']:
     if c.get('function',{}).get(key)is not None:state['function'][key]+=c['function'][key]
 assert len(ids)==1 and None not in ids
 result={'response_id':next(iter(ids)),'reasoning_content':''.join(reasoning),'content':''.join(visible),
    'tool_calls':[calls[k]for k in sorted(calls)],'SSE_chunks':chunks}
 _stream_cache[ref['sha256']]=result;return result

def api_args(a):
 decoded=sse(a['source_compatible_API_response']);assert decoded['response_id']==a['response_id']
 assert decoded['reasoning_content']==a['original_R']and h(decoded['reasoning_content'])==a['original_R_sha256']
 assert decoded['tool_calls']==a['original_response'].get('tool_calls',[])
 c=decoded['tool_calls'][0];v=c['function']['arguments'];return c,json.loads(v)if isinstance(v,str)else v

def edit_bytes(before,edits):
 original=before.decode();positions=[]
 for e in edits:
  assert original.count(e['oldText'])==1
  start=original.index(e['oldText']);positions.append((start,start+len(e['oldText']),e['newText']))
 positions.sort();assert all(a[1]<=b[0]for a,b in zip(positions,positions[1:])), 'EDIT_OVERLAP'
 result=original
 for start,end,new in reversed(positions):result=result[:start]+new+result[end:]
 return result.encode()

def reconstruct(a,all_api):
 job=load(OLD/a['stage']/'job.json');state={};origin={}
 for ref in job['resources']:
  p=Path(ref['path']);assert pin(p)['sha256']==ref['sha256']
  if 'bytes'in ref:assert p.stat().st_size==ref['bytes']
  key='/workspace/'+ref['mount'];state[key]=p.read_bytes();origin[key]={'kind':'original_startup','source':pin(p)}
 prior=sorted([x for x in all_api if x['stage']==a['stage']and int(x['call_id'][:4])<int(a['call_id'][:4])],key=lambda x:int(x['call_id'][:4]))
 for p in prior:
  call,ar=api_args(p);name=call['function']['name'];path=ar.get('path')
  if name=='write'and path:
   state[path]=ar['content'].encode();origin[path]={'kind':'prior_actual_API_write','response_pin':p['source_compatible_API_response'],'sequence':int(p['call_id'][:4])}
  elif name=='edit'and path:
   assert path in state
   state[path]=edit_bytes(state[path],ar.get('edits',[ar]));origin[path]={'kind':'prior_actual_API_edit','response_pin':p['source_compatible_API_response'],'sequence':int(p['call_id'][:4])}
  elif name=='exec'and a['stage']=='B_revision_report_01'and p['call_id'].startswith('0017'):
   cmd=ar['command']
   assert 'cp -r /workspace/inputs/previous_skill/.'in cmd and'cp -r /workspace/inputs/previous_tests/.'in cmd
   for source,destination in [('/workspace/inputs/previous_skill/','/workspace/outputs/skill/'),('/workspace/inputs/previous_tests/','/workspace/outputs/tests/')]:
    for oldkey,b in list(state.items()):
     if oldkey.startswith(source):
      newkey=destination+oldkey[len(source):];state[newkey]=b;origin[newkey]={'kind':'prior_actual_literal_copy','source_key':oldkey,'sequence':17}
   oldkey='/workspace/outputs/tests/test_run_log.json';newkey='/workspace/outputs/tests/original_run_log_preserved.json'
   assert 'original_run_log_preserved.json'in cmd
   state[newkey]=state[oldkey];origin[newkey]={'kind':'prior_actual_literal_log_copy','source_key':oldkey,'sequence':17}
 if a['stage']=='B_make_report_02'and a['call_id'].startswith('0016'):
  call,ar=api_args(a);assert call['function']['name']=='read'
  prev=next(x for x in prior if x['call_id'].startswith('0015'))
  pc,pa=api_args(prev);assert pc['function']['name']=='exec'and'run_tests.py'in pa['command']
  feedback=a['actual_native_tool_feedback'];assert len(feedback)==1
  body=text(feedback[0]['message']);report=json.loads(body)
  cpu=OUT/'cpu_checks02/bmake_original21/workspace/outputs/tests/reports/B1a_length_exactly_at_limit_report.json'
  assert load(cpu)==report
  runner=state['/workspace/outputs/tests/run_tests.py'].decode();fixtures=state['/workspace/outputs/tests/make_fixtures.py'].decode()
  assert 'B1a_length_exactly_at_limit'in runner and'B1a'in fixtures
  assert 'name + "_report.json"'in runner and'--report'in runner
  assert 'report'in runner and 'reports'in runner
  state[ar['path']]=body.encode();origin[ar['path']]={'kind':'artifact_created_by_prior_run15_recovered_from_read16','sequence':15,
    'actual_read_feedback_is_not_a_past_observation':True,'independent_CPU_JSON_identity':pin(cpu)}
 return state,origin

def source_and_state(candidates,api):
 report=[];sourcepins=[]
 for r in candidates:
  proof=r['original_R_provenance'];a=next(a for a in api if a['response_id']==proof['original_response_id']);d=sse(a['source_compatible_API_response'])
  region=proof['continuous_excerpt'];R=d['reasoning_content'];selected=R[region['start']:region['end']]
  assert proof['original_R_field']=='reasoning_content'and proof['source_original_R_sha256']==h(R)
  assert selected==r['messages'][2]['reasoning_content']and h(selected)==region['text_sha256']
  assert proof['source_response_pin']==a['source_compatible_API_response']
  assert r['messages'][2]['tool_calls']==d['tool_calls']
  call,args=api_args(a);assert h(call['function']['arguments'])==r['A_original_API_arguments_sha256']
  nativefile=verify(a['source_native']);native=[]
  for line in nativefile.read_text(encoding='utf-8-sig').splitlines():
   e=json.loads(line)
   if e.get('type')=='message'and isinstance(e.get('message'),dict):native.append(e['message'])
  nm=native[a['native_message_index']];assert h(json.dumps(nm,ensure_ascii=False,separators=(',',':'),sort_keys=True))==a['native_message_SHA_sorted']
  nc=next(b for b in nm['content']if b.get('type')=='toolCall'and b.get('id')==call['id'])
  na=nc['arguments'];na=json.loads(na)if isinstance(na,str)else na
  identical=na==args
  assert identical==r['A_original_native_record_arguments_identical']
  artifact=None;difference=None
  if not identical:
   assert (a['stage'],a['call_id'][:4])in {('B_make_report_02','0014'),('B_revision_report_01','0025')}
   assert r['API_native_body_exception_for_separate_root_review']is True and call['function']['name']=='write'
   assert na['path']==args['path']and'***'in na['content']and na['content']!=args['content']
   artifact=OLD/a['stage']/'workspace'/Path(args['path']).relative_to('/workspace')
   assert artifact.is_file()and artifact.read_bytes()==args['content'].encode()
   feedback_text='\n'.join(text(f['message'])for f in a['actual_native_tool_feedback'])
   assert str(len(args['content'].encode()))in feedback_text
   difference={'native_content_sha256':h(na['content']),'API_content_sha256':h(args['content']),
      'API_content_bytes':len(args['content'].encode()),'actual_written_artifact':pin(artifact),
      'same_call_written_byte_count_feedback_verified':True,'native_original_not_normalized':True}
  state,origins=reconstruct(a,api);assets={f['virtual_path']:f for f in r['functional_state_resource_manifest']}
  assert set(assets)==set(state),('POINT_STATE_FILE_SET_MISMATCH',r['id'],set(assets)^set(state))
  for path,ref in assets.items():assert verify(ref['actual_asset']).read_bytes()==state[path],('POINT_VERSION_MISMATCH',r['id'],path)
  payload=json.loads(r['messages'][1]['content']);visible={f['path']:f for f in payload['visible_file_contents']}
  assert {x['path']:x['sha256']for x in payload['actual_files']}=={k:h(v)for k,v in state.items()}
  for path,v in visible.items():assert path in state and v['content'].encode()==state[path]and h(v['content'])==v['sha256']
  suffix=r['id'].rsplit('-',1)[1];stage=a['stage']
  if stage=='B_revision_report_01':
   required={'/workspace/inputs/independent/actual_repair_feedback.json'}
   if suffix=='0017':required|={'/workspace/inputs/previous_skill/scripts/validate_pack.py','/workspace/inputs/previous_tests/run_tests.py',
      '/workspace/inputs/previous_tests/make_fixtures.py','/workspace/inputs/independent/legal_sources.json',
      '/workspace/inputs/independent/legal_ledger.json','/workspace/inputs/independent/legal_draft.json'}
   else:
    required.add('/workspace/outputs/skill/scripts/validate_pack.py')
    required.add('/workspace/outputs/tests/run_tests.py'if suffix=='0024'else'/workspace/outputs/tests/make_fixtures_extra.py')
  else:
   required={'/workspace/outputs/skill/scripts/validate_pack.py','/workspace/outputs/tests/make_fixtures.py'}
   if suffix=='0016':required.add('/workspace/outputs/tests/run_tests.py')
  assert required<=set(visible)
  # Parent-completed observations must be strictly earlier actual API calls.
  for p in payload['past_observations']:
   past=next(x for x in api if x['source_compatible_API_response']==p['original_response_pin'])
   assert past['stage']==a['stage']and int(past['call_id'][:4])<int(a['call_id'][:4])
   assert p['actual_past_tool_feedback']==[x['message']for x in past['actual_native_tool_feedback']]
  assert all(o.get('sequence',0)<int(a['call_id'][:4])for o in origins.values())
  if call['function']['name']=='write':assert args['path']not in state,'CURRENT_TARGET_WRITE_LEAKED_INTO_PRESTATE'
  assert r['loss_multiplier']==.25 and proof['kind']=='RECONTEXTUALIZED_ORIGINAL_COMPAT_R'
  assert r['is_original_native_request_identical']is False and r['actual_native_tool_dispatch']is False
  assert r['is_full_autonomous_execution_demonstration']is False and r['full_pipeline_or_skill_utility_approved']is False
  assert r['new_authored_R_tokens']==0 and proof['hidden_upstream_private_CoT_claimed']is False
  for z in r['target_R_zero_unicode_ranges']:
   assert h(selected[z['start']:z['end']])==z['text_sha256']and R[z['original_field_start']:z['original_field_end']]==selected[z['start']:z['end']]
  if ' to prove genericity'in selected:
   start=selected.index(' to prove genericity');assert any(z['start']<=start<start+len(' to prove genericity')<=z['end']for z in r['target_R_zero_unicode_ranges'])
  report.append({'id':r['id'],'source_SSE_pin':a['source_compatible_API_response'],'source_field_sha256':h(R),
    'continuous_excerpt':region,'source_SSE_chunks':d['SSE_chunks'],'native_args_identical':identical,
    'native_API_exception':difference,'point_state_assets':len(state),'required_full_visible_resources':sorted(required),
    'all_assets_rebuilt_from_startup_or_strictly_prior_literal_API_actions':True,
    'target15_artifact_exception':stage=='B_make_report_02'and suffix=='0016',
    'negative_R_characters':sum(z['end']-z['start']for z in r['target_R_zero_unicode_ranges']),
    'compatible_R_recontextualized_not_original_native_request':True,'not_gold_or_full_quality':True})
 return report

def same_masks(candidates,compiled):
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 toks={n:AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False)for n in ['primary_14b','control_8b']}
 template=toks['primary_14b'].chat_template
 template=template.replace('{%- if loop.index0 > ns.last_query_index %}','{%- if true %}')
 template=template.replace('{%- if loop.last or (not loop.last and reasoning_content) %}','{%- if true %}')
 template=template.replace("reasoning_content.strip('\\n')",'reasoning_content').replace("content.lstrip('\\n')",'content')
 assert template==load(COMPILED/'CAUSAL_TEMPLATE.json')['variant']
 render=_compile_jinja_template(template);output=[]
 for r in candidates:
  row=compiled[r['id']];assert row['messages']==r['messages']and row['tools']==r['tools']
  string=render.render(messages=r['messages'],tools=r['tools'],documents=None,add_generation_prompt=False,
      **dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
  encoded={k:t(string,add_special_tokens=False,return_offsets_mapping=True)for k,t in toks.items()}
  assert encoded['primary_14b']==encoded['control_8b']
  ids=encoded['primary_14b']['input_ids'];offsets=encoded['primary_14b']['offset_mapping'];n=len(ids)
  assert ids==row['input_ids']and n==row['total_tokens']<=32768 and n>16384
  assert h(string)==row['rendered_sha256']and u32sha(ids)==row['input_ids_sha256_u32le']
  a=string.rfind(HEADER);b=len(string);m=r['messages'][2];R=m['reasoning_content'];C=m.get('content')or''
  assert a>=0 and string[a:]==HEADER+OPEN+R+CLOSE+C+string[a+len(HEADER+OPEN+R+CLOSE+C):]
  assert string[a:].startswith(HEADER+OPEN+R+CLOSE+C)and string.endswith(END)
  body=a+len(HEADER);ra=body+len(OPEN);rb=ra+len(R);ca=rb+len(CLOSE);cb=ca+len(C);eos=b-len(END)
  geometry=[(body,ra,'F'),(ra,rb,'R'),(rb,ca,'F'),(ca,cb,'E'),(cb,eos,'A'),(eos,b,'F')]
  allowed=set(r['approved_components']);assert allowed=={'A'}
  positive_ranges=[]
  for f in r['approved_field_ranges']:
   assert f['message_index']==2 and f['field']=='reasoning_content'and h(R[f['start']:f['end']])==f['text_sha256']
   positive_ranges.append((ra+f['start'],ra+f['end']))
  spans=[];expected_labels=[-100]*n;expected_weights=[0.0]*n;expected_components=['']*n
  for token,(start,end)in enumerate(offsets):
   if not body<=start<end<=b:continue
   labels={label for lo,hi,label in geometry if start<hi and end>lo}
   if not labels:continue
   component=next(iter(labels))if len(labels)==1 else'R_BOUNDARY_MIXED'if'R'in labels else'MIXED'
   keep=component in allowed or any(lo<=start<end<=hi for lo,hi in positive_ranges)
   if not keep:continue
   expected_labels[token]=ids[token];expected_weights[token]=.25;expected_components[token]=component
   if spans and spans[-1][1]==token and spans[-1][2:]==[component,.25]:spans[-1][1]=token+1
   else:spans.append([token,token+1,component,.25])
  assert spans==row['supervision_spans'],('FULL_INDEPENDENT_MASK_SPAN_MISMATCH',r['id'])
  actual_labels=[-100]*n;actual_weights=[0.0]*n;actual_components=['']*n
  for start,end,component,w in row['supervision_spans']:
   for t in range(start,end):
    assert actual_labels[t]==-100
    actual_labels[t]=ids[t];actual_weights[t]=w;actual_components[t]=component
  assert (actual_labels,actual_weights,actual_components)==(expected_labels,expected_weights,expected_components)
  negatives=0
  for z in r['target_R_zero_unicode_ranges']:
   lo,hi=ra+z['start'],ra+z['end']
   for t,(start,end)in enumerate(offsets):
    if start<hi and end>lo:assert actual_labels[t]==-100 and actual_weights[t]==0.0;negatives+=1
  counts=Counter(c for c in expected_components if c)
  assert dict(counts)==row['supervised_tokens_by_component']and sum(counts.values())==row['supervised_tokens']
  assert h(js(spans))==row['supervision_spans_sha256']
  assert len(row['targets'])==1 and row['targets'][0]['owned_supervision_spans']==spans
  assert all(x==-100 for x in actual_labels[:next(i for i,(s,e)in enumerate(offsets)if s>=body)])
  output.append({'id':r['id'],'total_tokens':n,'positive_tokens':sum(counts.values()),'component_tokens':dict(counts),
    'independent_full_label_weight_component_positions_compared':n,'negative_or_crossing_tokens_checked':negatives,
    'separate_HF14_and_HF8_ids_and_offsets_equal':True,'full_mask_geometry_equal':True,
    'shifted_labels_definition':'labels[t]=input_ids[t] only at target positions; model/trainer shifts logits, no labels assigned to prompt',
    'input_ids_sha256_u32le':row['input_ids_sha256_u32le'],'mask_sha256':row['supervision_spans_sha256']})
 return output

def atom_strings(v):
 if isinstance(v,dict):
  for x in v.values():yield from atom_strings(x)
 elif isinstance(v,list):
  for x in v:yield from atom_strings(x)
 elif isinstance(v,str):yield v

def cross_bank(candidates,api):
 baseline=load(DATA/'TRAINING_MANIFEST.json');existing=[];sources=[]
 assert pin(DATA/'TRAINING_MANIFEST.json')['sha256']=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
 for f in baseline['actual_train_files']:
  p=DATA/f['path'];assert pin(p)['sha256']==f['sha256'];existing.extend(rows(p))
 for directory in [WORK/'early_reads/compiled01',WORK/'resource_review10/meeting_gen01/pruned03',WORK/'identity_semantic/compiled02']:
  report=load(directory/'COMPILATION_REPORT.json');sources.append(pin(directory/'COMPILATION_REPORT.json'))
  for f in report['files']:
   p=directory/f['path'];assert pin(p)['sha256']==f['sha256'];existing.extend(rows(p))
 assert len(existing)==619 and len({r['id']for r in existing})==619
 positive_calls={};a_alias=defaultdict(list);R_rows=[]
 for r in existing:
  meta=r['original_record_metadata'];aliases=set(atom_strings(meta))
  for target in r['targets']:
   if any(z[2]=='A'for z in target['owned_supervision_spans']):
    for c in r['messages'][target['message_index']].get('tool_calls',[]):positive_calls[c['id']]=r['id']
    for s in aliases:a_alias[s].append(r['id'])
   if any(z[2]=='R'for z in target['owned_supervision_spans']):R_rows.append((r,target,aliases))
 result=[];seenA=set();seenR=[]
 for c in candidates:
  proof=c['original_R_provenance'];owner=proof['source_response_pin']['sha256'];aowner=c['original_recorded_action_owner'];region=proof['continuous_excerpt']
  calls=c['messages'][2]['tool_calls'];assert not any(x['id']in positive_calls for x in calls)
  assert aowner not in a_alias,('ORIGINAL_A_OWNER_ALREADY_CREDITED',c['id'],a_alias.get(aowner))
  assert not any(x['id']in seenA for x in calls);seenA.update(x['id']for x in calls)
  full=next(a['original_R']for a in api if a['source_compatible_API_response']['sha256']==owner)
  collisions=[]
  for old,t,aliases in R_rows:
   md=old['original_record_metadata'];field=old['messages'][t['message_index']].get('reasoning_content','')or''
   # Canonical ownership first; exact full/continuous field matching is an
   # additional anti-join and is never used to merge unrelated generic text.
   matches=owner in aliases or aowner in aliases or(field and field==full)
   if not matches:continue
   start=full.find(field);assert start>=0,'SAME_R_OWNER_WITH_UNMAPPABLE_OLD_FIELD'
   ranges=md.get('approved_field_ranges',[]);approved=md.get('approved_components')
   prior=[(0,len(field))]if approved is None or'R'in approved else[(x['start'],x['end'])for x in ranges if x.get('field')=='reasoning_content'and x.get('message_index')==t['message_index']]
   for lo,hi in prior:
    if max(start+lo,region['start'])<min(start+hi,region['end']):collisions.append(old['id'])
  assert not collisions,('ORIGINAL_R_RANGE_ALREADY_CREDITED',c['id'],collisions)
  for oo,lo,hi in seenR:assert oo!=owner or max(lo,region['start'])>=min(hi,region['end'])
  seenR.append((owner,region['start'],region['end']))
  result.append({'id':c['id'],'R_source_response_owner':owner,'R_continuous_original_field_range':region,
      'A_original_native_owner':aowner,'A_positive_call_ids':[x['id']for x in calls],
      'prior619_positive_A_owner_or_call_collisions':0,'prior619_R_owner_field_credit_overlap':0,
      'within_five_R_field_or_A_call_overlap':0})
 return {'existing_positive_views_checked':619,'bank_report_pins':sources,'rows':result,
    'canonical_owner_and_original_field_geometry_not_sample_count_dedup':True}

def main():
 assert not(OUT/'INDEPENDENT_R5_SUMMARY_QA.json').exists(),'PRESERVE_OLD_INDEPENDENT_AUDIT'
 frozen=[pin(RAW),pin(COMPILED/'COMPILATION_REPORT.json'),pin(OUT/'CANDIDATES.proposed.raw.jsonl.gz')]
 allc=list(rows(RAW));api=list(rows(WORK/'reasoning_native10/API67_R_A_FEEDBACK.original.audit.jsonl.gz'))
 assert len(allc)==5
 report=load(COMPILED/'COMPILATION_REPORT.json');compiled={}
 for ref in report['files']:
  p=COMPILED/ref['path'];assert pin(p)['sha256']==ref['sha256'];frozen.append(pin(p))
  for r in rows(p):assert r['id']not in compiled;compiled[r['id']]=r
 assert set(compiled)=={r['id']for r in allc}
 phase='SOURCE_STATE'
 try:
  source=source_and_state(allc,api);save('INDEPENDENT_R5_SOURCE_STATE_QA.json',{'status':'PASS_INDEPENDENT_SSE_FIELD_API_ACTION_POINT_STATE_AND_VISIBLE_PREMISES','rows':source})
  phase='FULL_DUAL_TOKENIZER_MASK';tokens=same_masks(allc,compiled)
  assert sum(r['positive_tokens']for r in tokens)==14184 and sum(r['total_tokens']for r in tokens)==135175
  assert sum(r['component_tokens'].get('R',0)for r in tokens)==4326 and sum(r['component_tokens'].get('A',0)for r in tokens)==9858
  save('INDEPENDENT_R5_TOKEN_MASK_QA.json',{'status':'PASS_FULL_FIVE_HF14_HF8_AND_ALL_LABEL_WEIGHT_COMPONENT_POSITIONS','rows':tokens,
    'total_sequence_tokens_compared':135175,'positive_tokens':14184,'recorded_compatible_R_tokens':4326,'recorded_compatible_A_tokens':9858,
    'all_five_long_bucket_le32K':True,'tokenizer_calls':{'primary_14b':5,'control_8b':5},'no_weights_loaded':True})
  phase='CROSS_BANK_CREDIT';dedup=cross_bank(allc,api);save('INDEPENDENT_R5_CREDIT_DEDUP_QA.json',{'status':'PASS_R_A_CANONICAL_OWNER_AND_FIELD_RANGE_CROSS_BANK_ANTI_JOIN',**dedup})
  assert all(pin(f['path'])==f for f in frozen)
  summary={'status':'PASS_INDEPENDENT_R5_SOURCE_STATE_FULL_DUAL_TOKENIZER_MASK_AND_CROSS_BANK_CREDIT','rows':5,
    'sequence_tokens':135175,'positive_tokens':14184,'recorded_compatible_R_tokens':4326,'recorded_compatible_A_tokens':9858,
    'source_field_contiguous_verbatim':True,'all_mask_positions_independently_compared':True,
    'comparison_prior_positive_views':619,'main_or_candidate_or_compiled_files_modified':False,
    'recontextualized_weight':.25,'original_native_request_equivalence':False,'business_Q_or_KEEP_or_gold_approved':False,
    'new_business_calls':0,'weights_loaded':False,'training_started':False,'frozen_inputs':frozen,'script':pin(__file__)}
  save('INDEPENDENT_R5_SUMMARY_QA.json',summary);print(js(summary))
 except Exception as e:
  save('INDEPENDENT_R5_BLOCKING_QA.json',{'status':'BLOCKED_INDEPENDENT_R5_AUDIT','phase':phase,'exception_type':type(e).__name__,
      'detail':str(e),'script':pin(__file__),'main_or_candidate_modified':False,'weights_loaded':False,'training_started':False})
  raise

if __name__=='__main__':main()
