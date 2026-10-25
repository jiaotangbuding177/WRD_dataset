"""Offline linkage and structured-label census. No native/model execution."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip,hashlib,json,re,time
from pathlib import Path

def jd(o):return json.dumps(o,ensure_ascii=False,separators=(',',':'))
def rows(p):
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for l in f:
            if l.strip():yield json.loads(l)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
    return h.hexdigest()
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cas(b,r):
    p=b/r['object'];p=p if p.exists() else b/'archive'/r['object']
    if not p.exists():return None
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('CAS mismatch')
    try:return json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError,ValueError):return None
def nested_dicts(o,path=''):
    if isinstance(o,dict):
        yield path,o
        for k,v in o.items():
            if isinstance(v,(dict,list)):yield from nested_dicts(v,path+'/'+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o):yield from nested_dicts(v,path+'/'+str(i))
def normpath(x):return str(x or '').replace('\\','/').rstrip('/').casefold()

def main():
    pa=argparse.ArgumentParser();pa.add_argument('--bundle',type=Path,required=True);pa.add_argument('--output',type=Path,required=True);a=pa.parse_args();start=time.monotonic();b=a.bundle;o=a.output;o.mkdir(parents=True,exist_ok=True);c=o/'controlled_linkage';c.mkdir(exist_ok=True)
    watched=[b/'catalog/jobs.jsonl',b/'catalog/episodes.jsonl',b/'archive/file_index.jsonl',o/'controlled_master/resource_and_stage_artifact_texts.jsonl.gz']
    before={str(p):sha(p) for p in watched};jobs=list(rows(watched[0]));eps=list(rows(watched[1]));ji={j['id']:j for j in jobs};ei={e['episode_id']:e for e in eps}
    job_eps=defaultdict(set);path_eps=defaultdict(set)
    for e in eps:
        for jid in set([e.get('job_id')]+[j if isinstance(j,str) else j.get('id') for j in e.get('job_refs',[])]):
            if jid:job_eps[jid].add(e['episode_id'])
        path_eps[normpath(e.get('source_path'))].add(e['episode_id'])
    edges=[];edge_seen=set();unresolved=Counter();job_census=Counter();routes=defaultdict(lambda:defaultdict(list));field_counts=defaultdict(Counter)
    def edge(fr,to,typ,proof,**kw):
        key=(fr,to,typ,proof)
        if fr==to or key in edge_seen:return
        edge_seen.add(key);edges.append({'from':fr,'to':to,'relation':typ,'proof':proof,'association_not_causality':True,**kw})
    for j in jobs:
        jid=j['id'];k=j['kind'];p=j.get('payload') or {};rid=j.get('route_id');job_census[k]+=1;field_counts[k].update(p.keys())
        if rid:routes[rid][k].append(jid)
        for old in (p.get('previous') or {}).get('making_jobs',[]) if isinstance(p.get('previous'),dict) else []:
            if isinstance(old,dict) and old.get('id'):edge('job:'+old['id'],'job:'+jid,'make_revision_history','payload.previous.making_jobs.id',parent_job_found=old['id'] in ji)
        result=j.get('result') or {}
        if result.get('reused_from_job'):edge('job:'+result['reused_from_job'],'job:'+jid,'reuses_prior_result','result.reused_from_job',parent_job_found=result['reused_from_job'] in ji)
        previous_failed=p.get('previous_failed_episode')
        if previous_failed:
            matches=path_eps.get(normpath(previous_failed),set())
            for ep in matches:edge('episode:'+ep,'job:'+jid,'retry_after_failed_episode','payload.previous_failed_episode')
            if not matches:unresolved['previous_failed_episode_path_not_in_catalog']+=1
    output_sha_eps=defaultdict(set)
    for ar in rows(o/'controlled_master/episode_output_artifacts.index.jsonl.gz'):
        output_sha_eps[ar['stored_sha256']].add(ar['episode_id'])
    normalized_reports=defaultdict(set)
    for ar in rows(o/'controlled_master/resource_and_stage_artifact_texts.jsonl.gz'):
        if ar['kind'] not in {'review','make'} or not ar['logical_path'].endswith('.json'):continue
        try:obj=json.loads(ar['content'])
        except ValueError:continue
        if not isinstance(obj,dict):continue
        if not ((ar['kind']=='review' and obj.get('decision') in {'retain','revise','reject','defer'}) or (ar['kind']=='make' and 'skill_files' in obj and 'program_runs' in obj)):continue
        nh=hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        normalized_reports[nh].update(output_sha_eps.get(ar['stored_sha256'],{ar['episode_id']}))
    input_names={'review_input.json','previous.json','previous_feedback.json','prior_making.json','making_lineage.json','route.json','task_route.json','task_sources.json','reusable.json','read_usage_evidence.json','sources.json'}
    input_aliases=Counter();input_unique=defaultdict(set);input_keys=defaultdict(Counter);input_records=[];known_input_shas=set();review_link_counts=Counter();sourcelinks=[];bodycache={}
    # Retain typed input artifacts and only exact native identifiers/path references as graph edges.
    with gzip.open(c/'input_artifacts.jsonl.gz','wt',encoding='utf-8',newline='\n') as out:
        for r in rows(b/'archive/file_index.jsonl'):
            logical=r['logical_path'].replace('\\','/');parts=logical.split('/')
            if len(parts)<4 or parts[0]!='episodes' or parts[1] not in ei or '/workspace/' not in logical:continue
            name=parts[-1]
            if name not in input_names or '/outputs/' in logical:continue
            input_aliases[name]+=1;input_unique[name].add(r['sha256']);eid=parts[1]
            x=bodycache.get(r['sha256'])
            if x is None:x=cas(b,r);bodycache[r['sha256']]=x
            if x is None:continue
            if isinstance(x,dict):input_keys[name].update(x.keys())
            meta={'episode_id':eid,'kind':ei[eid]['kind'],'artifact_name':name,'logical_path':logical,'sha256':r['sha256'],'object':r['object'],'content':x,'training_admitted':False,'publication_approved':False}
            out.write(jd(meta)+'\n');input_records.append({k:v for k,v in meta.items() if k!='content'})
            if name in {'previous_feedback.json','prior_making.json'}:
                for src in output_sha_eps.get(r['sha256'],[]):edge('episode:'+src,'episode:'+eid,'exact_output_bytes_reused_as_stage_input',name,sha256=r['sha256'])
            # Parsed recursive references rely on complete exact strings, never natural-language similarity.
            matched=Counter()
            for path,d in nested_dicts(x):
                if name in {'previous_feedback.json','prior_making.json'}:
                    nh=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                    for src in normalized_reports.get(nh,[]):edge('episode:'+src,'episode:'+eid,'exact_structured_report_reused_as_stage_input',name+path,json_canonical_sha256=nh)
                for kk,v in d.items():
                    if not isinstance(v,str):continue
                    if v in ji:
                        for src in job_eps.get(v,[]):edge('episode:'+src,'episode:'+eid,'explicit_input_job_reference',name+path+'/'+kk);matched['job_ref']+=1
                    if normpath(v) in path_eps:
                        for src in path_eps[normpath(v)]:edge('episode:'+src,'episode:'+eid,'explicit_input_episode_reference',name+path+'/'+kk);matched['episode_path_ref']+=1
            if name=='review_input.json':review_link_counts.update(matched)
    # Structured labels recovered from existing observed outputs; no model-generated labels here.
    label_counts=Counter();label_fields=Counter();class_counts=defaultdict(Counter);unique_documents=Counter();labelseen=set();outputlabels=[];report_shapes=Counter();caseids=Counter();sourceids=set();artifact_alias_for_sha=defaultdict(set)
    for r in rows(o/'controlled_master/episode_output_artifacts.index.jsonl.gz'):artifact_alias_for_sha[r['stored_sha256']].add(r['episode_id'])
    with gzip.open(c/'structured_decisions.jsonl.gz','wt',encoding='utf-8',newline='\n') as out:
        for r in rows(o/'controlled_master/resource_and_stage_artifact_texts.jsonl.gz'):
            if not r['logical_path'].endswith('.json'):continue
            try:x=json.loads(r['content'])
            except ValueError:continue
            if not isinstance(x,dict):continue
            k=r['kind'];h=r['stored_sha256'];unit=None;items=[]
            if k=='screen' and isinstance(x.get('decisions'),list):unit='screen_decisions';items=[('/decisions/'+str(i),v) for i,v in enumerate(x['decisions']) if isinstance(v,dict)]
            elif k=='prepare' and isinstance(x.get('cases'),list):
                report_shapes['prepare_case_documents']+=1;report_shapes['prepare_selected_cases']+=len(x['cases'])
                for v in x['cases']:
                    if isinstance(v,dict):
                        if v.get('id'):caseids[str(v['id'])]+=1
                        if v.get('source_id'):sourceids.add(str(v['source_id']))
                if isinstance(x.get('case_decisions'),list):unit='prepare_case_decisions';items=[('/case_decisions/'+str(i),v) for i,v in enumerate(x['case_decisions']) if isinstance(v,dict)]
                else:unit='prepare_selection_document';items=[('',x)]
            elif k=='review' and x.get('decision') in {'retain','revise','reject','defer'}:unit='review_decision';items=[('',x)]
            elif k=='make' and isinstance(x.get('skill_files'),list) and 'program_runs' in x:unit='making_report';items=[('',x)]
            if not unit:continue
            unique_documents[unit]+=1
            for path,v in items:
                uid=hashlib.sha256((h+':'+path).encode()).hexdigest()[:24]
                if uid in labelseen:continue
                labelseen.add(uid);label_counts[unit]+=1;label_fields.update(unit+':'+str(key) for key in v)
                for field in ('decision','action','case_id','source_id'):
                    vv=v.get(field)
                    if field in {'decision','action'} and isinstance(vv,(str,bool,int,float)):class_counts[unit+':'+field][str(vv)]+=1
                rr={'id':uid,'unit':unit,'episode_ids':sorted(artifact_alias_for_sha[h]),'original_episode_id':r['episode_id'],'artifact_sha256':h,'logical_path':r['logical_path'],'json_pointer':path,'label':v,'evidence_type':'observed_structured_artifact','human_gold':False,'training_admitted':False,'publication_approved':False,'future_artifact_added_to_past_prompt':False}
                out.write(jd(rr)+'\n');outputlabels.append({key:val for key,val in rr.items() if key!='label'})
    # Explicit stage-field views retain full parent JSON plus separately addressable child evidence.
    extracted_counts=Counter();parent_counts=Counter();stage_extract_seen=set()
    with gzip.open(c/'stage_decisions.extracted.jsonl.gz','wt',encoding='utf-8',newline='\n') as out:
        for r in rows(o/'controlled_master/resource_and_stage_artifact_texts.jsonl.gz'):
            if not r['logical_path'].endswith('.json'):continue
            try:x=json.loads(r['content'])
            except ValueError:continue
            if not isinstance(x,dict):continue
            kind=r['kind'];h=r['stored_sha256'];fields=[];unit=None
            if kind=='prepare' and isinstance(x.get('cases'),list):unit='prepare';fields=['cases','case_decisions','blocked_inputs','reason']
            elif kind=='review' and x.get('decision') in {'retain','revise','reject','defer'}:unit='review';fields=['decision','reason','replaced_work','resource_reliable','delivery_passed','resource_used','evidence_refs','case_findings','repair_notes']
            elif kind=='make' and isinstance(x.get('skill_files'),list) and 'program_runs' in x:unit='make';fields=['skill_files','replaced_work','program_runs','known_issues','decision','reason','resource_reliable','delivery_passed','repair_notes']
            elif kind=='screen' and isinstance(x.get('decisions'),list):unit='screen';fields=['decisions','routes','cards']
            if unit is None:continue
            parent_key=(h,unit)
            if parent_key in stage_extract_seen:continue
            stage_extract_seen.add(parent_key);parent_counts[unit]+=1
            def emit(pointer,value,field,is_parent=False):
                ident=hashlib.sha256((h+':'+pointer).encode()).hexdigest()[:24]
                record={'id':ident,'episode_id':r['episode_id'],'episode_ids':sorted(artifact_alias_for_sha[h]),'kind':kind,'parent_artifact_sha256':h,'logical_path':r['logical_path'],'json_pointer':pointer,'field':field,'value':value,'evidence_type':'original_field_observed_not_gold','is_parent_document':is_parent,'parent_child_views_not_additive_independent_tasks':True,'artifact_available_no_earlier_than_its_observed_write_or_stage_end':True,'actual_write_message_link_not_yet_verified':True,'future_artifact_added_to_early_prompt':False,'human_gold':False,'quality_approved':False,'training_admitted':False,'publication_approved':False}
                out.write(jd(record)+'\n');extracted_counts[unit+':'+field]+=1
            emit('',x,'parent_document',True)
            for field in fields:
                if field not in x:continue
                value=x[field]
                if isinstance(value,list):
                    for idx,item in enumerate(value):emit('/'+field+'/'+str(idx),item,field)
                else:emit('/'+field,value,field)
    # Noncanonical episodes: salvage evidence, never invent missing native intermediate turns.
    missing=json.loads((o/'controlled_master/missing_canonical_evidence.json').read_text(encoding='utf-8'));missing_counts=Counter();missing_states=Counter();recovered=[]
    with gzip.open(c/'noncanonical_evidence.jsonl.gz','wt',encoding='utf-8',newline='\n') as out:
        for e in missing['episodes']:
            refs=e['request_response_result_references'];pieces={rel:cas(b,r) for rel,r in refs.items()};pieces={k:v for k,v in pieces.items() if v is not None}
            for rel in pieces:missing_counts[rel]+=1
            result=pieces.get('result.json') or {};resp=result.get('response');answer=resp.get('answer') if isinstance(resp,dict) else None
            if isinstance(answer,str) and answer.strip():missing_counts['nonempty_result_response_answer']+=1
            missing_states[str(result.get('status','no_result'))]+=1
            row={**e,'recovered_objects':pieces,'intermediate_native_messages_recovered':False,'training_admitted':False,'publication_approved':False}
            out.write(jd(row)+'\n');recovered.append({'episode_id':e['episode_id'],'kind':e['kind'],'refs':sorted(pieces),'nonempty_answer':bool(isinstance(answer,str) and answer.strip())})
    # Route overlap is a grouping suggestion, not a chronological chain assertion.
    route_counts=Counter();route_index=[]
    for rid,st in routes.items():
        keys=set(st);route_counts['routes']+=1
        if {'make','prepare','actor','review'}<=keys:route_counts['routes_with_make_prepare_actor_review']+=1
        if {'prepare','actor','review'}<=keys:route_counts['routes_with_prepare_actor_review']+=1
        route_index.append({'route_id':rid,'jobs_by_stage':dict(st),'link_strength':'same_route_group_only_not_temporal_chain'})
    # Two transparent component views. Catalog-declared source links are conservatively retained;
    # common runtimes/indexes/templates/same-route membership do not add artificial edges.
    class UF:
        def __init__(self):self.p={}
        def root(self,x):
            self.p.setdefault(x,x)
            if self.p[x]!=x:self.p[x]=self.root(self.p[x])
            return self.p[x]
        def union(self,x,y):self.p[self.root(x)]=self.root(y)
    explicit=UF();declared=UF()
    for e in eps:
        en='episode:'+e['episode_id'];explicit.root(en);declared.root(en)
        for jid in set([e.get('job_id')]+[j if isinstance(j,str) else j.get('id') for j in e.get('job_refs',[])]):
            if jid:
                explicit.union(en,'job:'+jid);declared.union(en,'job:'+jid)
        for sid in e.get('source_ids',[]):declared.union(en,'source:'+str(sid))
    for ed in edges:
        explicit.union(ed['from'],ed['to']);declared.union(ed['from'],ed['to'])
    canonical_set=set()
    for ep in rows(o/'controlled_master/episode_inventory.jsonl.gz'):canonical_set.add(ep['episode_id'])
    def component_census(uf):
        allc=Counter(uf.root('episode:'+e['episode_id']) for e in eps)
        nativec=Counter(uf.root('episode:'+eid) for eid in canonical_set)
        maker=Counter(uf.root('episode:'+eid) for eid in canonical_set if ei[eid]['kind'] in {'make','screen','prepare','review'})
        return {'catalog_episode_components':len(allc),'canonical_episode_components':len(nativec),'skillmaker_canonical_components':len(maker),'largest_catalog_component_episodes':max(allc.values(),default=0),'largest_canonical_component_episodes':max(nativec.values(),default=0),'largest_skillmaker_component_episodes':max(maker.values(),default=0),'canonical_component_size_histogram':dict(Counter(nativec.values()))}
    components={'explicit_reference_and_exact_bytes_or_structured_report_reuse':component_census(explicit),'plus_all_catalog_declared_source_dependencies_conservative':component_census(declared),'weak_edges_not_used':['same route membership','common native runtime/tools','common public templates without task-specific information flow','shared library/source index alone'],'confirmed_independent_generalization_groups':None,'interpretation':'Disconnected components here do not prove independence; unknown dataflow remains. Catalog dependencies are not removed to make a convenient train/test split.'}
    # Actual linked review -> revision maker episodes, not merely similar prose or same route.
    rm={(ed['from'].split(':',1)[1],ed['to'].split(':',1)[1]) for ed in edges if ed['from'].startswith('episode:') and ed['to'].startswith('episode:') and ei.get(ed['from'].split(':',1)[1],{}).get('kind')=='review' and ei.get(ed['to'].split(':',1)[1],{}).get('kind')=='make'}
    predecessors=defaultdict(set)
    for ed in edges:
        if ed['from'].startswith('episode:') and ed['to'].startswith('episode:'):
            src=ed['from'].split(':',1)[1];dst=ed['to'].split(':',1)[1]
            if ei.get(src,{}).get('kind')=='make' and ei.get(dst,{}).get('kind')=='review':predecessors[dst].add(src)
    with gzip.open(c/'revision_pairs.extracted.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for rev,maker in sorted(rm):
            proof=[ed for ed in edges if ed['from']=='episode:'+rev and ed['to']=='episode:'+maker]
            f.write(jd({'review_episode_id':rev,'revision_make_episode_id':maker,'predecessor_make_episode_ids':sorted(predecessors[rev]),'exact_reference_proofs':proof,'meaning':'prior review report/provenance explicitly supplied to subsequent make; native read and successful correction not yet verified','observed_not_gold':True,'quality_approved':False,'training_admitted':False,'publication_approved':False,'future_outcome_inserted_into_early_prompt':False})+'\n')
    with gzip.open(c/'explicit_edges.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for x in edges:f.write(jd(x)+'\n')
    with gzip.open(c/'route_groups.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for x in route_index:f.write(jd(x)+'\n')
    after={str(p):sha(p) for p in watched};assert before==after
    manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in c.glob('*.gz')}
    report={'schema_version':'wrd-fullchain-link-audit-v1','status':'offline_evidence_recovery_not_training_admission','catalog_jobs':len(jobs),'catalog_episodes':len(eps),'jobs_by_stage':dict(job_census),'payload_field_counts_by_stage':{k:dict(v) for k,v in field_counts.items()},'explicit_edge_counts':dict(Counter(e['relation'] for e in edges)),'explicit_edges_total':len(edges),'unresolved_links':dict(unresolved),'route_group_counts':dict(route_counts),'route_groups_not_independent_full_pipeline_demonstrations':True,'input_artifact_alias_counts':dict(input_aliases),'input_artifact_unique_sha_counts':{k:len(v) for k,v in input_unique.items()},'input_artifact_key_counts':{k:dict(v) for k,v in input_keys.items()},'review_input_reference_matches':dict(review_link_counts),'recovered_structured_label_units':dict(label_counts),'structured_document_counts':dict(unique_documents),'stage_extracted_parent_document_counts':dict(parent_counts),'stage_extracted_field_record_counts':dict(extracted_counts),'structured_decision_class_counts':{k:dict(v) for k,v in class_counts.items()},'prepare_selected_case_statistics':dict(report_shapes),'prepare_distinct_case_ids':len(caseids),'prepare_distinct_source_ids':len(sourceids),'label_field_counts':dict(label_fields),'missing_canonical_episode_count':len(missing['episodes']),'noncanonical_evidence_counts':dict(missing_counts),'noncanonical_result_statuses':dict(missing_states),'noncanonical_intermediate_native_messages_recovered':0,'source_hashes':before,'source_files_unchanged':True,'script_sha256':sha(Path(__file__)),'controlled_output_manifest':manifest,'human_gold':0,'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-start,3),'limitations':['structured artifacts may be historical/superseded versions; counts are unique bytes plus JSON pointer, not independent tasks','exact identifier references establish provenance links, not proof that all referenced content was actually read by model','same-route membership does not order sessions or establish revision causality','no actual unseen evaluation output newly ingested; marker and semantic leakage review remains required','all raw evidence stays controlled; no public approval inferred','no fabricated internal CoT; observed rationale fields remain teacher evidence rather than verified private thoughts']}
    report['component_audit']=components;report['explicit_review_to_make_episode_pairs']=len(rm);report['explicit_review_to_make_distinct_review_episodes']=len({r for r,m in rm});report['explicit_review_to_make_distinct_make_episodes']=len({m for r,m in rm});report['revision_pairs_with_explicit_predecessor_make_reference']=sum(bool(predecessors[r]) for r,m in rm)
    write(o/'LINK_AUDIT.json',report);print(jd({k:report[k] for k in ['status','explicit_edges_total','recovered_structured_label_units','structured_decision_class_counts','prepare_distinct_case_ids','prepare_distinct_source_ids','noncanonical_evidence_counts','explicit_review_to_make_episode_pairs','component_audit','elapsed_seconds']}))
if __name__=='__main__':main()
