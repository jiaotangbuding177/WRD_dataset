"""First3 historical R candidate: narrow mixed claims, retain grounded design.

Old native conditions are NOT claimed. Original input/R stay complete. All old
ActionProposal outputs and every wrong/unreviewed R token remain zero loss.
"""
from __future__ import annotations
from array import array
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261027_wrd_main_v10'
PARENT=BASE/'historical_v6_reasoning_review_01'
HERE=PARENT/'first3_semantic_revision_02'
V6=ROOT/'output/20261026_wrd_sequences_v6/controlled'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(l) for l in f if l.strip()]
def save(p,v):
    assert not p.exists(),str(p)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def arr(p,code,values):
    a=array(code,values)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes())
    return {'path':str(p.relative_to(HERE)),'sha256':digest(p),'bytes':p.stat().st_size,
        'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[code],'count':len(values)}

def main():
    assert not (HERE/'COMPLETE.json').exists()
    original_review_path=PARENT/'first3_semantic_review_01/REVIEW.json';old=load(original_review_path)
    pairs={r['id']:r for r in rows(V6/'reasoning_pairs.original116.jsonl.gz')}
    revised=[];changes=[]
    def fragment(base,a,b,suffix=''):
        r=pairs[base['pair_id']]['original_response']['choices'][0]['message']['reasoning_content']
        value=deepcopy(base);value.update(id=base['id']+suffix,start=a,end=b,text=r[a:b],text_sha256=sha(r[a:b].encode()),parent_range_id=base['id'])
        assert a<b and base['start']<=a<b<=base['end'];revised.append(value)
    for r in old['ranges']:
        if r['source_id']=='conv_b5e6f3d3bab9' and r['decision']=='decision_004' and r['text'].startswith('- 真实表格结构：'):
            text=r['text'];a=text.index('，与本会话标题');b=text.index('真实资源是合成脱敏练习材料')
            fragment(r,r['start'],r['start']+a,'a');fragment(r,r['start']+b,r['end'],'b')
            changes.append({'id':r['id'],'reason':'Do not label historical sheet names as this conversation title; retain actual staged structure and explicit synthetic identity.'})
        elif r['source_id']=='conv_5ca3f6271b31' and r['decision']=='decision_002' and r['text'].startswith('The code must operate on WORKSPACE.'):
            text=r['text'];a=text.index('But resource_id is given;')
            fragment(r,r['start'],r['start']+a)
            changes.append({'id':r['id'],'reason':'Keep explicit delivered path / future parameter design; withdraw unsupported claim that choosing first glob result is generally safe.'})
        elif r['source_id']=='conv_6ebe8e1cb53e' and r['decision']=='decision_001' and r['text'].startswith('Key requirements from user corrections:'):
            text=r['text'];a=text.index(' (cover ends naturally, body starts page 2).');b=a+len(' (cover ends naturally, body starts page 2).')
            fragment(r,r['start'],r['start']+a,'a');fragment(r,r['start']+b,r['end'],'b')
            changes.append({'id':r['id'],'reason':'User reported a blank page; a specific cover/section implementation has not been verified and is not an explicit requirement.'})
        else:revised.append(deepcopy(r))
    by_key={(p.get('episode_id'),p['request_ordinal']):p for p in pairs.values() if p.get('episode_id') in old['full_R_read_sources']}
    def add_between(source,decision,start,end,why,facts):
        p=by_key[(source,decision)];r=p['original_response']['choices'][0]['message']['reasoning_content']
        assert r.count(start)==r.count(end)==1,(source,decision,start,end)
        a,b=r.index(start),r.index(end);assert a<b
        value={'id':f'V6R_DESIGN_{len(revised)+1:03d}','pair_id':p['id'],'source_id':source,'decision':decision,
            'field':'reasoning_content','start':a,'end':b,'text':r[a:b],'text_sha256':sha(r[a:b].encode()),
            'speech_act':'SOURCE_GROUNDED_REQUIREMENT_OR_PARAMETER_DESIGN_NOT_EXECUTED_SUCCESS',
            'rationale':why,'required_fact_ids':facts,'semantic_credit':'CANDIDATE_LOCAL_AI_SILVER_ROOT_PENDING',
            'loss_multiplier':0.25,'current_native_equivalence':False,'whole_stage_skill_quality_approved':False}
        revised.append(value)
    add_between('conv_6ebe8e1cb53e','decision_002','  "parameters": {\n    "input_path": "future user-provided raw usage workbook (.xlsx)"','  "requirements": [',
        'Explicit future input/output/platform/date/currency parameters avoid freezing current business values. This is proposed resource design, not proof of a generated report.',
        ['U_SOURCE_USER_CORRECTIONS','U_ACTUAL_SYSTEM_PARAMETER_RULE'])
    add_between('conv_6ebe8e1cb53e','decision_002','  "requirements": [\n    {"text":"报告需覆盖本期开通账号数','    {"text":"Word 文档不得出现空白页',
        'The first six requirement objects retain actual user corrections and their exact source references. The later unverified section-layout addition is excluded.',
        ['U_SOURCE_USER_CORRECTIONS'])
    add_between('conv_b5e6f3d3bab9','decision_002','  "parameters": {\n    "input_path": "未来用户提供的待脱敏表格路径','  "requirements": [',
        'A proposed parameter interface uses delivered input/output paths and header-based column binding instead of hardcoded historical columns. Column kinds are parameters, not an assertion that the current unknown workbook contains them.',
        ['B_SOURCE_USER_TURNS','B_MATERIAL_IDENTITY'])
    add_between('conv_5ca3f6271b31','decision_001',' "parameters":{"input_docx_path":"申报书docx路径',' "requirements":[',
        'The specific first-payment value is explicitly an example for a future parameter, while input and output paths remain caller-supplied. No legal compliance or successful budget allocation is certified.',
        ['D_SOURCE_USER_REQUIREMENTS','D_CURRENT_INPUT_CATALOG'])
    for pair_id in {r['pair_id'] for r in revised}:
        selected=sorted([r for r in revised if r['pair_id']==pair_id],key=lambda r:r['start'])
        assert all(a['end']<=b['start'] for a,b in zip(selected,selected[1:])),(pair_id,'overlap')
    review=deepcopy(old);review.update(schema='wrd-historical-v6-first3-original-R-semantic-revision-2',
        ranges=revised,review_revision=2,parent_review={'path':str(original_review_path),'sha256':digest(original_review_path)},
        non_destructive_changes=changes,
        candidate_positive_spans=len(revised),candidate_positive_original_characters=sum(r['end']-r['start'] for r in revised),
        candidate_original_response_owners=len({r['pair_id'] for r in revised}))
    for item in review['inventory']:
        count=sum(r['end']-r['start'] for r in revised if r['pair_id']==item['pair_id'])
        item['candidate_positive_original_characters']=count
        item['all_other_original_characters_mask0']=item['original_R_characters']-count
        item['candidate_spans']=sum(r['pair_id']==item['pair_id'] for r in revised)
    save(HERE/'REVIEW.json',review)
    scope_path=BASE/'clean_inputs/source_scope.metadata.jsonl.gz';scope={r['source_id']:r for r in rows(scope_path)}
    assert all(scope[s]['status']=='TRAIN' for s in review['full_R_read_sources'])
    causal_path=ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py'
    select_path=ROOT/'research/data_prep/wrd_main_v10/compile_main.py'
    causal=module('v6r_existing_causal',causal_path);selector=module('v6r_existing_span_selector',select_path)
    compiler=causal.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    compiled=[];stats=Counter()
    for pair_id in sorted({r['pair_id'] for r in revised}):
        p=pairs[pair_id];message=deepcopy(p['original_response']['choices'][0]['message'])
        request=deepcopy(p['original_request']);messages=request['messages']+[message];target=len(messages)-1
        for m in messages:
            if m['role']=='assistant':m.setdefault('reasoning_content','')
        assert not request.get('tools'),'original EWI tools are described in the historical policy payload, not current native tool calls'
        fields=[{'message_index':target,'field':'reasoning_content','start':r['start'],'end':r['end'],'text_sha256':r['text_sha256']} for r in revised if r['pair_id']==pair_id]
        result=compiler.compile_messages(messages,[],{target:{'id':pair_id,'mechanical_usable':True}},independent=True)
        selector.select_reviewed_spans(compiler,messages,[],result,[],fields)
        assert 0<result['supervised_tokens'] and result['total_tokens']<=32768
        assert all(c=='R' for a,b,c,w in result['supervision_spans'])
        result['supervision_spans']=[[a,b,c,w*.25] for a,b,c,w in result['supervision_spans']]
        for item in result['targets']:item['owned_supervision_spans']=[[a,b,c,w*.25] for a,b,c,w in item['owned_supervision_spans']]
        ids=result['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids)
        for a,b,c,w in result['supervision_spans']:
            for i in range(a,b):labels[i]=ids[i];weights[i]=w
        source=p['episode_id'];folder=HERE/'arrays'/pair_id
        refs=[arr(folder/'input_ids.u32','I',ids),arr(folder/'labels.i64','q',labels),arr(folder/'loss_weights.f32','f',weights)]
        row={**result,'id':'historical_v6_R02_'+pair_id,'canonical_original_response_owner':pair_id,
            'messages':messages,'tools':[],'bank':'HISTORICAL_EWI_R_ONLY_CANDIDATE_NOT_NATIVE_EQUIVALENT',
            'source_ids':[source],'source_group_id':scope[source]['component_id'],'split':'train',
            'source_admission':'CURRENT_TRAIN_SOURCE_PLUS_OLD_CLOSED_RESOURCE_GRAPH_FINAL_REVIEW_PENDING',
            'training_admitted':False,'root_main_admission':False,'full_autonomous_controller_demonstration':False,
            'schema_version':'wrd-v10-historical-R-only-candidate-02','stage':'historical_workflow_design_and_local_diagnosis',
            'original_historical_action':p['observed_parsed_output']['kind'],'original_request_source':p['source_request'],'original_SSE_source':p['source_sse'],
            'source_teacher_role':p['role_scope'],'source_historical_condition':p['historical_condition'],
            'current_native_runtime_equivalence_claimed':False,'original_teacher_decisions_not_rewritten_as_native_calls':True,
            'new_semantic_review':{'path':str(HERE/'REVIEW.json'),'sha256':digest(HERE/'REVIEW.json')},
            'approved_field_ranges':fields,'binary_arrays':refs,'loss_multiplier':.25,
            'all_original_request_messages_and_whole_current_response_preserved':True,
            'original_R_rewritten_or_summarized':False,'all_old_ActionProposal_JSON_body_loss':0,
            'whole_resource_quality_or_reuse_benefit_approved':False,'training_started':False,'weights_loaded':False}
        row['supervision_spans_sha256']=sha(js(row['supervision_spans']).encode())
        compiled.append(row);stats['sequences']+=1;stats['input_tokens']+=len(ids);stats['positive_R_tokens']+=result['supervised_tokens']
        stats['le16k']+=len(ids)<=16384;stats['le32k']+=len(ids)<=32768
    with gzip.open(HERE/'candidate_R_only.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for row in compiled:f.write(js(row)+'\n')
    save(HERE/'CAUSAL_TEMPLATE.json',{'variant':compiler.plain_template})
    save(HERE/'COMPLETE.json',{'status':'ACTUAL_R_ONLY_CANDIDATE_ARRAYS_BUILT_NOT_ACTIVE','stats':dict(stats),
        'original_response_owners':len(compiled),'source_groups':len({r['source_group_id'] for r in compiled}),
        'all_positive_classes':['R'],'candidate_R_original_characters':review['candidate_positive_original_characters'],
        'review_sha256':digest(HERE/'REVIEW.json'),'candidate_sha256':digest(HERE/'candidate_R_only.jsonl.gz'),
        'current_scope_sha256':digest(scope_path),'causal_compiler_sha256':digest(causal_path),'selector_sha256':digest(select_path),
        'script_sha256':digest(Path(__file__)),'root_main_admission':False,'training_started':False,'weights_loaded':False,'new_native_calls':0})
    print(js(load(HERE/'COMPLETE.json')))

if __name__=='__main__':main()
