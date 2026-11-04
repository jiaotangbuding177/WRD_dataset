"""Independent full math module/source/arrays/owner component verification."""
from array import array
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
HERE=Path(__file__).resolve().parent;OUT=HERE/'native_construction_01';ROOT=next(p for p in HERE.parents if(p/'AGENTS.md').is_file());BASE=ROOT/'output/20261027_wrd_main_v10';PAIR='8856374c439400f01448d478'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def one(p):
    with gzip.open(p,'rt',encoding='utf-8')as f:return json.loads(next(f))
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def binary(p,k):
    a=array(k);a.frombytes(Path(p).read_bytes())
    if sys.byteorder!='little':a.byteswap()
    return list(a)
def main():
    assert not(OUT/'INDEPENDENT_QA.json').exists()
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    from jsonschema import Draft202012Validator
    toks=[AutoTokenizer.from_pretrained(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'/n,local_files_only=True,trust_remote_code=False)for n in('primary_14b','control_8b')];template=_compile_jinja_template(load(OUT/'CAUSAL_TEMPLATE.json')['variant']);capture=load(OUT/'TOOLS_CAPTURE_53.json');registry={t['function']['name']:t['function']for t in capture['tools']}
    assert load(Path(capture['original_capture']['path']))['tools']==capture['tools']and digest(Path(capture['original_capture']['path']))==capture['original_capture']['sha256']
    source=load(HERE/'SOURCE_REVIEW.json');module=(HERE/'resources/proportional_split.py').read_text(encoding='utf-8');original=(HERE/'original/original_action_code.LF.py').read_text(encoding='utf-8');assert sha(original.encode())==source['original_action_code_LF_sha256']
    physical=next(Path(x['portable_copy']['path'])for x in source['original_files']if x['original']['path'].replace('\\','/').endswith('/repair/probe.py'));assert digest(physical)==source['original_physical_probe_CRLF_sha256']and physical.read_text(encoding='utf-8')==original
    old_lines=original.splitlines(keepends=True);new_lines=module.splitlines(keepends=True)
    old_functions={n.name:''.join(old_lines[n.lineno-1:n.end_lineno]).rstrip('\n')for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
    new_functions={n.name:''.join(new_lines[n.lineno-1:n.end_lineno]).rstrip('\n')for n in ast.parse(module).body if isinstance(n,ast.FunctionDef)};assert old_functions==new_functions and set(new_functions)=={'compute_valuation','main'}
    assert module.endswith('if __name__ == "__main__":\n    main()\n')and'480.0'not in module and'0.142012'not in module
    for n,v in old_functions.items():assert sha(v.encode())==next(x['original_function_LF_sha256']for x in source['new_resource_authoring']['verbatim_teacher_functions']if x['name']==n)
    for pin in source['original_files']:assert digest(Path(pin['portable_copy']['path']))==pin['portable_copy']['sha256']==pin['original']['sha256']
    qa=load(HERE/'FINITE_RESOURCE_QA.json');assert qa['checks_passed']==414 and qa['fraction_oracle_parameter_cases']==60 and qa['new_complete_resource_sha256']==digest(HERE/'resources/proportional_split.py')and qa['financial_accounting_or_legal_gold']is False
    details=[];messages=None;owners=[]
    for profile in('core7','full53'):
        raw=one(OUT/f'math_resource.{profile}.raw.jsonl.gz');c=one(OUT/f'math_resource.{profile}.compiled.jsonl.gz')
        if messages is None:messages=raw['messages']
        else:assert messages==raw['messages']
        target=messages[2];assert not target['reasoning_content']and not target['content'];fn=target['tool_calls'][0]['function'];assert fn['name']=='write';args=json.loads(fn['arguments']);Draft202012Validator(registry['write']['parameters']).validate(args);assert args['content']==module
        assert all(t['function']==registry[t['function']['name']]for t in raw['tools']);owners.append(raw['target_owner']['canonical_original_action_owner_id'])
        rendered=template.render(messages=messages,tools=raw['tools'],documents=None,add_generation_prompt=False,**{**toks[0].special_tokens_map,'enable_thinking':False});enc=[t(rendered,add_special_tokens=False,return_offsets_mapping=True)for t in toks];assert enc[0]==enc[1]and enc[0]['input_ids']==c['input_ids']
        start=rendered.rfind('<|im_start|>assistant\n')+len('<|im_start|>assistant\n<think>\n\n</think>\n\n');end=len(rendered)-len('<|im_end|>\n');assert rendered[start:end].lstrip().startswith('<tool_call>')
        expected={i for i,(a,b)in enumerate(enc[0]['offset_mapping'])if start<=a<b<=end};actual={i for a,b,k,w in c['supervision_spans']for i in range(a,b)};assert expected==actual and all(k=='A'and w==.25 for a,b,k,w in c['supervision_spans'])
        labels=[-100]*len(c['input_ids']);weights=[0.]*len(labels)
        for i in actual:labels[i]=c['input_ids'][i];weights[i]=.25
        for ref in c['binary_arrays']:
            p=OUT/ref['path'];assert digest(p)==ref['sha256'];kind,value={'uint32_le':('I',c['input_ids']),'int64_le':('q',labels),'float32_le':('f',weights)}[ref['dtype']];assert binary(p,kind)==value
        future=template.render(messages=messages[:-1],tools=raw['tools'],documents=None,add_generation_prompt=True,**{**toks[0].special_tokens_map,'enable_thinking':True});n=len(toks[0](future,add_special_tokens=False)['input_ids']);details.append({'profile':profile,'sequence_tokens':len(labels),'positive_A':len(actual),'positive_R':0,'two_fresh_tokenizers_and_every_array_exact':True,'all_input_and_R_and_end_marker_labels_zero':True,'future_serving_input_tokens':n,'reserved_output_tokens':32768,'strict_serving_total':n+32768,'pinned40960_fits':n+32768<=40960,'candidate64K_fits':n+32768<=65536,'candidate128K_fits':n+32768<=131072})
    assert owners[0]==owners[1]=='historical_EWI_action:'+PAIR
    user=messages[1]['content'];assert module not in user and 'def compute_valuation('not in user and '414'not in user
    for marker in('native_construction_','root_main_admission','teacher','原SSE','新作者','source_scope'):assert marker not in user,marker
    state=HERE/'state_before_write';assert not(state/'outputs/proportional_split.py').exists()and not any(p.is_file()for p in state.rglob('*'))
    # The same recorded response's original R already exists. Verify it carries
    # no A, and ensure this new A owner is absent from current active A targets.
    manifest=load(BASE/'TRAINING_MANIFEST.json');save(OUT/'ACTIVE_OWNER_SNAPSHOT.original.json',manifest);R_rows=[];A_duplicates=[]
    for file in manifest['actual_train_files']:
        path=BASE/file['path'];assert digest(path)==file['sha256']
        with gzip.open(path,'rt',encoding='utf-8')as f:
            for row in map(json.loads,f):
                meta=row.get('original_record_metadata',{});raw_owner=meta.get('canonical_original_response_owner',row.get('canonical_original_response_owner'))
                if raw_owner==PAIR or row['id'].endswith(PAIR):R_rows.append({'id':row['id'],'classes':sorted({k for a,b,k,w in row['supervision_spans']})})
                owner=meta.get('target_owner',row.get('target_owner',{})).get('canonical_original_action_owner_id')
                if owner==owners[0]:A_duplicates.append(row['id'])
    assert len(R_rows)==1 and R_rows[0]['classes']==['R']and not A_duplicates,(R_rows,A_duplicates)
    result={'schema':'wrd-EWI-math-resource-independent-source-token-mask-owner-QA-v1','status':'PASS','details':details,'teacher_function_bytes_exact_after_explicit_LF_action_identity':True,'original_CRLF_physical_byte_identity_separate':True,'new_entrypoint_scoped_and_all_dependencies_present':True,'original_R_existing_main_rows':R_rows,'new_target_R_tokens':0,'same_A_owner_already_in_active':A_duplicates,'same_core_full_A_owner_mutually_exclusive':True,'new_independent_source_count':0,'new_complete_pipeline_demonstrations':0,'future_QA_or_source_code_not_in_input':True,'finite_math_QA_sha256':digest(HERE/'FINITE_RESOURCE_QA.json'),'semantic_peer_pending':True,'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'weights_loaded':False,'new_Agent_calls':0,'script_sha256':digest(Path(__file__))};save(OUT/'INDEPENDENT_QA.json',result);print(json.dumps({'status':'PASS','details':details,'existing_R':R_rows,'QA_sha256':digest(OUT/'INDEPENDENT_QA.json')}))
if __name__=='__main__':main()
