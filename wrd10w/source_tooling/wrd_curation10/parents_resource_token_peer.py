"""Independent full-geometry token/mask QA of root's pruned meeting export.

Does not import the compiler, pruner, main verifier or trainer. Loads each
local tokenizer independently, renders the declared causal variant directly
through HF, independently reconstructs every allowed/excluded character span,
then compares the entire positive-token set and coalesced geometry exactly.
"""
import os
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1')
from pathlib import Path
from array import array
import argparse,collections,gzip,hashlib,json,re,sys
from transformers import AutoTokenizer

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation10/resource_review10/meeting_gen01'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
HEADER='<|im_start|>assistant\n';END='<|im_end|>\n';OPEN='<think>\n';CLOSE='\n</think>\n\n'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig') if l.strip()]
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def intsha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return sha(a.tobytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--compiled',type=Path,default=OUT/'pruned03');a=ap.parse_args()
 report=load(a.compiled/'COMPILATION_REPORT.json')
 rawfile=OUT/'CANDIDATES.raw.jsonl.gz';raw={r['id']:r for r in rows(rawfile)}
 assert sha(rawfile.read_bytes())=='ea293bb1c5f6dd96401d1b4dab139703b116ef7559f49b24eeb336b949d553e5'
 toks={name:AutoTokenizer.from_pretrained(ASSETS/name,local_files_only=True,trust_remote_code=False) for name in ['primary_14b','control_8b']}
 templates={}
 for name,tok in toks.items():
  t=tok.chat_template
  t=t.replace('{%- if loop.index0 > ns.last_query_index %}','{%- if true %}')
  t=t.replace('{%- if loop.last or (not loop.last and reasoning_content) %}','{%- if true %}')
  t=t.replace("reasoning_content.strip('\\n')",'reasoning_content').replace("content.lstrip('\\n')",'content')
  assert sha(t)==report['tokenizer_proof']['causal_template_sha256']
  templates[name]=t
 summary=[];counts=collections.Counter();all_ids=set();crossing_negative_tokens=0
 for ref in report['files']:
  p=a.compiled/ref['path'];assert p.stat().st_size==ref['bytes'] and sha(p.read_bytes())==ref['sha256']
  for row in rows(p):
   rid=row['id'];assert rid in raw and rid not in all_ids;all_ids.add(rid);original=raw[rid]
   assert row['messages']==original['messages'] and row['tools']==original['tools']
   texts={name:tok.apply_chat_template(row['messages'],tools=row['tools'],chat_template=templates[name],
    tokenize=False,add_generation_prompt=False,enable_thinking=False) for name,tok in toks.items()}
   assert texts['primary_14b']==texts['control_8b'];text=texts['primary_14b']
   encoded={name:tok(text,add_special_tokens=False,return_offsets_mapping=True) for name,tok in toks.items()}
   x=encoded['primary_14b'];y=encoded['control_8b'];assert x==y
   ids=x['input_ids'];offsets=x['offset_mapping']
   assert ids==row['input_ids'] and len(ids)==row['total_tokens']<16385
   assert intsha(ids)==row['input_ids_sha256_u32le'] and sha(text)==row['rendered_sha256']
   assert len(offsets)==len(ids)
   assistants=[i for i,m in enumerate(row['messages']) if m['role']=='assistant']
   starts=[m.start() for m in re.finditer(re.escape(HEADER),text)]
   assert len(starts)==len(assistants),'AMBIGUOUS_ASSISTANT_HEADER_GEOMETRY'
   positions={}
   for i,start in zip(assistants,starts):
    end=text.index(END,start)+len(END);m=row['messages'][i]
    prefix=HEADER+OPEN+m.get('reasoning_content','')+CLOSE+(m.get('content') or '')
    assert text[start:end].startswith(prefix)
    positions[i]=(start,end)
   targets_by_i={t['message_index']:t for t in row['targets']}
   assert set(targets_by_i)==set(assistants)
   assert row['assistant_generation_spans']==[list(positions[i]) for i in assistants]
   for i,(start,end) in positions.items():assert targets_by_i[i]['rendered_assistant_span']==[start,end]
   approved=original['supervision_message_indices'];assert len(approved)==1
   index=approved[0];start,end=positions[index];m=row['messages'][index]
   ra=start+len(HEADER)+len(OPEN);rb=ra+len(m.get('reasoning_content',''))
   ca=rb+len(CLOSE);cb=ca+len(m.get('content') or '');end_a=end-len(END)
   assert m.get('content')=='' and len(m['tool_calls'])==1
   call=m['tool_calls'][0];args=call['function']['arguments'];assert isinstance(args,dict)
   # Independent dictionary/field location, not supplied root exclusion coords.
   decoder=json.JSONDecoder();found=[]
   for pos in range(cb,end_a):
    if text[pos]!='{':continue
    try:value,n=decoder.raw_decode(text[pos:end_a])
    except ValueError:continue
    if value==args:found.append((pos,pos+n))
   assert len(found)==1;lo,hi=found[0]
   argument_text=text[lo:hi];ex=[]
   field=original.get('target_exclusion_argument_field','content')
   body=args.get(field)
   source_ex=original.get('target_code_unicode_exclusions',[])
   if source_ex:
    encoded_body=json.dumps(body,ensure_ascii=False)
    assert argument_text.count(encoded_body)==1
    base=lo+argument_text.index(encoded_body)+1
    for r in source_ex:
     u,v=r['start'],r['end'];assert sha(body[u:v])==r['text_sha256']
     a0=base+len(json.dumps(body[:u],ensure_ascii=False))-2
     b0=base+len(json.dumps(body[:v],ensure_ascii=False))-2
     assert text[a0:b0]==json.dumps(body[u:v],ensure_ascii=False)[1:-1]
     ex.append((a0,b0))
   metadata=row['original_record_metadata']
   assert metadata.get('target_code_unicode_exclusions',[])==source_ex
   root_ex=metadata.get('target_excluded_rendered_ranges',[])
   assert [(r['start'],r['end']) for r in root_ex]==ex
   if ex:
    assert metadata['serialized_tool_argument_rendered_span']=={'start':lo,'end':hi,'text_sha256':sha(argument_text)}
   expected=[];cross=0
   for token,(a0,b0) in enumerate(offsets):
    comp=None
    if ra<=a0<b0<=rb and 'R' in original['approved_components']:comp='R'
    if cb<=a0<b0<=end_a and 'A' in original['approved_components']:comp='A'
    intersects=any(a0<y and b0>x for x,y in ex)
    if intersects:
     if any((a0<x<b0) or (a0<y<b0) for x,y in ex):cross+=1
     comp=None
    if comp is None:continue
    w=original['loss_multiplier']
    if expected and expected[-1][1]==token and expected[-1][2:]==[comp,w]:expected[-1][1]=token+1
    else:expected.append([token,token+1,comp,w])
   assert expected==row['supervision_spans'],'FULL_POSITIVE_GEOMETRY_MISMATCH'
   positive_targets=[t for t in row['targets'] if t['owned_supervision_spans']]
   assert len(positive_targets)==1 and positive_targets[0]['message_index']==index
   assert positive_targets[0]['owned_supervision_spans']==expected
   assert all(not t['owned_supervision_spans'] and t['supervised_tokens']==0 for t in row['targets'] if t['message_index']!=index)
   component=collections.Counter()
   labels=[-100]*len(ids);weights=[0.0]*len(ids)
   for a0,b0,c,w in expected:
    component[c]+=b0-a0
    for n in range(a0,b0):labels[n]=ids[n];weights[n]=w
   assert dict(component)==row['supervised_tokens_by_component']
   assert sum(component.values())==row['supervised_tokens']
   assert sum(x!=-100 for x in labels)==row['supervised_tokens']
   if len(assistants)>1:
    assert rid=='resource10-meeting-reconciled37-shell-retry'
    for i,(x0,y0) in positions.items():
     if i==index:continue
     assert all(labels[n]==-100 and weights[n]==0 for n,(u,v) in enumerate(offsets) if u<y0 and v>x0),'PREVIOUS_FAILED_ASSISTANT_HAS_LOSS'
   counts.update({'sequences':1,'targets':1,'input_tokens':len(ids),'supervised_tokens':sum(component.values()),
    'rendered_assistant_frames':len(assistants),'zero_loss_context_assistant_frames':len(assistants)-1,'negative_ranges':len(ex)})
   for c,v in component.items():counts['component_'+c]+=v
   crossing_negative_tokens+=cross
   summary.append({'id':rid,'tokens':len(ids),'positive_tokens':sum(component.values()),'components':dict(component),
    'full_expected_positive_geometry_equal':True,'negative_ranges':len(ex),'crossing_negative_tokens_zero_loss':cross,
    'HF_14B_and_8B_render_and_token_calls':'independent_equal',
    'unapproved_assistant_body_and_prompt_labels_minus100':True,
    'all_target_mask_weights_exact':True,'all_message_tools_equal_to_frozen_raw':True})
 assert all_ids==set(raw) and counts['sequences']==6 and counts['targets']==6
 for key in ['sequences','targets','input_tokens','supervised_tokens','component_A','component_R']:
  assert counts[key]==report['counts'][key]
 assert counts['supervised_tokens']==5449 and counts['component_R']==56 and counts['input_tokens']==31358
 assert counts['rendered_assistant_frames']==7 and counts['zero_loss_context_assistant_frames']==1
 assert counts['negative_ranges']==4
 assert 'torch' not in sys.modules
 result={'schema':'wrd10-meeting-independent-exact-token-mask-peer-v1','status':'PASS_ALL6_DUAL_TOKENIZERS_AND_EXACT_FULL_MASK_GEOMETRY',
  'independent_of_compiler_pruner_verifier_imports':True,
  'same_resource_reviewer_not_independent_semantic_root_acceptor':True,
  'counts':dict(counts),'crossing_negative_tokens_zero_loss':crossing_negative_tokens,'records':summary,
  'raw_pin':pin(rawfile),'compiled_report_pin':pin(a.compiled/'COMPILATION_REPORT.json'),
  'frozen_pruned_files':[{'path':str(a.compiled/r['path']),'bytes':r['bytes'],'sha256':r['sha256']} for r in report['files']],
  'scope':'Only the SHA-pinned pruned03 six-record export. Unpruned compiled01/02 are not eligible for main.',
  'models_loaded':False,'torch_imported':False,'forward_or_backward_or_native_calls':False,
  'QA_script_pin':pin(Path(__file__))}
 dest=OUT/'INDEPENDENT_TOKEN_MASK_QA.json';dest.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':result['status'],'counts':dict(counts),'receipt':pin(dest)},ensure_ascii=False))
if __name__=='__main__':main()
