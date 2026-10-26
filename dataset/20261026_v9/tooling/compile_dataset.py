"""Actual CPU-only v9 SFT compilation; no model, agent or business execution.

Historical skill quality, protocol practice and newly annotated coordination
are separate banks. Original unsuccessful/unknown actions remain context-only.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9'
CORE = {'ls', 'read', 'edit', 'write', 'apply_patch', 'exec', 'process'}
STUDENT_SYSTEM = '''你是WRD技能沉淀助手，在原生OpenClaw会话中使用提供的工具工作。依据当前可见的原始会话、用户纠正、实际输入和工具反馈，判断复用路线，制作工作流及程序、模板、资料，试做、评审、局部修订并交付skills。缺材料时说明缺口；未知结果不得报告成功。工具调用成功不等于内容正确；只有实际对应版本的试跑证据才能支持资源效果结论。保留失败观察并据反馈修订。不得读取或使用隔离评测来源。此训练视图的工具接口来自已核原生schema；当前状态之外的信息不可假设。'''


def js(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def sha(x): return hashlib.sha256(x if isinstance(x, bytes) else x.encode()).hexdigest()
def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def rows(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def gzopen(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    return gzip.open(p, 'wt', encoding='utf-8', newline='\n')
def write(f, v): f.write(js(v)+'\n')
def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def tid(e, i): return sha(e+':'+str(i))[:24]


def compact_label(r):
    return {k:r.get(k) for k in (
        'id','episode_id','source_message_index','source_admission','source_ids_visible_prefix',
        'protected_sources_visible_prefix','scope_status','unknown_reasons','outcome_quality_tier',
        'positive_skill_action_eligible','positive_outcome_loss_candidate','positive_quality_review_candidate',
        'quality_positive_review_candidate','positive_evidence_review_eligible','outcome_label_source_admission',
        'quality_positive_review_eligible_scope',
        'quality_label_source_admission','positive_silver_trial_edge_ids','linked_trial_edge_ids',
        'exact_produced_version_ids','after_actual_feedback_read','source_message_sha256',
        'source_event_line','stage','route_id','review_evidence_check')}


def validation(m, registry):
    from jsonschema import Draft202012Validator
    reasons=[]; calls=m.get('tool_calls', [])
    for c in calls:
        fn=c.get('function',{}); name=fn.get('name')
        if name not in registry: reasons.append('CURRENT_TOOL_NOT_IN_FIXED_CORE7_VERIFIED_SCHEMA');continue
        a=fn.get('arguments',{})
        if isinstance(a,str):
            try:a=json.loads(a)
            except ValueError:reasons.append('INVALID_ARGUMENTS_JSON');continue
        if list(Draft202012Validator(registry[name]['function']['parameters']).iter_errors(a)):
            reasons.append('ARGUMENTS_SCHEMA_INVALID')
        if name=='write' and isinstance(a,dict) and isinstance(a.get('content'),str):
            path=str(a.get('path',a.get('file_path',''))).lower()
            try:
                if path.endswith('.json'):json.loads(a['content'])
                if path.endswith('.py'):
                    import ast
                    ast.parse(a['content'])
            except (ValueError,SyntaxError,RecursionError):reasons.append('GENERATED_JSON_OR_PYTHON_SYNTAX_INVALID')
    return sorted(set(reasons))


def choose_quality(label, q, m, reasons):
    if label.get('source_admission')!='ADMIT':return None,0.0,['SOURCE_PREFIX_NOT_CLOSED']
    if label.get('protected_sources_visible_prefix'):return None,0.0,['PROTECTED_PREFIX']
    if reasons:return None,0.0,reasons
    if not q.get('nonempty', bool(m.get('content') or m.get('tool_calls'))):return None,0.0,['EMPTY_TARGET']
    if q.get('nonempty_incomplete_stop'):return None,0.0,['INCOMPLETE_NATIVE_STOP']
    if label.get('outcome_quality_tier')=='KNOWN_WRONG':return None,0.0,['KNOWN_WRONG_KEEP_CONTEXT']
    # Skill outcome metadata itself must be source-closed. It must never select
    # a positive using a protected future trial, even for a clean early action.
    skill=label.get('positive_skill_action_eligible') is True
    review=any(label.get(k) is True for k in ('positive_quality_review_candidate','quality_positive_review_candidate','positive_evidence_review_eligible'))
    label_scope=label.get('outcome_label_source_admission') or label.get('quality_label_source_admission')
    if (skill or review) and label_scope=='ADMIT':
        return ('outcome_skill_silver' if skill else 'evidence_review_silver'),1.0,[]
    # These independent syntactic, read-only protocol exercises are deliberately
    # NOT skill success or trial-derived credit. No future tool result is used
    # to declare the read correct. Unknown/mutating actions stay loss=0.
    names=[c.get('function',{}).get('name') for c in m.get('tool_calls',[])]
    if names and all(n in {'read','ls'} for n in names):
        if q.get('observed_tool_failure') is not False:
            return None,0.0,['OBSERVED_TOOL_FAILURE_OR_UNVERIFIED_RESULT_NOT_APPROVED_FOR_POSITIVE_PROTOCOL_LOSS']
        if m.get('content') or m.get('reasoning_content'):
            return None,0.0,['UNREVIEWED_EXPLANATION_NOT_APPROVED_BY_TOOL_FORMAT']
        return 'read_only_protocol_auxiliary',0.1,[]
    return None,0.0,['NO_ADMITTED_OUTCOME_OR_SEMANTIC_SUPERVISION']


class Union:
    def __init__(self):self.p={}
    def find(self,x):
        self.p.setdefault(x,x)
        if self.p[x]!=x:self.p[x]=self.find(self.p[x])
        return self.p[x]
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.p[max(a,b)]=min(a,b)


def compile_native(compiler, native_mod):
    canonical={}
    for e in rows(ROOT/'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz'):
        for i,m in enumerate(e['messages']):
            if m.get('role')=='assistant':canonical[tid(e['episode_id'],i)]=(sha(js(m)),sha(js(m.get('content'))),e['source_event_lines'][i])
    labels=defaultdict(dict)
    for r in rows(OUT/'outcomes/target_outcome_labels.jsonl.gz'):
        labels[r['episode_id']][r['source_message_index']]=compact_label(r)
    quality=defaultdict(dict)
    for r in rows(ROOT/'output/20261026_wrd_quality_v8/controlled/native_targets.quality.jsonl.gz'):
        quality[r['episode_id']][r['source_message_index']]={k:r.get(k) for k in ('nonempty','nonempty_incomplete_stop','observed_tool_failure','text_only_response','source_message_sha256')}
    counts=Counter(); by_stage=defaultdict(Counter); target_tiers=Counter(); length=Counter(); files=[]
    trace_path=OUT/'processed/native.student_traces.all.jsonl.gz'
    ledger_path=OUT/'processed/targets.processing.jsonl.gz'
    pre_path=OUT/'compiled/native.pre_split.jsonl.gz'
    with gzopen(trace_path) as traces,gzopen(ledger_path) as ledger,gzopen(pre_path) as samples:
        for ep in rows(OUT/'recovery/episodes.contexts.jsonl.gz'):
            eid=ep['episode_id']; counts['native_episodes_processed']+=1
            converted,indices,issues=native_mod.native_messages({'system':STUDENT_SYSTEM,'messages':ep['messages']})
            index_map={native_i:i for i,native_i in enumerate(indices) if native_i is not None}
            overlay_count=0
            for overlay in ep.get('reasoning_overlays_same_response_id',[]):
                index=overlay['message_index']
                if index in index_map:
                    m=converted[index_map[index]]
                    assert m['role']=='assistant' and not m.get('reasoning_content')
                    assert sha(overlay['text'])==overlay['text_sha256']
                    m['reasoning_content']=overlay['text'];overlay_count+=1
            counts['same_response_id_R_fields_preserved_in_student_views']+=overlay_count
            registry={t['name']:{'type':'function','function':t} for t in ep.get('tools_supported',[]) if t.get('name') in CORE}
            specs={}; local={}; source_ids=set(); raw_target_count=0;unsupported_prefix=False
            for ni,native_m in enumerate(ep['messages']):
                native_content=native_m.get('content')
                if isinstance(native_content,list) and any(isinstance(b,dict) and b.get('type') not in {'text','toolCall','thinking','reasoning'} for b in native_content):unsupported_prefix=True
                if native_m.get('role')!='assistant' or ni not in index_map:continue
                mi=index_map[ni];m=converted[mi];raw_target_count+=1
                label=labels[eid].get(ni,{'source_admission':'HOLD_MISSING_EVIDENCE','scope_status':'SUPPLEMENTAL_SOURCE_CLOSURE_NOT_ESTABLISHED'})
                q=quality[eid].get(ni,{})
                reasons=validation(m,registry)
                tier,weight,why=choose_quality(label,q,m,reasons)
                if unsupported_prefix:tier,weight,why=None,0.0,['NON_TEXT_OBSERVATION_NOT_REPRESENTED_IN_TEXT_ONLY_STUDENT_VIEW']
                if eid=='ep_4459b810deb6fe70c6dc' and ni==11:tier,weight,why=None,0.0,['KNOWN_CSS_CONTRAST_CONTENT_ERROR']
                if eid=='ep_4920642a6640d5045d90' and q.get('text_only_response'):tier,weight,why=None,0.0,['KNOWN_INCOMPLETE_DELIVERY_NO_POSITIVE_TERMINAL_CLAIM']
                owner=tid(eid,ni)
                if owner in canonical:
                    cm_hash,content_hash,source_line=canonical[owner]
                    assert content_hash==sha(js(native_m.get('content')))
                    assert ep['source_event_lines'][ni]==source_line
                    assert label.get('source_message_sha256')==cm_hash
                    assert q.get('source_message_sha256')==cm_hash
                specs[mi]={'id':owner,'source_message_index':ni,'mechanical_usable':tier is not None,'supervision_tier':tier,'loss_multiplier':weight}
                entry={'id':owner,'episode_id':eid,'source_message_index':ni,'stage':label.get('stage',ep.get('stage')),
                    'route_id':label.get('route_id',ep.get('route_id')),'source_admission':label.get('source_admission'),
                    'scope_status':label.get('scope_status'),'source_ids':label.get('source_ids_visible_prefix') or [],
                    'supervision_tier':tier,'loss_multiplier':weight,'mask_reasons':why,'scope_and_outcome_label':label,
                    'original_message_sha256':sha(js(native_m)), 'original_content_sha256':sha(js(native_m.get('content'))),
                    'quality_is_not_inferred_from_done_retain_or_exit0':True,'training_started':False}
                local[mi]=entry
                counts['assistant_positions_processed']+=1;counts['scope_'+str(label.get('source_admission'))]+=1
                if tier:source_ids.update(entry['source_ids']);target_tiers[tier]+=1
                by_stage[entry['stage'] or 'unknown'][tier or 'context_only']+=1
            # This serialization is a disclosed student task interface, not a
            # recovered original system or a claim that all native inputs survived.
            trace={'schema_version':'wrd-v9-student-native-view','episode_id':eid,'stage':ep.get('stage'),'route_id':ep.get('route_id'),
                'messages':converted,'tools':list(registry.values()),'source_native':ep['source_native'],
                'native_message_indices':indices,'original_system_capture_status':ep['system_capture_status'],
                'system_origin':'NEW_DECLARED_STUDENT_TASK_INTERFACE_NOT_ORIGINAL_SYSTEM',
                'tool_schema_provenance':ep.get('tool_schema_provenance'),'original_messages_recovered_separately':True,
                'raw_original_capture_is_not_claimed_complete':True,'targets':list(local.values()),'projection_issues':issues}
            write(traces,trace)
            if not any(s['mechanical_usable'] for s in specs.values()):
                for e in local.values():write(ledger,{**e,'admitted_in_common_32k':False})
                continue
            compiled=compiler.compile_messages(converted,list(registry.values()),specs,independent=True)
            counts['episodes_encoded_with_both_actual_tokenizers']+=1
            counts['encoded_all_sequence_tokens']+=compiled['total_tokens']
            active=[]
            for target in compiled['targets']:
                mi=target['message_index'];e=local[mi];end=target['response_end_token_exclusive'];ok=e['supervision_tier'] is not None
                if e['supervision_tier'] in {'outcome_skill_silver','evidence_review_silver'}:
                    # A file/version proof does not certify an adjacent thought,
                    # visible claim, or other action in the same response.
                    calls=converted[mi].get('tool_calls',[])
                    if len(calls)!=1 or calls[0].get('function',{}).get('name')!='write':
                        ok=False;e['mask_reasons'].append('SINGLE_FILE_CREDIT_CANNOT_COVER_MULTIACTION_RESPONSE')
                    else:
                        target['owned_supervision_spans']=[s for s in target['owned_supervision_spans'] if s[2]=='A']
                        target['supervised_tokens']=sum(s[1]-s[0]for s in target['owned_supervision_spans'])
                        target['credit_scope']='EXACT_SINGLE_TOOL_ARGUMENT_PAYLOAD_ONLY_NOT_ADJACENT_REASONING_OR_CLAIMS'
                if ok:
                    length['positive_targets_before_length_filter']+=1
                    length['positive_targets_le16k' if end<=16384 else 'positive_targets_gt16k']+=1
                    length['positive_targets_le32k' if end<=32768 else 'positive_targets_gt32k']+=1
                eligible=ok and end<=32768
                if eligible:active.append(target)
                write(ledger,{**e,'student_response_end_tokens':end,'admitted_in_common_32k':eligible,
                    'owned_spans_before_length_filter':target['owned_supervision_spans'] if ok else [],
                    'length_filter_never_truncates_source_prefix_or_target':True})
            if not active:continue
            end=max(t['response_end_token_exclusive'] for t in active)
            source_ids=set(s for t in active for s in local[t['message_index']]['source_ids'])
            spans=[]
            for t in active:
                multiplier=t['loss_multiplier']
                t['owned_supervision_spans']=[[lo,hi,cl,w*multiplier] for lo,hi,cl,w in t['owned_supervision_spans']]
                spans.extend(t['owned_supervision_spans'])
            spans.sort(); ids=compiled['input_ids'][:end]
            assert spans and all(0<=s[0]<s[1]<=len(ids) for s in spans)
            row={k:v for k,v in compiled.items() if k not in ('input_ids','supervision_spans','targets','assistant_generation_spans')}
            row.update(schema_version='wrd-causal-outcome-dataset-v9',id='native_'+eid,episode_id=eid,route_id=ep.get('route_id'),
                bank='native_process',input_ids=ids,total_tokens=len(ids),targets=active,supervision_spans=spans,
                supervised_tokens=sum(s[1]-s[0] for s in spans),source_ids=sorted(source_ids),
                source_closure='ACTUAL_VISIBLE_PREFIX_CLOSED_AND_LABEL_SOURCE_CLOSED_WHEN_OUTCOME_USED',
                messages=converted[:max(t['message_index'] for t in active)+1],tools=list(registry.values()),
                student_interface_projection=trace['system_origin'],source_native=ep['source_native'],
                full_trace_reference='processed/native.student_traces.all.jsonl.gz',label_ignore_index=-100,
                is_full_autonomous_execution_demonstration=False,training_started=False)
            row['input_ids_sha256_u32le']=native_mod.int_sha(ids)
            row['supervision_spans_sha256']=sha(js(spans))
            row['full_episode_rendered_sha256']=row.pop('rendered_sha256')
            row['rendered_sha256']=sha(compiler.tokenizers['primary_14b'].decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False))
            row['supervised_tokens_by_component']=dict(sum((Counter({s[2]:s[1]-s[0]})for s in spans),Counter()))
            write(samples,row);counts['native_compiled_sequences']+=1;counts['native_owned_targets']+=len(active)
            counts['native_supervised_tokens']+=row['supervised_tokens']
            if counts['native_episodes_processed']%100==0:print(js({'phase':'native_actual_SFT_compile','counts':dict(counts)}),flush=True)
    for p in (trace_path,ledger_path,pre_path):files.append({'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)})
    return {'counts':dict(counts),'stage_target_tiers':{k:dict(v)for k,v in by_stage.items()},'target_tiers_before_length_filter':dict(target_tiers),'length_counts':dict(length),'files':files}


def compile_coordination(compiler, paths):
    result=Counter();pre=OUT/'compiled/coordination.pre_split.jsonl.gz'
    with gzopen(pre)as output:
        for path in paths:
            for original in rows(path):
                result['input_rows']+=1
                clean_statuses={'CLEAN_ORIGINAL_INPUT_EXCLUDING_226_AND_HOLDOUT12','SOURCE_INDEPENDENT_RULE_NO_ENTERPRISE_CONTENT','CLEAN_OBSERVED_SOURCE_PREFIX','CLEAN_PROTOCOL_ONLY_PREFIX','CLEAN_PRODUCER_TARGET_PREFIX_V9'}
                if original.get('training_admitted') is not True or original.get('scope_status') not in clean_statuses or original.get('source_admission') in {'HOLD_PROTECTED','HOLD_MISSING_EVIDENCE','HOLD_UNKNOWN'}:
                    result['held_not_source_admitted']+=1;continue
                if original.get('original226') or original.get('holdout12') or original.get('protected_sources_visible_prefix'):
                    result['held_explicit_protected_ancestry']+=1;continue
                messages=deepcopy(original.get('messages',[]))
                if not messages or messages[-1].get('role')!='assistant':result['held_no_final_assistant']+=1;continue
                for m in messages:
                    if m.get('role')=='assistant':m.setdefault('reasoning_content','')
                current=len(messages)-1
                multiplier=float(original.get('recommended_relative_sampling_weight',0.2))
                assert 0<multiplier<=1
                approved=original.get('supervision_candidate_message_indices',[current])
                assert approved and all(isinstance(i,int)and 0<=i<len(messages)and messages[i]['role']=='assistant'for i in approved)
                if 'message_loss_mask'in original:
                    assert [i for i,v in enumerate(original['message_loss_mask'])if v] == approved
                owner=original.get('coordination_id',original.get('id',sha(js(original))[:24]))
                specs={i:{'id':owner if len(approved)==1 else owner+':m'+str(i),
                    'mechanical_usable':True,'supervision_tier':'program_rule_coordination','loss_multiplier':multiplier}for i in approved}
                c=compiler.compile_messages(messages,original.get('tools',[]),specs,independent=True)
                result['encoded_rows']+=1
                if c['total_tokens']>32768:result['held_gt32k_no_truncation']+=1;continue
                c['supervision_spans']=[[lo,hi,cl,w*multiplier]for lo,hi,cl,w in c['supervision_spans']]
                for target in c['targets']:
                    target['owned_supervision_spans']=[[lo,hi,cl,w*multiplier]for lo,hi,cl,w in target['owned_supervision_spans']]
                c['targets']=[t for t in c['targets']if t.get('mechanical_usable')is True and t['owned_supervision_spans']]
                c['supervision_spans_sha256']=sha(js(c['supervision_spans']))
                row={**c,'schema_version':'wrd-causal-outcome-dataset-v9','id':'coord_'+str(owner),
                    'bank':'coordination','messages':messages,'tools':original.get('tools',[]),
                    'route_id':original.get('route_id'),'source_ids':original.get('source_ids',[]),
                    'annotation_provenance':original.get('provenance',original.get('annotation_source',original.get('data_origin'))),
                    'rule_provenance':original.get('rule_provenance'),
                    'source_leakage_group_id':original.get('source_group_id'),
                    'coordination_original_record':{k:v for k,v in original.items()if k!='messages'},
                    'is_full_autonomous_execution_demonstration':False,
                    'training_started':False,'is_original_teacher_CoT':False}
                write(output,row);result['compiled_rows']+=1;result['supervised_tokens']+=c['supervised_tokens']
    return {'counts':dict(result),'file':{'path':str(pre),'bytes':pre.stat().st_size,'sha256':digest(pre)}}


def split_banks():
    paths=list((OUT/'compiled').glob('*.pre_split.jsonl.gz'));u=Union(); meta=[]
    for p in paths:
        for r in rows(p):
            key='row:'+r['id'];u.find(key)
            if r.get('route_id'):u.join(key,'route:'+r['route_id'])
            for source in r.get('source_ids',[]):u.join(key,'source:'+source)
            if r.get('source_leakage_group_id') and r.get('source_ids'):
                u.join(key,'source_leakage_group:'+r['source_leakage_group_id'])
            # Rule-only examples are one train-only auxiliary family, not an
            # independent evaluation of autonomous skills or template novelty.
            if not r.get('source_ids') and r['bank']=='coordination':u.join(key,'rule_family:v9')
            meta.append((r['id'],key,r['bank']))
    group_rows=defaultdict(list)
    for rid,key,bank in meta:group_rows[u.find(key)].append((rid,bank))
    group_ids={g:'group_'+sha(g)[:20]for g in group_rows}
    candidate_groups=sorted((g for g in group_rows if u.find('rule_family:v9')!=g),key=lambda g:sha('wrd-v9-split:'+g))
    split={g:'train'for g in group_rows}
    if len(candidate_groups)>=10:
        n=max(1,len(candidate_groups)//10)
        for g in candidate_groups[:n]:split[g]='dev'
        for g in candidate_groups[n:2*n]:split[g]='test'
    counts=Counter();by_bank=defaultdict(Counter);handles={};seen=set();manifest=[]
    try:
        for p in paths:
            for r in rows(p):
                assert r['id'] not in seen;seen.add(r['id']);g=u.find('row:'+r['id']);s=split[g]
                r['split']=s;r['source_component_id']=group_ids[g]
                bucket='16k'if r['total_tokens']<=16384 else '32k'
                name=f"{r['bank']}.{s}.{bucket}.jsonl.gz"
                if name not in handles:handles[name]=gzopen(OUT/'sft'/name)
                write(handles[name],r);counts[s+'_rows']+=1;counts[s+'_supervised_tokens']+=r['supervised_tokens'];counts[s+'_input_tokens']+=r['total_tokens']
                by_bank[r['bank']][s+'_rows']+=1;by_bank[r['bank']][s+'_supervised_tokens']+=r['supervised_tokens']
    finally:
        for f in handles.values():f.close()
    for name in sorted(handles):
        p=OUT/'sft'/name;manifest.append({'path':'sft/'+name,'bytes':p.stat().st_size,'sha256':digest(p)})
    groups=[{'component_id':group_ids[g],'split':split[g],'rows':len(group_rows[g]),'row_ids':[r[0]for r in group_rows[g]]}for g in sorted(group_rows)]
    save(OUT/'SOURCE_GROUP_SPLIT.json',{'schema_version':'wrd-v9-source-groups','groups':groups,'counts':dict(counts),
        'route_and_source_identity_union_before_split':True,'no_random_window_split':True,
        'dev_test_are_static_record_holdouts_not_closed_loop_success_measurements':True,
        'rule_only_family_is_train_only':True,'independent_components':len(group_rows),
        'independent_dev_test_available':any(s!='train'for s in split.values())})
    return {'counts':dict(counts),'by_bank':{k:dict(v)for k,v in by_bank.items()},'files':manifest,'source_components':len(group_rows)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--coordination-input',action='append',default=[]);parser.add_argument('--skip-native',action='store_true');args=parser.parse_args()
    started=time.monotonic();native=load_module('wrd_causal_v4',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py')
    compiler=native.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    report={'schema_version':'wrd-v9-actual-SFT-compilation','training_started':False,'weights_loaded':False,'new_business_runs':0,'system_interface_origin':'DECLARED_STUDENT_PROJECTION_NOT_ORIGINAL_CAPTURE'}
    input_paths=[OUT/'recovery/episodes.contexts.jsonl.gz',OUT/'outcomes/target_outcome_labels.jsonl.gz',ROOT/'output/20261026_wrd_quality_v8/controlled/native_targets.quality.jsonl.gz']+[Path(p)for p in args.coordination_input]
    pins=[{'path':str(p.resolve()),'sha256':digest(p),'bytes':p.stat().st_size}for p in input_paths]
    if args.skip_native:
        previous=json.loads((OUT/'COMPILATION_REPORT.json').read_text(encoding='utf-8'))
        assert previous.get('native')
        for item in previous['native']['files']:assert digest(Path(item['path']))==item['sha256']
        report['native']=previous['native']
        report['native_compilation_parent_receipt']={'script_sha256':previous.get('native_compilation_parent_receipt',{}).get('script_sha256',previous['compile_script_sha256']),
            'original_report':'processing_history/COMPILATION_REPORT.first.json','native_data_reused_byte_identically':True,'native_original_script':'processing_history/compile_dataset.first.py'}
    if not args.skip_native:report['native']=compile_native(compiler,native)
    if args.coordination_input:report['coordination']=compile_coordination(compiler,[Path(p)for p in args.coordination_input])
    report['split']=split_banks();report['tokenizer_and_template_proof']=compiler.proof
    report['elapsed_seconds']=round(time.monotonic()-started,3);report['compile_script_sha256']=digest(Path(__file__))
    for item in pins:assert digest(Path(item['path']))==item['sha256'],'input_changed_during_compilation'
    report['immutable_input_pins']=pins
    save(OUT/'COMPILATION_REPORT.json',report)
    print(js({k:v for k,v in report.items()if k not in ('tokenizer_and_template_proof','native')}),flush=True)


if __name__=='__main__':main()
