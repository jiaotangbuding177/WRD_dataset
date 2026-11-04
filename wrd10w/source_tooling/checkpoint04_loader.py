"""Portable CPU-only loader/QA for manifest-selected v10 main arrays.

It reconstructs token labels and reliability weights without a model, trainer,
optimizer or GPU library. Conditional 64K data is verified separately and never
added to the default iterator. This is data QA, not semantic gold certification.
"""
from __future__ import annotations
from array import array
from collections import Counter, defaultdict
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def js(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def safe(root, name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('unsafe_data_path')
    path = Path(root).joinpath(*p.parts)
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('data_path_escape')
    return path


def ids_digest(ids):
    data = array('I',ids)
    if data.itemsize != 4:
        raise ValueError('uint32_not_supported')
    if sys.byteorder != 'little':
        data.byteswap()
    return hashlib.sha256(data.tobytes()).hexdigest()


def rows(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def manifest(root):
    value = load(Path(root)/'TRAINING_MANIFEST.json')
    assert value['full_WRD_main_training_ready'] is False
    assert value['training_started'] is False
    assert value['default_full_pipeline_training_entrypoint'] is None
    assert value['original226_and_newH_and_static_dev_test_excluded'] is True
    return value


def active_paths(root, value):
    seen = set()
    for ref in value['actual_train_files']:
        assert ref['path'].startswith('compiled/') and 'conditional' not in ref['path']
        assert ref['path'] not in seen
        seen.add(ref['path'])
        path = safe(root,ref['path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
        yield ref['path'],path


def iter_features(root):
    root = Path(root)
    value = manifest(root)
    for _,path in active_paths(root,value):
        for row in rows(path):
            ids = row['input_ids']
            labels,weights = [-100]*len(ids),[0.0]*len(ids)
            last = 0
            for lo,hi,component,weight in row['supervision_spans']:
                assert type(lo) is int and type(hi) is int
                assert 0 <= last <= lo < hi <= len(ids) and 0 < weight <= 1
                labels[lo:hi] = ids[lo:hi]
                weights[lo:hi] = [float(weight)]*(hi-lo)
                last = hi
            assert sum(x != -100 for x in labels) == row['supervised_tokens']
            assert len(ids) <= 32768
            yield {'input_ids':ids,'attention_mask':[1]*len(ids),
                   'labels':labels,'loss_weights':weights}


def verify(root):
    root = Path(root)
    value = manifest(root)
    reports = {}
    for ref in value['active_compilation_reports']:
        path = safe(root,ref['path'])
        assert digest(path) == ref['sha256']
        reports[str(PurePosixPath(ref['path']).parent)] = ref
    admissions = {}
    for ref in value.get('external_root_admission_receipts',[]):
        path = safe(root,ref['path'])
        assert digest(path) == ref['sha256']
        proof = load(path)
        assert proof['status'] in {
            'ADMIT_LOCAL_REAL_STATE_REPAIR_WITH_EXPLICIT_NEW_AUTHOR',
            'ADMIT_LOCAL_C_PROCESS_AND_AUTHORED_COST_STOP',
            'ADMIT_PARTIAL_HISTORICAL_R_SEMANTIC_STAGE',
            'ADMIT_NEW_AUTHORED_NATIVE_RESOURCE_REPAIR_PROJECTION',
            'ADMIT_ORIGINAL_NATIVE_CV_PROCESS_R_AND_LOCAL_ACTIONS',
        }
        bank = ref['compiled_bank']
        assert bank in reports and bank not in admissions
        assert proof['compilation_report_sha256'] == reports[bank]['sha256']
        assert len(proof['record_ids']) == len(set(proof['record_ids']))
        admissions[bank] = proof
    counts,bank_ids = Counter(),defaultdict(set)
    source_ids,record_ids,owner_ids,action_owners,R_owners = set(),set(),set(),set(),set()
    projected_action_owners,historical_R_owners,canonical_projected_owners = set(),set(),set()
    group_splits,source_splits = defaultdict(set),defaultdict(set)
    origins,weighted = Counter(),Counter()
    parent = {}

    def find(x):
        parent.setdefault(x,x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def join(a,b):
        a,b = find(a),find(b)
        if a != b:
            parent[max(a,b)] = min(a,b)

    for name,path in active_paths(root,value):
        compiled_bank = str(PurePosixPath(name).parent)
        assert compiled_bank in reports
        for row in rows(path):
            identity = row['id']
            assert identity not in record_ids
            record_ids.add(identity)
            bank_ids[compiled_bank].add(identity)
            metadata = row['original_record_metadata']
            assert metadata['training_admitted'] is True and metadata['source_admission'] == 'ADMIT'
            assert not any(metadata.get(k) for k in ('original226','holdout12','protected_sources_visible_prefix'))
            if metadata.get('root_main_admission') is False:
                assert compiled_bank in admissions
                assert identity in admissions[compiled_bank]['record_ids']
            owner = metadata.get('owner_id',identity)
            assert owner not in owner_ids
            owner_ids.add(owner)
            assert row['split'] == 'train'
            ids,spans = row['input_ids'],row['supervision_spans']
            assert len(ids) == row['total_tokens'] <= 32768
            assert all(type(x) is int and 0 <= x < 2**32 for x in ids)
            assert ids_digest(ids) == row['input_ids_sha256_u32le']
            assert hashlib.sha256(js(spans).encode()).hexdigest() == row['supervision_spans_sha256']
            owned = [span for target in row['targets'] for span in target['owned_supervision_spans']]
            assert owned == spans
            components,positive_messages = Counter(),set()
            for target in row['targets']:
                owned_spans = target['owned_supervision_spans']
                assert target['supervised_tokens'] == sum(hi-lo for lo,hi,_,_ in owned_spans)
                if not owned_spans:
                    continue
                index = target['message_index']
                assert row['messages'][index]['role'] == 'assistant'
                positive_messages.add(index)
                if any(span[2] == 'A' for span in owned_spans):
                    for call in row['messages'][index].get('tool_calls',[]):
                        assert call['id'] and call['id'] not in action_owners|projected_action_owners
                        owners=projected_action_owners if metadata.get('actual_native_tool_dispatch') is False else action_owners
                        owners.add(call['id'])
            approved = metadata.get('supervision_message_indices',metadata.get('supervision_candidate_message_indices'))
            assert approved and set(approved) == positive_messages
            if 'message_loss_mask' in metadata:
                mask = metadata['message_loss_mask']
                assert len(mask) == len(row['messages']) and all(type(x) is int and x in (0,1) for x in mask)
                assert {i for i,x in enumerate(mask) if x} == positive_messages
            last = 0
            for lo,hi,component,weight in spans:
                assert type(lo) is int and type(hi) is int
                assert 0 <= last <= lo < hi <= len(ids) and 0 < weight <= 1
                components[component] += hi-lo
                weighted[component] += (hi-lo)*weight
                last = hi
            assert dict(components) == row['supervised_tokens_by_component']
            assert sum(components.values()) == row['supervised_tokens'] > 0
            if row['bank'] in {'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01'}:
                if components.get('R',0):
                    response_owner = metadata['actual_response_sha256'] if row['bank']=='native_CV_B_training_01' else metadata['evidence']['response_sha256']
                    assert response_owner not in R_owners
                    R_owners.add(response_owner)
                    origins['original_native_R_tokens'] += components['R']
                if row['bank']=='native_CV_B_training_01':origins['original_native_local_process_A_tokens']+=components.get('A',0)
            elif row['bank'] == 'real_state_repair_main':
                origins['new_authored_R_tokens'] += components.get('R',0)
                origins['revalidated_original_action_A_tokens'] += components.get('A',0)
            elif row['bank'] == 'source_contract_main':
                origins['new_source_contract_annotation_tokens'] += row['supervised_tokens']
            elif row['bank'] == 'native_C_execution_local_02':
                origins['original_native_execution_A_tokens'] += components.get('A',0)
            elif row['bank'] == 'new_real_state_cost_stop_02':
                origins['new_authored_R_tokens'] += components.get('R',0)
                origins['new_authored_cost_stop_D_tokens'] += components.get('D',0)
            elif row['bank'] == 'historical_semantic_R_main':
                owner=metadata['canonical_original_response_owner']
                assert owner not in historical_R_owners
                historical_R_owners.add(owner)
                origins['historical_original_R_tokens'] += components.get('R',0)
                assert not components.get('A',0) and not components.get('D',0)
            elif row['bank'] == 'historical_v6_native_repair_01':
                owner=metadata['target_owner']['canonical_original_action_owner_id']
                assert owner not in canonical_projected_owners
                canonical_projected_owners.add(owner)
                origins['new_authored_R_tokens'] += components.get('R',0)
                origins['new_authored_native_action_projection_A_tokens'] += components.get('A',0)
            else:
                origins['other_explicitly_named_bank_tokens'] += row['supervised_tokens']
            counts['sequences'] += 1
            counts['targets'] += len(approved)
            counts['input_tokens'] += len(ids)
            counts['supervised_tokens'] += row['supervised_tokens']
            counts['le16k_sequences'] += len(ids) <= 16384
            counts['le32k_sequences'] += len(ids) <= 32768
            for component,n in components.items():
                counts['component_'+component] += n
            record = 'record:'+identity
            find(record)
            if row.get('source_group_id'):
                group = row['source_group_id']
                group_splits[group].add(row['split'])
                join(record,'group:'+group)
            for source in row['source_ids']:
                source_ids.add(source)
                source_splits[source].add(row['split'])
                join(record,'source:'+source)
    for bank,proof in admissions.items():
        assert bank_ids[bank] == set(proof['record_ids'])
    assert dict(counts) == value['actual_counts']
    if 'supervision_origin_tokens' in value:
        assert dict(origins) == value['supervision_origin_tokens']
    assert len(source_ids) == value['distinct_source_ids']
    component_count = len({find('record:'+x) for x in record_ids})
    assert component_count == value['source_connected_components_across_banks']
    assert all(len(x) == 1 for x in list(source_splits.values())+list(group_splits.values()))
    assert len(action_owners) == value.get('actual_action_owners_with_positive_loss',len(action_owners))
    assert len(R_owners) == value.get('original_native_R_response_owners',len(R_owners))
    assert len(projected_action_owners) == value.get('new_authored_projected_action_owners',0)
    assert len(historical_R_owners) == value.get('historical_original_R_response_owners',0)
    loader_counts = Counter()
    for feature in iter_features(root):
        assert all((label == -100) == (weight == 0) for label,weight in zip(feature['labels'],feature['loss_weights']))
        loader_counts['sequences'] += 1
        loader_counts['supervised_tokens'] += sum(x != -100 for x in feature['labels'])
    assert loader_counts['sequences'] == counts['sequences']
    assert loader_counts['supervised_tokens'] == counts['supervised_tokens']
    return {'status':'PASS','counts':dict(counts),'actual_loader_counts':dict(loader_counts),
            'supervision_origin_tokens':dict(origins),'weighted_supervised_token_equivalents':dict(weighted),
            'external_root_admission_receipts_verified':len(admissions),
            'actual_positive_action_owners':len(action_owners),'original_R_response_owners':len(R_owners),
            'new_authored_projected_action_owners':len(projected_action_owners),
            'historical_original_R_response_owners':len(historical_R_owners),
            'distinct_sources':len(source_ids),'joined_source_components':component_count,
            'conditional_or_audit_only_arrays_loaded':False,
            'source_flags_and_candidate_metadata_do_not_override_root_receipts':True,
            'weights_loaded':False,'training_started':False,'full_WRD_main_training_ready':False}


def verify_conditional(root, candidate_base=None, exclusions_path=None):
    """Verify six frozen 64K candidates without admitting or iterating them."""
    root = Path(root)
    base = Path(candidate_base) if candidate_base is not None else root/'conditional/native_context_64k_01'
    if not base.exists():
        return {'status':'NOT_PRESENT_NOT_ADMITTED'}
    frozen = load(base/'FINAL_MANIFEST.json')
    exclusions = load(Path(exclusions_path) if exclusions_path is not None else base/'PACKAGING_BYPRODUCT_EXCLUSIONS.json')
    excluded = {r['path']:r for r in exclusions['byproducts_recorded_not_shipped']}
    for ref in frozen['files']:
        if ref['path'] in excluded:
            assert ref == excluded[ref['path']] and ref['path'].endswith('.pyc')
            continue
        path = safe(base,ref['path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
    assert len(frozen['files']) == 65 and len(excluded) == 3
    owner_file = load(base/'OWNER_EXCLUSIVITY.json')
    owners = {r['candidate_view_id']:r for r in owner_file['owners']}
    seen,supervised = set(),0
    for row in rows(base/'candidate_native64k.jsonl.gz'):
        assert row['id'] not in seen and row['id'] in owners
        seen.add(row['id'])
        assert row['candidate_training_readiness'] is False
        assert row['bank'] == 'conditional_native64k_only'
        assert owners[row['id']]['core7_view_and_native53_view_mutually_exclusive'] is True
        arrays = {}
        for name,code,size in [('input_ids.u32','I',4),('labels.i64','q',8),('loss_weights.f32','f',4)]:
            raw = (base/'arrays'/row['id']/name).read_bytes()
            data = array(code)
            assert data.itemsize == size and len(raw) == row['total_tokens']*size
            data.frombytes(raw)
            if sys.byteorder != 'little':
                data.byteswap()
            arrays[name] = data
        assert list(arrays['input_ids.u32']) == row['input_ids']
        assert ids_digest(row['input_ids']) == row['input_ids_sha256_u32le']
        expected = {}
        for lo,hi,component,weight in row['supervision_spans']:
            assert component == 'R' and 0 <= lo < hi <= row['total_tokens'] <= 65536
            expected.update({i:weight for i in range(lo,hi)})
        assert len(expected) == row['supervised_tokens']
        for i,(label,weight) in enumerate(zip(arrays['labels.i64'],arrays['loss_weights.f32'])):
            if i in expected:
                assert label == row['input_ids'][i] and abs(weight-expected[i]) < 1e-7
            else:
                assert label == -100 and weight == 0
        supervised += len(expected)
    assert len(seen) == 6 and supervised == 5980
    return {'status':'PASS_CONDITIONAL_NOT_ACTIVE','candidate_sequences':6,
            'candidate_original_R_supervised_tokens':5980,'binary_arrays_verified':18,
            'original_manifest_files':65,'pyc_byproducts_metadata_only':3,
            'core32_and_full53_same_owner_must_not_both_receive_loss':True,
            'included_in_default_main_counts':False,'Spark_forward_or_training_tested':False,
            'full_WRD_main_training_ready':False,'training_started':False}


def verify_evidence_profiles(root, profile_path=None, index_path=None, source_paths=None):
    """Check raw evidence populations separately from positive training rows."""
    root = Path(root)
    profiles = load(Path(profile_path) if profile_path is not None else root/'EVIDENCE_PROFILE_SCOPES.json')
    index = load(Path(index_path) if index_path is not None else root/'API_CAPTURE_INDEX.json')

    def get(name):
        return Path(source_paths[name]) if source_paths is not None else safe(root,name)

    calls = index['calls']
    assert len(calls) == 158 and len({(r['episode'],r['call_id']) for r in calls}) == 158
    assert sum(r['DONE_observed'] for r in calls) == 156
    a2_id = 'A_phase2_source_screen_01'
    first_calls = [r for r in calls if r['episode'] != a2_id]
    a2_calls = [r for r in calls if r['episode'] == a2_id]
    assert len(first_calls) == 147 and sum(r['DONE_observed'] for r in first_calls) == 145
    assert len(a2_calls) == 11 and all(r['DONE_observed'] for r in a2_calls)
    partial_R = 0
    for row in calls:
        request = get(row['request_archive_path'])
        response = get(row['response_archive_path'])
        receipt = load(get(row['receipt_archive_path']))
        assert digest(request) == row['request_sha256'] == receipt['request_sha256']
        assert digest(response) == row['response_sha256']
        assert response.stat().st_size == row['response_bytes']
        assert receipt['status'] == row['receipt_status']
        if row['episode'] == a2_id:
            assert row['A2_audit_only_zero_new_positive_loss'] is True
            assert row['request_archive_path'].startswith('audit_only/A2/')
        if not row['DONE_observed']:
            original = response.read_bytes().decode('utf-8')
            assert 'data: [DONE]' not in original and receipt['status'] != 'COMPLETE'
            for block in original.replace('\r\n','\n').split('\n\n'):
                payload = '\n'.join(line[5:].lstrip(' ') for line in block.splitlines() if line.startswith('data:'))
                if not payload:
                    continue
                frame = json.loads(payload)
                for choice in frame.get('choices',[]):
                    if choice.get('index',0) == 0:
                        partial_R += len(choice.get('delta',{}).get('reasoning_content','') or '')
    complete_count,complete_R = 0,0
    first_complete_count,first_complete_R = 0,0
    episodes = sorted({r['episode'] for r in calls})
    assert len(episodes) == 11
    for episode in episodes:
        prefix = 'audit_only/A2/' if episode == a2_id else ''
        ledger = get(prefix+'native_records/'+episode+'/raw_recovery/provider_responses.original.jsonl.gz')
        report = load(get(prefix+'native_records/'+episode+'/raw_recovery/EXTRACTION_REPORT.json'))
        original_rows = list(rows(ledger))
        count = len(original_rows)
        chars = sum(len(r['message'].get('reasoning_content','') or '') for r in original_rows)
        assert count == report['captured_complete_responses']
        assert chars == report['original_readable_R_chars']
        complete_count += count
        complete_R += chars
        if episode != a2_id:
            first_complete_count += count
            first_complete_R += chars
        else:
            assert count == 11 and chars == 37441
            assert report['reviewed_student_records'] == 0
    assert complete_count == 156 and complete_R == 266844 and partial_R == 5642
    assert first_complete_count == 145 and first_complete_R == 229403
    first = profiles['first_ten_chain']
    a2 = profiles['A2_audit_only']
    combined = profiles['legacy_first_chain_and_A2_scope']
    assert first['compatible_HTTP'] == 147 and first['original_R_chars'] == 235045
    assert a2['compatible_HTTP'] == 11 and a2['original_R_chars'] == 37441
    assert a2['new_positive_training_targets'] == 0
    assert combined['compatible_HTTP'] == 158 and combined['original_R_chars'] == complete_R+partial_R == 272486
    old_cost = load(get('runtime_preflight/quality/FIRST_CHAIN_INDEPENDENT_REVIEW/ACTUAL_COST_RECONCILIATION.json'))
    a2_cost = load(get('audit_only/A2/runtime_preflight/episodes/'+a2_id+'/usage.json'))
    assert old_cost['known_total_tokens'] == first['known_tokens'] == 8660547
    assert old_cost['actual_request_identities'] == first['actual_upstream_request_identities'] == 110
    assert a2_cost['known_total_tokens'] == a2['known_tokens'] == 1134348
    assert a2_cost['model_calls'] == a2['actual_upstream_request_identities'] == 11
    assert combined['known_tokens'] == old_cost['known_total_tokens']+a2_cost['known_total_tokens'] == 9794895
    assert combined['actual_upstream_request_identities'] == 121
    assert old_cost['unknown_usage_calls']+a2_cost['unknown_usage_calls'] == combined['unknown_usage_calls'] == 1
    a2_prefix = 'audit_only/A2/runtime_preflight/episodes/'+a2_id+'/'
    session_rows = [json.loads(line) for line in get(a2_prefix+'openclaw_transport/session_events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    all_rows = [json.loads(line) for line in get(a2_prefix+'openclaw_transport/all_session_events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    meter_rows = [line for line in get(a2_prefix+'native_events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(session_rows) == len(all_rows) == a2['native_SQLite_export_rows'] == 36
    assert sum(r.get('type') == 'message' for r in session_rows) == a2['native_SQLite_message_rows'] == 22
    assert len({r['session_id'] for r in all_rows}) == 1
    assert len(meter_rows) == a2['provider_meter_rows'] == 55
    assert profiles['conditional_window_profile']['compatible_HTTP'] == 111
    assert profiles['conditional_window_profile']['not_a_profile_of_all_158_HTTP'] is True
    return {'status':'PASS_EVIDENCE_COUNTS_NOT_POSITIVE_TARGET_COUNTS',
            'outer_dispatches':11,'native_sessions':12,'compatible_HTTP':158,'complete_HTTP':156,'partial_HTTP':2,
            'original_R_complete_chars':complete_R,'original_R_partial_chars':partial_R,
            'original_R_total_chars':complete_R+partial_R,'known_tokens':9794895,
            'actual_upstream_request_identities':121,'unknown_usage_calls':1,
            'first_ten_chain_separately_preserved':True,'A2_audit_only_new_positive_targets':0,
            'A2_native_SQLite_rows':36,'A2_SQLite_message_rows':22,'A2_provider_meter_rows_separate':55,
            'conditional_window_profile_population':111,'default_main_counts_not_increased_by_this_audit':True,
            'training_started':False,'full_WRD_main_training_ready':False}


def verify_recovered_profiles(root, profile_path=None):
    """Read all three new closed API scopes, keeping length and helper units."""
    root=Path(root)
    profile=load(profile_path or root/'RECOVERED_DATA_PROFILE_SCOPES.json')
    total=Counter(); rows=[]
    for episode in profile['closed_episodes']:
        observed=Counter()
        for call in episode['calls']:
            for name in ('request','response','receipt'):
                ref=call[name];path=safe(root,ref['path'])
                assert path.stat().st_size==ref['bytes'] and digest(path)==ref['sha256']
            request=load(safe(root,call['request']['path']))
            assert isinstance(request['messages'],list)
            reasoning=[];finished=[];done=False
            response_path=safe(root,call['response']['path'])
            if response_path.suffix=='.json':
                event=load(response_path)
                assert call.get('external_vision_helper')
                choices=event['choices'];assert len(choices)==1
                reasoning.append(choices[0]['message'].get('reasoning_content',''))
                finished.append(choices[0]['finish_reason']);done=True
            else:
                for line in response_path.read_text(encoding='utf-8').splitlines():
                    if not line.startswith('data:'):continue
                    value=line[5:].strip()
                    if value=='[DONE]':done=True;continue
                    if not value:continue
                    event=json.loads(value)
                    for choice in event.get('choices',[]):
                        delta=choice.get('delta') or {}
                        if delta.get('reasoning_content') is not None:
                            assert isinstance(delta['reasoning_content'],str)
                            reasoning.append(delta['reasoning_content'])
                        if choice.get('finish_reason'):finished.append(choice['finish_reason'])
            assert done and len(finished)==1
            observed['HTTP']+=1
            observed['R_characters']+=len(''.join(reasoning))
            observed['finish_length']+=finished[0]=='length'
            observed['stop_or_tool_calls']+=finished[0] in ('stop','tool_calls')
            if call.get('external_vision_helper'):
                assert len(request['messages'])==1 and not request.get('tools')
                observed['external_helper_HTTP_not_text_main_Agent']+=1
        assert dict(observed)==episode['expected_counts']
        total.update(observed);rows.append({'episode':episode['episode'],'actual_counts':dict(observed)})
    assert total['HTTP']==97 and total['R_characters']==111729
    assert total['finish_length']==1 and total['external_helper_HTTP_not_text_main_Agent']==1
    return {'status':'PASS_ALL_NEW_CLOSED_ORIGINAL_STREAMS_REPARSED', 'counts':dict(total),
            'episodes':rows,'legacy158_plus_new97_total_HTTP':255,
            'length_is_complete_transport_not_fake_EOS':True,
            'helper_not_a_Qwen_text_model_visual_demonstration':True,
            'raw_and_candidate_counts_not_added_to_default_supervision':True,
            'training_started':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--verify-conditional',action='store_true')
    parser.add_argument('--verify-evidence',action='store_true')
    args = parser.parse_args()
    result = verify(args.root)
    if args.verify_conditional:
        result['conditional_64k_separate_verification'] = verify_conditional(args.root)
    if args.verify_evidence:
        result['evidence_profile_separate_verification'] = verify_evidence_profiles(args.root)
        result['new_closed_recovery_verification'] = verify_recovered_profiles(args.root)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
