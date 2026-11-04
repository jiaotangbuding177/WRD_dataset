"""CPU-only26 evaluation-input compilation: 2 tokenizers x2 tool profiles.

Never loads weights, performs inference, launches OpenClaw or trains. Every
label=-100 and every loss_weight=0. Frozen task05 input messages stay unchanged.
"""
import os
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1')
import collections,gzip,hashlib,importlib.util,json,platform,sys,time
from array import array
from pathlib import Path
sys.dont_write_bytecode=True

ROOT=Path('D:/skillloop');HOLD=ROOT/'output/20261031_wrd_curation09/holdout'
OUT=ROOT/'output/20261031_wrd_curation09/eval_input_arrays09'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
COMPILED=ROOT/'output/20261031_wrd_curation09/compiled_staging01/compiled01'
CAPTURE=ROOT/'output/20261027_wrd_main_v10/historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'
SOURCE_CAPTURE_SHA='a47db18b7c6bafcfddfe4bce79ae68787303320225a1edf99457720ee1622345'
CORE7=['apply_patch','edit','exec','ls','process','read','write']
TOKENIZER_NAMES=['primary_14b','control_8b']
MODELS={'primary_14b':{'repository':'Qwen/Qwen3-14B','revision':'40c069824f4251a91eefaf281ebe4c544efd3e18'},
 'control_8b':{'repository':'Qwen/Qwen3-8B','revision':'b968826d9c46dd6066d109eabc6255188de91218'}}
ADD_GENERATION_PROMPT=True;ENABLE_THINKING=True

def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def pin(p,base=OUT):return {'path':str(p.relative_to(base)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def source_pin(p):return pin(p,ROOT)
def pack_values(typecode,values):
 a=array(typecode,values)
 if sys.byteorder!='little' and a.itemsize>1:a.byteswap()
 return a.tobytes()

LOADER=r'''"""Python-standard-library loader for input-only eval arrays.
No tokenizer/model/torch dependency. Returns four real serialized features.
"""
from array import array
from pathlib import Path
import hashlib,json,sys

def load_index(root):
 return json.loads((Path(root)/'INDEX.json').read_text(encoding='utf-8'))
def validate_features(features):
 n=len(features['input_ids'])
 assert n>0 and all(len(v)==n for v in features.values()),'FEATURE_LENGTH_MISMATCH'
 assert all(v==-100 for v in features['labels']),'EVAL_LABEL_MUST_IGNORE'
 assert all(v==0 for v in features['loss_weights']),'EVAL_WEIGHT_MUST_ZERO'
 assert all(v==1 for v in features['attention_mask']),'ATTENTION_MASK_MUST_ONE'
 return True
def load_record(root,profile_id,task_id):
 root=Path(root);index=load_index(root)
 profile=next(x for x in index['profiles'] if x['profile_id']==profile_id)
 row=next(x for x in profile['records'] if x['task_id']==task_id)
 out={}
 for name,meta in row['features'].items():
  path=(root/meta['path']).resolve()
  assert path.is_relative_to(root.resolve()),'ARRAY_PATH_ESCAPE'
  b=path.read_bytes()
  assert len(b)==meta['bytes'] and hashlib.sha256(b).hexdigest()==meta['sha256'],'ARRAY_ENTITY_SHA_MISMATCH'
  a=array(meta['typecode']);a.frombytes(b)
  if sys.byteorder!='little' and a.itemsize>1:a.byteswap()
  assert len(a)==row['tokens'],'ARRAY_TOKEN_LENGTH_MISMATCH'
  out[name]=list(a)
 validate_features(out)
 return out
def iter_records(root,profile_id,split=None):
 index=load_index(root);profile=next(x for x in index['profiles'] if x['profile_id']==profile_id)
 for row in profile['records']:
  if split is None or row['split']==split:yield row,load_record(root,profile_id,row['task_id'])
'''

def main():
 start=time.monotonic()
 frozen=HOLD/'MANIFEST.json'
 assert frozen.is_file(),'HOLDOUT_NOT_SEALED'
 freeze=read(frozen)
 for f in freeze['files']:
  p=HOLD/f['path'];assert p.stat().st_size==f['bytes'] and sha(p.read_bytes())==f['sha256'],'HOLDOUT_FROZEN_FILE_CHANGED'
 assert not OUT.exists(),'OUTPUT_MUST_BE_FRESH'
 OUT.mkdir(parents=True)
 entrypoint_path=HOLD/'INPUT_ONLY_EVAL_ENTRYPOINT05.json';entrypoint=read(entrypoint_path)
 assert entrypoint['actual_counts']['input_tasks']==26
 assert sha(CAPTURE.read_bytes())==SOURCE_CAPTURE_SHA
 actual_capture=read(CAPTURE);full_tools=actual_capture['tools'];assert len(full_tools)==53
 registry={t['function']['name']:t for t in full_tools};core_tools=[registry[n] for n in CORE7]
 proofs=read(COMPILED/'COMPILATION_REPORT.json')['tokenizer_proof']
 assets={}
 for name,expected in proofs['asset_sha256'].items():
  assets[name]={f:sha((ASSETS/name/f).read_bytes()) for f in expected}
  assert assets[name]==expected,'TOKENIZER_PIN_DIFFERENT_FROM_TRAIN32'
 assert assets['primary_14b']==assets['control_8b']
 template_meta=read(COMPILED/'CAUSAL_TEMPLATE.json');variant=template_meta['variant']
 assert sha(variant)==proofs['causal_template_sha256']=='5b5e083127485923d9d66e3262ccfb08ceb51afec37b8c4abfafa30cb18a17b4'
 save(OUT/'tool_profiles/core7.json',{'tools':core_tools,'selected_names_in_order':CORE7,'source_capture':source_pin(CAPTURE)})
 (OUT/'tool_profiles/full53_CAPTURE.original.json').write_bytes(CAPTURE.read_bytes())
 (OUT/'CAUSAL_TEMPLATE.jinja').write_bytes(variant.encode())
 (OUT/'binary_loader.py').write_bytes(LOADER.encode())
 import transformers,tokenizers
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 toks={n:AutoTokenizer.from_pretrained(ASSETS/n,local_files_only=True,trust_remote_code=False) for n in TOKENIZER_NAMES}
 assert all(sha(t.chat_template)==proofs['official_template_sha256'] for t in toks.values())
 renderer=_compile_jinja_template(variant)
 (OUT/'OFFICIAL_TEMPLATE.jinja').write_bytes(toks['primary_14b'].chat_template.encode())
 profiles=[];standard=[];call_counts=collections.Counter();pair_cache={};no_answer_leakage=[]
 for tool_name,tools in [('core7',core_tools),('full53',full_tools)]:
  for tokenizer_name in TOKENIZER_NAMES:
   profile_id=tool_name+'__'+tokenizer_name;records=[];counts=collections.Counter()
   for entry in entrypoint['entries']:
    packet_path=HOLD/entry['input_packet']['path'];assert pin(packet_path,HOLD)==entry['input_packet']
    packet=read(packet_path);messages=packet['messages']
    assert sha(json.dumps(messages,ensure_ascii=False,separators=(',',':'),sort_keys=True))==entry['messages_canonical_sha256_sorted_utf8']
    assert all(m['role']=='user' for m in messages),'NON_TASK_OR_ANSWER_MESSAGE'
    for alias in packet['input_files']:
     assert alias['native_path'] in '\n'.join(m['content'] for m in messages)
     file=packet_path.parent/alias['relative_path'];assert sha(file.read_bytes())==alias['sha256'] and file.stat().st_size==alias['bytes']
    kwargs=dict(toks[tokenizer_name].special_tokens_map,enable_thinking=ENABLE_THINKING)
    rendered=renderer.render(messages=messages,tools=tools,documents=None,add_generation_prompt=ADD_GENERATION_PROMPT,**kwargs)
    official=toks[tokenizer_name].apply_chat_template(messages,tools=tools,documents=None,tokenize=False,
      add_generation_prompt=ADD_GENERATION_PROMPT,enable_thinking=ENABLE_THINKING)
    assert rendered==official,'USER_ONLY_VARIANT_OFFICIAL_RENDER_DIFFERENCE'
    assert rendered.endswith('<|im_start|>assistant\n')
    ids=toks[tokenizer_name](rendered,add_special_tokens=False,truncation=False,padding=False)['input_ids'];call_counts[tokenizer_name]+=1
    key=(tool_name,entry['task_id'])
    if tokenizer_name=='primary_14b':pair_cache[key]=(rendered,ids)
    else:assert pair_cache[key]==(rendered,ids),'ACTUAL_SECOND_TOKENIZER_DISAGREEMENT'
    n=len(ids);features={'input_ids':('i',ids),'labels':('i',[-100]*n),'loss_weights':('f',[0.0]*n),'attention_mask':('B',[1]*n)}
    descriptors={}
    for feature,(code,values) in features.items():
     data=pack_values(code,values);path=OUT/'arrays'/profile_id/(entry['task_id']+'.'+feature+'.bin');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
     descriptors[feature]={**pin(path),'typecode':code,'dtype':{'i':'int32','f':'float32','B':'uint8'}[code],'byte_order':'little'}
    prompt_path=OUT/'prompts'/profile_id/(entry['task_id']+'.txt');prompt_path.parent.mkdir(parents=True,exist_ok=True);prompt_path.write_bytes(rendered.encode())
    row={'task_id':entry['task_id'],'split':entry['split'],'task_class':entry['task_class'],'evaluation_level':'COMPONENT_OR_CONSUMPTION',
     'source_scope_component_id':entry['source_scope_component_id'],'reserved_source_ids':entry['reserved_source_ids'],
     'tokens':n,'le16k':n<=16384,'le32k':n<=32768,'headroom_if_context16k':max(0,16384-n),'headroom_if_context32k':max(0,32768-n),
     'generation_output_budget_not_assigned':True,'input_packet_pin':entry['input_packet'],'material_mount_manifest':packet['input_files'],
     'actual_messages_sha256':entry['messages_canonical_sha256_sorted_utf8'],'rendered_prompt':pin(prompt_path),
     'features':descriptors,'supervised_tokens':0,'positive_loss_weights':0,'answer_or_rubric_in_prompt':False}
    records.append(row)
    standard.append({'profile_id':profile_id,'task_id':entry['task_id'],'split':entry['split'],
     'input_ids':ids,'labels':[-100]*n,'loss_weights':[0.0]*n,'attention_mask':[1]*n})
    counts.update(records=1,input_tokens=n,le16k=int(n<=16384),le32k=int(n<=32768),over32k=int(n>32768))
   lengths=[r['tokens'] for r in records]
   profiles.append({'profile_id':profile_id,'tokenizer':tokenizer_name,'model':MODELS[tokenizer_name],
    'tool_profile':tool_name,'tool_count':len(tools),'tool_list_canonical_SHA256':sha(js(tools)),
    'counts':dict(counts),'minimum_tokens':min(lengths),'maximum_tokens':max(lengths),
    'mean_tokens':round(sum(lengths)/len(lengths),6),'records':records})
 assert len(standard)==104 and dict(call_counts)=={'primary_14b':52,'control_8b':52}
 standard_path=OUT/'tokenized_inputs.standard.jsonl.gz'
 with gzip.open(standard_path,'wt',encoding='utf-8',newline='\n') as f:
  for row in standard:f.write(js(row)+'\n')
 index={'schema':'wrd09-input-only-eval-binary-index-v1','profiles':profiles,
  'task_count':26,'sequence_profile_instances':104,'actual_feature_entities':416,
  'feature_order':['input_ids','labels','loss_weights','attention_mask'],'no_padding_or_truncation':True,
  'add_special_tokens':False,'add_generation_prompt':ADD_GENERATION_PROMPT,'enable_thinking':ENABLE_THINKING,
  'thinking_flag_does_not_insert_gold_reasoning':True,'labels_all_ignore_index':-100,'loss_weights_all_zero':True,
  'not_a_training_manifest':True,'source_entrypoint':source_pin(entrypoint_path),'source_holdout_manifest':source_pin(frozen),
  'tool_capture':source_pin(CAPTURE),'tokenizer_asset_sha256':assets,'tokenizer_named_models_from_training_plan':source_pin(ROOT/'research/plans/20261030_wrd_gap_completion/TRAINING_PLAN_08.md'),
  'training32_causal_template_SHA256':proofs['causal_template_sha256'],'official_template_SHA256':proofs['official_template_sha256'],
  'these_user_only_generation_prompts_equal_official_render':True,
  'system_capture':'NO_ORIGINAL_SYSTEM_CAPTURE_CLAIM; these are declared offline prompt profiles. HF template default system/tool wrapper is not a recovered OpenClaw system.',
  'live_native_API_or_53tool_dispatch_preflight_done':False,'full_WRD_autonomous_evaluation_cases':0,
  'input_fits_does_not_prove_output_headroom_or_runtime_feasibility':True,'standard_reference':pin(standard_path),
  'runtime_versions':{'python':platform.python_version(),'transformers':transformers.__version__,'tokenizers':tokenizers.__version__},
  'actual_tokenizer_calls':dict(call_counts),'model_weights_loaded':False,'model_inference_started':False,'training_started':False,
  'script_sha256':sha(Path(__file__).read_bytes())}
 save(OUT/'INDEX.json',index)
 spec=importlib.util.spec_from_file_location('wrd09_input_eval_stdlib_loader',OUT/'binary_loader.py');loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
 checked=0
 for row in standard:
  actual=loader.load_record(OUT,row['profile_id'],row['task_id'])
  assert all(actual[k]==row[k] for k in index['feature_order']);checked+=1
 bad={k:list(standard[0][k]) for k in index['feature_order']};bad['labels'][0]=bad['input_ids'][0]
 try:loader.validate_features(bad)
 except AssertionError:label_canary=True
 else:raise AssertionError('POSITIVE_LABEL_CANARY_NOT_REJECTED')
 bad={k:list(standard[0][k]) for k in index['feature_order']};bad['loss_weights'][0]=1.0
 try:loader.validate_features(bad)
 except AssertionError:weight_canary=True
 else:raise AssertionError('POSITIVE_WEIGHT_CANARY_NOT_REJECTED')
 assert pin(frozen,ROOT)==index['source_holdout_manifest']
 for file in freeze['files']:assert sha((HOLD/file['path']).read_bytes())==file['sha256'],'SEALED_HOLDOUT_CHANGED_DURING_BUILD'
 qa={'schema':'wrd09-input-only-eval-array-build-QA-v1','status':'PASS_ACTUAL_CPU_TOKENIZATION_BINARY_AND_STANDARD_LOADER_NO_INFERENCE',
  'task_count':26,'profile_instances':104,'actual_feature_entities':416,'four_features_exactly_compared':checked,
  'actual_tokenizer_calls':dict(call_counts),'pinned_tokenizer_assets_both_checked':True,
  'same_input_for_both_models_and_two_actual_tokenizer_calls':True,
  'labels_positive_count':0,'nonzero_loss_weights':0,'rubric_or_gold_answers_in_messages':0,
  'input_message_and_material_pins_rechecked':True,'frozen_holdout_changed':False,
  'negative_canaries':{'positive_label_rejected':label_canary,'positive_weight_rejected':weight_canary},
  'profile_counts':{p['profile_id']:{**p['counts'],'min':p['minimum_tokens'],'max':p['maximum_tokens']} for p in profiles},
  'index_pin':pin(OUT/'INDEX.json'),'binary_loader_pin':pin(OUT/'binary_loader.py'),
  'elapsed_seconds':round(time.monotonic()-start,3),'model_weights_loaded':False,'model_inference_started':False,'training_started':False,
  'independent_author_QA_not_claimed_by_this_self_reconstruction':True}
 save(OUT/'BUILD_QA.json',qa)
 files=[pin(p) for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
 save(OUT/'MANIFEST.json',{'schema':'wrd09-input-only-eval-entity-manifest-v1','files':files,'file_count':len(files),'bytes':sum(f['bytes'] for f in files),
  'excludes_self':True,'status':'EVAL_INPUT_ONLY_ALL_LOSS_ZERO_NOT_TRAIN','source_entrypoint_SHA256':sha(entrypoint_path.read_bytes())})
 print(js({'status':qa['status'],'index':pin(OUT/'INDEX.json'),'qa':pin(OUT/'BUILD_QA.json'),'manifest':pin(OUT/'MANIFEST.json'),'profiles':qa['profile_counts']}))

if __name__=='__main__':main()
