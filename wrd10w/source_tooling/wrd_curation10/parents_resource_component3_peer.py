"""Independent full token geometry and source/version checks for component3.

No compiler/pruner/verifier/trainer imports. The tiny controlled CPU snippets
only exercise the making-side script's literal assertion/exit blocks in a new
task-owned directory; no captured shell, subprocess, Agent or model is run.
"""
import os
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1')
from pathlib import Path
from array import array
from types import SimpleNamespace
import ast,collections,gzip,hashlib,json,sys
from jsonschema import Draft202012Validator
from transformers import AutoTokenizer
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity_semantic'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
HEADER='<|im_start|>assistant\n';END='<|im_end|>\n';OPEN='<think>\n';CLOSE='\n</think>\n\n'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig') if l.strip()]
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def intsha(x):
 a=array('I',x)
 if sys.byteorder!='little':a.byteswap()
 return sha(a.tobytes())
def text(m):
 body=m.get('content','')
 return body if isinstance(body,str) else '\n'.join(x.get('text','') for x in body if x.get('type')=='text')
def original_replace_pairs(command):
 lines=command.splitlines();start=next(i for i,x in enumerate(lines) if 'python - <<' in x)
 end=next(i for i in range(start+1,len(lines)) if lines[i].strip()=='EOF')
 tree=ast.parse('\n'.join(lines[start+1:end]));constants={};pairs=[]
 for node in tree.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   try:constants[node.targets[0].id]=ast.literal_eval(node.value)
   except (ValueError,TypeError):pass
  for call in ast.walk(node):
   if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='replace':
    assert len(call.args)==2
    values=[]
    for arg in call.args:values.append(constants[arg.id] if isinstance(arg,ast.Name) else ast.literal_eval(arg))
    assert all(isinstance(x,str) for x in values);pairs.append(tuple(values))
 return pairs
def case_body(tree):
 outer=next(x for x in tree.body if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='prog')
 inner=next(x for x in outer.body if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='case')
 return inner.body
def bounded_stderr_case(code,outdir,returncode):
 tree=ast.parse(code);body=case_body(tree);start=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='exit_ok')
 end=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='case_ok')
 module=ast.fix_missing_locations(ast.Module(body=body[start:end+1],type_ignores=[]))
 outdir.mkdir(parents=True,exist_ok=False)
 def check_assertion(a,where):return a['value'] in (Path(where)/a['path']).read_text(encoding='utf-8')
 env={'os':os,'cp':SimpleNamespace(returncode=returncode,stdout='authentic_stdout',stderr='authentic_error_detail'),
  'case':{'expected_exit':2,'assertions':[{'kind':'contains','path':'stderr.txt','value':'authentic_error_detail'}]},
  'outdir':str(outdir),'check_assertion':check_assertion,'ok_all':True}
 try:
  exec(compile(module,'<bounded-original-making-side-exit-block>','exec'),env)
  error=None
 except Exception as e:error=type(e).__name__
 return {'exception':error,'exit_ok':env.get('exit_ok'),'case_ok':env.get('case_ok'),
  'stderr_file':(outdir/'stderr.txt').exists(),'stderr_exact':(outdir/'stderr.txt').read_text(encoding='utf-8')=='authentic_error_detail' if (outdir/'stderr.txt').exists() else False}
def source_check(raw):
 v=[(OUT/n).read_text(encoding='utf-8') for n in ['verifier_before_path_fix.py','verifier_after_path_fix.py','verifier_after_stderr_fix.py']]
 for n,s in zip(['before','after_path','after_stderr'],v):ast.parse(s)
 context=rows(Path(raw[0]['evidence']['original_context']['path']))[0]
 assert sha(Path(raw[0]['evidence']['original_context']['path']).read_bytes())==raw[0]['evidence']['original_context']['sha256']
 for j,index in enumerate([57,59]):
  call=next(x for x in context['messages'][index]['content'] if x.get('type')=='toolCall')
  pairs=original_replace_pairs(call['arguments']['command'])
  target=raw[j]['messages'][-1]['tool_calls'];assert len(target)==1
  args=target[0]['function']['arguments'];assert target[0]['function']['name']=='edit'
  edits=args['edits'];assert len(edits)==(2 if j==0 else 1)
  assert pairs==[(e['oldText'],e['newText']) for e in edits]
  s=v[j];positions=[]
  for e in edits:
   assert s.count(e['oldText'])==1;positions.append((s.index(e['oldText']),s.index(e['oldText'])+len(e['oldText'])))
  assert all(a[1]<=b[0] for a,b in zip(sorted(positions),sorted(positions)[1:]))
  for e in edits:s=s.replace(e['oldText'],e['newText'])
  assert s==v[j+1] and sha(v[j])==raw[j]['version_before_sha256'] and sha(s)==raw[j]['version_after_sha256']
  assert v[j] in raw[j]['messages'][1]['content']
  past=text(context['messages'][index-1]);assert past in raw[j]['messages'][1]['content']
  for f in raw[j]['actual_feedback_for_credit_only']:
   assert text(context['messages'][f['native_message_index']])==f['text']
   assert f['text'] not in raw[j]['messages'][1]['content']
  assert raw[j]['new_authored_R'] and not raw[j]['teacher_original_R_supervised']
 physical=Path(raw[0]['evidence']['original_final_verifier']['path'])
 assert v[-1].encode()==physical.read_bytes()
 assert ast.dump(ast.parse('sys.exit(0 if ok_all else 1)').body[0])==ast.dump(ast.parse(v[-1]).body[-1])
 # The repair neither rewrites expected_exit nor case/composition assertions.
 for code in v:
  assert 'cp.returncode == case["expected_exit"]' in code
  assert 'case_ok = exit_ok and all(c["ok"] for c in checks)' in code
  assert 'sys.exit(0 if ok_all else 1)' in code
 h=raw[2];original=rows(Path(h['evidence']['original_context']['path']))[0]
 msg=original['messages'][h['original_native_message_index']];full=text(msg)
 assert sha(js(msg))==h['original_visible_D_source_message_sha256']
 a,b=h['original_visible_D_unicode_start'],h['original_visible_D_unicode_end']
 assert full[a:b]==h['messages'][-1]['content'] and sha(full[a:b])==h['original_visible_D_sha256']
 assert h['approved_components']==['D'] and not h['new_authored_R'] and not h['messages'][-1]['reasoning_content']
 assert 'HOLD' in full[a:b] and not h['is_qualified_KEEP_demonstration']
 episode=Path(original['source_native']['path']).parent.parent
 missing=[n for n in ['evidence.json','resource_manifest.json'] if not (episode/'workspace/outputs'/n).exists()]
 assert len(missing)==2
 assert not any('preflight' in c.get('arguments',{}).get('command','') for m in original['messages'] for c in m.get('content',[]) if isinstance(c,dict) and c.get('type')=='toolCall' and c.get('name')=='exec')
 # New own scratch work. Only literal no-subprocess exit blocks are executed.
 base=OUT/'peer3_checks';assert not base.exists();base.mkdir()
 old=bounded_stderr_case(v[1],base/'old_expected_failure',2)
 new=bounded_stderr_case(v[2],base/'new_expected_failure',2)
 wrong=bounded_stderr_case(v[2],base/'new_wrong_exit',0)
 assert old['exception']=='FileNotFoundError' and not old['stderr_file']
 assert new['exception'] is None and new['case_ok'] and new['stderr_exact']
 assert wrong['exception'] is None and not wrong['case_ok'] and not wrong['exit_ok'] and wrong['stderr_exact']
 src={'status':'PASS_INDEPENDENT_VERSION_LITERAL_CHAIN_FEEDBACK_HOLD_AND_ERROR_EXIT',
  'literal_edits_per_call':[2,1],'all_literal_strings_match_original_native_exec':True,
  'both_versions_rebuilt_exactly':True,'final_matches_archived4318_bytes':True,
  'expected_failure_preserved_stderr':new,'before_bug_reproduced':old,'wrong_exit_still_fails':wrong,
  'HOLD_original_visible_body_verbatim':True,'HOLD_missing_actual_files':missing,
  'HOLD_no_recorded_exec_preflight':True,'old_wrong_ABI_is_new_curator_projection_error_not_original_teacher_error':True,
  'original_R_count':0,'business_Q_or_whole_KEEP_approved':False,
  'executed_scope':'Only bounded literal making-side assertion/exit blocks, no captured subprocess/shell/Agent/model.',
  'source_pins':[pin(physical),pin(Path(h['evidence']['original_context']['path']))],
  'weights_loaded':False,'training_started':False}
 save(OUT/'COMPONENT3_SOURCE_PEER_QA.json',src)
 return src
def token_check(raw):
 compiled=OUT/'compiled02';report=load(compiled/'COMPILATION_REPORT.json')
 byid={r['id']:r for r in raw};toks={n:AutoTokenizer.from_pretrained(ASSETS/n,local_files_only=True,trust_remote_code=False) for n in ['primary_14b','control_8b']}
 templates={}
 for n,tok in toks.items():
  t=tok.chat_template.replace('{%- if loop.index0 > ns.last_query_index %}','{%- if true %}').replace('{%- if loop.last or (not loop.last and reasoning_content) %}','{%- if true %}')
  t=t.replace("reasoning_content.strip('\\n')",'reasoning_content').replace("content.lstrip('\\n')",'content')
  assert sha(t)==report['tokenizer_proof']['causal_template_sha256'];templates[n]=t
 results=[];counts=collections.Counter();seen=set()
 for ref in report['files']:
  p=compiled/ref['path'];assert p.stat().st_size==ref['bytes'] and sha(p.read_bytes())==ref['sha256']
  for row in rows(p):
   rid=row['id'];assert rid not in seen and rid in byid;seen.add(rid);r=byid[rid]
   assert row['messages']==r['messages'] and row['tools']==r['tools']
   def render(name,msgs):return toks[name].apply_chat_template(msgs,tools=row['tools'],chat_template=templates[name],tokenize=False,add_generation_prompt=False,enable_thinking=False)
   texts={n:render(n,row['messages']) for n in toks};assert len(set(texts.values()))==1;text=texts['primary_14b']
   enc={n:tok(text,add_special_tokens=False,return_offsets_mapping=True) for n,tok in toks.items()};assert enc['primary_14b']==enc['control_8b']
   ids=enc['primary_14b']['input_ids'];offsets=enc['primary_14b']['offset_mapping'];assert ids==row['input_ids'] and intsha(ids)==row['input_ids_sha256_u32le']
   assert len(ids)==row['total_tokens']<=16384 and sha(text)==row['rendered_sha256']
   pos={}
   for i,m in enumerate(row['messages']):
    if m['role']!='assistant':continue
    prefix=render('primary_14b',row['messages'][:i]);through=render('primary_14b',row['messages'][:i+1])
    assert text.startswith(through) and through.startswith(prefix)
    a,b=len(prefix),len(through);assert text[a:b].startswith(HEADER+OPEN+m.get('reasoning_content','')+CLOSE+(m.get('content') or '')) and text[a:b].endswith(END)
    pos[i]=(a,b)
   tmap={t['message_index']:t for t in row['targets']};assert set(tmap)==set(pos)
   for i,(a,b) in pos.items():assert tmap[i]['rendered_assistant_span']==[a,b]
   assert row['assistant_generation_spans']==[list(pos[i]) for i in pos]
   approved=r['supervision_message_indices'];assert len(approved)==1;index=approved[0]
   a,b=pos[index];m=row['messages'][index];ra=a+len(HEADER)+len(OPEN);rb=ra+len(m.get('reasoning_content',''));ca=rb+len(CLOSE);cb=ca+len(m.get('content') or '');end_a=b-len(END)
   wanted=[]
   for n,(u,v) in enumerate(offsets):
    c=None
    if ra<=u<v<=rb and 'R' in r['approved_components']:c='R'
    if ca<=u<v<=cb and 'D' in r['approved_components']:c='D'
    if cb<=u<v<=end_a and 'A' in r['approved_components']:c='A'
    if c is None:continue
    w=r['loss_multiplier']
    if wanted and wanted[-1][1]==n and wanted[-1][2:]==[c,w]:wanted[-1][1]=n+1
    else:wanted.append([n,n+1,c,w])
   assert wanted==row['supervision_spans'] and wanted==tmap[index]['owned_supervision_spans']
   components=collections.Counter()
   for x,y,c,w in wanted:components[c]+=y-x;assert w==0.25
   assert dict(components)==row['supervised_tokens_by_component'] and sum(components.values())==row['supervised_tokens']
   proof=r['tool_schema_provenance'];capture=load(Path(proof['path']));assert sha(Path(proof['path']).read_bytes())==proof['sha256'];registry={t['function']['name']:t['function'] for t in capture['tools']}
   for call in m.get('tool_calls',[]):
    name=call['function']['name'];args=call['function']['arguments'];assert not list(Draft202012Validator(registry[name]['parameters']).iter_errors(args))
    if rid.endswith('path-repair'):assert len(args['edits'])==2
   counts.update({'sequences':1,'targets':1,'input_tokens':len(ids),'supervised_tokens':sum(components.values())})
   for c,x in components.items():counts['component_'+c]+=x
   results.append({'id':rid,'tokens':len(ids),'positive':sum(components.values()),'components':dict(components),
    'HF_dual_tokenizer_render_offsets_and_ids_exact':True,'full_positive_mask_geometry_exact':True,
    'all_prompt_role_controls_and_other_fields_zero_loss':True,'edits_in_single_call':len(m['tool_calls'][0]['function']['arguments']['edits']) if m.get('tool_calls') else 0})
 assert set(byid)==seen and counts==collections.Counter({'sequences':3,'targets':3,'input_tokens':18557,'supervised_tokens':705,'component_R':79,'component_A':555,'component_D':71})
 assert 'torch' not in sys.modules
 result={'status':'PASS_COMPONENT3_DUAL_TOKENIZERS_EXACT_FULL_MASK_AND_TOOL_ABI',
  'counts':dict(counts),'records':results,'original_R':0,'new_authored_R':79,'original_visible_D':71,
  'compiled_report_pin':pin(compiled/'COMPILATION_REPORT.json'),'frozen_files':[{'path':str(compiled/r['path']),'bytes':r['bytes'],'sha256':r['sha256']} for r in report['files']],
  'raw_pin':pin(OUT/'CANDIDATES_TOOL_ABI_V2.raw.jsonl.gz'),'script_pin':pin(Path(__file__)),
  'compiler_pruner_verifier_trainer_imported':False,'weights_or_forward_backward_native':False,'torch_imported':False}
 save(OUT/'COMPONENT3_TOKEN_PEER_QA.json',result)
 return result
if __name__=='__main__':
 rawfile=OUT/'CANDIDATES_TOOL_ABI_V2.raw.jsonl.gz';assert sha(rawfile.read_bytes())=='6f097fec7b1d18d8f89ab4f4e080c22accdbdbeb4069226ee7dbc4dd023215fd'
 r=rows(rawfile);assert len(r)==3;source=source_check(r);token=token_check(r)
 print(json.dumps({'source':source['status'],'token':token['status'],'counts':token['counts'],
  'source_receipt':pin(OUT/'COMPONENT3_SOURCE_PEER_QA.json'),'token_receipt':pin(OUT/'COMPONENT3_TOKEN_PEER_QA.json')},ensure_ascii=False))
