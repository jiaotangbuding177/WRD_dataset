"""CPU-only independent oracle arrays/lineage and exact positive-mask audit.

Fresh Jinja rendering and two local tokenizer calls.  No shared compiler,
trainer, model weights, business Agent, or private SDK configuration is used.
"""
from array import array
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
HERE=Path(__file__).resolve().parent;RESOURCE=HERE.parent;OUT=RESOURCE/'native_projection_02'
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
BASE=ROOT/'output/20261027_wrd_main_v10'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def one(p):
    with gzip.open(p,'rt',encoding='utf-8')as f:return json.loads(next(f))
def save(p,v):
    assert not p.exists(),str(p)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def numbers(p,k):
    a=array(k);a.frombytes(Path(p).read_bytes())
    if sys.byteorder!='little':a.byteswap()
    return list(a)
def normalize(messages):
    return [{**m,**({'reasoning_content':m.get('reasoning_content')if isinstance(m.get('reasoning_content'),str)else''}if m.get('role')=='assistant'else{})}for m in messages]
def main():
    assert not (HERE/'QA.json').exists()
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    from jsonschema import Draft202012Validator
    assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
    toks=[AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False)for n in('primary_14b','control_8b')]
    template=_compile_jinja_template(load(OUT/'CAUSAL_TEMPLATE.json')['variant'])
    capture=load(OUT/'TOOLS_CAPTURE_53.json');registry={t['function']['name']:t['function']for t in capture['tools']}
    original_capture=Path(capture['original_capture']['path'])
    assert digest(original_capture)==capture['original_capture']['sha256'] and load(original_capture)['tools']==capture['tools']
    source=load(RESOURCE/'SOURCE_STATE_AND_RANGES.json')
    revision=load(OUT/'SEMANTIC_REVISION.json')
    source['positive_excerpt_ranges']=revision['positive_excerpt_ranges']
    source['mask0_exclusions']=revision['mask0_exclusions']
    original=json.loads(gzip.decompress(Path(source['original_cumulative_R_response']['path']).read_bytes()))
    fullR=original['choices'][0]['message']['reasoning_content'];excerpt=(RESOURCE/'resources/original_contiguous_cumulative_R_excerpt.txt').read_text(encoding='utf-8')
    assert len(fullR)==49942 and fullR[source['original_R_excerpt_source_start']:source['original_R_excerpt_source_end']]==excerpt and len(excerpt)==1596
    assert sha(fullR.encode())==source['original_R_full_field_sha256'] and sha(excerpt.encode())==source['original_R_excerpt_sha256']
    details=[];messages=None;owners=[]
    for profile in('core7','full53'):
        raw=one(OUT/f'native_oracle.{profile}.raw.jsonl.gz');c=one(OUT/f'native_oracle.{profile}.compiled.jsonl.gz')
        if messages is None:messages=raw['messages']
        else:assert messages==raw['messages']
        target=messages[2];assert target['reasoning_content']==excerpt and raw['root_main_admission']is False
        assert raw['target_owner']['R_and_A_are_different_recorded_owners']is True
        owners.append(raw['target_owner']);args=json.loads(target['tool_calls'][0]['function']['arguments'])
        assert target['tool_calls'][0]['function']['name']=='edit';Draft202012Validator(registry['edit']['parameters']).validate(args)
        assert args==load(RESOURCE/'resources/native_edit.arguments.json') and all(t['function']==registry[t['function']['name']]for t in raw['tools'])
        rendered=template.render(messages=normalize(messages),tools=raw['tools'],documents=None,add_generation_prompt=False,**{**toks[0].special_tokens_map,'enable_thinking':False})
        enc=[t(rendered,add_special_tokens=False,return_offsets_mapping=True)for t in toks]
        assert enc[0]==enc[1]and enc[0]['input_ids']==c['input_ids']
        p=rendered.rfind('<|im_start|>assistant\n')+len('<|im_start|>assistant\n<think>\n');assert rendered[p:p+len(excerpt)]==excerpt
        ranges=[(p+x['start'],p+x['end'])for x in raw['approved_field_ranges']]
        a=p+len(excerpt)+len('\n</think>\n\n');b=len(rendered)-len('<|im_end|>\n');assert rendered[a:b].lstrip().startswith('<tool_call>')
        expected={i for i,(s,e)in enumerate(enc[0]['offset_mapping'])if s<e and(any(x<=s and e<=y for x,y in ranges)or a<=s and e<=b)}
        actual={i for x,y,k,w in c['supervision_spans']for i in range(x,y)}
        assert actual==expected and all(k in('R','A')and w==.25 for x,y,k,w in c['supervision_spans'])
        for excluded in source['mask0_exclusions']:
            x,y=p+excluded['start'],p+excluded['end'];assert rendered[x:y]==excluded['text']
            assert not any(i in actual for i,(s,e)in enumerate(enc[0]['offset_mapping'])if s<y and e>x)
        labels=[-100]*len(c['input_ids']);weights=[0.]*len(labels)
        for i in actual:labels[i]=c['input_ids'][i];weights[i]=.25
        for ref in c['binary_arrays']:
            file=OUT/ref['path'];assert digest(file)==ref['sha256']and file.stat().st_size==ref['bytes']
            kind,value={'uint32_le':('I',c['input_ids']),'int64_le':('q',labels),'float32_le':('f',weights)}[ref['dtype']]
            assert numbers(file,kind)==value
        service=template.render(messages=normalize(messages[:-1]),tools=raw['tools'],documents=None,add_generation_prompt=True,**{**toks[0].special_tokens_map,'enable_thinking':True})
        n=len(toks[0](service,add_special_tokens=False)['input_ids'])
        details.append({'profile':profile,'sequence_tokens':len(labels),'supervised_tokens':len(actual),'by_component':c['supervised_tokens_by_component'],'both_tokenizers_exact_ids_and_offsets':True,'all_three_binary_arrays_independently_equal':True,'all_exclusion_overlap_tokens_zero':True,'future_serving_input_tokens':n,'reserved_output_tokens':32768,'strict_serving_total':n+32768,'pinned40960_fits':n+32768<=40960,'candidate64K_fits':n+32768<=65536,'candidate128K_fits':n+32768<=131072})
    assert owners[0]==owners[1]
    state=OUT/'state';user=messages[1]['content']
    backup=state/'inputs/previous_failed_edge_case_tests.py'
    assert digest(backup)==revision['real_readonly_input_backup']['sha256']
    assert backup.read_bytes()==(state/'outputs/validation_history/edge_case_tests.py').read_bytes()
    assert '/workspace/inputs/previous_failed_edge_case_tests.py' in user and '只读规则保全' in user
    for rel in('inputs/task_contract.functional.json','outputs/validation_history/edge_case_tests.py','outputs/validation_history/previous_failed_run.json'):assert(state/rel).read_text(encoding='utf-8')in user
    for flag in('native_projection_','root_main_admission','source_boundary','projection_note','原累计','teacher','root独审'):assert flag not in user,flag
    assert '共 31 项检查，失败 0 项'not in user and 'PASS_SCOPED_TWO_TEST_ORACLES'not in user
    old=(state/'outputs/validation_history/edge_case_tests.py').read_text(encoding='utf-8');new=old
    for e in args['edits']:assert old.count(e['oldText'])==1 and e['newText']not in user;new=new.replace(e['oldText'],e['newText'])
    assert new==(RESOURCE/'resources/new_edge_case_tests.py').read_text(encoding='utf-8')
    # Verify the original 024/025 literal provenance independently from the
    # constructor: read only these current TRAIN raw records and literal ASTs.
    import ast
    original025=json.loads(gzip.decompress(Path(source['original_action_response']['path']).read_bytes()))['choices'][0]['message']
    literals={n.targets[0].id:ast.literal_eval(n.value)for n in ast.parse(json.loads(original025['tool_calls'][0]['function']['arguments'])['code']).body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in{'old1','old2','new1','new2'}}
    assert args['edits']==[{'oldText':literals[f'old{i}'],'newText':literals[f'new{i}']}for i in(1,2)]
    original024=json.loads(gzip.decompress(Path(source['original_old_test_creator_response']['path']).read_bytes()))['choices'][0]['message']
    code=json.loads(original024['tool_calls'][0]['function']['arguments'])['code'];literal=next(n.value.value for n in ast.parse(code).body if isinstance(n,ast.Assign)and isinstance(n.value,ast.Constant)and any(isinstance(x,ast.Name)and x.id=='code'for x in n.targets))
    assert literal==old
    originalrequest=json.loads(gzip.decompress(Path(source['original_asof_request']['path']).read_bytes()))
    observed=json.loads(originalrequest['messages'][49]['content']);assert observed==load(RESOURCE/'resources/actual_previous_failed_test_observation.json')
    assert observed['exit_code']==0 and 'exit: 1'in observed['stdout']and'失败 2 项'in observed['stdout']
    # Freeze the already saved original 526-shard snapshot for this audit. An
    # exact serialized token prefix can omit only future zero-loss text. For
    # deduplication, exact ID-prefix equality suffices to map existing positive
    # token positions; absent old metadata flags are not invented.
    snapshot=OUT/'ACTIVE_FOR_DEDUP.original.json';manifest=load(snapshot);positive=[];rows=0;prefix_rows=0
    for item in manifest['actual_train_files']:
        path=BASE/item['path'];assert digest(path)==item['sha256']
        with gzip.open(path,'rt',encoding='utf-8')as f:
            for row in map(json.loads,f):
                rows+=1;rendered=template.render(messages=normalize(row['messages']),tools=row.get('tools')or None,documents=None,add_generation_prompt=False,**{**toks[0].special_tokens_map,'enable_thinking':False});encoded=toks[0](rendered,add_special_tokens=False,return_offsets_mapping=True)
                if row.get('view')=='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION':
                    assert encoded['input_ids'][:len(row['input_ids'])]==row['input_ids'],row['id'];prefix_rows+=1
                    if 'complete_rendered_tokens'in row:assert len(encoded['input_ids'])==row['complete_rendered_tokens']
                else:assert encoded['input_ids']==row['input_ids'],row['id']
                for lo,hi,kind,weight in row['supervision_spans']:
                    assert 0<=lo<hi<=len(row['input_ids'])
                    x=encoded['offset_mapping'][lo][0];y=encoded['offset_mapping'][hi-1][1];positive.append((row['id'],kind,rendered[x:y]))
    assert rows==526,rows
    # Hash windows once; report only exact positive-mask overlap, never a
    # body/context match interpreted as supervised exposure.
    desired={}
    for r in source['positive_excerpt_ranges']:
        s=excerpt[r['start']:r['end']]
        for i in range(max(0,len(s)-63)):desired.setdefault(s[i:i+64],[]).append(r['start']+i)
    hits=[]
    for row_id,kind,known in positive:
        for window,starts in desired.items():
            at=known.find(window)
            if at>=0:hits.append({'current_row_id':row_id,'component':kind,'current_positive_text_offset':at,'excerpt_starts':starts,'length':64,'text_sha256':sha(window.encode())})
    dedup={'schema':'wrd-original-cumulative-excerpt-exact-positive-mask-dedup-v1','status':'PASS_NO_EXACT_64CHAR_POSITIVE_OVERLAP'if not hits else'HOLD_EXACT_POSITIVE_OVERLAP','current_526_snapshot_sha256':digest(snapshot),'rows_actually_rendered_and_ID_matched':rows,'exact_token_prefix_rows':prefix_rows,'positive_text_segments':len(positive),'exact64char_positive_matches':hits,'source_or_component_count_increased_by_view':False,'limits':'Exact >=64char exposure only; shorter common phrases and semantic similarity do not prove independence.'}
    save(HERE/'EXACT_POSITIVE_DEDUP.json',dedup);assert not hits,hits[:3]
    result={'schema':'wrd-original-cumulative-excerpt-native-edit-independent-QA-v3-peer-refined','status':'PASS','details':details,'canonical_owners':owners[0],'original_R_contiguous_and_verbatim':True,'cumulative_R_not_per_turn_CoT_or_newly_generated_49k':True,'exact_original_024_and_025_literals_independently_verified':True,'future_QA_absent_from_input':True,'exact72char_saved_logs_claim_mask0':True,'real_complete_old_test_readonly_backup_present':True,'positive_mask_dedup':{'path':str(HERE/'EXACT_POSITIVE_DEDUP.json'),'sha256':digest(HERE/'EXACT_POSITIVE_DEDUP.json')},'resource_QA':{'path':str(RESOURCE/'RESOURCE_QA.json'),'sha256':digest(RESOURCE/'RESOURCE_QA.json')},'historical_partial_verifier_failures':'2026-10-27 verifier stopped during old-shard dedup on complete-vs-token-prefix and missing optional flag; no array/data changes. This version uses independently verified exact ID-prefix mapping.','native_projection_semantic_peer_pending':True,'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'weights_loaded':False,'new_Agent_calls':0,'script_sha256':digest(Path(__file__))}
    save(HERE/'QA.json',result);save(OUT/'INDEPENDENT_QA.json',result)
    print(json.dumps({'status':'PASS','details':details,'dedup_rows':rows,'QA_sha256':digest(HERE/'QA.json')}))
if __name__=='__main__':main()
