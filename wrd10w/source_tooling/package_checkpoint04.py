"""Prepare/freeze/build checkpoint04 with explicit immutable evidence pins.

--prepare only writes a reviewable allowlist outside Git and never reads keys.
--build additionally requires the exact prepared SHA supplied after root's go.
No model, Agent session, optimizer, training, commit, push or checkout action.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'output/20261027_wrd_main_v10'
RELEASE = ROOT/'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE/'dataset/20261027_v10_checkpoint04'
KEY = ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
SCRIPT_DIR = Path(__file__).parent
FIRST_CHAIN_EPISODES = ('technical_native_child_capture_probe','A_screen_narrative_01',
            'B_make_report_01','B_make_report_02','B_revision_report_01',
            'C_L_no_skill_01','C_L_skill_01','C_E_skill_01','C_E_no_skill_01',
            'C_review_report_01')
A2_EPISODE = 'A_phase2_source_screen_01'
EPISODES = FIRST_CHAIN_EPISODES+(A2_EPISODE,)
CONDITIONAL_SHA = 'b32933eab92b3b6e58f432dcd0381a2c32a2cd09a2556172266351327d0e0f6d'
FORBIDDEN = {'.claude','.codex','private','private_credential_audit','credential_audit','.git'}
PRIVATE_SUFFIXES = {'.key','.pem','.pfx','.p12','.sqlite','.sqlite3','.db','.wal','.shm'}
BLOCK = 1048576


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(BLOCK),b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path,value):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def module(path,name):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def safe_name(name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    assert not any(x.lower() in FORBIDDEN|{'__pycache__'} for x in p.parts)
    assert p.suffix.lower() not in PRIVATE_SUFFIXES|{'.pyc'}
    return p


def regular(path):
    path = Path(path).absolute()
    assert path.is_file() and not path.is_symlink()
    assert not any(x.lower() in FORBIDDEN for x in path.parts)
    assert path.suffix.lower() not in PRIVATE_SUFFIXES
    assert not (path.lstat().st_file_attributes & 0x400) if hasattr(path.lstat(),'st_file_attributes') else True
    return path


def pin(path,name,role):
    path = regular(path)
    safe_name(name)
    return {'path':name,'original_path':str(path),'bytes':path.stat().st_size,
            'sha256':digest(path),'role':role}


def prepare():
    work = OUT/'checkpoint04_preparation'/('attempt_'+str(time.time_ns()))
    work.mkdir(parents=True,exist_ok=False)
    members,byproducts = {},[]

    def add(name,path,role):
        path = Path(path).absolute()
        if path.suffix.lower() == '.pyc' or '__pycache__' in path.parts:
            regular(path)
            byproducts.append({'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path),
                               'reason':'generated_byproduct_metadata_only_never_training_or_archived'})
            return
        row = pin(path,name,role)
        if name in members:
            assert members[name]['sha256'] == row['sha256'] and members[name]['bytes'] == row['bytes']
            return
        members[name] = row

    def add_out(path,role):
        path = Path(path).absolute()
        assert path.is_relative_to(OUT.absolute()), 'expected_v10_source_path'
        relative = path.relative_to(OUT).as_posix()
        a2_scope = A2_EPISODE in path.parts or 'phase2_A_release_01' in path.parts or any(
            part in {'A2_ACTUAL_OUTPUT_AUDIT_01','A2_SOURCE_CONTRACT_REVIEW_01'} for part in path.parts)
        add(('audit_only/A2/' if a2_scope else '')+relative,path,role)

    def scoped_tree(base,prefix,role):
        # This enumerates only named bounded evidence/fixture/version scopes.
        # It never walks a runtime/workspace root or follows reparse entries.
        base = Path(base).absolute()
        stack = [base]
        while stack:
            folder = stack.pop()
            assert not folder.is_symlink()
            for path in sorted(folder.iterdir()):
                info = path.lstat()
                assert not path.is_symlink() and not (getattr(info,'st_file_attributes',0)&0x400), 'reparse_not_allowed'
                assert not any(x.lower() in FORBIDDEN for x in path.relative_to(base).parts)
                if path.is_dir():
                    stack.append(path)
                elif stat.S_ISREG(info.st_mode):
                    add(prefix+'/'+path.relative_to(base).as_posix(),path,role)
                else:
                    raise ValueError('nonregular_evidence_entry')

    manifest_path = OUT/'TRAINING_MANIFEST.json'
    active = load(manifest_path)
    assert active['full_WRD_main_training_ready'] is False and active['training_started'] is False
    assert active['original226_and_newH_and_static_dev_test_excluded'] is True
    for name in ('TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json'):
        add_out(OUT/name,'default_active_manifest_and_actual_counts')
    add_out(OUT/'COST_ACCOUNTING_SCOPE.json','current_collection_curation_and_training_cost_scope_not_zero_cost')
    banks = {str(PurePosixPath(row['path']).parent) for row in active['actual_train_files']}
    assert 'compiled/real_state_repair_02' in banks and 'compiled/real_state_repair_01' not in banks
    assert 'compiled/native_A_partial_03' in banks and 'compiled/native_A_partial_02' not in banks
    for ref in active['actual_train_files']:
        path = OUT/ref['path']
        assert digest(path) == ref['sha256'] and path.stat().st_size == ref['bytes']
        add_out(path,'default_active_actual_token_array')
    for ref in active['active_compilation_reports']:
        path = OUT/ref['path']
        assert digest(path) == ref['sha256']
        add_out(path,'default_active_compilation_report')
        template = path.parent/'CAUSAL_TEMPLATE.json'
        if template.is_file():
            add_out(template,'declared_causal_serialization_template')
    for ref in active.get('external_root_admission_receipts',[]):
        path = OUT/ref['path']
        assert digest(path) == ref['sha256']
        add_out(path,'external_root_semantic_admission_required_by_active_manifest')
    state = OUT/'real_state_reconstruction_02'
    for name in ('build_functional_state_view.py','verify_functional_state_view.py','real_state_tasks.jsonl.gz',
                 'SOURCE_RECEIPTS.json','FUNCTIONAL_SOURCE_CLOSED_QA.json','COMPILED_BANK_QA.json',
                 'EXPOSURE_OWNERS.json','VIEW_01_IMMUTABILITY_CHECK.json','FUNCTIONAL_VIEW_PROJECTION_REVIEW.json',
                 'IMPLEMENTATION_RECEIPT.json','ROOT_COMPILED_QA.json','ROOT_SEMANTIC_ADMISSION.json','README.md'):
        add_out(state/name,'approved_real_state02_source_provenance_and_scoped_credit')
    closure = load(state/'SOURCE_RECEIPTS.json')
    for ref in closure['files']:
        path = Path(ref['path'])
        assert digest(path) == ref['sha256'] and path.stat().st_size == ref['bytes']
        add('real_state_reconstruction_02/source_receipts/objects/'+ref['sha256'],path,
            'state02_exact_necessary_source_object_audit_not_extra_positive_target')
    for ref_name in ('allowlist','resource_ancestry'):
        ref = closure[ref_name]
        path = Path(ref['path'])
        assert digest(path) == ref['sha256'] and path.stat().st_size == ref['bytes']
        add('real_state_reconstruction_02/source_receipts/objects/'+ref['sha256'],path,
            'state02_source_boundary_receipt')

    for folder in ('a_reasoning_review_03','b_reasoning_review_01'):
        for name in ('REVIEW.json','README.md','ROOT_COMPILED_QA.json'):
            add_out(OUT/folder/name,'original_R_scoped_AI_silver_review_not_human_gold')
    for path in [OUT/'native_records/A_screen_narrative_01/A_PARTIAL_REASONING_REVIEW_V3.json',
                 OUT/'native_records/B_make_report_02/B_PARTIAL_REASONING_REVIEW_V1.json',
                 OUT/'compiled/native_A_partial_03/SCOPED_TOKEN_QA.json',
                 OUT/'compiled/native_A_partial_03/R03_RAW_AND_MASK_QA.json',
                 OUT/'compiled/native_A_partial_03/README.md',
                 OUT/'compiled/native_B_partial_01/B01_RAW_MASK_COVERAGE_QA.json']:
        add_out(path,'original_R_approval_and_exact_mask_QA')

    # First ten episodes retain their separate 147-exchange accounting. The
    # completed A2 screen adds eleven exchanges, all explicitly audit-only.
    api_rows = []
    for episode_id in EPISODES:
        episode = OUT/'runtime_preflight/episodes'/episode_id
        audit_prefix = 'audit_only/A2/' if episode_id == A2_EPISODE else ''
        for name in ('job.json','request.json','dispatch.json','execution.json','process.json',
                     'native_events.jsonl','outer_recording_receipt.json','response.json','result.json',
                     'usage.json','PASSIVE_USAGE_RECONCILIATION.json','CAPTURE_ASSESSMENT.json',
                     'CONSUMPTION_AUDIT.json'):
            path = episode/name
            if path.is_file():
                add_out(path,'original_native_episode_identity_events_result_and_cost_audit_only')
        job = load(episode/'job.json')
        for ref in job.get('resources',[]):
            path = Path(ref['path'])
            assert digest(path) == ref['sha256']
            mount = str(PurePosixPath(ref['mount']))
            safe_name(mount)
            add(audit_prefix+'native_job_inputs/'+episode_id+'/'+mount,path,'exact_original_declared_job_resource')
        for key in ('source_allowlist_receipt','resource_ancestry_receipt'):
            ref = job.get(key)
            if ref:
                path = Path(ref['path'] if isinstance(ref,dict) else ref)
                if isinstance(ref,dict) and ref.get('sha256'):
                    assert digest(path) == ref['sha256']
                add(audit_prefix+'native_job_receipts/'+episode_id+'/'+path.name,path,'exact_source_and_resource_ancestry_receipt')
        calls = sorted(p for p in (episode/'api_audit').iterdir() if p.is_dir())
        for folder in calls:
            assert not folder.is_symlink()
            request,receipt = folder/'request.raw.json',folder/'receipt.json'
            info = load(receipt)
            assert digest(request) == info['request_sha256']
            assert info.get('headers_recorded') is False and info.get('credential_recorded') is False
            response_paths = [p for p in (folder/'response.raw.sse',folder/'response.raw.json') if p.is_file()]
            assert len(response_paths) == 1
            response = response_paths[0]
            if info.get('response_sha256'):
                assert digest(response) == info['response_sha256']
            raw = response.read_bytes()
            done = b'data: [DONE]' in raw if response.suffix == '.sse' else info.get('status') == 'COMPLETE'
            if info['status'] == 'COMPLETE':
                assert done
            for path in (request,response,receipt):
                add_out(path,'actual_compatible_API_original_bytes_audit_only_not_blanket_positive_loss')
            api_rows.append({'episode':episode_id,'call_id':folder.name,'receipt_status':info['status'],
                             'DONE_observed':done,'request_sha256':digest(request),
                             'response_sha256':digest(response),'response_bytes':response.stat().st_size,
                             'request_archive_path':audit_prefix+request.relative_to(OUT).as_posix(),
                             'response_archive_path':audit_prefix+response.relative_to(OUT).as_posix(),
                             'receipt_archive_path':audit_prefix+receipt.relative_to(OUT).as_posix(),
                             'A2_audit_only_zero_new_positive_loss':episode_id == A2_EPISODE,
                             'positive_loss_not_inferred_from_completion':True})
        transport = episode/'openclaw_transport'
        for name in ('all_session_events.jsonl','session_events.jsonl','episode_turns.json','skill_reads.json',
                     'native_result.json','turn_0001.native_result.json','runtime_observation.json',
                     'container_receipt.json','host_receipt.json'):
            path = transport/name
            if path.is_file():
                add_out(path,'native_parent_child_observations_discovery_reads_and_exact_environment')
        recovered = OUT/'native_records'/episode_id/'raw_recovery'
        for name in ('provider_responses.original.jsonl.gz','EXTRACTION_REPORT.json'):
            add_out(recovered/name,'complete_original_R_and_actions_recovered_at_compatibility_boundary')
        version_folder = recovered.parent/'file_versions_01'
        if version_folder.is_dir():
            graph = load(version_folder/'VERSION_GRAPH.json')
            add_out(version_folder/'VERSION_GRAPH.json','exact_write_edit_observation_version_graph')
            object_ids = set()
            def object_refs(value):
                if isinstance(value,dict):
                    for key,item in value.items():
                        if key == 'object' and isinstance(item,str):
                            object_ids.add(item)
                        else:
                            object_refs(item)
                elif isinstance(value,list):
                    for item in value:
                        object_refs(item)
            object_refs(graph)
            for oid in object_ids:
                path = version_folder/'objects'/oid
                assert digest(path) == oid
                add_out(path,'exact_original_resource_version_or_delivered_observation_object')
    assert len(api_rows) == 158 and sum(r['DONE_observed'] for r in api_rows) == 156
    assert len([r for r in api_rows if not r['DONE_observed']]) == 2
    save(work/'API_CAPTURE_INDEX.json',{'episodes':len(EPISODES),'native_sessions':12,
        'compatible_HTTP_records':158,'complete_original_HTTP_records':156,'incomplete_records':2,
        'first_ten_chain':{'outer_episodes':10,'native_sessions':11,'HTTP':147,'COMPLETE':145,'partial':2},
        'A2_audit_only':{'outer_episodes':1,'native_sessions':1,'HTTP':11,'COMPLETE':11,'partial':0,'new_positive_targets':0},
        'outer_order_is_not_single_native_autonomous_controller':True,'calls':api_rows})
    add('API_CAPTURE_INDEX.json',work/'API_CAPTURE_INDEX.json','full_capture_count_and_partial_stream_index')

    quality = OUT/'runtime_preflight/quality'
    for name in ('A_B_MAKE_FEEDBACK.json','source_profiles.verified_fields.annotation.json',
                 'A_SEMANTIC_REVIEW.json','A_STRUCTURE_QUOTE_AUDIT.json','A_NATIVE_API_PROVIDER_MAPPING.json',
                 'B_REVISION_01_ACTUAL_FEEDBACK.json','FIRST_C_REVIEW_PROTOCOL.json'):
        add_out(quality/name,'independent_source_requirements_failure_feedback_or_review_protocol')
    for name in ('B02_INDEPENDENT_RESOURCE_AUDIT','B_REVISION01_INDEPENDENT_RESOURCE_AUDIT',
                 'B_REVISION01_CLEAN_VIEW_RECHECK','C_REVIEW_01_INPUTS','FIRST_CHAIN_INDEPENDENT_REVIEW'):
        scoped_tree(quality/name,'runtime_preflight/quality/'+name,
                    'frozen_independent_actual_tests_consumption_blind_Q_cost_and_STOP_evidence')
    for name in ('CENSUS.json','all_session_events.recovered.jsonl','native_events.already_incurred.jsonl',
                 'usage.partial.json','0001_9764241a7f814bde8191339fbe8a1c68.explicit_reasoning.partial.txt',
                 '0003_5570e1f719bf4d989dc7d896b8ae0719.explicit_reasoning.partial.txt',
                 '0006_0fd90a556d664ee78bee25ecc0bf7541.explicit_reasoning.partial.txt'):
        add_out(quality/'B_INTERRUPTION_20261027'/name,'original_interrupted_failure_R_and_cost_preserved_zero_new_loss')
    for name in ('A2_ACTUAL_OUTPUT_AUDIT_01','A2_SOURCE_CONTRACT_REVIEW_01'):
        scoped_tree(quality/name,'audit_only/A2/runtime_preflight/quality/'+name,
                    'A2_independent_mechanical_semantic_review_zero_positive_loss')
    handoff_path = quality/'A2_ACTUAL_OUTPUT_AUDIT_01/HANDOFF_PINS.json'
    handoff = load(handoff_path)
    assert len(handoff['key_evidence_files']) == 17
    assert handoff['raw_R_complete_responses'] == 11 and handoff['raw_readable_R_chars'] == 37441
    assert handoff['collection_agent_new_positive_training_admissions'] == 0
    for ref in handoff['key_evidence_files']:
        path = Path(ref['path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
        add_out(path,'A2_exact_handoff_evidence_pin_audit_only')
    a2_release = OUT/'runtime_preflight/jobs/phase2_A_release_01'
    for name in ('A_phase2_source_screen_01.job.json','EXECUTION_FREEZE.json','PREPARATION.json',
                 'resource_ancestry_receipt.json','source_allowlist_receipt.json','SOURCE_PROJECTION_MAP.json'):
        add_out(a2_release/name,'A2_frozen_input_contract_and_source_receipts_audit_only')
    for ref in load(a2_release/'EXECUTION_FREEZE.json')['frozen_pins']:
        path = Path(ref['frozen_path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
        add_out(path,'A2_exact_execution_time_contract_copy_not_current_training_contract')
    # The five actual model-input JSON files are already pinned as job resources;
    # retain their original preparation paths too. No profile/model config copy.
    for name in ('source_pack_1.json','source_pack_2.json','pilot_user_context.json','material_metadata.json','pilot_feedback.json'):
        add_out(a2_release/'inputs'/name,'A2_exact_five_model_input_files_not_five_source_sessions')
    # Existing locally frozen C candidate manifest supplies exact files; only
    # the later root-selected bank in TRAINING_MANIFEST is loaded by default.
    c_manifest = OUT/'c_review_dataset_01/DELIVERY_MANIFEST.json'
    if c_manifest.is_file():
        add_out(c_manifest,'C_candidate_delivery_manifest_not_automatic_root_admission')
        for ref in load(c_manifest)['files']:
            path = Path(ref['path'])
            assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
            add_out(path,'C_originals_exact_error_masks_candidate_views_and_independent_reviews')

    conditional = OUT/'native_context_64k_01'
    assert digest(conditional/'FINAL_MANIFEST.json') == CONDITIONAL_SHA
    byproduct_rows = []
    for ref in load(conditional/'FINAL_MANIFEST.json')['files']:
        path = conditional/ref['path']
        assert digest(path) == ref['sha256'] and path.stat().st_size == ref['bytes']
        if path.suffix == '.pyc':
            byproduct_rows.append(ref)
        else:
            add('conditional/native_context_64k_01/'+ref['path'],path,
                'conditional64K_not_active_same_owner_exclusive_failed_attempts_audit_only')
    assert len(byproduct_rows) == 3
    add('conditional/native_context_64k_01/FINAL_MANIFEST.json',conditional/'FINAL_MANIFEST.json',
        'unaltered_frozen_65_file_conditional_manifest')
    save(work/'PACKAGING_BYPRODUCT_EXCLUSIONS.json',{
        'original_manifest_sha256':CONDITIONAL_SHA,'original_manifest_files':65,
        'byproducts_recorded_not_shipped':byproduct_rows,'non_byproduct_entities_packaged':62,
        'byproducts_are_not_training_resources':True,'original_manifest_not_rewritten':True})
    add('conditional/native_context_64k_01/PACKAGING_BYPRODUCT_EXCLUSIONS.json',
        work/'PACKAGING_BYPRODUCT_EXCLUSIONS.json','explicit_unchanged_manifest_byproduct_exclusion_overlay')
    save(work/'NONTRAINING_BYPRODUCTS.json',{'status':'HASH_METADATA_ONLY_NOT_SHIPPED_NOT_TRAINING',
        'bounded_scope_generated_files':byproducts,'conditional_generated_files':byproduct_rows})
    add('NONTRAINING_BYPRODUCTS.json',work/'NONTRAINING_BYPRODUCTS.json','generated_cache_file_pin_metadata_only')

    # Prior releases and the producer audit are referenced by exact manifests;
    # no legacy 750-object corpus/12-part dist is copied into this payload.
    prior = []
    for name in ('20261027_v10_checkpoint01','20261027_v10_checkpoint02','20261027_v10_checkpoint03'):
        base = RELEASE/'dataset'/name
        old = load(base/'ENCRYPTED_DELIVERY_REPORT.json')
        prior.append({'path':'dataset/'+name,'manifest_sha256':digest(base/'MANIFEST.json'),
                      'ciphertext_sha256':old['ciphertext_sha256'],
                      'payload_manifest_sha256':old['payload_manifest_sha256']})
    producer = RELEASE/'assessment/20261027_actor_write_producers'
    public_refs = []
    for name in ('PUBLIC_MANIFEST.json','MANIFEST.json','COMBINED_V9_AUX_ERRATA.json','COMBINED_ERRATA_QA.json'):
        path = producer/name
        public_refs.append({'path':path.relative_to(RELEASE).as_posix(),'bytes':path.stat().st_size,
                            'sha256':digest(path),'availability':'same_repository_public_packet_remote_status_separate'})
    errata_qa = load(producer/'COMBINED_ERRATA_QA.json')
    assert errata_qa['status'] == 'PASS_SAME_ACTUAL_SHARDS_SPLITS_AND_DISJOINT_TARGET_IDS'
    assert errata_qa['cross_audit_target_intersection'] == 0
    assert errata_qa['train_equals_all_splits_for_this_limited_erratum'] is True
    assert errata_qa['combined']['confirmed_revoke']['by_split']['train']['supervised_tokens'] == 2198
    assert errata_qa['combined']['pending_hold']['by_split']['train']['supervised_tokens'] == 888
    save(work/'PRIOR_RELEASE_REFERENCES.json',{'prior_checkpoints':prior,'public_producer_audit':public_refs,
        'v9_confirmed_revoked_train_supervised_tokens':2198,'v9_pending_train_supervised_tokens':888,
        'confirmed_and_pending_disjoint':True,'old_v9_auxiliary_never_implicitly_loaded':True,
        'old_750_source_objects_12dist_parts_not_duplicated':True})
    add('PRIOR_RELEASE_REFERENCES.json',work/'PRIOR_RELEASE_REFERENCES.json','unchanged_prior_data_and_public_producer_errata_exact_pins')
    for name in ('TRAINING_PLAN.md','MODEL_INPUT_OUTPUT.md','MODEL_CONTEXT_REQUIREMENTS.md',
                 'COST_ACCOUNTING_SCOPE.md','COVERAGE_EXPANSION.md','IMPLEMENTATION_RECORD.json'):
        path = ROOT/'research/plans/20261027_wrd_main_v10'/name
        add('design_reference/'+name,path,'current_frozen_nonexecuting_training_plan_and_source_pins')
    for name in ('A_B_MODULES.md','PIPELINE.md'):
        path = ROOT/'research/designs'/name
        assert '5.0.41' in path.read_text(encoding='utf-8')[:300]
        add('design_reference/'+name,path,'same_version_design_5_0_41')
    # New recovered banks contain actual source text and arrays, not just an
    # inventory. Only named, TRAIN-checked scientific bundles are enumerated.
    # No native runtime/workspace root, live episode or private SDK trace.
    for folder in ('historical_v6_reasoning_review_01', 'historical_v6_native_repair_01',
                   'recontext_original_R_01', 'brev_reasoning_review_01', 'native_CV_B_training_01'):
        scoped_tree(OUT/folder,folder,'recovered_TRAIN_only_original_R_actions_versions_and_explicit_curation_history')
    recovered_profiles=[]
    for episode_id in ('B_phase2_cv_01','B_phase2_html_01','B_phase2_cv_revision_01'):
        episode = OUT/'runtime_preflight/episodes'/episode_id
        assert (episode/'result.json').is_file() and (episode/'usage.json').is_file()
        for name in ('job.json','request.json','dispatch.json','execution.json','process.json',
                     'native_events.jsonl','outer_recording_receipt.json','response.json','result.json',
                     'usage.json','PASSIVE_USAGE_RECONCILIATION.json','CAPTURE_ASSESSMENT.json'):
            path=episode/name
            if path.is_file():add_out(path,'completed_new_native_collection_evidence_not_live_runtime')
        profile_calls=[]
        for call in sorted((episode/'api_audit').iterdir()):
            if not call.is_dir():continue
            for name in ('receipt.json','request.raw.json','response.raw.sse','response.raw.json','response.inspection.json'):
                path=call/name
                if path.is_file():add_out(path,'exact_closed_native_API_original_messages_reasoning_actions_and_observations')
            entries={}
            response_name=Path(load(call/'receipt.json')['response_path']).name
            assert response_name in {'response.raw.sse','response.raw.json'}
            for key,name in (('request','request.raw.json'),('response',response_name),('receipt','receipt.json')):
                path=call/name
                entries[key]={'path':path.relative_to(OUT).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
            entries['external_vision_helper']=episode_id=='B_phase2_html_01' and call.name.startswith('0017_')
            profile_calls.append(entries)
        expected={'HTTP':len(profile_calls),'R_characters':{'B_phase2_cv_01':22806,'B_phase2_html_01':45604,'B_phase2_cv_revision_01':43319}[episode_id],
                  'finish_length':int(episode_id=='B_phase2_cv_01'),
                  'stop_or_tool_calls':len(profile_calls)-int(episode_id=='B_phase2_cv_01')}
        if episode_id=='B_phase2_html_01':expected['external_helper_HTTP_not_text_main_Agent']=1
        recovered_profiles.append({'episode':episode_id,'calls':profile_calls,'expected_counts':expected})
        scoped_tree(OUT/'native_records'/episode_id,'native_records/'+episode_id,
                    'complete_original_fields_and_resource_version_lineage_not_automatic_positive_loss')
    save(work/'RECOVERED_DATA_PROFILE_SCOPES.json',{
        'closed_episodes':recovered_profiles,'all_are_TRAIN_ancestry_no_formal_evaluation':True,
        'last_closed_scope':load(OUT/'COST_ACCOUNTING_SCOPE.json')['latest_closed_native_collection_snapshot'],
        'other_live_or_later_trials_are_not_in_this_frozen_payload':True,
        'legacy26_original_R_characters_preserved':396231,'legacy26_positive_original_R_tokens':33153,
        'legacy26_replaces_old12_not_added_twice':True,'training_started':False})
    add('RECOVERED_DATA_PROFILE_SCOPES.json',work/'RECOVERED_DATA_PROFILE_SCOPES.json',
        'new97_complete_streams_one_length_one_external_helper_not_extra_training_targets')
    for folder in ('B_PHASE2_CV_RESOURCE_AUDIT_01','B_PHASE2_CV_REVISION_AUDIT_01','B_PHASE2_HTML_RESOURCE_AUDIT_01',
                   'B_REVISION_FAILURE_OBJECT_PAIRS_01'):
        scoped_tree(OUT/'runtime_preflight/quality'/folder,'runtime_preflight/quality/'+folder,
                    'independent_limited_resource_tests_and_preserved_counterexamples_not_retention')
    for ref in active['active_compilation_reports']:
        parent=(OUT/ref['path']).parent
        for name in ('ROOT_TOKEN_QA.json','ROOT_SEMANTIC_ADMISSION.json'):
            path=parent/name
            if path.is_file():add_out(path,'actual_new_bank_root_dual_token_and_scoped_semantic_QA')
    for name in ('ROOT_MAIN_460_LOADER_QA.json','ROOT_MAIN_481_LOADER_QA.json','ROOT_MAIN_495_LOADER_QA.json'):
        path=OUT/name
        if path.is_file():add_out(path,'actual_manifest_admission_snapshot_loader_QA_not_new_training_samples')
    for name in ('checkpoint04_loader.py','package_checkpoint04.py','package_checkpoint.py',
                 'compile_main.py','extract_native_main.py','build_training_manifest.py',
                 'verify_compilation.py','native_file_version_graph.py','summarize_first_chain.py',
                 'approve_real_state_bank_02.py','audit_B02_resources.py','audit_B02_nested_refs.py',
                 'audit_B_revision_01.py','audit_C_consumption.py','audit_first_C_review.py'):
        add('source_tooling/'+name,SCRIPT_DIR/name,'reproducible_offline_compilation_QA_or_packaging_source')
    for name in ('admit_recovered_banks_01.py','normalize_historical_R_bank_05.py',
                 'normalize_native_cv_bank_01.py','admit_native_cv_01.py',
                 'build_call17_real_state_R.py','refresh_closed_cost_scope_01.py','check_failure_id_path_pairs.py'):
        add('source_tooling/'+name,SCRIPT_DIR/name,'new_recovered_data_exact_normalization_mask_semantic_admission_and_QA')
    for name in ('normalize_historical_R_bank_26.py','admit_historical_R_26.py'):
        add('source_tooling/'+name,SCRIPT_DIR/name,'peer_refined26_replaces12_without_duplicate_original_R_exposure')
    add('source_tooling/shared_causal_compiler_v4.py',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py',
        'reused_causal_compiler_source')
    add('source_tooling/encrypted_delivery_v4.py',ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py',
        'authenticated_delivery_implementation_no_keys')
    for name in ('REMOTE_CHECKPOINT01_VERIFICATION.json','REMOTE_CHECKPOINT02_VERIFICATION.json',
                 'REMOTE_PLAN_UPDATES_VERIFICATION.json'):
        add_out(OUT/name,'prior_actual_remote_readback_receipt')
    loader = module(SCRIPT_DIR/'checkpoint04_loader.py','checkpoint04_preparation_loader')
    main_qa = loader.verify(OUT)
    new_recovery_qa=loader.verify_recovered_profiles(OUT,work/'RECOVERED_DATA_PROFILE_SCOPES.json')
    save(work/'NEW_RECOVERY_PREPARATION_QA.json',new_recovery_qa)
    add('NEW_RECOVERY_PREPARATION_QA.json',work/'NEW_RECOVERY_PREPARATION_QA.json',
        'actual97_raw_stream_reparse_with_length_and_external_helper_units')
    conditional_qa = loader.verify_conditional(OUT,candidate_base=conditional,
                        exclusions_path=work/'PACKAGING_BYPRODUCT_EXCLUSIONS.json')
    assert conditional_qa['candidate_sequences'] == 6 and conditional_qa['candidate_original_R_supervised_tokens'] == 5980
    save(work/'DEFAULT_MAIN_PREPARATION_QA.json',main_qa)
    add('DEFAULT_MAIN_PREPARATION_QA.json',work/'DEFAULT_MAIN_PREPARATION_QA.json','actual_default_main_loader_scope_check')
    save(work/'CONDITIONAL_SEPARATE_PREPARATION_QA.json',conditional_qa)
    add('CONDITIONAL_SEPARATE_PREPARATION_QA.json',work/'CONDITIONAL_SEPARATE_PREPARATION_QA.json',
        'actual_18_binary_array_checks_not_added_to_default_main')
    first_chain = quality/'FIRST_CHAIN_INDEPENDENT_REVIEW'
    census = load(first_chain/'RAW_RECOVERY_SUPPLEMENT.json')['latest_exact_units']
    assert census['compatible_HTTP_records'] == len([r for r in api_rows if r['episode'] != A2_EPISODE]) == 147
    assert census['complete_HTTP_original_response_records_recovered'] == 145
    assert census['total_original_R_chars_preserved'] == 235045
    assert sum(load(OUT/'native_records'/e/'raw_recovery/EXTRACTION_REPORT.json')['captured_complete_responses']
               for e in FIRST_CHAIN_EPISODES) == 145
    assert sum(load(OUT/'native_records'/e/'raw_recovery/EXTRACTION_REPORT.json')['original_readable_R_chars']
               for e in FIRST_CHAIN_EPISODES) == census['complete_HTTP_original_R_chars'] == 229403
    costs = load(first_chain/'ACTUAL_COST_RECONCILIATION.json')
    assert costs['actual_request_identities'] == 110 and costs['known_total_tokens'] == 8660547
    assert costs['unknown_usage_calls'] == 1 and costs['qualified_retained_skills'] == 0
    for ref in costs['episodes']:
        assert digest(Path(ref['usage_path'])) == ref['usage_sha256']
    a2_usage = load(OUT/'runtime_preflight/episodes'/A2_EPISODE/'usage.json')
    assert a2_usage['known_total_tokens'] == 1134348 and a2_usage['model_calls'] == 11
    assert a2_usage['unknown_usage_calls'] == 0
    a2_raw = load(OUT/'native_records'/A2_EPISODE/'raw_recovery/EXTRACTION_REPORT.json')
    assert a2_raw['captured_complete_responses'] == 11 and a2_raw['original_readable_R_chars'] == 37441
    assert a2_raw['reviewed_student_records'] == 0
    save(work/'EVIDENCE_PROFILE_SCOPES.json',{
        'first_ten_chain':{'episode_ids':list(FIRST_CHAIN_EPISODES),'outer_dispatches':10,'native_sessions':11,
            'compatible_HTTP':147,'complete_HTTP':145,'partial_HTTP':2,'original_R_chars':235045,
            'known_tokens':8660547,'actual_upstream_request_identities':110,'unknown_usage_calls':1,
            'qualified_retained_skills':0,'original_frozen_reports_not_rewritten':True},
        'A2_audit_only':{'episode_ids':[A2_EPISODE],'outer_dispatches':1,'native_sessions':1,
            'compatible_HTTP':11,'complete_HTTP':11,'partial_HTTP':0,'original_R_chars':37441,
            'known_tokens':1134348,'actual_upstream_request_identities':11,'unknown_usage_calls':0,
            'native_SQLite_export_rows':36,'native_SQLite_message_rows':22,'provider_meter_rows':55,
            'other_layer_trajectory_items_separate_unit':72,'new_positive_training_targets':0,
            'error_quotes_wrong_grouping_or_unsourced_halfpage_cap_not_promoted':True,
            'handoff_pins_sha256':digest(handoff_path)},
        'legacy_first_chain_and_A2_scope':{'outer_dispatches':11,'native_sessions':12,'compatible_HTTP':158,
            'complete_HTTP':156,'partial_HTTP':2,'original_R_chars':272486,'known_tokens':9794895,
            'actual_upstream_request_identities':121,'unknown_usage_calls':1},
        'conditional_window_profile':{'complete_natural_business_episodes':7,'compatible_HTTP':111,
            'excludes_final_C_review_and_A2':True,'not_a_profile_of_all_158_HTTP':True},
        'first_chain_cost_plus_A2_known_tokens':costs['known_total_tokens']+a2_usage['known_total_tokens'],
        'native_wrapper_still_original_unchanged':True,'training_started':False})
    add('EVIDENCE_PROFILE_SCOPES.json',work/'EVIDENCE_PROFILE_SCOPES.json','separate_first_chain_A2_and_conditional_population_units')
    profile_qa = loader.verify_evidence_profiles(OUT,profile_path=work/'EVIDENCE_PROFILE_SCOPES.json',
                    index_path=work/'API_CAPTURE_INDEX.json',
                    source_paths={name:Path(ref['original_path']) for name,ref in members.items()})
    save(work/'EVIDENCE_PROFILE_PREPARATION_QA.json',profile_qa)
    add('EVIDENCE_PROFILE_PREPARATION_QA.json',work/'EVIDENCE_PROFILE_PREPARATION_QA.json',
        'actual_full_158_exchange_R_usage_and_event_layer_recount_not_extra_training_targets')
    proposal = {
        'schema':'wrd-v10-checkpoint04-explicit-allowlist-preparation',
        'status':'PREPARED_FOR_ROOT_REVIEW_NOT_BUILT_NOT_PUBLISHED',
        'design_revision':'5.0.41','training_manifest_sha256':digest(manifest_path),
        'actual_counts':active['actual_counts'],'active_compiled_banks':sorted(banks),
        'default_main_QA':main_qa,'conditional64K_separate_QA':conditional_qa,'compatible_HTTP_records':255,
        'evidence_profiles_separate_QA':profile_qa,
        'new97_recovery_QA':new_recovery_qa,
        'complete_HTTP_records':253,'partial_HTTP_records':2,
        'native_sessions':15,'outer_dispatches':14,
        'original_R_preserved_chars':384215,
        'known_native_tokens':16197610,'actual_upstream_request_identities':206,'unknown_usage_calls':2,
        'later_HTML_revision_and_C_trials_not_in_this_frozen_scope':True,
        'qualified_retained_skills':0,'all_cost_per_qualified_skill':'UNDEFINED_ZERO_QUALIFIED_SKILLS',
        'cash_and_AI_curation_cost':'UNKNOWN_NOT_ZERO',
        'conditional_64k_original_manifest_sha256':CONDITIONAL_SHA,
        'conditional_64k_is_default_active':False,'conditional_coverage_111_calls_not_all_158':True,
        'first_ten_chain_frozen_reports_147_HTTP_235045_R_chars_not_overwritten':True,
        'A2_audit_only_does_not_add_default_positive_targets':True,
        'generated_file_byproducts_are_metadata_only':True,
        'files':sorted(members.values(),key=lambda r:r['path']),
        'file_count':len(members),'source_bytes':sum(r['bytes'] for r in members.values()),
        'source_allowlist_is_not_a_training_target_count':True,
        'no_private_credential_modelconfig_SQL_SDK_or_reparse_tree':True,
        'preparation_reads_keys':False,'training_started':False,'weights_loaded':False,
        'full_WRD_main_training_ready':False,'git_mutated_or_pushed':False,
        'work_directory':str(work),'script_sha256':digest(Path(__file__)),
    }
    dest = work/'CHECKPOINT04_ALLOWLIST_PROPOSAL.json'
    save(dest,proposal)
    save(OUT/'CHECKPOINT04_PREPARATION_RECEIPT.json',{'status':proposal['status'],
        'prepared_allowlist':str(dest),'prepared_allowlist_sha256':digest(dest),
        'file_count':len(members),'source_bytes':proposal['source_bytes'],
        'actual_counts':active['actual_counts'],'keys_read':False,'build_or_Git_copy_performed':False})
    print(json.dumps({'status':proposal['status'],'prepared_allowlist':str(dest),
        'prepared_allowlist_sha256':digest(dest),'files':len(members),'source_bytes':proposal['source_bytes'],
        'actual_counts':active['actual_counts']},ensure_ascii=False))


def scan_stream(stream,patterns):
    carry = b''
    keep = max(map(len,patterns))-1
    for block in iter(lambda:stream.read(BLOCK),b''):
        current = carry+block
        if any(pattern in current for pattern in patterns):
            return False
        carry = current[-keep:] if keep else b''
    return True


def scan_file(path,patterns):
    with path.open('rb') as f:
        assert scan_stream(f,patterns),'credential_bytes_in_allowlisted_member'
    if path.suffix == '.gz':
        with gzip.open(path,'rb') as f:
            assert scan_stream(f,patterns),'credential_bytes_in_decompressed_member'
    elif path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                assert not info.filename.startswith('/') and '..' not in PurePosixPath(info.filename).parts
                with archive.open(info) as f:
                    assert scan_stream(f,patterns),'credential_bytes_in_zip_member'


def build(prepared_path,root_go):
    assert prepared_path and root_go
    assert digest(prepared_path) == root_go,'root_go_must_pin_exact_reviewed_preparation'
    prepared = load(prepared_path)
    assert prepared['status'] == 'PREPARED_FOR_ROOT_REVIEW_NOT_BUILT_NOT_PUBLISHED'
    assert prepared['script_sha256'] == digest(Path(__file__)),'prepare_again_after_script_changes'
    assert digest(OUT/'TRAINING_MANIFEST.json') == prepared['training_manifest_sha256']
    assert not DEST.exists(),'new_checkpoint_destination_required'
    work = OUT/'p04build'/str(time.time_ns())[-8:]
    stage = work/'public'
    stage.mkdir(parents=True,exist_ok=False)
    members = {}
    for ref in prepared['files']:
        path = regular(Path(ref['original_path']))
        safe_name(ref['path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256'],'frozen_source_changed'
        members[ref['path']] = path
    key_values = [load(OUT/'runtime_preflight/private'/name)['api_key']
                  for name in ('model_consumer.json','model_upstream.json')]
    assert all(isinstance(x,str) and x for x in key_values)
    aes_key = KEY.read_bytes()
    assert len(aes_key) == 32
    patterns = {aes_key}|{x.encode('utf-8') for x in key_values}
    patterns.update(json.dumps(x,ensure_ascii=False)[1:-1].encode('utf-8') for x in key_values)
    for path in members.values():
        scan_file(path,patterns)
    save(work/'EVIDENCE_PATH_ALIASES.json',{
        'original_absolute_path_to_archive_path':{str(path):name for name,path in members.items()},
        'original_files_not_rewritten':True,'default_active_manifest':'TRAINING_MANIFEST.json',
        'only_default_manifest_arrays_may_be_loaded':True,
        'conditional_64k_and_failed_attempts_and_old_candidates_never_glob':True})
    members['EVIDENCE_PATH_ALIASES.json'] = work/'EVIDENCE_PATH_ALIASES.json'
    files = [{'path':name,'bytes':p.stat().st_size,'sha256':digest(p),'original_path':str(p)}
             for name,p in sorted(members.items())]
    inner = {'schema':'wrd-v10-checkpoint04-authenticated-payload',
        'status':'INTERMEDIATE_NOT_FINAL_FULL_WRD_NOT_READY','active_manifest':'TRAINING_MANIFEST.json',
        'actual_counts':prepared['actual_counts'],'files':files,'full_WRD_main_training_ready':False,
        'training_started':False,'conditional_64k_is_default_active':False,
        'qualified_retained_skills':0,'all_cost_per_qualified_skill':'UNDEFINED_ZERO_QUALIFIED_SKILLS',
        'prepared_allowlist_sha256':root_go}
    save(work/'PAYLOAD_MANIFEST.json',inner)
    plain = work/'wrd-v10-checkpoint04.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT) as archive:
        archive.add(work/'PAYLOAD_MANIFEST.json',arcname='PAYLOAD_MANIFEST.json',recursive=False)
        for name,path in sorted(members.items()):
            archive.add(path,arcname=name,recursive=False)
    helper = module(SCRIPT_DIR/'package_checkpoint.py','checkpoint04_shared_restore')
    crypto = module(ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py','checkpoint04_crypto')
    controlled = stage/'controlled'
    controlled.mkdir()
    cipher = controlled/'wrd-v10-checkpoint04.tar.gz.aesgcm'
    receipt = crypto.encrypt(plain,cipher,KEY,reuse_key=True)
    receipt.update(schema_version='wrd-v10-checkpoint04-encryption-receipt',
        payload_manifest_sha256=digest(work/'PAYLOAD_MANIFEST.json'),plaintext_bytes=plain.stat().st_size,
        authenticated_files=len(files)+1,training_started=False,full_WRD_main_training_ready=False)
    save(stage/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
    tooling = stage/'tooling'
    tooling.mkdir()
    (tooling/'restore_checkpoint.py').write_text(helper.RESTORE,encoding='utf-8')
    shutil.copyfile(SCRIPT_DIR/'checkpoint04_loader.py',tooling/'checkpoint_loader.py')
    restore = module(tooling/'restore_checkpoint.py','checkpoint04_portable_restore')
    restored = work/'restore_validation'
    restored_qa = restore.restore(cipher,stage/'ENCRYPTED_DELIVERY_REPORT.json',KEY,restored)
    loader = module(tooling/'checkpoint_loader.py','checkpoint04_portable_loader')
    main_qa,conditional_qa = loader.verify(restored),loader.verify_conditional(restored)
    profile_qa = loader.verify_evidence_profiles(restored)
    recovered_qa=loader.verify_recovered_profiles(restored)
    assert main_qa['counts'] == prepared['actual_counts']
    assert conditional_qa['candidate_sequences'] == 6
    for name in ('TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json'):
        shutil.copyfile(restored/name,stage/name)
    shutil.copyfile(restored/'COST_ACCOUNTING_SCOPE.json',stage/'COST_ACCOUNTING_SCOPE.json')
    shutil.copyfile(restored/'design_reference/COST_ACCOUNTING_SCOPE.md',stage/'COST_ACCOUNTING_SCOPE.md')
    shutil.copyfile(restored/'design_reference/TRAINING_PLAN.md',stage/'TRAINING_PLAN.md')
    shutil.copyfile(restored/'runtime_preflight/quality/FIRST_CHAIN_INDEPENDENT_REVIEW/FIRST_CHAIN_REPORT.md',stage/'FIRST_CHAIN_REPORT.md')
    save(stage/'CHECKPOINT_STATUS.json',{
        key:prepared[key] for key in ('actual_counts','active_compiled_banks','compatible_HTTP_records',
          'complete_HTTP_records','partial_HTTP_records','native_sessions','outer_dispatches',
          'original_R_preserved_chars','known_native_tokens','actual_upstream_request_identities','unknown_usage_calls',
          'qualified_retained_skills','all_cost_per_qualified_skill','cash_and_AI_curation_cost',
          'conditional_64k_is_default_active','conditional_coverage_111_calls_not_all_158',
          'first_ten_chain_frozen_reports_147_HTTP_235045_R_chars_not_overwritten',
          'A2_audit_only_does_not_add_default_positive_targets',
          'generated_file_byproducts_are_metadata_only','training_started','weights_loaded','full_WRD_main_training_ready')})
    save(stage/'CHECKPOINT_QA.json',{'status':'PASS','actual_restoration':restored_qa,
        'actual_default_loader_verification':main_qa,'conditional64K_separate_verification':conditional_qa,
        'new97_closed_original_streams_actual_reparse':recovered_qa,
        'raw_evidence_population_separate_verification':profile_qa,
        'AES_GCM_roundtrip':receipt['authenticated_roundtrip_sha_verified'],
        'credential_scan':{'model_keys_read_only_in_memory':2,'AES_key_not_archived':True,
          'members_scanned_including_decompressed_gzip_and_zip':len(members),'matches':0,
          'key_values_not_serialized_or_printed':True},
        'root_go_preparation_sha256':root_go,'token_QA_not_full_pipeline_quality_or_sufficiency':True,
        'training_started':False,'full_WRD_main_training_ready':False})
    (stage/'README.md').write_text('''# WRD v10 检查点04：实际原思考与程序过程继续扩充

本包交付实际可恢复的默认训练正文／token数组／loss mask／来源群与版本证据。当前495目标、124452监督tokens、2636716输入tokens，437≤16K、58在16—32K；436需求契约目标与59过程目标分别统计。新增六TRAIN源26段逐字历史原思考33153监督tokens，保全396231原R字符；CV原生过程21目标6469监督；三个完整必要状态的新原生动作投影1098监督。历史12已被26替换，不能相加38；新动作不冒称原Teacher原生调用。原226、新H和静态dev/test继续隔离，旧v9辅助不默认混入。完整自主A—D示范仍0，合格保留0，没有启动训练。

原旧158兼容HTTP之外，新保全CV制作、HTML制作、CV修订共97完整传输HTTP／111729原R字符，其中1个finish=length，不补EOS；HTML独立视觉helper1次／5030tokens单列，不冒充Qwen文字模型视觉能力且不重复加费。包内总255HTTP／384215原R字符不是255个训练目标。当前冻结已结束范围14 outer／15 native、16197610已知tokens／206上游身份／2unknown；之后HTML修订及四消费不在本冻结范围，另按实际终态报告。Codex／CPU／现金成本仍未知非零。

首次有界链共有10 outer阶段、11原生sessions、147兼容HTTP，其中145完整、2部分响应；实际110上游身份、8660547已知tokens及1个未知usage。现金和AI整理费用UNKNOWN_NOT_ZERO。两例技能消费比无技能更贵，原决策STOP，0个合格留存技能，每合格技能总成本因此未定义。保全负结果不等于批准全部原R/动作；局修仅授原21＋独立8所支持的局部信用，新状态理由与原Teacher R分别标记。训练尚未开始。

已完成A2筛查另作为audit_only第11 outer阶段保全：11完整HTTP、37441原R字符，1134348已知tokens、11实际请求身份，0新增正监督。其错误quote ID、错误归并或无依据的半页上限判断均不因completed被授信用。合计11 outer／12 native／158 HTTP（156完整＋2部分）、272486原R字符，9794895已知tokens／121请求身份／1未知usage；首10链的旧原报告与费用不回写。A2的36 SQLite事件／22 message／1 session与55 provider meter行分开统计，不能互换。

恢复：安装CPU cryptography，执行 `python tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint04.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地既有v4密钥> --out <新目录>`，随后执行 `python tooling/checkpoint_loader.py --root <恢复目录> --verify-conditional --verify-evidence`。恢复先认证密文并逐成员SHA，loader只按主manifest指定路径重建labels/weights，验证外置root准入与真实owner唯一，不加载模型或训练；证据全量统计与条件64K另行核查，不增加默认训练量。

conditional/native_context_64k_01另有6个full53候选、5980原R tokens和18个二进制数组，非默认ACTIVE，不能与core32同owner重复曝光。其111请求窗口统计不包含后续终评或A2，不是全部158请求的覆盖率；Spark未前向或训练。原冻结manifest65文件中的3个pyc只保存SHA/size元数据，不发布为训练资源；失败CPU尝试也是审计记录，不能glob训练。完整原生53工具与core7学生投影、训练序列长度与服务总窗口在方案中分别解释。

历史checkpoint01/02、old750对象/12dist和producer公开勘误只按精确SHA引用，不覆盖或重复整个旧库。source_tooling提供复现源码；EVIDENCE_PATH_ALIASES说明原绝对证据路径与归档路径的关系。不要递归扫描旧银行或条件目录作为训练入口。该交付是经过审阅的主子任务检查点，仍须扩充更多真实机制与完整自主调度证据，不能据此保证达到目标模型能力。
''',encoding='utf-8')
    # Recheck every frozen member after restoration; do not silently package a
    # moving plan, updated bank or altered test/credit receipt.
    for ref in files:
        path = Path(ref['original_path'])
        assert path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256']
    for path in stage.rglob('*'):
        if path.is_file():
            safe_name(path.relative_to(stage).as_posix())
            scan_file(path,patterns)
    payload = [{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
               for p in sorted(stage.rglob('*')) if p.is_file()]
    save(stage/'MANIFEST.json',{'schema':'wrd-v10-checkpoint04-public-manifest',
        'status':'INTERMEDIATE_NOT_FINAL_FULL_WRD_NOT_READY','files':payload,
        'payload_files':len(payload),'payload_bytes':sum(r['bytes'] for r in payload),
        'authenticated_private_members':len(files)+1,'contains_actual_data_encrypted':True,
        'no_keys_uploaded':True,'training_started':False,'full_WRD_main_training_ready':False,
        'not_a_final_completion_claim':True})
    assert DEST.resolve().is_relative_to((RELEASE/'dataset').resolve())
    shutil.copytree(stage,DEST)
    result = {'status':'CHECKPOINT04_BUILT_NOT_FINAL_NOT_PUSHED','destination':str(DEST),
        'manifest_sha256':digest(DEST/'MANIFEST.json'),'cipher_sha256':digest(cipher),
        'cipher_bytes':cipher.stat().st_size,'authenticated_private_members':len(files)+1,
        'payload_files_including_manifest':len(payload)+1,'actual_counts':prepared['actual_counts'],
        'actual_restore_and_default_loader':'PASS','conditional_separate_QA':conditional_qa,
        'credential_matches':0,'keys_not_uploaded':True,'training_started':False,
        'full_WRD_main_training_ready':False,'git_commit_or_push_performed':False,
        'prepared_allowlist_sha256':root_go,'work_directory':str(work)}
    save(OUT/'CHECKPOINT04_BUILD_RECEIPT.json',result)
    print(json.dumps(result,ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true')
    mode.add_argument('--build',action='store_true')
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--root-go',help='exact SHA256 of the root-reviewed preparation, only after explicit go')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        build(args.prepared,args.root_go)


if __name__ == '__main__':
    main()
