"""Independent CPU-only 64K candidate and complete native-request coverage audit.

Reads only seven explicitly frozen completed clean episodes. Never performs a
native run, model forward, training, network request, or shared-file mutation.
The frozen shared compiler is imported for its exact reviewed-span selector;
its main() is not invoked. Max length is an explicit candidate argument.
"""
from __future__ import annotations
import argparse
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import difflib
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

os.environ['USE_TORCH']='0'
os.environ['USE_TF']='0'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['TOKENIZERS_PARALLELISM']='false'
ROOT=Path('D:/skillloop')
BASE=ROOT/'output/20261027_wrd_main_v10'
HERE=Path(__file__).resolve().parent
EPISODES=('A_screen_narrative_01','B_make_report_02','B_revision_report_01',
          'C_E_no_skill_01','C_E_skill_01','C_L_no_skill_01','C_L_skill_01')
CORE={'ls','read','write','edit','apply_patch','exec','process'}
LIMITS=(32768,40960,65536,131072)
FROZEN_MAIN_SHA='caa4449936c9705f17d50c09e27923d7cbd572d369e26e36bc8f8a4f27fb496f'

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def numbers(path,code,values):
    v=array(code,values)
    if sys.byteorder!='little':v.byteswap()
    path.write_bytes(v.tobytes())
    return {'path':str(path.relative_to(HERE)),'sha256':digest(path),'bytes':path.stat().st_size,
            'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[code], 'count':len(values)}
def text_view(messages):
    m=deepcopy(messages);projections=[]
    for i,x in enumerate(m):
        if isinstance(x.get('content'),list):
            blocks=x['content']
            assert all(isinstance(b,dict) and b.get('type')=='text' and isinstance(b.get('text'),str) for b in blocks),'non_text_content_not_supported'
            x['content']='\n'.join(b['text'] for b in blocks)
            projections.append({'message_index':i,'rule':'JOIN_COMPLETE_TEXT_BLOCKS_WITH_NEWLINE',
                                'original_blocks_sha256':sha(js(blocks).encode()),'projected_sha256':sha(x['content'].encode())})
        if x['role']=='assistant':x.setdefault('reasoning_content','')
    return m,projections
def serial(compiler,messages,tools,add_generation_prompt=False,enable_thinking=False):
    kw=dict(compiler.tokenizers['primary_14b'].special_tokens_map)
    return compiler.plain_compiled.render(messages=messages,tools=tools or None,documents=None,
        add_generation_prompt=add_generation_prompt,enable_thinking=enable_thinking,**kw)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--max-length',type=int,default=65536,choices=LIMITS)
    args=ap.parse_args()
    assert not (HERE/'COMPLETE.json').exists(),'immutable_completed_run_do_not_overwrite'
    frozen=HERE/'tools';frozen.mkdir(exist_ok=True)
    originals={name:ROOT/path for name,path in {
        'compile_main.frozen.py':'research/data_prep/wrd_main_v10/compile_main.py',
        'compile_native.frozen.py':'research/data_prep/wrd_reasoning_v4/compile_native.py',
        'extract_native_main.frozen.py':'research/data_prep/wrd_main_v10/extract_native_main.py'}.items()}
    assert digest(originals['compile_main.frozen.py'])==FROZEN_MAIN_SHA
    for name,path in originals.items():shutil.copyfile(path,frozen/name)
    # Unmodified frozen source + a separate parameterized candidate driver.
    # No monkeypatch, 32K-constant replacement, or call to frozen main().
    selector=module('frozen_v10_main',frozen/'compile_main.frozen.py')
    causal=module('frozen_causal_native',frozen/'compile_native.frozen.py')
    extractor=module('frozen_native_extractor',frozen/'extract_native_main.frozen.py')
    compiler=causal.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    tok=compiler.tokenizers['primary_14b']
    review_paths={
        'A_screen_narrative_01':BASE/'native_records/A_screen_narrative_01/A_PARTIAL_REASONING_REVIEW_V3.json',
        'B_make_report_02':BASE/'native_records/B_make_report_02/B_PARTIAL_REASONING_REVIEW_V1.json'}
    reviews={e:{r['call_id']:r for r in load(p)['responses']} for e,p in review_paths.items()}
    pins={};episode_summary=[];coverage=[];raw_recovered=[];candidate_records=[];candidate_audit=[]
    def pin(p):
        p=Path(p);pins[str(p)]={'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
    for p in review_paths.values():pin(p)
    for p in originals.values():pin(p)
    for p in (ROOT/'research/designs/A_B_MODULES.md',ROOT/'research/designs/PIPELINE.md',
              ROOT/'research/plans/20261027_wrd_main_v10/TRAINING_PLAN.md',
              ROOT/'research/plans/20261027_wrd_main_v10/MODEL_CONTEXT_REQUIREMENTS.md'):
        pin(p)
    raw_archive=HERE/'raw_api_originals.zip'
    with zipfile.ZipFile(raw_archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
      for episode in EPISODES:
        folder=BASE/'runtime_preflight/episodes'/episode
        result=load(folder/'result.json');job=load(folder/'job.json')
        assert result['status']=='completed','episode_must_be_naturally_complete'
        for p in (folder/'result.json',folder/'job.json'):pin(p)
        # Check frozen source proofs, without traversing old/protected datasets.
        for name in ('source_allowlist_receipt','resource_ancestry_receipt'):
            p=Path(job[name]);pin(p)
            assert digest(p)==job[name.replace('_receipt','_sha256')]
            proof=load(p);assert proof['status']=='PASS'
            if name=='source_allowlist_receipt':
                assert set(job['source_ids'])<=set(proof['train_source_ids'])
                if episode in ('A_screen_narrative_01','B_make_report_02','B_revision_report_01'):
                    assert set(proof['train_source_ids'])==set(job['source_ids'])
            else:
                assert proof['source_allowlist_sha256']==job['source_allowlist_sha256']
                if 'source_ids' in proof:assert set(proof['source_ids'])==set(job['source_ids'])
        stat={'episode':episode,'stage':job['stage'],'source_ids':job['source_ids'],
              'job_sha256':digest(folder/'job.json'),'result_sha256':digest(folder/'result.json'),
              'native_paid_model_calls':result.get('usage',{}).get('model_calls'),
              'known_total_tokens':result.get('usage',{}).get('known_total_tokens'),
              'unknown_usage_calls':result.get('usage',{}).get('unknown_usage_calls'),
              'captured_complete_http_responses':0,'excluded_capture':[]}
        for call_folder in sorted((folder/'api_audit').iterdir()):
          if not call_folder.is_dir():continue
          receipt_path=call_folder/'receipt.json'
          receipt=load(receipt_path)
          if receipt.get('status')!='COMPLETE' or receipt.get('http_status')!=200:
            stat['excluded_capture'].append({'call_id':call_folder.name,'reason':'NOT_COMPLETE_HTTP_200'});continue
          message,meta,request_path,response_path=extractor.recover(call_folder)
          assert receipt['response_mode']=='SSE' and b'data: [DONE]' in response_path.read_bytes(),'this_audit_requires_original_DONE'
          for p in (receipt_path,request_path,response_path):
            pin(p);archive.write(p,arcname=str(p.relative_to(BASE)).replace('\\','/'))
          actual=load(request_path)
          assert len(actual['tools'])==53
          original_messages=actual['messages'];messages,projection=text_view(original_messages)
          assert all(not m.get('reasoning_content') for m in original_messages if m['role']=='assistant'),'unexpected_past_R_requires_audit'
          target=deepcopy(message);target.setdefault('reasoning_content','')
          all_messages=messages+[target]
          d=reviews.get(episode,{}).get(call_folder.name)
          if d:
            assert d['response_sha256']==digest(response_path) and d['semantic_approved'] is True
            assert d['approved_components']==[] and d['loss_multiplier']==0.25
            for r in d['approved_field_ranges']:
                assert r['field']=='reasoning_content' and sha(target[r['field']][r['start']:r['end']].encode())==r['text_sha256']
          stat['captured_complete_http_responses']+=1
          raw_recovered.append({'episode':episode,'call_id':call_folder.name,'request':actual,
                'response_message':target,'provider_meta':meta,'receipt':receipt,
                'request_sha256':digest(request_path),'response_sha256':digest(response_path),
                'original_past_R_was_absent_no_recovery_injected':True})
          for view in ('fullnative53','core7'):
            tools=actual['tools'] if view=='fullnative53' else [t for t in actual['tools'] if t['function']['name'] in CORE]
            assert len(tools)==(53 if view=='fullnative53' else 7)
            target_index=len(all_messages)-1
            owned={target_index:{'id':episode+':'+call_folder.name,'mechanical_usable':True}} if d else {}
            compiled=compiler.compile_messages(all_messages,tools,owned,independent=True)
            approved_ranges=[{**r,'message_index':target_index} for r in d['approved_field_ranges']] if d else []
            if d:selector.select_reviewed_spans(compiler,all_messages,tools,compiled,[],approved_ranges)
            assert all(c=='R' for _,_,c,_ in compiled['supervision_spans'])
            rendered=serial(compiler,all_messages,tools)
            encoded=tok(rendered,add_special_tokens=False,return_offsets_mapping=True)
            assert encoded['input_ids']==compiled['input_ids']
            offsets=encoded['offset_mapping']
            current=compiled['targets'][-1]
            past_end=current['rendered_assistant_span'][0]
            past_tokens=bisect_left([a for a,b in offsets],past_end)
            gen_render=serial(compiler,messages,tools,True,True)
            causal_request_tokens=len(tok.encode(gen_render,add_special_tokens=False))
            # Diagnostic official template request count: matches existing32799,
            # explicitly a different generation-prefix measurement from SFT.
            official_request=tok.apply_chat_template(original_messages,tools=tools,tokenize=True,
                add_generation_prompt=True,enable_thinking=False)
            last=max((s[1] for s in compiled['supervision_spans']),default=None)
            metric={'episode':episode,'stage':job['stage'],'call_id':call_folder.name,'view':view,
                'tools':len(tools),'request_sha256':digest(request_path),'response_sha256':digest(response_path),
                'original_request_messages_sha256':sha(js(original_messages).encode()),
                'student_messages_sha256':sha(js(all_messages).encode()),'text_block_projections':projection,
                'past_assistant_R_characters':0,'current_original_R_characters':len(target['reasoning_content']),
                'exact_past_tokens_before_current_assistant':past_tokens,
                'causal_thinking_request_tokens':causal_request_tokens,
                'official_non_thinking_request_tokens':len(official_request),
                'whole_response_tokens':compiled['total_tokens'],'last_approved_R_end_token':last,
                'approved_R_tokens':compiled['supervised_tokens'],'approved_R_characters':sum(r['end']-r['start'] for r in approved_ranges),
                'supervision_spans':compiled['supervision_spans'],
                'input_ids_sha256_u32le':compiled['input_ids_sha256_u32le'],
                'rendered_sha256':compiled['rendered_sha256'],
                'limits':{str(n):{'past_fits':past_tokens<=n,'thinking_request_fits':causal_request_tokens<=n,
                    'whole_response_fits':compiled['total_tokens']<=n,
                    'all_approved_R_fits_with_full_past':last<=n if last is not None else None,
                    'approved_R_tokens_fitting_prefix':sum(max(0,min(b,n)-a) for a,b,c,w in compiled['supervision_spans'] if a<n)} for n in LIMITS}}
            coverage.append(metric)
            if d and view=='fullnative53':
                row_id='native64k_'+episode+'_'+call_folder.name
                full_ids=compiled['input_ids'];end=len(full_ids)
                if end>args.max_length and last<=args.max_length:end=last
                admitted=end<=args.max_length
                audit={'id':row_id,'status':'CONDITIONAL_NATIVE_64K_ONLY_NOT_READY_TO_TRAIN' if admitted else 'HOLD_REQUIRED_PAST_OR_APPROVED_R_EXCEEDS_CANDIDATE_LIMIT',
                    'whole_response_tokens':len(full_ids),'candidate_tokens':end if admitted else None,
                    'last_approved_R_end_token':last,'supervised_R_tokens':compiled['supervised_tokens'],
                    'full_past_retained':True,'candidate_is_whole_response':admitted and end==len(full_ids),
                    'omitted_only_future_unsupervised_completion_tokens':len(full_ids)-end if admitted else None,
                    'no_artificial_stop_or_thinking_close_inserted':True,'loss_multiplier':0.25,
                    'whole_response_hash':compiled['input_ids_sha256_u32le']}
                if admitted:
                    ids=full_ids[:end];labels=[-100]*len(ids);weights=[0.0]*len(ids)
                    for a,b,c,w in compiled['supervision_spans']:
                        assert b<=end
                        for i in range(a,b):labels[i]=ids[i];weights[i]=w*0.25
                    arrays=HERE/'arrays'/row_id;arrays.mkdir(parents=True,exist_ok=True)
                    audit['arrays']=[numbers(arrays/'input_ids.u32','I',ids),numbers(arrays/'labels.i64','q',labels),numbers(arrays/'loss_weights.f32','f',weights)]
                    assert sum(x!=-100 for x in labels)==compiled['supervised_tokens']
                    assert all(w==0.25 if label!=-100 else w==0.0 for label,w in zip(labels,weights))
                    record={**compiled,'id':row_id,'schema_version':'wrd-v10-conditional-native64k-candidate-1',
                        'input_ids':ids,'total_tokens':len(ids),'input_ids_sha256_u32le':causal.int_sha(ids),
                        'supervision_spans':[[a,b,c,w*0.25] for a,b,c,w in compiled['supervision_spans']],
                        'messages':all_messages,'tools':tools,'source_ids':job['source_ids'],'stage':job['stage'],
                        'split':'train','bank':'conditional_native64k_only','candidate_training_readiness':False,
                        'semantic_review':d,'evidence':metric,'candidate_audit':audit,
                        'complete_response_input_ids_sha256_u32le':compiled['input_ids_sha256_u32le'],
                        'future_prefix_is_not_full_response':end<len(full_ids),'original_request_past_R_not_injected':True,
                        'action_schema_may_contain_original_errors_all_action_labels_are_minus100':True,
                        'whole_response_original_retained_in_raw_archive':True,'training_started':False,'weights_loaded':False}
                    for item in record['targets']:
                        item['owned_supervision_spans']=[[a,b,c,w*0.25] for a,b,c,w in item.get('owned_supervision_spans',[])]
                    record['supervision_spans_sha256']=sha(js(record['supervision_spans']).encode())
                    record['complete_rendered_sha256']=compiled['rendered_sha256']
                    record['rendered_sha256']=sha(tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False).encode())
                    record['rendered_sha256_definition']='UTF8_SHA_OF_EXACT_TOKEN_PREFIX_DECODE; complete_rendered_sha256 hashes full causal rendering'
                    candidate_records.append(record)
                candidate_audit.append(audit)
          print(js({'episode':episode,'complete_http':stat['captured_complete_http_responses'],'last_call':call_folder.name}),flush=True)
        episode_summary.append(stat)
    for filename,data in [('recovered_originals.jsonl.gz',raw_recovered),('coverage_per_call.jsonl.gz',coverage),('candidate_native64k.jsonl.gz',candidate_records)]:
        with gzip.open(HERE/filename,'wt',encoding='utf-8',newline='\n') as f:
            for row in data:f.write(js(row)+'\n')
    summary=[]
    for episode in ('ALL',)+EPISODES:
      for view in ('fullnative53','core7'):
        values=[r for r in coverage if r['view']==view and (episode=='ALL' or r['episode']==episode)]
        for limit in LIMITS:
            summary.append({'episode':episode,'view':view,'context_limit':limit,'http_responses':len(values),
                'past_fits':sum(r['limits'][str(limit)]['past_fits'] for r in values),
                'thinking_request_fits':sum(r['limits'][str(limit)]['thinking_request_fits'] for r in values),
                'whole_response_fits':sum(r['limits'][str(limit)]['whole_response_fits'] for r in values),
                'approved_R_responses':sum(r['last_approved_R_end_token'] is not None for r in values),
                'all_approved_R_with_full_past_fits':sum(r['limits'][str(limit)]['all_approved_R_fits_with_full_past'] is True for r in values),
                'approved_R_tokens':sum(r['approved_R_tokens'] for r in values),
                'approved_R_tokens_fitting_prefix':sum(r['limits'][str(limit)]['approved_R_tokens_fitting_prefix'] for r in values),
                'max_whole_response_tokens':max(r['whole_response_tokens'] for r in values)})
    with (HERE/'COVERAGE_SUMMARY.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
    for p in pins.values():assert digest(p['path'])==p['sha256'],'source_changed_during_read'
    save(HERE/'SOURCE_PINS.json',list(pins.values()))
    save(HERE/'CANDIDATE_AUDIT.json',candidate_audit)
    report={'status':'CONDITIONAL_NATIVE_64K_ONLY_NOT_READY_TO_TRAIN','max_length':args.max_length,
        'design_revision_read':'5.0.39','shared_compile_main_sha256':FROZEN_MAIN_SHA,
        'frozen_sources_unmodified':{name:digest(frozen/name)==digest(path) for name,path in originals.items()},
        'candidate_driver_is_separate_explicit_max_length_not_shared_compiler_patch':True,
        'frozen_source_diff':'tools/compile_main.frozen.py is byte-identical; no modifications and no constant replacements',
        'episodes':episode_summary,'coverage_summary':summary,'candidate_records':len(candidate_records),
        'candidate_positive_R_tokens':sum(r['supervised_tokens'] for r in candidate_records),
        'candidate_audit':candidate_audit,'tokenizer_proof':compiler.proof,
        'raw_api_archive':{'path':raw_archive.name,'sha256':digest(raw_archive),'bytes':raw_archive.stat().st_size},
        'length_unit':'local pinned Qwen tokenizer tokens under declared causal serialization variant',
        'http_responses_are_not_paid_model_calls':True,'raw_compatibility_api_not_final_CodeBuddy_provider_prompt':True,
        'previous_R_not_recovered_or_injected':True,'only_new_current_original_R_is_reviewed_supervision':True,
        'shared_files_changed':False,'active_manifest_changed':False,'native_execution_started':False,
        'weights_loaded':False,'torch_installed':False,'model_forward_started':False,'training_started':False,
        'Spark_remote_test':'NOT_PERFORMED','position_extension_beyond_40960':'REQUIRED_BUT_NOT_ENABLED',
        'training_sufficiency':'NOT_ESTABLISHED_SIX_LOCAL_APPROVALS_ARE_NOT_SIX_INDEPENDENT_TASKS',
        'script_sha256':digest(Path(__file__))}
    save(HERE/'REPORT.json',report)
    save(HERE/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,**compiler.proof})
    save(HERE/'COMPLETE.json',{'status':'COMPLETE_CPU_ONLY_CONDITIONAL_CANDIDATE','report_sha256':digest(HERE/'REPORT.json'),
        'files':[{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in HERE.rglob('*') if p.is_file() and p.name!='COMPLETE.json']})
    print(js({'episodes':len(episode_summary),'complete_http_responses':sum(s['captured_complete_http_responses'] for s in episode_summary),
        'candidate_records':len(candidate_records),'candidate_R_tokens':report['candidate_positive_R_tokens']}),flush=True)

if __name__=='__main__':main()
