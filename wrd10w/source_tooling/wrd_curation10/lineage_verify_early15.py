"""Independent original-evidence, semantic scope and exact two-tokenizer QA.

No compiler is used to generate expected masks; they are derived directly from
the rendered original fields and independently requested tokenizer offsets.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import gzip,hashlib,importlib.util,json,os,sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['TOKENIZERS_PARALLELISM']='false'
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261031_wrd_curation10/early_reads'
OUT=ROOT/'output/20261031_wrd_curation10/reasoning_native10'
CORE={'ls','read','write','edit','apply_patch','exec','process'}
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8-sig')if l.strip()]
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s)
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:s.loader.exec_module(m)
    finally:sys.dont_write_bytecode=old
    return m
def explicit_empty_R(messages):
    out=deepcopy(messages)
    for m in out:
        if m.get('role')=='assistant'and 'reasoning_content'not in m:m['reasoning_content']=''
    return out
def verify_refs(jobs):
    out=[]
    for stage,j in jobs.items():
        assert pin(j['job']['path'])==j['job']
        job=load(j['job']['path'])
        for ref in job['resources']:
            actual=pin(ref['path']);assert actual['sha256']==ref['sha256']
        for pathkey,hashkey in [('source_allowlist_receipt','source_allowlist_sha256'),('resource_ancestry_receipt','resource_ancestry_sha256')]:
            assert pin(job[pathkey])['sha256']==job[hashkey]
        for r in j['resources_and_ancestry']:
            assert pin(r['path'])=={k:r[k]for k in ['path','bytes','sha256']}
        out.append({'stage':stage,'job_pin':j['job'],'resource_refs_actual_SHA_verified':len(job['resources']),
          'source_allowlist_and_ancestry_receipts_verified':True})
    return out

def main():
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    helper=module('peer_frozen_verify_main10',ROOT/'research/data_prep/wrd_curation10/verify_main10.py')
    assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
    toks={k:AutoTokenizer.from_pretrained(assets/k,local_files_only=True,trust_remote_code=False)for k in ['primary_14b','control_8b']}
    template=_compile_jinja_template(load(BASE/'compiled01/CAUSAL_TEMPLATE.json')['variant'])
    report=load(BASE/'compiled01/COMPILATION_REPORT.json')
    packets=rows(OUT/'EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz')
    byowner={r['owner_id']:r for r in packets};assert len(byowner)==15
    raw={r['id']:r for r in rows(BASE/'CANDIDATES.raw.jsonl.gz')}
    rootreview=load(BASE/'ROOT_SEMANTIC_READ_REVIEW.json');jobs=verify_refs(rootreview['source_jobs'])
    checks=[];counts=Counter();seen=set()
    for f in report['files']:
        path=BASE/'compiled01'/f['path'];assert pin(path)['sha256']==f['sha256']
        for row in rows(path):
            assert row['id']not in seen;seen.add(row['id']);assert row['messages']==explicit_empty_R(raw[row['id']]['messages'])
            md=row['original_record_metadata'];packet=byowner[md['original_recorded_action_owner']]
            assert packet['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']
            assert packet['existing_positive_R_approved_unicode_characters']==0
            requestpin=packet['source_compatible_API_request'];assert pin(requestpin['path'])==requestpin
            assert pin(packet['source_compatible_API_response']['path'])==packet['source_compatible_API_response']
            request=load(requestpin['path']);expected=deepcopy(request['messages'])+[deepcopy(packet['original_response'])]
            for m in expected:
                if isinstance(m.get('content'),list):
                    assert all(b.get('type')=='text'and isinstance(b.get('text'),str)for b in m['content'])
                    m['content']='\n'.join(b['text']for b in m['content'])
            expected=explicit_empty_R(expected)
            assert row['messages']==expected,'CURRENT_OR_FUTURE_CONTEXT_MODIFIED'
            assert row['tools']==[t for t in request['tools']if t['function']['name']in CORE]
            assert len(row['tools'])==7 and len(request['tools'])==53
            assert md['is_original_native_request_identical']is False
            assert md['full_pipeline_or_skill_utility_approved']is False
            assert md['future_feedback_in_model_input']is False
            assert set(row['source_ids'])=={'conv_246b5e915810','conv_41874c950938','conv_d1ef29d65e7a'}
            assert 'conv_34b56ae9c535'not in row['source_ids']
            feedback=packet['actual_native_tool_feedback'];assert len(feedback)==1
            actual=feedback[0]['message'];call=packet['original_response']['tool_calls'][0]
            args=call['function']['arguments'];args=json.loads(args)if isinstance(args,str)else args
            assert call['function']['name']in {'read','ls'}and set(args)<={'path','offset','limit'}
            assert args['path'].startswith('/workspace/inputs/')or args['path']=='/workspace/outputs'
            assert actual['isError']is False and actual['toolCallId']==call['id']
            assert h(json.dumps(actual,ensure_ascii=False,separators=(',',':'),sort_keys=True))==feedback[0]['message_sha256_sorted']
            assert row['messages'][-1].get('reasoning_content','')==packet['original_R']
            n,excluded=helper.verify_token_row(row,template,toks)
            assert excluded==0
            kwargs=dict(toks['primary_14b'].special_tokens_map,enable_thinking=False)
            rendered=template.render(messages=row['messages'],tools=row['tools'],documents=None,add_generation_prompt=False,**kwargs)
            x=toks['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
            y=toks['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
            assert x==y and x['input_ids']==row['input_ids']
            approved=md['supervision_message_indices'];assert approved==[len(expected)-1]
            target=next(t for t in row['targets']if t['message_index']==approved[0])
            start,end=target['rendered_assistant_span'];targetR=packet['original_R']
            ra=start+len('<|im_start|>assistant\n<think>\n');rb=ra+len(targetR)
            aa=rb+len('\n</think>\n\n');ab=end-len('<|im_end|>\n')
            assert rendered[ra:rb]==targetR and not row['messages'][-1]['content']
            assert rendered[aa:ab].startswith('<tool_call>\n')and rendered[aa:ab].endswith('\n</tool_call>')
            expected_mask={}
            for i,(a,b)in enumerate(x['offset_mapping']):
                if ra<=a<b<=rb:expected_mask[i]='R'
                elif aa<=a<b<=ab:expected_mask[i]='A'
            actual_mask={}
            for lo,hi,cl,w in row['supervision_spans']:
                assert cl in {'R','A'}and w==1.0
                for i in range(lo,hi):assert i not in actual_mask;actual_mask[i]=cl
            assert actual_mask==expected_mask,'INDEPENDENT_FULL_FIELD_AND_BOUNDARY_MASK_MISMATCH'
            assert row['supervised_tokens']==len(expected_mask)
            assert row['supervised_tokens_by_component']==dict(Counter(expected_mask.values()))
            # Reconstruct all four training features independently, every input
            # and prior assistant token remains labels=-100 and weight0.
            labels=[-100]*n;weights=[0.0]*n
            for i in actual_mask:labels[i]=row['input_ids'][i];weights[i]=1.0
            assert all(labels[i]==-100 and weights[i]==0 for i in range(n)if i not in expected_mask)
            assert labels[0]==-100 and n<=32768
            counts['rows']+=1;counts['input_tokens']+=n;counts['positive_tokens']+=len(expected_mask)
            counts.update(Counter(expected_mask.values()))
            counts['le16k']+=n<=16384;counts['long32k']+=n>16384
            checks.append({'id':row['id'],'owner_id':packet['owner_id'],'original_R_chars':len(targetR),
              'source_API_request_sha256':requestpin['sha256'],'source_API_response_sha256':packet['source_compatible_API_response']['sha256'],
              'native_RID':packet['response_id'],'actual_tool_call_ID':call['id'],
              'tokens':n,'positive_R_tokens':row['supervised_tokens_by_component'].get('R',0),
              'positive_A_tokens':row['supervised_tokens_by_component'].get('A',0),
              'independent_14B_8B_ids_offsets_render_and_exact_full_mask':'PASS',
              'semantic_scope':'LOCAL_PLAN_OR_PROCEDURAL_READ_WITH_OBSERVED_INPUT_ONLY_NOT_UTILITY_OR_KEEP'})
    assert seen==set(raw)and counts==Counter({'rows':15,'input_tokens':168195,'positive_tokens':646,'R':201,'A':445,'le16k':14,'long32k':1})
    q={'status':'PASS_INDEPENDENT_ORIGINAL_SOURCE_SEMANTIC_SCOPE_DUAL_TOKENIZER_AND_EXACT_MASK15',
      'counts':dict(counts),'R_A_pairs':sum(bool(p['original_R'])for p in packets),'new_source_groups':0,
      'candidate_file':pin(BASE/'CANDIDATES.raw.jsonl.gz'),'original_packet':pin(OUT/'EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz'),
      'compilation_report':pin(BASE/'compiled01/COMPILATION_REPORT.json'),
      'compiled_files':[pin(BASE/'compiled01'/f['path'])for f in report['files']],
      'source_job_checks':jobs,'rows':checks,'source_HOLD_or_protected_Q_not_used':True,
      'whole_native_request_identical':False,'core7_projection_only':True,
      'compiler_missing_historical_reasoning_field_to_explicit_empty_only_verified':True,
      'no_future_feedback_in_earlier_input':True,'independent_positive_mask_equality_not_only_legal_subsets':True,
      'original_R_local_plan_and_progress_style_content_preserved_not_private_upstream_CoT_claim':True,
      'weights_loaded':False,'new_business_calls':0,'training_started':False,
      'helper_sha256':pin(ROOT/'research/data_prep/wrd_curation10/verify_main10.py')['sha256'],
      'script_pin':pin(__file__)}
    p=OUT/'EARLY15_INDEPENDENT_SOURCE_TOKEN_MASK_QA.json';p.write_bytes((json.dumps(q,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'status':q['status'],'counts':dict(counts),'QA':pin(p)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
