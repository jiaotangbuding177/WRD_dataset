"""Recover exact 706+615 owner bodies and contexts without executing payload code.

Literal classification is separate from semantic credit. No model/agent loop,
training, data admission or invented reasoning is performed by this script.
"""
from pathlib import Path
from collections import Counter,defaultdict
import ast,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261030_wrd_gap08/corpus'
OUT=ROOT/'output/20261031_wrd_curation09/process'
AUDIT=ROOT/'output/20261031_wrd_readiness_plan/reviews/corpus_audit.json'
GROUPS=['other_business_semantic_pending','business_protocol_auxiliary']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(t):return hashlib.sha256(t.encode()).hexdigest()
def js(v,sort=False):return json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=sort)
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def gzsave(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as g:
   for r in data:g.write((js(r)+'\n').encode())
def blocks(m):
 c=m.get('content',[])
 return [{'type':'text','text':c}]if isinstance(c,str)else c
def text(m):return '\n'.join(b.get('text','')for b in blocks(m)if isinstance(b,dict)and b.get('type')=='text')
def extract_heredocs(command):
 # Exact source substrings. No shell evaluation, unescaping, import or exec.
 result=[];lines=command.splitlines(keepends=True);positions=[];offset=0
 for line in lines:positions.append(offset);offset+=len(line)
 for i,line in enumerate(lines):
  match=re.search(r"<<\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1\s*$",line.rstrip('\r\n'))
  if not match:continue
  delimiter=match[2];end=next((j for j in range(i+1,len(lines))if lines[j].strip()==delimiter),None)
  if end is None:continue
  start=positions[i]+len(line);stop=positions[end];code=command[start:stop]
  filematch=re.search(r'(?:cat|tee)\s*>\s*([^\s]+)',line)
  dest=filematch[1].strip('"\'')if filematch else None
  language='python'if ('python'in line or(dest and dest.endswith('.py')))else'javascript'if ('node'in line or(dest and dest.endswith(('.js','.jsx','.tsx','.ts'))))else'shell'if dest and dest.endswith('.sh')else'text'
  syntax=None
  if language=='python':
   try:ast.parse(code);syntax='AST_PARSE_PASS_ONLY_NOT_EXECUTION'
   except SyntaxError as e:syntax={'status':'AST_PARSE_ERROR','line':e.lineno,'offset':e.offset}
  result.append({'destination_if_explicit':dest,'language':language,'command_unicode_start':start,'command_unicode_end':stop,'text_sha256':h(code),'characters':len(code),'syntax':syntax,'code':code})
 return result

def main():
 assert not (OUT/'RECOVERY_RECEIPT.json').exists(),'preserve previous recovery'
 OUT.mkdir(parents=True,exist_ok=True)
 audit=json.loads(AUDIT.read_text(encoding='utf-8'));queue=audit['disjoint_primary_owner_work_queue']
 groups={i:k for k in GROUPS for i in queue[k]['owner_ids']};assert len(groups)==1321
 owner={r['canonical_owner_id']:r for r in rows(BASE/'CORPUS_OWNER_COVERAGE.native.jsonl.gz')if r['canonical_owner_id']in groups};assert len(owner)==1321
 wanted={r['episode_id']for r in owner.values()};contexts={}
 for name in ['audit_inputs/native1843.contexts.original.jsonl.gz','EXTRA_NATIVE_CONTEXTS.original.jsonl.gz']:
  for c in rows(BASE/name):
   if c['episode_id']in wanted:
    assert c['episode_id']not in contexts;contexts[c['episode_id']]=c
 assert set(contexts)==wanted
 gzsave(OUT/'ORIGINAL_CONTEXTS_343.audit.jsonl.gz',[contexts[i]for i in sorted(contexts)])
 outputs=[];toolcounts=defaultdict(Counter);classcounts=defaultdict(Counter);code_index=[]
 for oid in sorted(owner):
  r=owner[oid];c=contexts[r['episode_id']];index=r['source_message_index'];m=c['messages'][index]
  assert h(js(m,True))==r['original_message_sha256_sorted']
  assert h(js(m))==r['original_message_sha256_insertion_order']
  calls=[b for b in blocks(m)if isinstance(b,dict)and b.get('type')=='toolCall'];bycall={a['id']:a for a in calls}
  observed=[]
  for j,f in enumerate(c['messages'][index+1:],start=index+1):
   if f.get('role')=='assistant':break
   if f.get('role')=='toolResult'and f.get('toolCallId')in bycall:observed.append({'message_index':j,'message':f,'message_sha256':h(js(f,True))})
  literals=[]
  for call in calls:
   toolcounts[groups[oid]][call['name']]+=1
   args=call.get('arguments',{});args=json.loads(args)if isinstance(args,str)else args
   if call['name']=='exec':
    for k,x in enumerate(extract_heredocs(args.get('command',''))):
     code=x.pop('code');suffix={'python':'.py','javascript':'.js','shell':'.sh'}.get(x['language'],'.txt')
     p=OUT/'inline_programs'/oid/(str(k)+suffix);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(code.encode())
     assert sha(p)==x['text_sha256'];ref={**x,'path':str(p.resolve()),'owner_id':oid,'call_id':call['id'],'episode_id':r['episode_id'],'source_ids':r['source_ids'],'route_id':r['route_id']};literals.append(ref);code_index.append(ref)
  names=[x['name']for x in calls]
  if not calls:literal_kind='ASSISTANT_TEXT_ONLY'
  elif all(n in {'read','ls'}for n in names):literal_kind='LITERAL_READ_LIST_ONLY'
  elif literals:literal_kind='EXEC_WITH_EXACT_INLINE_RESOURCE_BODY'
  elif any(n in {'write','edit','apply_patch'}for n in names):literal_kind='EXPLICIT_RESOURCE_WRITE_OR_EDIT'
  elif any(n in {'web_search','web_fetch','browser'}for n in names):literal_kind='WEB_OBSERVATION_OR_INTERACTION'
  elif any(n in {'ask_user','secrets'}for n in names):literal_kind='CLARIFICATION_OR_AUTHORIZATION_BOUNDARY_TOOL'
  elif any(n in {'exec','process'}for n in names):literal_kind='COMMAND_OR_EXISTING_PROCESS_ACTION'
  else:literal_kind='OTHER_RECORDED_NATIVE_ACTION'
  classcounts[groups[oid]][literal_kind]+=1
  outputs.append({'owner_id':oid,'queue':groups[oid],'episode_id':r['episode_id'],'source_message_index':index,'route_id':r['route_id'],
   'source_ids':r['source_ids'],'source_disposition':r['source_disposition'],'current_source_statuses':r['current_source_statuses'],
   'original_owner_ledger':r,'target_message_original':m,'target_original_SHA256_sorted':h(js(m,True)),
   'input_context_ref':{'file':'ORIGINAL_CONTEXTS_343.audit.jsonl.gz','episode_id':r['episode_id'],'messages_prefix_end_exclusive':index},
   'immediate_original_tool_feedback':observed,'following_messages_remain_in_original_context':True,
   'literal_target_classification':literal_kind,'actual_tool_names':names,'literal_inline_programs':literals,
   'native_readable_reasoning_blocks':r.get('native_readable_R_blocks',0),'text_characters':len(text(m)),
   'semantic_status':'NOT_INFERRED_FROM_LITERAL_CLASSIFICATION_OR_EXIT_STATUS','training_admitted':False,'positive_loss':0})
 gzsave(OUT/'OWNER1321_EXACT_CONTENT.audit.jsonl.gz',outputs)
 save(OUT/'INLINE_PROGRAM_INDEX.json',{'status':'EXACT_SOURCE_SUBSTRING_RECOVERY_NOT_SEMANTIC_ADMISSION','programs':code_index})
 save(OUT/'LITERAL_CLASSIFICATION1321.json',{'status':'ALL_LITERAL_CLASSES_NOT_SEMANTIC_VERDICTS','queue_counts':{k:sum(r['queue']==k for r in outputs)for k in GROUPS},'tool_counts':{k:dict(v)for k,v in toolcounts.items()},'classes':{k:dict(v)for k,v in classcounts.items()},'semantic_admissions':0})
 # Packets retain entire original state. No future observation is represented as prior input.
 priority=[]
 for r in outputs:
  if r['literal_inline_programs']or r['literal_target_classification']=='EXPLICIT_RESOURCE_WRITE_OR_EDIT':
   score=sum(x['characters']for x in r['literal_inline_programs']);priority.append((score,r))
 for score,r in sorted(priority,key=lambda z:(-z[0],z[1]['owner_id'])):
  c=contexts[r['episode_id']];packet={'schema':'wrd09-exact-owner-review-packet','owner':r,'original_context':c,
   'state_before_target':c['messages'][:r['source_message_index']],
   'target_and_following_messages':c['messages'][r['source_message_index']:],
   'future_observations_for_grading_only_not_input':True,'training_admitted':False,'source_scope_not_rechecked_by_this_literal_recovery':True}
  save(OUT/'packets'/f'{r["owner_id"]}.json',packet)
 refs=[]
 for p in sorted(OUT.rglob('*')):
  if p.is_file()and p.name!='RECOVERY_RECEIPT.json':refs.append({'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 report={'status':'PASS_EXACT_RECOVERY1321_343_CONTEXTS_NO_EXECUTION_NO_ADMISSION','owners':len(outputs),'original_contexts':len(contexts),
  'inline_resource_bodies':len(code_index),'priority_resource_packets':len(priority),'all_owner_target_two_original_message_SHA_matches':True,
  'files':refs,'inputs':{'corpus_audit':sha(AUDIT),'owner_ledger':sha(BASE/'CORPUS_OWNER_COVERAGE.native.jsonl.gz')},
  'script_sha256':sha(__file__),'training_started':False,'model_or_business_calls':0,'new_positive_targets':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
 save(OUT/'RECOVERY_RECEIPT.json',report)
 print(json.dumps({k:report[k]for k in ['status','owners','original_contexts','inline_resource_bodies','priority_resource_packets','new_positive_targets']}))
if __name__=='__main__':main()
