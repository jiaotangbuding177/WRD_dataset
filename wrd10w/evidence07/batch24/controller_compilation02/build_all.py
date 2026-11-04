"""CPU tokenizer-only compilation of 19 bounded source-only controller labels."""
from pathlib import Path
from array import array
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path('D:/skillloop');HERE=Path(__file__).resolve().parent;BATCH=HERE.parent
OUT=HERE/'compiled'
INPUTS=[BATCH/'source_decisions_02/decisions.raw.jsonl.gz',BATCH/'remotion/source_only02/source_only_controller.raw.jsonl.gz']

def h(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def gz(p,rs):
    with p.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as f:
            for r in rs:f.write((js(r)+'\n').encode())
def load_module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def binary(p,kind,values):
    a=array(kind,values)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes())
    return {'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':h(p.read_bytes()),
        'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[kind]}

def main():
    assert not OUT.exists(), 'do not overwrite any compiled bank'
    original=[r for p in INPUTS for r in rows(p)];assert len(original)==19 and len({r['id'] for r in original})==19
    admitted=[]
    for source in original:
        r=deepcopy(source)
        assert r['training_admitted'] is False and r['source_admission']=='ADMIT_SOURCE_ONLY'
        assert r['loss_multiplier']==.25 and r['message_loss_mask']==[0,0,1] and r['approved_components']==['R','D']
        assert r['tools']==[] and len(r['messages'])==3 and r['messages'][2]['role']=='assistant'
        r.update(source_admission='ADMIT',training_admitted=True,root_main_admission=False,requires_external_root_admission=True,
            supervision_message_indices=[2],original226=[],holdout12=[],protected_sources_visible_prefix=[],protected_source_ids=[],
            owner_id='new_annotation:'+r['id'],actual_native_tool_dispatch=False,original_R_positive_tokens=0,original_A_positive_tokens=0,
            is_full_autonomous_execution_demonstration=False,artifact_or_skill_semantic_gold=False,confirmed_repair=False,
            qualified_skill_KEEP=False,root_approval_is_not_tokenizer_QA=True)
        r['target_owner']={'canonical_new_annotation_owner_id':'new_annotation:'+r['id'],
            'original_teacher_R_or_A_owner':None,'scope':'source_only_new_decision_not_native_action'}
        r['source_only_authorization']={'root_explicit_approval':'Root reviewed six Remotion decisions and independently accepted peer-reviewed version02 thirteen decisions before compilation; final main-manifest admission remains external.',
            'root13_peer':pin(BATCH/'source_decisions_peer/PEER.json'),'original_input_pin':next(pin(p) for p in INPUTS if any(x['id']==r['id'] for x in rows(p)))}
        admitted.append(r)
    raw=HERE/'approved.raw.jsonl.gz';assert not raw.exists();gz(raw,admitted)
    compiler=ROOT/'research/data_prep/wrd_main_v10/compile_main.py'
    subprocess.run([sys.executable,str(compiler),'--input',str(raw),'--output',str(OUT)],check=True,cwd=ROOT)
    report=json.loads((OUT/'COMPILATION_REPORT.json').read_text(encoding='utf-8'))
    assert report['counts']['input_records']==19
    allowed_ids={r['id'] for r in admitted};actual=[];array_refs=[]
    for f in report['files']:
        p=OUT/f['path'];rs=rows(p)
        for r in rs:
            assert r['id'] in allowed_ids and r['total_tokens']<=32768
            labels=[-100]*len(r['input_ids']);weights=[0.]*len(labels)
            for lo,hi,component,w in r['supervision_spans']:
                assert component in {'R','D'} and w==.25
                for i in range(lo,hi):assert labels[i]==-100;labels[i]=r['input_ids'][i];weights[i]=w
            aid=h(r['id'].encode())[:24]
            refs=[binary(OUT/'arrays'/aid/n,k,v) for n,k,v in [('input_ids.u32le.bin','I',r['input_ids']),('labels.i64le.bin','q',labels),('loss_weights.f32le.bin','f',weights)]]
            r['binary_arrays']=refs;array_refs.extend(refs)
            actual.append({'id':r['id'],'stage':r['stage'],'source_ids':r['source_ids'],'source_group_id':r['source_group_id'],
                'total_tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],'supervised_tokens_by_component':r['supervised_tokens_by_component']})
        gz(p,rs);f.update(bytes=p.stat().st_size,sha256=h(p.read_bytes()))
    save(OUT/'COMPILATION_REPORT.json',report)
    assert len(actual)+len(rows(OUT/'held.jsonl.gz'))==19
    # Independent verifier renders the saved template with both tokenizer sets
    # directly; it does not call CausalCompiler to reproduce expected IDs.
    verifier=ROOT/'research/data_prep/wrd_main_v10/verify_compilation.py'
    subprocess.run([sys.executable,str(verifier),'--compiled',str(OUT),'--out',str(HERE/'DIRECT_DUAL_TOKENIZER_MASK_QA.json')],check=True,cwd=ROOT)
    direct=load_module('controller_direct_mask_verifier',ROOT/'research/data_prep/wrd_main_v10/verify_main05.py')
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
    toks={n:AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False)for n in ['primary_14b','control_8b']}
    template=_compile_jinja_template(json.loads((OUT/'CAUSAL_TEMPLATE.json').read_text(encoding='utf-8'))['variant'])
    seen=[];allarr=Counter();first=None
    for f in report['files']:
        for r in rows(OUT/f['path']):
            direct.verify_token_row(r,template,toks);first=first or r
            rr={x['dtype']:x for x in r['binary_arrays']}
            read=[]
            for kind,dtype in [('I','uint32_le'),('q','int64_le'),('f','float32_le')]:
                ref=rr[dtype];p=OUT/ref['path'];assert h(p.read_bytes())==ref['sha256'] and p.stat().st_size==ref['bytes']
                a=array(kind);a.frombytes(p.read_bytes())
                if sys.byteorder!='little':a.byteswap()
                assert len(a)==r['total_tokens'];read.append(a)
            ids,labels,weights=read;assert list(ids)==r['input_ids']
            wanted=[False]*len(ids)
            for lo,hi,component,w in r['supervision_spans']:
                for i in range(lo,hi):wanted[i]=True;assert labels[i]==ids[i] and weights[i]==w
            assert all((labels[i]==-100 and weights[i]==0.) if not wanted[i] else (labels[i]==ids[i] and weights[i]==.25) for i in range(len(ids)))
            allarr.update(arrays=3,source_positions=len(ids),positive_labels=sum(wanted));seen.append(r['id'])
    # A malformed positive label on the prompt must be rejected by direct offsets.
    canary=deepcopy(first);canary['supervision_spans']=[[0,1,'D',.25]]+canary['supervision_spans']
    try:direct.verify_token_row(canary,template,toks)
    except AssertionError as e:
        assert str(e)=='INPUT_OR_ROLE_HEADER_HAS_LOSS';negative={'status':'PASS_REJECTED_PROMPT_POSITIVE_LOSS','error':str(e)}
    else:raise AssertionError('negative canary escaped')
    save(HERE/'ARRAYS_AND_MASK_QA.json',{'status':'PASS','every_row_independently_dual_rendered':len(seen),
        'all_binary_counts':dict(allarr),'negative_prompt_loss_canary':negative,'source_and_historical_self_report_input_loss_zero':True,
        'only_new_assistant_index2_R_D_has_loss':True,'training_started':False,'weights_loaded':False})
    components=Counter()
    for r in actual:components.update(r['supervised_tokens_by_component'])
    status={'status':'ACTUAL_COMMON_14B_8B_BANK_ROOT_MAIN_ADMISSION_PENDING','raw_input_candidates':19,
        'compiled_sequences':len(actual),'compiled_targets':len(actual),'held':rows(OUT/'held.jsonl.gz'),
        'input_tokens':sum(r['total_tokens']for r in actual),'supervised_tokens':sum(r['supervised_tokens']for r in actual),
        'supervised_tokens_by_component':dict(components),'weighted_supervised_tokens':sum(components.values())*.25,
        'le16k':sum(r['total_tokens']<=16384 for r in actual),'gt16k_le32k':sum(16384<r['total_tokens']<=32768 for r in actual),
        'le32k':sum(r['total_tokens']<=32768 for r in actual),'distinct_sources':len({s for r in actual for s in r['source_ids']}),
        'distinct_source_groups':len({r['source_group_id'] for r in actual}),'by_stage':dict(Counter(r['stage']for r in actual)),
        'origin':'NEW_AUTHORED_SOURCE_ONLY_R_AND_DECISION_BODY_NOT_ORIGINAL_R_OR_A',
        'actual_resource_constructions':0,'actual_repair_successes':0,'qualified_KEEPS':0,'native_A_to_D_demonstrations':0,
        'primary_and_control_use_same_owner_and_labels':True,'no_context_truncation':True,
        'original_inputs':[pin(p)for p in INPUTS],'actual_raw_approved_copy':pin(raw),'compilation_report':pin(OUT/'COMPILATION_REPORT.json'),
        'direct_QA':pin(HERE/'DIRECT_DUAL_TOKENIZER_MASK_QA.json'),'array_QA':pin(HERE/'ARRAYS_AND_MASK_QA.json'),
        'record_statistics':actual,'training_started':False,'weights_loaded':False,'new_Agent_calls':0,'ACTIVE_modified':False,
        'script_sha256':h(Path(__file__).read_bytes())}
    save(HERE/'BUILD.json',status)
    save(HERE/'ROOT_SEMANTIC_ADMISSION.template.json',{'status':'ROOT_SIGNATURE_PENDING_NOT_ADMITTED_TO_MAIN',
        'record_ids':[r['id']for r in actual],'compilation_report_sha256':h((OUT/'COMPILATION_REPORT.json').read_bytes()),
        'scope':'SOURCE_ONLY_NEWLY_AUTHORED_SCHEDULING_FEEDBACK_AND_UNKNOWN_STATE_DECISIONS',
        'original_R_or_A_tokens':0,'no_actual_resource_or_successful_repair_credit':True,'no_native_autonomous_chain_or_KEEP_credit':True,
        'build_pin':pin(HERE/'BUILD.json'),'root_reviewer_must_check':True,'training_started':False})
    print(js({k:v for k,v in status.items()if k in ['status','compiled_targets','input_tokens','supervised_tokens','supervised_tokens_by_component','le16k','gt16k_le32k','distinct_sources','distinct_source_groups']}))

if __name__=='__main__':main()
