"""Independent shallow/memory discovery beyond the old workflow-library list.

No recursive source-tree scan, training admission, database mutation or agent
execution. Do not inspect the active 20261026_ablation_v2 tree. Original v7
lineage and physical-census files remain unchanged.
"""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_raw_census_v7'
TOPS=[ROOT/'output',Path('E:/skillloop_runs')]
ACTIVE=ROOT/'output/20261026_ablation_v2'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def norm(x):return re.sub(r'/+','/',str(x).replace('\\','/')).rstrip('/').lower()
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def walk(v,p=''):
    if isinstance(v,dict):
        for k,c in v.items():
            if any(s in str(k).lower() for s in ('credential','password','secret','api_key','access_token')):continue
            yield p+'/'+str(k),c
            if isinstance(c,(dict,list)):yield from walk(c,p+'/'+str(k))
    elif isinstance(v,list):
        for i,c in enumerate(v):
            yield p+'/'+str(i),c
            if isinstance(c,(dict,list)):yield from walk(c,p+'/'+str(i))

def purpose(p):
    n=p.name.lower()
    if re.match(r'20261021_v(?:1[1-9]|2\d|3[0-5])_',n):return 'same_algorithm_v11_to_v35_iteration_execution_or_artifact_root'
    if re.match(r'20261020_wrd_v[4-7]_',n):return 'early_WRD_real_generation_or_regeneration_branch'
    if n.startswith(('outer152_','wrd153_','v7_controls_','validation_noskill_coordinator_')) or 'controls' in n:
        return 'implementation_or_scheduler_control_fixture_not_automatically_a_paid_Agent_run'
    if 'wrd' in n or 'workflow' in n or 'pipeline' in n or n.startswith('p7_'):
        return 'WRD_pipeline_generation_or_related_process_branch_requires_carrier_stat'
    if any(s in n for s in ('eval','two_arm','real250','t0012','t0112','t0145','t0194','testset','hard_test','modified','adopt')):
        return 'evaluation_or_single_case_branch_address_not_training_scope_verdict'
    if any(s in n for s in ('heartbeat','status','audit','repair','closeout','completion','concurrency','selection','skill','resume','followup','speed','rematch','host_paths')):
        return 'preparation_repair_resource_or_progress_metadata_branch'
    return 'shallow_discovered_root_purpose_not_yet_independently_classified'

def main():
    baseline_path=OUT/'PHYSICAL_ROOTS.json';baseline_bytes=baseline_path.read_bytes();baseline=json.loads(baseline_bytes)
    prior=baseline['roots'];all_roots=[p for top in TOPS for p in top.iterdir() if p.is_dir()]
    memories=[p for p in (ROOT/'research/memory').glob('*.md') if re.search(r'2026-10-2[0-4]',p.name)]
    texts=[]
    for p in memories:
        text=p.read_text(encoding='utf-8-sig');title=next((x.lstrip('# ').strip() for x in text.splitlines() if x.startswith('#')),'')
        texts.append((p,title,text.splitlines()))
    evidence=defaultdict(list)
    memory_refs=Counter()
    for p,title,lines in texts:
        for i,line in enumerate(lines,1):
            ln=norm(line)
            for root in all_roots:
                if norm(root)==norm(ACTIVE):continue
                direct=norm(root) in ln
                relative=root.parent==ROOT/'output' and ('output/'+root.name.lower()) in ln
                basename=bool(re.search(r'(?<![\w-])'+re.escape(root.name)+r'(?![\w-])',line,re.I))
                if direct or relative or basename:
                    kind='exact_absolute_path' if direct else 'exact_repo_output_path' if relative else 'literal_directory_basename_reference'
                    evidence[norm(root)].append({'source':str(p.relative_to(ROOT)),'line':i,'title':title,'kind':kind})
                    memory_refs[str(p.relative_to(ROOT))]+=1
    # Original retained-29 catalog/history and its explicit path references are
    # an independent source of entry points, not a seed of accepted SFT rows.
    structured_sources=[ROOT/'output/20261025_wrd_training_dataset/bundle/tools/resources/history_inventory.json',
        ROOT/'output/20261025_wrd_training_dataset/bundle/catalog/state_meta.json',
        ROOT/'output/20261025_wrd_training_dataset/bundle/catalog/routes.jsonl']
    for p in structured_sources:
        values=list(rows(p)) if p.suffix=='.jsonl' else [json.loads(p.read_text(encoding='utf-8-sig'))]
        for ordinal,value in enumerate(values):
            for pointer,v in walk(value):
                if not isinstance(v,str) or '\n' in v:continue
                vn=norm(v)
                for root in all_roots:
                    rn=norm(root)
                    if vn==rn or vn.startswith(rn+'/'):
                        evidence[rn].append({'source':str(p.relative_to(ROOT)),'record_ordinal_0based':ordinal,
                            'json_pointer':pointer,'kind':'original_29_history_or_resource_exact_path_reference'})
    for name in ('job_physical_path_references.jsonl.gz','provider_runtime_path_references.jsonl.gz'):
        p=OUT/'indexes'/name
        for row in rows(p):
            vn=norm(row['path'])
            for root in all_roots:
                rn=norm(root)
                if vn==rn or vn.startswith(rn+'/'):
                    evidence[rn].append({'source':str(p.relative_to(ROOT)),'episode_id':row.get('episode_id'),
                        'job_id':row.get('job_id'),'json_pointer':row.get('json_pointer'),
                        'kind':'original_production_dispatch_or_result_path_reference'})
    # Dynamic fixture roots need their creating code, rather than a name-based
    # claim that they contain production model runs.
    prefixes=('v7_controls_','outer152_','wrd153_','validation_noskill_coordinator_','p7_')
    code_refs=defaultdict(list)
    for parent in (ROOT/'research/archive',ROOT/'research/pipelines'):
        for p in parent.rglob('*.py'):
            try:lines=p.read_text(encoding='utf-8-sig').splitlines()
            except (UnicodeError,OSError):continue
            for i,line in enumerate(lines,1):
                for prefix in prefixes:
                    if prefix in line:code_refs[prefix].append({'source':str(p.relative_to(ROOT)),'line':i,
                        'kind':'creating_controller_prefix_reference','prefix':prefix})
    entries=[];stat_candidates=[]
    for root in sorted(all_roots,key=norm):
        rn=norm(root);existing=[r for r in prior if rn==norm(r['path'])]
        covered=[r for r in prior if r.get('recursive_scan') is True and rn.startswith(norm(r['path'])+'/')]
        refs=evidence[rn]
        for prefix in prefixes:
            if root.name.startswith(prefix):refs=refs+code_refs[prefix]
        is_period=bool(re.match(r'202610(?:19|20|21|22|23|24)_',root.name))
        execution_parent=root.parent==Path('E:/skillloop_runs')
        fixture=any(root.name.startswith(prefix) for prefix in prefixes)
        relevant=rn!=norm(ACTIVE) and (bool(refs) or is_period or execution_parent or fixture or root.name=='workflow_library')
        old_recursive=bool(covered) or any(r.get('recursive_scan') is True and r.get('scan_status') not in {'missing','error'} for r in existing)
        item={'path':str(root),'exists_from_independent_shallow_directory_inventory':True,
            'purpose_classification':purpose(root),'memory_original_reference_count':len(refs),
            'reference_evidence':refs,'original_production_path_reference_count':sum(r['kind']=='original_production_dispatch_or_result_path_reference' for r in refs),
            'old_PHYSICAL50_exact_root_entry':bool(existing),'old_PHYSICAL50_recursive_scan_covered':old_recursive,
            'old_PHYSICAL50_entry_scan_status':[r.get('scan_status') for r in existing],
            'relevant_to_independent_WRD_address_discovery':relevant,
            'actual_retained29_producer_not_proven_only_by_name_or_presence':True,
            'no_recursive_stat_or_business_execution_by_this_review':True}
        entries.append(item)
        if relevant and not old_recursive:
            stat_candidates.append({'path':str(root),'purpose':item['purpose_classification'],
                'memory_or_original_reference_count':len(refs),
                'original_production_path_reference_count':item['original_production_path_reference_count'],
                'priority':'iteration_or_execution_carrier' if execution_parent or re.match(r'20261021_v\d+_',root.name) or 'generation' in root.name
                    else 'bounded_metadata_or_branch_carrier',
                'old_root_was_listed_without_recursive_stat':bool(existing)})
    dump_path=OUT/'indexes/additional_shallow_root_coverage_matrix.jsonl.gz'
    with gzip.open(dump_path,'wt',encoding='utf-8',newline='\n',compresslevel=3) as f:
        for entry in entries:f.write(js(entry)+'\n')
    report={'schema_version':'wrd-v7-independent-additional-root-discovery','generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'method':'date-bounded original memory + original29 history/resource/dispatch references + exhaustive shallow D-output and E-run directory inventory',
        'memory_files_reviewed':len(memories),'memory_files_with_root_references':len(memory_refs),
        'memory_sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha_bytes(p.read_bytes()),'reference_matches':memory_refs[str(p.relative_to(ROOT))]} for p in memories],
        'shallow_parents':[str(p) for p in TOPS],'D_output_typo_correction':{'D:/output_exists':Path('D:/output').is_dir(),'actual_project_output':str(ROOT/'output')},
        'shallow_directory_roots_reviewed':len(entries),'old_PHYSICAL50_baseline_sha256':sha_bytes(baseline_bytes),
        'old_PHYSICAL50_root_entries':len(prior),'new_or_reference_only_roots_requiring_sibling_stat':len(stat_candidates),
        'stat_candidates':stat_candidates,'candidate_purpose_counts':dict(Counter(x['purpose'] for x in stat_candidates)),
        'D_v11_to_v35_roots':[e['path'] for e in entries if e['path'].startswith(str(ROOT/'output')) and re.match(r'20261021_v(?:1[1-9]|2\d|3[0-5])_',Path(e['path']).name)],
        'E_v11_to_v34_execution_roots':[e['path'] for e in entries if e['path'].startswith('E:') and re.match(r'20261021_v(?:1[1-9]|2\d|3[0-4])_',Path(e['path']).name)],
        'all_shallow_root_evidence_index':str(dump_path),'structured_original_sources':[str(p) for p in structured_sources],
        'dynamic_root_prefix_controller_evidence':dict(code_refs),
        'active_ablation_tree_not_opened_or_scanned':str(ACTIVE),
        'do_not_add_overlapping_child_roots_to_parent_byte_totals':True,
        'D_E_copies_and_iteration_versions_not_new_independent_tasks':True,
        'training_source_admission_or_91_106_filters_used':False,'training_started':False,'new_model_or_business_calls':0,
        'original_graph_and_existing_physical_reports_modified':False,
        'limitations':['This discovers addresses and purposes; sibling source_audit owns physical stat totals.',
            'Original production references, algorithmic case branches and no-model controls are separated; an address is not automatically a retained29 producer.',
            'Memory literal basename references alone do not distinguish D artifacts from E execution copies; the report marks them weaker than exact paths.',
            'The old PHYSICAL50 baseline is pinned at read time; newly completed sibling supplements can already cover some listed candidates.'],
        'script_sha256':sha_bytes(Path(__file__).read_bytes())}
    save(OUT/'ADDITIONAL_DISCOVERY_REVIEW.json',report)
    print(js({'memories':len(memories),'top_roots':len(entries),'stat_candidates':len(stat_candidates),
        'D_v11_v35':len(report['D_v11_to_v35_roots']),'E_v11_v34':len(report['E_v11_to_v34_execution_roots'])}),flush=True)

if __name__=='__main__':main()
