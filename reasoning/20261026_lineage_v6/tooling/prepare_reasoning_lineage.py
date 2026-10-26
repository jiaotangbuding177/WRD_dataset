"""Preserve original historical reasoning requests for independent lineage review.

Offline preparation only. Source identity is not a resource-closure admission.
All source bodies stay in controlled output. No model, training or agent runs.
"""
from __future__ import annotations
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
OUT = ROOT / 'output/20261026_wrd_sequences_v6'


def js(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def sha_bytes(x): return hashlib.sha256(x).hexdigest()
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def dump(p, values):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, 'wt', encoding='utf-8', newline='\n') as f:
        for value in values: f.write(js(value)+'\n')


def main():
    compiled_path = BASE/'curated_reasoning/controlled.original_reasoning32k.jsonl.gz'
    compiled = list(rows(compiled_path)); ids = {r['id'] for r in compiled}
    assert len(compiled) == len(ids)
    pair_paths = [BASE/'controlled/raw_pairs.all.jsonl.gz', BASE/'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz']
    pairs = {r['id']:r for p in pair_paths for r in rows(p) if r['id'] in ids}
    assert set(pairs) == ids
    run_path = BASE/'controlled/raw_run_trajectories.jsonl.gz'
    runs = {r['run_id']:r for r in rows(run_path) if r['run_id'] in {p.get('run_id') for p in pairs.values()}}
    sse_scope_path = BASE/'controlled/sse_scope_review.by_pair.jsonl.gz'
    raw_scope_path = BASE/'controlled/raw_scope_review.by_run.jsonl.gz'
    sse_scope = {r['pair_id']:r for r in rows(sse_scope_path)}
    raw_scope = {r['run_id']:r for r in rows(raw_scope_path)}
    raw_scope_by_path = {str(Path(r['run_path'])).lower():r for r in rows(raw_scope_path)}
    public_pair_paths = [BASE/'curated_reasoning/public/sse_core.pairs.jsonl.gz',
                         BASE/'curated_reasoning/public/historical_generation.pairs.jsonl.gz']
    # This SHA is the privacy transform's original record identity; it is a
    # join to actual source bytes, not an assumption that public IDs are equal.
    raw_pair_by_hash = {sha_bytes(js(p).encode()):i for i,p in pairs.items()}
    sse_all_path = BASE/'controlled/sse_reasoning_pairs.all.jsonl.gz'
    # The evolution view adds split-evidence fields after privacy projection;
    # join its immutable pre-overlay source record, with the same pair ID.
    for p in rows(sse_all_path):
        if p['id'] in ids:
            raw_pair_by_hash[sha_bytes(js(p).encode())]=p['id']
    public_pairs = {}
    for p in public_pair_paths:
        for r in rows(p):
            original_hash = (r.get('privacy_transform') or {}).get('source_record_sha256')
            public_pairs[r['id']] = {'source_original_pair_id':raw_pair_by_hash.get(original_hash),
                'original_record_sha256':original_hash, 'public_pair':r}
    public_compiled_path = BASE/'public_reasoning_compiled_final/all_records.jsonl.gz'
    public_compiled = [r for r in rows(public_compiled_path) if r['total_tokens']<=32768 and r['supervised_tokens']>0]
    public_index = []
    for r in public_compiled:
        join = public_pairs[r['id']]
        public_index.append({'public_compiled_id':r['id'], 'source_original_pair_id':join['source_original_pair_id'],
            'original_record_sha256':join['original_record_sha256'], 'source_public_record_sha256':r['source_public_record_sha256'],
            'public_pair_file':r['source_pair_file'], 'total_tokens':r['total_tokens'],
            'supervised_tokens':r['supervised_tokens'], 'original_reasoning_present':any(s[2].startswith('R') for s in r['supervision_spans']),
            'is_distinct_projection_not_additional_independent_training_task':True})
    cas = OUT/'controlled/reasoning_cas'; cas.mkdir(parents=True, exist_ok=True)
    source_checks = {}; lineage_inputs = []; complete_runs = set()
    def source_record(value, role):
        if not isinstance(value,dict) or not isinstance(value.get('path'),str): return None
        p = Path(value['path'])
        # Never discover secrets through globbing or follow a key dependency.
        if p.suffix.lower()=='.key' or 'local_delivery_key' in p.parts:
            raise ValueError('key_dependency_not_allowed')
        expected = value.get('sha256')
        identity = str(p)
        if identity not in source_checks:
            row = {'path':identity,'declared_sha256':expected,'role':role,'exists':p.is_file()}
            if p.is_file():
                actual = digest(p); row.update({'actual_sha256':actual,'bytes':p.stat().st_size,
                    'declared_sha256_matches':expected==actual if expected else None})
                destination = cas/actual
                if not destination.exists(): shutil.copyfile(p,destination)
                assert digest(destination)==actual
                row['immutable_export_path']=str(destination.relative_to(ROOT))
            source_checks[identity]=row
        return source_checks[identity]
    for c in compiled:
        p=pairs[c['id']]; run=runs.get(p.get('run_id')); dependencies=[]
        for field in ('source_request','source_response','source_sse','source_stored_response','source_parsed','source_receipt'):
            dependency=source_record(p.get(field),field)
            if dependency: dependencies.append(dependency)
        outcome=c.get('original_outcome_evidence') or {}
        if outcome.get('source_transcript_path'):
            dependency=source_record({'path':outcome['source_transcript_path'], 'sha256':outcome['source_transcript_sha256']},'original_action_transcript')
            dependencies.append(dependency)
        if run:
            for field in ('source_result','source_input_packet','source_final_messages'):
                dependency=source_record(run.get(field),field)
                if dependency: dependencies.append(dependency)
            complete_runs.add(run['run_id'])
        request=p['original_request']; response=p['original_response']
        scope=sse_scope.get(p['id']) if p.get('episode_id') else raw_scope_by_path.get(str(Path(p['run_path'])).lower())
        lineage_inputs.append({'schema_version':'wrd-v6-historical-pair-lineage-input', 'pair_id':p['id'],
            'parent_run_id':p.get('run_id'), 'historical_source_episode_id':p.get('episode_id'),
            'role_scope':p['role_scope'],'historical_condition':p['historical_condition'],
            'source_record_sha256':sha_bytes(js(p).encode()), 'original_request_canonical_sha256':sha_bytes(js(request).encode()),
            'original_response_canonical_sha256':sha_bytes(js(response).encode()),
            'request_messages_canonical_sha256':sha_bytes(js(request.get('messages',[])).encode()),
            'original_request':request,'original_response':response,
            'original_pair':p,'parent_run_record':run,'existing_source_identity_review':scope,
            'original_action_outcome_evidence':outcome,'source_file_dependencies':dependencies,
            'full_request_is_preserved':True,'resource_closure_not_inferred_from_source_identity':True,
            'training_admitted_by_this_preparation':False, 'publication_approved':False,
            'old_compiled_original_reasoning_characters':c['original_reasoning_characters'],
            'old_compiled_supervised_tokens':c['supervised_tokens'],
            'old_compiled_components':c['supervised_tokens_by_component']})
    controlled=OUT/'controlled'
    outputs = {
        'reasoning_pair_lineage_inputs.jsonl.gz':lineage_inputs,
        'reasoning_pairs.original116.jsonl.gz':pairs.values(),
        'reasoning_runs.original.jsonl.gz':[runs[i] for i in sorted(complete_runs)],
        'reasoning_public_to_original.index.jsonl.gz':public_index,
        'reasoning_source_file_dependencies.jsonl.gz':source_checks.values(),
    }
    for name,values in outputs.items(): dump(controlled/name,values)
    missing=[r for r in source_checks.values() if not r['exists'] or r.get('declared_sha256_matches') is False]
    report={'schema_version':'wrd-v6-historical-reasoning-lineage-preparation','controlled_pairs':len(compiled),
        'controlled_original_R_positive_pairs':sum(any(s[2].startswith('R') for s in r['supervision_spans']) for r in compiled),
        'controlled_original_R_chars':sum(c['original_reasoning_characters'] for c in compiled),
        'controlled_components':dict(sum((Counter(c['supervised_tokens_by_component']) for c in compiled),Counter())),
        'parent_raw_runs':len(runs),'sse_historical_source_episodes':len({p.get('episode_id') for p in pairs.values() if p.get('episode_id')}),
        'public_32k_positive_projection_pairs':len(public_compiled),
        'public_projections_joined_to_selected_original_pair_by_immutable_record_hash':sum(bool(r['source_original_pair_id']) for r in public_index),
        'public_unmatched_projection_ids':[r['public_compiled_id'] for r in public_index if not r['source_original_pair_id']],
        'source_files':len(source_checks),'missing_or_changed_source_files':missing,
        'source_files_copied_byte_exact_to_controlled_CAS':sum(r['exists'] for r in source_checks.values()),
        'no_resource_closure_admission_created':True, 'source_identity_evidence_not_equal_full_resource_closure':True,
        'native_91_episode_R_not_created_or_spliced':True, 'training_started':False,'new_model_calls':0,
        'outputs':{name:{'sha256':digest(controlled/name),'bytes':(controlled/name).stat().st_size} for name in outputs},
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [compiled_path,*pair_paths,sse_all_path,run_path,sse_scope_path,raw_scope_path,*public_pair_paths,public_compiled_path]},
        'script_sha256':digest(Path(__file__))}
    save(OUT/'REASONING_PREPARATION_REPORT.json',report)
    print(js({k:report[k] for k in ['controlled_pairs','controlled_original_R_positive_pairs','parent_raw_runs',
        'public_32k_positive_projection_pairs','public_projections_joined_to_selected_original_pair_by_immutable_record_hash',
        'source_files','source_files_copied_byte_exact_to_controlled_CAS']}),flush=True)


if __name__=='__main__': main()
