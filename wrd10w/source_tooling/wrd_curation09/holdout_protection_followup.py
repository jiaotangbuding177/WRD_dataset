"""Follow-up isolation scan with no writes to the sealed holdout/eval trees."""
import argparse,ast,collections,gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09';HOLD=WORK/'holdout'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def pin(p):return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def norm(s):return re.sub(r'\s+','',s)
def strings(x):
 if isinstance(x,str):
  yield x
  if x[:1] in '{[':
   try:yield from strings(json.loads(x))
   except (ValueError,TypeError):pass
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)

def protected_patterns():
 # Reuse only this research script's data-reading/fingerprint prefix AST.
 # Stop BEFORE main/staging scan and BEFORE any output statement. Never run
 # archived business code or execute a protected conversation instruction.
 path=ROOT/'research/data_prep/wrd_curation09/holdout_protected_vs_train.py'
 tree=ast.parse(path.read_text(encoding='utf-8-sig'));nodes=[]
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='manifest' for t in node.targets):break
  nodes.append(node)
 assert nodes and any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='patterns' for t in n.targets) for n in nodes)
 env={'__file__':str(path)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),env)
 assert len(env['forbidden'])==411 and env['users']==1927 and env['np']==7651
 return env['patterns'],{'sources':len(env['forbidden']),'users':env['users'],'patterns':env['np'],'definition_script':pin(path)}

def eval_patterns():
 catalog=read(HOLD/'TASK_CATALOG_ALL36_05.json');pats=collections.defaultdict(list);material_tasks=collections.defaultdict(set);n=0
 for task in catalog:
  if task['status']=='HOLD':continue
  packet=read(HOLD/task['task_input_pin']['path']);text=norm(packet['messages'][0]['content'])
  for offset in range(0,len(text)-159,40):
   a=text[offset:offset+160];pats[a[:40]].append((a,offset,{'kind':'EVAL_REQUEST','task_id':task['task_id']}));n+=1
  for m in task['material_aliases']:material_tasks[m['sha256']].add(task['task_id'])
 for h,tasks in material_tasks.items():
  text=norm((HOLD/'material_review/text'/f'{h}.txt').read_text(encoding='utf-8'))
  for offset in range(0,len(text)-159,40):
   a=text[offset:offset+160];pats[a[:40]].append((a,offset,{'kind':'EVAL_MATERIAL','sha256':h,'task_ids':sorted(tasks)}));n+=1
 return pats,{'tasks':26,'materials':len(material_tasks),'patterns':n,'catalog_pin':pin(HOLD/'TASK_CATALOG_ALL36_05.json')}

def scan(messages,patterns):
 matches=[]
 for mi,msg in enumerate(messages):
  text=norm('\n'.join(strings(msg)));found=collections.defaultdict(list);origins={}
  for i in range(len(text)-159):
   candidates=patterns.get(text[i:i+40])
   if candidates:
    actual=text[i:i+160]
    for expected,p,origin in candidates:
     if actual==expected:
      key=sha(json.dumps(origin,ensure_ascii=False,separators=(',',':'),sort_keys=True));origins[key]=origin
      found[key].append({'source_normalized_offset':p,'message_normalized_offset':i,'text':actual,'sha256':sha(actual)})
  for k,anchors in found.items():matches.append({'message_index':mi,'message_role':msg.get('role'),
   'message_SHA_sorted':sha(json.dumps(msg,ensure_ascii=False,separators=(',',':'),sort_keys=True)),
   'source_origin':origins[k],'anchors':anchors})
 return matches

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,default=WORK/'process/batch02/SCOPED_CANDIDATES_FINAL14.jsonl.gz')
 p.add_argument('--prepared',type=Path,default=WORK/'compiled_followup02/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz')
 p.add_argument('--compiled',type=Path,default=WORK/'compiled_followup02/compiled03');p.add_argument('--tag',default='FINAL14_01')
 args=p.parse_args();out=WORK/'protection_followup09';out.mkdir(exist_ok=True)
 protected,pinfo=protected_patterns();evaluation,einfo=eval_patterns()
 raw=rows(args.raw);prepared=rows(args.prepared);assert {r['id'] for r in raw}=={r['id'] for r in prepared}
 prepared_map={r['id']:r for r in prepared};compiled_map={};compiled_pins=[]
 if (args.compiled/'COMPILATION_REPORT.json').exists():
  report=read(args.compiled/'COMPILATION_REPORT.json')
  for f in report['files']:
   q=args.compiled/f['path'];assert sha(q.read_bytes())==f['sha256'];compiled_pins.append(pin(q));compiled_map.update({r['id']:r for r in rows(q)})
  assert set(compiled_map)==set(prepared_map)
 results=[]
 for r in raw:
  proof=r['source_context'];packet_path=Path(proof['path']);assert pin(packet_path)['sha256']==proof['sha256'] and packet_path.stat().st_size==proof['bytes']
  packet=read(packet_path);owner=packet['owner'];ctx=packet['original_context'];index=owner['source_message_index']
  assert owner['owner_id']==r['owner_id'] and ctx['episode_id']==r['original_episode_id'] and index==r['original_message_index']
  target=ctx['messages'][index];target_sha=sha(json.dumps(target,ensure_ascii=False,separators=(',',':'),sort_keys=True))
  assert target_sha==owner['target_original_SHA256_sorted']
  prefix=ctx['messages'][:index+1];state=prepared_map[r['id']]['messages']
  if compiled_map:assert compiled_map[r['id']]['messages']==state
  pm=scan(prefix,protected);em=scan(prefix,evaluation);ps=scan(state,protected);es=scan(state,evaluation)
  row={'id':r['id'],'owner_id':owner['owner_id'],'source_ids':r['source_ids'],'original_episode_id':ctx['episode_id'],
   'original_target_message_index':index,'original_target_SHA_sorted':target_sha,'packet_pin':pin(packet_path),
   'actual_prefix_message_count':index+1,'future_messages_excluded':len(ctx['messages'])-index-1,
   'original_system_capture_status':ctx.get('system_capture_status'),
   'protected_user_original_prefix_matches':pm,'eval26_original_prefix_matches':em,
   'protected_user_new_state_matches':ps,'eval26_new_state_matches':es,
   'prepared_state_SHA256':sha(json.dumps(state,ensure_ascii=False,separators=(',',':'),sort_keys=True)),
   'compiled_messages_same_as_prepared_when_available':bool(compiled_map),
   'status':'NEEDS_PRIVATE_VS_GENERIC_CLASSIFICATION' if pm or em or ps or es else 'NO_EXACT160_MATCH_NOT_GLOBAL_ANCESTRY_PROOF'}
  results.append(row)
 qa={'schema':'wrd09-followup-protected-eval-prefix-and-state-isolation-v1','tag':args.tag,
  'raw_pin':pin(args.raw),'prepared_pin':pin(args.prepared),'compiled_file_pins':compiled_pins,
  'protected_pattern_basis':pinfo,'eval_pattern_basis':einfo,'records':len(results),'rows':results,
  'compiled_actual_messages_checked':len(compiled_map),
  'critical_rule':'New functional state cannot erase ancestry of original code/action. Check actual original prefix through target, then new input state separately.',
  'limits':['No exact160 match does not exclude shorter/paraphrased/image-only/uncaptured ancestry or unknown resource producers.',
   'Protected source patterns use only original role=user; no protected thought, assistant answer, score or result is used for rubric or new labels.',
   'Missing original system remains missing. No original native-condition equivalence or model efficacy inferred.'],
  'holdout_or_eval_arrays_modified':False,'main_manifest_modified':False,'model_or_training_started':False,'script_pin':pin(Path(__file__).resolve())}
 path=out/(args.tag+'_ISOLATION_SCAN.json');assert not path.exists();path.write_bytes((json.dumps(qa,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'output':pin(path),'records':len(results),'compiled_checked':len(compiled_map),
  'matches':[{'id':r['id'],'prefix_protected':len(r['protected_user_original_prefix_matches']),'prefix_eval':len(r['eval26_original_prefix_matches']),'state_protected':len(r['protected_user_new_state_matches']),'state_eval':len(r['eval26_new_state_matches'])} for r in results if r['status'].startswith('NEEDS')]},ensure_ascii=False))

if __name__=='__main__':main()
