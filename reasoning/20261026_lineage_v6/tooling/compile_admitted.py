"""Export real positive SFT sequences after stable resource-closure decisions.

No training, model weights, GPU or agent execution. Existing quality decisions
remain in force. Genuine source-closed process positives are independent of
the separate, still-unproved complete-autonomy/deployment readiness claim.
"""
from __future__ import annotations
import argparse
from array import array
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
BUNDLE=ROOT/'output/20261025_wrd_training_dataset/bundle'
OUT=ROOT/'output/20261026_wrd_sequences_v6'
LINEAGE=ROOT/'output/20261026_wrd_lineage_v6/controlled'

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def bsha(x):return hashlib.sha256(x).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def int_sha(ids):
    a=array('I',ids)
    if sys.byteorder!='little':a.byteswap()
    return bsha(a.tobytes())
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def dump(p,values):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n') as f:
        for value in values:f.write(js(value)+'\n')
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def admitted(r):
    return r.get('status')=='ADMIT' and r.get('resource_closure_proven') is True and r.get('protected_ancestor_present') is False
def freeze_input(path):
    sha=digest(path);suffix=''.join(path.suffixes)
    dest=OUT/'controlled/decision_snapshots'/(path.name[:-len(suffix)]+'.'+sha[:16]+suffix)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.is_file():shutil.copyfile(path,dest)
    assert digest(path)==sha and digest(dest)==sha
    return dest,{'original_path':str(path),'sha256':sha,'immutable_snapshot':str(dest.relative_to(OUT))}
def accepted_decisions(path,key):
    values=list(rows(path))
    assert all(isinstance(r.get(key),str) for r in values)
    assert len({r[key] for r in values})==len(values)
    return {r[key]:r for r in values}
def decision_for_projection(decision,scope):
    if scope=='controlled':return decision
    return {'status':'ADMIT','resource_closure_proven':True,'protected_ancestor_present':False,
        'controlled_evidence_record_sha256':bsha(js(decision).encode()),
        'full_original_lineage_evidence_is_in_controlled_package':True,
        'private_raw_paths_or_business_proof_fields_not_copied_into_public_projection':True}

def masked_owner_check(r,owners,scope,bank):
    ids=r['input_ids'];assert r['total_tokens']==len(ids)<=32768
    assert int_sha(ids)==r['input_ids_sha256_u32le']
    assert r['label_ignore_index']==-100
    spans=sorted(r['supervision_spans'])
    assert spans==sorted(s for t in r['targets'] for s in t['owned_supervision_spans'])
    assert all(0<=s[0]<s[1]<=len(ids) for s in spans)
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    assert bsha(js(spans).encode())==r['supervision_spans_sha256']
    assert sum(s[1]-s[0] for s in spans)==r['supervised_tokens']>0
    for t in r['targets']:
        if not t['owned_supervision_spans']:continue
        assert t.get('mechanical_usable') is True
        assert t.get('observed_native_stop_reason') not in {'length','aborted','error'}
        assert t.get('quality_overlay') is None
        assert t['id'] not in owners
        assert all(s[1]<=t['response_end_token_exclusive'] for s in t['owned_supervision_spans'])
        owners[t['id']]={'target_id':t['id'],'scope':scope,'bank':bank,'record_id':r['id'],
            'episode_id':r.get('episode_id'),'source_pair_id':r.get('source_original_pair_id',r['id'] if bank=='reasoning' else None),
            'source_message_index':t.get('source_message_index'),'source_event_line':t.get('source_event_line'),
            'source_message_sha256':t.get('source_message_sha256'),
            'owned_supervision_spans':t['owned_supervision_spans'],'supervised_tokens':t['supervised_tokens'],
            'response_end_token_exclusive':t['response_end_token_exclusive']}

def verify_native(r,episode,compiler,native_messages):
    """Actual native source -> unchanged template -> both CPU tokenizers."""
    source=episode
    if not r['stage_complete_in_this_view']:
        source={**episode,'messages':episode['messages'][:max(t['source_message_index'] for t in r['targets'])+1]}
    messages,indices,issues=native_messages(source)
    assert not issues
    kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kwargs['enable_thinking']=False
    rendered=compiler.plain_compiled.render(messages=messages,tools=r['tools'] or None,documents=None,
        add_generation_prompt=False,**kwargs)
    for key in ('primary_14b','control_8b'):
        tokenizer=compiler.tokenizers[key]
        actual=tokenizer(rendered,add_special_tokens=False)['input_ids']
        assert actual==r['input_ids']
        assert tokenizer.decode(actual,skip_special_tokens=False,clean_up_tokenization_spaces=False)==rendered
    for t in r['targets']:
        assert t['source_message_sha256']==bsha(js(episode['messages'][t['source_message_index']]).encode())
    r['parent_original_rendered_sha256']=r['rendered_sha256']
    r['rendered_sha256']=bsha(rendered.encode())
    r['assistant_generation_spans']=[t['rendered_assistant_span'] for t in r['targets']]
    r['second_tokenizer_independently_called']=True
    r['tokenizer_pair_proof']='v6_both_tokenizers_fresh_encode_decode_equal_actual_source_render'
    r['v6_actual_native_source_re_render_verified']=True
    r['source_context_was_not_summarized_or_replaced']=True
    return r

def verify_reasoning(r,pair,compiler,valid_registry):
    request=pair['original_request'];response=pair['original_response'];target=dict(response['choices'][0]['message']);target['role']='assistant'
    messages=[dict(m) for m in request['messages']]
    registry,issues=valid_registry(request.get('tools',[]))
    old=next(t for t in r['targets'] if t.get('id')==r['id'])
    fresh=compiler.compile_messages(messages+[target],list(registry.values()),{len(messages):deepcopy(old)},independent=True)
    assert fresh['input_ids']==r['input_ids']
    assert fresh['supervision_spans']==r['supervision_spans']
    assert fresh['rendered_sha256']==r['rendered_sha256']
    reason=target.get('reasoning_content') or ''
    rendered=compiler.tokenizers['primary_14b'].decode(r['input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
    assert bsha(rendered.encode())==r['rendered_sha256']
    actual_target=next(t for t in fresh['targets'] if t.get('id')==r['id'])
    a,b=actual_target['rendered_assistant_span']
    if reason:
        assert rendered[a:b].startswith('<|im_start|>assistant\n<think>\n'+reason+'\n</think>\n\n')
        assert any(s[2] in {'R','R_BOUNDARY_MIXED'} for s in actual_target['owned_supervision_spans'])
    r['second_tokenizer_independently_called']=True
    r['tokenizer_pair_proof']='v6_both_tokenizers_fresh_original_request_response_compilation_equal'
    r['v6_original_reasoning_decode_exactly_verified']=bool(reason)
    r['source_context_was_not_summarized_or_replaced']=True
    return r

def stats(records):
    positive=[t for r in records for t in r['targets'] if t['owned_supervision_spans']]
    return {'windows':len(records),'original_parent_targets':len(positive),
        'input_tokens':sum(r['total_tokens'] for r in records),'supervised_tokens':sum(r['supervised_tokens'] for r in records),
        'supervised_tokens_by_component':dict(sum((Counter(r['supervised_tokens_by_component']) for r in records),Counter())),
        'le16k_windows':sum(r['total_tokens']<=16384 for r in records),'le32k_windows':len(records),
        'target_causal_end_le16k':sum(t['response_end_token_exclusive']<=16384 for t in positive),
        'target_causal_end_le32k':len(positive),
        'complete_native_stage_windows':sum(r.get('stage_complete_in_this_view') is True for r in records),
        'explicit_native_stage_prefix_windows':sum(r.get('stage_complete_in_this_view') is False for r in records),
        'complete_original_request_current_response_windows':sum('source_pair_file' in r for r in records),
        'original_R_positive_windows':sum(any(s[2].startswith('R') for s in r['supervision_spans']) for r in records),
        'exact_historical_resource_execution_versions_proven':sum(r.get('exact_historical_resource_execution_version_proven') is True for r in records),
        'by_original_stage':dict(Counter(r.get('kind',r.get('role_scope')) for r in records))}

def quality_zero_record(original,quality):
    row=deepcopy(original)
    row['candidate_supervision_spans_before_v6_quality']=row['supervision_spans']
    for target in row['targets']:
        target['candidate_owned_supervision_spans_before_v6_quality']=target['owned_supervision_spans']
        target['owned_supervision_spans']=[];target['supervised_tokens']=0
    row.update({'supervision_spans':[],'supervised_tokens':0,'supervised_tokens_by_component':{},
        'supervision_spans_sha256':bsha(js([]).encode()),'training_admitted':False,'training_manifest_admitted':False,
        'v6_historical_quality_overlay':quality,'failed_or_draft_current_target_preserved_as_zero_loss_context':True})
    return row

def collect_resources(admissions,node_path,prefix_path):
    if not admissions:return [],[]
    nodes={r['node_id']:r for r in rows(node_path)}
    prefixes=list(rows(prefix_path)) if prefix_path and prefix_path.is_file() else []
    wanted={n for d in admissions for n in d.get('resource_node_ids',[])}
    # Admissions include recursively verified producer-prefix dependencies.
    # Keep exact prefix records to make that boundary inspectable; only add
    # resources from a prefix explicitly linked by an admitted node/episode.
    prefix_map={(p['episode_id'],p['native_message_range'][1]):p for p in prefixes}
    pending=[p for d in admissions for p in d.get('direct_producer_prefixes',[])]
    wanted_prefixes=[];seen_prefixes=set()
    while pending:
        reference=pending.pop()
        key=(reference[0],reference[1]) if isinstance(reference,(list,tuple)) else (reference['episode_id'],reference['prefix_end_exclusive'])
        if key in seen_prefixes:continue
        assert key in prefix_map
        p=prefix_map[key];assert admitted(p)
        wanted_prefixes.append(p);seen_prefixes.add(key)
        wanted.update(p.get('resource_node_ids',[]))
        pending.extend(p.get('direct_producer_prefixes',[]))
    resources=[];cas=OUT/'controlled/admitted_resource_cas';cas.mkdir(parents=True,exist_ok=True)
    for node_id in sorted(wanted):
        assert node_id in nodes
        node=nodes[node_id];identity=node['file_identity'];oid=identity['sha256']
        assert not str(identity.get('logical_path','')).lower().endswith('.key')
        assert 'local_delivery_key' not in str(identity.get('logical_path',''))
        object_path=identity.get('object');assert isinstance(object_path,str)
        candidates=[BUNDLE/object_path,BUNDLE/'archive'/object_path]
        source=next((p for p in candidates if p.is_file()),None);assert source is not None
        assert source.stat().st_size==identity['bytes'] and digest(source)==oid
        destination=cas/oid
        if not destination.is_file():shutil.copyfile(source,destination)
        assert destination.stat().st_size==identity['bytes'] and digest(destination)==oid
        resources.append({'node_id':node_id,'file_identity':identity,
            'byte_exact_export_path':str(destination.relative_to(OUT)),
            'resource_closure_node':node,'training_resource_not_automatically_public':True})
    return resources,wanted_prefixes

def collect_reasoning_resources(admissions,node_path):
    wanted={n for d in admissions for n in d.get('resource_node_ids',[])}
    nodes={r['node_id']:r for r in rows(node_path)}
    result=[];cas=OUT/'controlled/admitted_resource_cas';cas.mkdir(parents=True,exist_ok=True)
    for node_id in sorted(wanted):
        assert node_id in nodes
        node=nodes[node_id];source=ROOT/node['immutable_export_path']
        assert source.is_file() and source.stat().st_size==node['bytes'] and digest(source)==node['sha256']
        destination=cas/node['sha256']
        if not destination.is_file():shutil.copyfile(source,destination)
        assert digest(destination)==node['sha256']
        result.append({'node_id':node_id,'sha256':node['sha256'],'bytes':node['bytes'],
            'resource_closure_node':node,'byte_exact_export_path':str(destination.relative_to(OUT)),
            'training_resource_not_automatically_public':True,'bank':'historical_reasoning'})
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--native-decisions',type=Path,default=LINEAGE/'lineage_episode_decisions.jsonl.gz')
    parser.add_argument('--reasoning-decisions',type=Path,required=True)
    parser.add_argument('--resource-nodes',type=Path,default=LINEAGE/'lineage_resources.jsonl.gz')
    parser.add_argument('--producer-prefix-decisions',type=Path,default=LINEAGE/'lineage_producer_prefix_decisions.jsonl.gz')
    parser.add_argument('--reasoning-resources',type=Path,default=LINEAGE/'reasoning_resource_nodes.jsonl.gz')
    parser.add_argument('--reasoning-only',action='store_true',help='Export stable R admissions while native review is still pending.')
    args=parser.parse_args()
    frozen_evidence={}
    names=['reasoning_decisions','reasoning_resources']
    if not args.reasoning_only:names+=['native_decisions','resource_nodes','producer_prefix_decisions']
    for name in names:
        path=getattr(args,name)
        if path.is_file():
            path,receipt=freeze_input(path);setattr(args,name,path);frozen_evidence[name]=receipt
    decisions={} if args.reasoning_only else accepted_decisions(args.native_decisions,'episode_id')
    rdecisions=accepted_decisions(args.reasoning_decisions,'pair_id')
    accepted={i:d for i,d in decisions.items() if admitted(d)}
    raccepted={i:d for i,d in rdecisions.items() if admitted(d)}
    frozen=json.loads((OUT/'FROZEN_NATIVE91_SET.json').read_text(encoding='utf-8'));fixed=set(frozen['episode_ids'])
    sys.path.insert(0,str(ROOT/'research/data_prep/wrd_reasoning_v4'))
    from compile_native import CausalCompiler,native_messages,valid_registry
    compiler=CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    native_sources={'controlled':BUNDLE/'canonical/native_episodes.jsonl.gz',
        'public':ROOT/'output/20261025_wrd_fullchain_reaudit/public_projection/fullchain.native_sessions.jsonl.gz'}
    contexts={scope:{r['episode_id']:r for r in rows(p) if r['episode_id'] in accepted} for scope,p in native_sources.items()}
    reasoning_pairs={r['pair_id']:r for r in rows(OUT/'controlled/reasoning_pair_lineage_inputs.jsonl.gz')}
    quality_path=OUT/'controlled/historical_raw_quality_overlay.jsonl.gz'
    raw_quality={r['pair_id']:r for r in rows(quality_path)}
    public_rindex={r['public_compiled_id']:r for r in rows(OUT/'controlled/reasoning_public_to_original.index.jsonl.gz')}
    public_rpairs={r['id']:r for name in ('sse_core','historical_generation')
        for r in rows(BASE/('curated_reasoning/public/'+name+'.pairs.jsonl.gz'))}
    immutable_sources=list(native_sources.values())+[
        BASE/('curated_native/'+scope+'.'+role+'.jsonl.gz')
        for scope in ('controlled','public') for role in ('core32k','actor_aux32k')]+[
        BASE/'curated_reasoning/controlled.original_reasoning32k.jsonl.gz',
        BASE/'public_reasoning_compiled_final/all_records.jsonl.gz',
        OUT/'controlled/reasoning_pair_lineage_inputs.jsonl.gz',
        OUT/'controlled/reasoning_public_to_original.index.jsonl.gz',quality_path,BASE/'CAUSAL_TEMPLATE.json']
    source_at_start={str(p.relative_to(ROOT)):digest(p) for p in immutable_sources}
    profiles={};all_owners={};native_admitted_eids=set();reasoning_positive_ids=set();raw_contexts=[];report_scopes={};checks=Counter()
    for scope in ('controlled','public'):
        banks={'native_core':[],'actor_aux':[],'reasoning':[]};owners={};held_quality=[]
        for role,bank in (('core32k','native_core'),('actor_aux32k','actor_aux')):
            for original in rows(BASE/('curated_native/'+scope+'.'+role+'.jsonl.gz')):
                eid=original['episode_id']
                if eid not in accepted:continue
                if scope=='controlled':
                    assert bsha(json.dumps(contexts[scope][eid],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==accepted[eid]['canonical_episode_sha256']
                row=verify_native(deepcopy(original),contexts[scope][eid],compiler,native_messages)
                row.update({'training_admitted':True,'training_manifest_admitted':True,
                    'training_admission_level':'RESOURCE_CLOSED_KNOWN_QUALITY_COVERED_PROCESS_SFT_SILVER',
                    'resource_closure_decision':decision_for_projection(accepted[eid],scope), 'full_autonomous_controller_demonstration':False,
                    'stage_dispatch_origin':'outer_pipeline','native_tool_action_origin':'observed_model_decision',
                    'original_226_boundary_preserved':True,'training_execution_authorized':False,
                    'fixed_91_episode_member':eid in fixed,'actor_auxiliary_recommended_max_loss_fraction':0.10 if bank=='actor_aux' else None,
                    'historical_BCD_effect_conclusions_not_semantic_or_scientific_gold':True})
                masked_owner_check(row,owners,scope,bank);banks[bank].append(row);checks['native_rows_verified']+=1
                if len(banks[bank])%16==0:print(js({'phase':'native_source_and_both_tokenizers_verified','scope':scope,'bank':bank,'rows':len(banks[bank])}),flush=True)
                if scope=='controlled':native_admitted_eids.add(eid)
        rsource=BASE/('curated_reasoning/controlled.original_reasoning32k.jsonl.gz' if scope=='controlled' else 'public_reasoning_compiled_final/all_records.jsonl.gz')
        for original in rows(rsource):
            oid=original['id'] if scope=='controlled' else public_rindex.get(original['id'],{}).get('source_original_pair_id')
            if oid in raw_quality and raw_quality[oid]['target_positive_allowed'] is False:
                held_quality.append(quality_zero_record(original,raw_quality[oid]));continue
            if oid not in raccepted or original['total_tokens']>32768 or not original['supervised_tokens']:continue
            assert raccepted[oid]['original_request_canonical_sha256']==reasoning_pairs[oid]['original_request_canonical_sha256']
            assert raccepted[oid]['source_record_sha256']==reasoning_pairs[oid]['source_record_sha256']
            pair=reasoning_pairs[oid]['original_pair'] if scope=='controlled' else public_rpairs[original['id']]
            row=verify_reasoning(deepcopy(original),pair,compiler,valid_registry)
            row.update({'training_admitted':True,'training_manifest_admitted':True,
                'training_admission_level':'RESOURCE_CLOSED_KNOWN_OUTCOME_COVERED_HISTORICAL_PROCESS_SFT_SILVER',
                'source_original_pair_id':oid,'resource_closure_decision':decision_for_projection(raccepted[oid],scope),
                'historical_protocol_and_runtime_preserved':True,'current_native_runtime_equivalence_claimed':False,
                'original_teacher_decisions_not_rewritten_as_native_tool_calls':True,
                'full_autonomous_controller_demonstration':False,'training_execution_authorized':False,
                'full_native_A_D_chain_proven':False,
                'process_action_silver_not_proven_business_resource_quality':True,
                'historical_BCD_effect_conclusions_not_semantic_or_scientific_gold':True})
            if oid in raw_quality:
                proof=raw_quality[oid]
                exact_resource_version=any(e.get('type') in {
                    'independent_exact_literal_patch_to_actual_observed_output_and_later_same_version_validation',
                    'exact_static_written_resource_bytes_match_recorded_successful_validation'} for e in proof['evidence'])
                row['exact_historical_resource_execution_version_proven']=exact_resource_version
                row['historical_quality_overlay']=proof if scope=='controlled' else {
                    'target_positive_allowed':True,'decision':proof['decision'],
                    'controlled_evidence_sha256':bsha(js(proof).encode()),
                    'exact_historical_resource_execution_version_proven':exact_resource_version}
            masked_owner_check(row,owners,scope,'reasoning');banks['reasoning'].append(row);checks['historical_rows_verified']+=1
            if len(banks['reasoning'])%16==0:print(js({'phase':'original_request_R_mask_and_both_tokenizers_verified','scope':scope,'rows':len(banks['reasoning'])}),flush=True)
            if scope=='controlled':reasoning_positive_ids.add(oid)
        for bank,records in banks.items():
            filename={'native_core':'admitted.native_core32k.jsonl.gz','actor_aux':'admitted.actor_aux32k.jsonl.gz','reasoning':'admitted.reasoning32k.jsonl.gz'}[bank]
            path=OUT/scope/filename;dump(path,records)
            profiles[(scope,bank)]={'path':str(path.relative_to(OUT)),'sha256':digest(path),'bytes':path.stat().st_size,'counts':stats(records)}
        dump(OUT/scope/'admitted.target_owners.jsonl.gz',owners.values())
        dump(OUT/scope/'held.reasoning_known_quality.jsonl.gz',held_quality)
        all_owners[scope]=owners
        report_scopes[scope]={bank:stats(values) for bank,values in banks.items()}
        report_scopes[scope]['unique_original_target_owners']=len(owners)
        report_scopes[scope]['known_quality_held_original_reasoning_records']=len(held_quality)
        report_scopes[scope]['fixed91_native_core']=stats([r for r in banks['native_core'] if r['episode_id'] in fixed])
        # Public and controlled banks are alternative projections of the same
        # events, never additive independent examples in a single training run.
        dump(OUT/scope/'admitted.contexts.jsonl.gz',[
            {'record_type':'native_original_context','episode_id':eid,'original_context':contexts[scope][eid],
                'not_a_concatenated_multi_episode_session':True}
            for eid in sorted({r['episode_id'] for k in ('native_core','actor_aux') for r in banks[k]})])
    selected_admissions=[accepted[eid] for eid in native_admitted_eids]
    resources,prefixes=collect_resources(selected_admissions,args.resource_nodes,args.producer_prefix_decisions)
    reasoning_resources=collect_reasoning_resources([raccepted[i] for i in sorted(reasoning_positive_ids)],args.reasoning_resources)
    dump(OUT/'controlled/admitted.resource_closure.index.jsonl.gz',resources)
    dump(OUT/'controlled/admitted.reasoning_resource_closure.index.jsonl.gz',reasoning_resources)
    dump(OUT/'controlled/admitted.producer_prefix_decisions.jsonl.gz',prefixes)
    prefix_by_episode=defaultdict(list)
    for prefix in prefixes:prefix_by_episode[prefix['episode_id']].append(prefix)
    producer_contexts=[]
    if prefix_by_episode:
        for original in rows(native_sources['controlled']):
            for prefix in prefix_by_episode.get(original['episode_id'],[]):
                assert bsha(json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==prefix['canonical_episode_sha256']
                end=prefix['native_message_range'][1]
                producer_contexts.append({'producer_episode_id':original['episode_id'],
                    'native_message_range':[0,end],'actual_original_system':original['system'],
                    'actual_original_messages':original['messages'][:end],
                    'actual_source_event_lines':original['source_event_lines'][:end],
                    'resource_closure_decision':prefix,'training_admitted':False,
                    'is_evidence_of_resource_creation_not_a_new_fused_conversation':True})
    dump(OUT/'controlled/admitted.producer_prefix_contexts.jsonl.gz',producer_contexts)
    dump(OUT/'controlled/admitted.reasoning_source_contexts.jsonl.gz',[
        reasoning_pairs[i] for i in sorted(reasoning_positive_ids)])
    dump(OUT/'controlled/admitted.lineage_decisions.jsonl.gz',selected_admissions)
    dump(OUT/'controlled/admitted.reasoning_lineage_decisions.jsonl.gz',[raccepted[i] for i in sorted(reasoning_positive_ids)])
    native_contexts=contexts['controlled']
    route_groups=defaultdict(list);interfaces=[];local_revision_episodes=set();feedback_then_revision_episodes=set()
    for eid in sorted(native_admitted_eids):
        episode=native_contexts[eid];route_groups[episode.get('route_id')].append(eid);saw_error=False
        for m in episode['messages']:
            if m.get('role') in {'tool','toolResult'} and m.get('isError'):saw_error=True
            if m.get('role')=='assistant' and isinstance(m.get('content'),list):
                names={b.get('name') for b in m['content'] if isinstance(b,dict) and b.get('type')=='toolCall'}
                if names&{'edit','apply_patch'}:
                    local_revision_episodes.add(eid)
                    if saw_error:feedback_then_revision_episodes.add(eid)
        for ancestor in accepted[eid].get('ancestor_episode_ids',[]):
            if ancestor==eid:continue
            interfaces.append({'consumer_episode_id':eid,'producer_ancestor_episode_id':ancestor,
                'resource_node_ids':accepted[eid].get('resource_node_ids',[]),
                'interface_origin':'original_resource_dependency_verified_by_lineage',
                'stage_dispatch_origin':'outer_pipeline','not_one_original_fused_conversation':True,
                'autonomous_stage_transition_proven':False})
    dump(OUT/'controlled/admitted.interepisode_interfaces.jsonl.gz',interfaces)
    observed_sources=set()
    for d in selected_admissions:
        observed_sources.update(d.get('observed_allowed_source_ids',d.get('observed_evolution_source_ids',[])))
    reasoning_parents={reasoning_pairs[i].get('parent_run_id') for i in reasoning_positive_ids if reasoning_pairs[i].get('parent_run_id')}
    reasoning_source_episodes={reasoning_pairs[i].get('historical_source_episode_id') for i in reasoning_positive_ids if reasoning_pairs[i].get('historical_source_episode_id')}
    historical_business_sources=set(reasoning_source_episodes)
    for i in reasoning_positive_ids:
        evidence=(reasoning_pairs[i].get('existing_source_identity_review') or {}).get('complete_semantic_source_evidence') or {}
        if evidence.get('verified_current_evolution_complete_source') is True and evidence.get('source_id'):
            historical_business_sources.add(evidence['source_id'])
    original_R_operations=Counter()
    historical_edges=[]
    for i in reasoning_positive_ids:
        if i in reasoning_pairs:
            item=reasoning_pairs[i];kind=(item['original_pair'].get('observed_parsed_output') or {}).get('kind')
            if kind:original_R_operations[kind]+=1
            run=item.get('parent_run_record')
            if run:
                steps=run['actual_steps'];position=next(j for j,s in enumerate(steps) if s['pair_id']==i);step=steps[position]
                calls=item['original_pair']['original_response']['choices'][0]['message'].get('tool_calls',[])
                ids={c.get('id') for c in calls}
                observed=[m for m in step.get('observations_before_next_response',[])
                          if m.get('role')=='tool' and m.get('tool_call_id') in ids]
                historical_edges.append({'original_parent_pair_id':i,'parent_run_id':run['run_id'],
                    'request_ordinal':step['request_ordinal'],'original_model_action':step['actual_response_message'],
                    'actual_original_tool_results_after_action':observed,
                    'actual_result_not_added_to_earlier_request':True,
                    'next_original_pair_id':steps[position+1]['pair_id'] if position+1<len(steps) else None,
                    'next_request_has_exact_current_prefix':step.get('next_request_has_exact_current_prefix'),
                    'next_request_contains_current_response_body':step.get('next_request_contains_current_response_body'),
                    'current_target_loss_owner_only':True,'transition_origin':'observed_model_action_and_actual_tool_result'})
    dump(OUT/'controlled/admitted.historical_action_observation_edges.jsonl.gz',historical_edges)
    independent_path=ROOT/'output/20261026_wrd_lineage_v6/INDEPENDENT_REASONING_REVIEW.json'
    independent=json.loads(independent_path.read_text(encoding='utf-8')) if independent_path.is_file() else {}
    repair=independent.get('complete_causal_repair_example_without_enterprise_body') or {}
    repair_is_positive=repair.get('original_repair_response_pair_id') in reasoning_positive_ids
    save(OUT/'controlled/admitted.historical_repair_chain.json',{
        'schema_version':'wrd-v6-original-historical-cross-run-repair-interface',
        'repair_target_has_actual_positive_loss':repair_is_positive,
        'exact_original_repair_example':repair if repair_is_positive else None,
        'prior_candidate_output_copy_edges':independent.get('prior_candidate_output_copy_edges',[]),
        'real_feedback_field_projection_proofs':independent.get('real_feedback_field_projection_proofs',[]),
        'interface_origins':'original_packet_copy_and_observed_model_repair_with_actual_results',
        'cross_run_interfaces_not_a_single_original_conversation':True,
        'complete_native_A_D_autonomy_not_proven':True,'training_started':False})
    source_paths=[args.reasoning_decisions,args.reasoning_resources,
        OUT/'FROZEN_NATIVE91_SET.json',OUT/'NATIVE91_PREPARATION_REPORT.json',OUT/'REASONING_PREPARATION_REPORT.json',
        OUT/'HISTORICAL_RAW_QUALITY_REPORT.json']
    if independent_path.is_file():source_paths.append(independent_path)
    raw_quality_qa=OUT/'INDEPENDENT_RAW_QUALITY_QA.json'
    if raw_quality_qa.is_file():source_paths.append(raw_quality_qa)
    if not args.reasoning_only:source_paths.extend([args.native_decisions,args.resource_nodes])
    if not args.reasoning_only and args.producer_prefix_decisions.is_file():source_paths.append(args.producer_prefix_decisions)
    source_sha={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p):digest(p) for p in source_paths}
    assert all(digest(ROOT/path)==sha for path,sha in source_at_start.items())
    source_sha.update(source_at_start)
    manifest={'schema_version':'wrd-v6-resource-closed-process-sft-manifest','status':'POSITIVE_PROCESS_DATA_NOT_PROVEN_COMPLETE_AUTONOMY',
        'training_execution_authorized':False,'training_started':False,'complete_autonomous_training_or_deployment_ready':False,
        'resource_closed_quality_covered_process_data_ready':bool(all_owners['controlled']),
        'native_lineage_review_pending':args.reasoning_only,
        'profiles':{scope:{bank:profiles[(scope,bank)] for bank in ('native_core','actor_aux','reasoning')} for scope in ('controlled','public')},
        'projection_rule':'Choose controlled OR public; never concatenate both projections.',
        'actor_auxiliary_max_loss_fraction':0.10,'historical_reasoning_native_ABI_equivalence_claimed':False,
        'all_final_positive_target_owners_unique_within_selected_projection':True,
        'generic_v5_discovery_prefixes_not_used_to_inflate_full_domain_chains':True,
        'source_sha256':source_sha,'causal_template_sha256':compiler.proof['causal_template_sha256']}
    manifest['immutable_lineage_decision_inputs']=frozen_evidence
    save(OUT/'TRAINING_MANIFEST.json',manifest)
    report={'schema_version':'wrd-v6-admitted-process-data-report','status':'RESOURCE_CLOSED_KNOWN_QUALITY_COVERED_POSITIVES_EXPORTED',
        'fixed91_total':len(fixed),'fixed91_resource_closed_episodes':len(fixed&set(accepted)),
        'fixed91_native_quality_positive_episodes':len(fixed&native_admitted_eids),
        'all_native_resource_closed_episodes':len(accepted),'all_native_quality_positive_episodes':len(native_admitted_eids),
        'reasoning_resource_closed_original_pairs':len(raccepted),
        'reasoning_quality_positive_original_pairs':len(reasoning_positive_ids),
        'historical_raw_quality_overlay_counts':dict(Counter(r['decision'] for r in raw_quality.values())),
        'source_closed_reasoning_pairs_held_by_additional_raw_quality':len(set(raccepted)&{i for i,r in raw_quality.items() if not r['target_positive_allowed']}),
        'failed_resource_versions_preserved_as_context_or_probe_inputs_not_correct_resource_targets':True,
        'old_final_validation_success_not_retroactive_quality_for_earlier_versions':True,
        'native_lineage_review_pending':args.reasoning_only,
        'original_parent_native_episodes':len(native_admitted_eids),
        'observed_business_source_ids_from_explicit_lineage_fields':sorted(observed_sources),
        'observed_business_source_count_known':len(observed_sources) if observed_sources else None,
        'source_count_unknown_is_not_zero_or_metadata_pool_size':True,
        'historical_reasoning_parent_raw_runs':len(reasoning_parents),
        'historical_reasoning_SSE_source_episodes':len(reasoning_source_episodes),
        'historical_unique_proven_business_source_ids':sorted(historical_business_sources),
        'historical_unique_proven_business_sources':len(historical_business_sources),
        'all_native_and_historical_unique_proven_business_sources':len(observed_sources|historical_business_sources),
        'repeated_raw_versions_of_one_source_not_counted_as_independent_enterprise_sources':True,
        'native_lineage_decision_status_counts':dict(Counter(d['status'] for d in decisions.values())),
        'historical_lineage_decision_status_counts':dict(Counter(d['status'] for d in rdecisions.values())),
        'historical_original_model_high_level_action_kinds':dict(original_R_operations),
        'historical_raw_action_to_actual_observation_edges':len(historical_edges),
        'historical_cross_run_feedback_revision_examples_with_actual_positive_writer':int(repair_is_positive),
        'historical_repair_chain_is_not_native_A_D_autonomous_pipeline_success':True,
        'same_native_session_local_revision_episodes':len(local_revision_episodes),
        'same_native_session_error_then_later_edit_temporal_episodes':len(feedback_then_revision_episodes),
        'temporal_edit_counts_do_not_prove_specific_error_caused_revision':True,
        'route_metadata_interface_groups_not_independent_source_groups':len(route_groups),
        'route_groups_containing_multiple_outer_dispatched_stages':sum(len({native_contexts[i]['kind'] for i in values})>1 for values in route_groups.values()),
        'verified_cross_episode_resource_interfaces':len(interfaces),
        'original_source_identity_count_is_not_independent_train_task_count':True,
        'scopes':report_scopes,'resource_closure_export_nodes':len(resources),
        'resource_closure_export_unique_CAS_objects':len({r['file_identity']['sha256'] for r in resources}),
        'reasoning_resource_closure_export_nodes':len(reasoning_resources),
        'reasoning_resource_source_ids':sorted({r['resource_closure_node']['source_id'] for r in reasoning_resources if r['resource_closure_node'].get('source_id')}),
        'source_context_resources_byte_exact_verified':True,'producer_prefix_dependency_records':len(prefixes),
        'all_frozen_input_source_hashes_unchanged_after_compilation':True,
        'actual_full_A_D_autonomous_native_chains':0,'stage_dispatch_origin':'outer_pipeline',
        'model_native_tool_decision_origin':'observed_model_decision',
        'cross_stage_interface_grouping_and_temporal_labels_origin':'derived_annotation',
        'skill_md_writes_or_FINISH_READY_not_relabelled_as_retain_or_frozen':True,
        'positive_process_data_readiness_separate_from_full_autonomy_readiness':True,
        'no_R_spliced_between_native_episodes':True,'training_started':False,
        'new_model_or_business_agent_calls':0,'gpu_used':False,'model_weights_loaded':False,
        'all_native_and_R_rows_both_CPU_tokenizers_freshly_verified':True,
        'original_R_spans_decoded_exactly_and_current_target_mask_verified':True,
        'system_user_tool_and_nonowned_history_have_no_positive_loss':True,
        'source_sha256':source_sha,'verification_counts':dict(checks),'script_sha256':digest(Path(__file__))}
    save(OUT/'ADMITTED_DATA_REPORT.json',report)
    print(js({'status':report['status'],'fixed91_positive':report['fixed91_native_quality_positive_episodes'],
        'native_positive':report['all_native_quality_positive_episodes'],'reasoning_positive':report['reasoning_quality_positive_original_pairs'],
        'scopes':report_scopes}),flush=True)

if __name__=='__main__':main()
