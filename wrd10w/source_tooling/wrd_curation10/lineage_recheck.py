"""P0 isolation and event/version audit; never admits or executes business data.

Read protected original-user content only to detect isolation overlap. Protected
package bytes are fingerprinted for resource ancestry, never used as labels/Q.
No protected answer, thought, grade or reviewer body is inspected for credit.
"""
from pathlib import Path
import ast,collections,gzip,hashlib,importlib.util,json,re,sys

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation10/lineage'
MAIN=ROOT/'output/20261027_wrd_main_v10'
BASE='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'

def h(x): return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig')as f:return[json.loads(l)for l in f if l.strip()]
def pin(p):
    p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(name,x):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def gzsave(name,rr):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
            for r in rr:f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    return pin(p)
def norm(x):return re.sub(r'\s+','',x)
def strings(x):
    if isinstance(x,str):
        yield x
        if x[:1]in '{[':
            try:yield from strings(json.loads(x))
            except(ValueError,TypeError):pass
    elif isinstance(x,list):
        for y in x:yield from strings(y)
    elif isinstance(x,dict):
        for y in x.values():yield from strings(y)
def blocks(m):
    c=m.get('content',[]);return[{'type':'text','text':c}]if isinstance(c,str)else c
def text(m):return'\n'.join(c.get('text','')for c in blocks(m)if isinstance(c,dict)and c.get('type')=='text')
def calls(m):return[c for c in blocks(m)if isinstance(c,dict)and c.get('type')=='toolCall']
def args(c):
    a=c.get('arguments',{})
    try:return json.loads(a)if isinstance(a,str)else a
    except ValueError:return{'UNPARSED_SHA':h(a)}

def original_user_basis():
    """Same declared411-source DSU, stopped before any historical main scan."""
    p=ROOT/'research/data_prep/wrd_curation09/holdout_protected_vs_train.py'
    nodes=[]
    for n in ast.parse(p.read_text(encoding='utf-8-sig')).body:
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='manifest'for t in n.targets):break
        nodes.append(n)
    env={'__file__':str(p)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),env)
    assert len(env['forbidden'])==411 and env['users']==1927 and env['np']==7651
    return env

def get_eval_basis():
    p=ROOT/'research/data_prep/wrd_curation09/holdout_protection_followup.py'
    s=importlib.util.spec_from_file_location('p0_followup_patterns',p);m=importlib.util.module_from_spec(s)
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:s.loader.exec_module(m)
    finally:sys.dont_write_bytecode=previous
    return m.eval_patterns()

def scan_messages(messages,patterns):
    out=[]
    for mi,msg in enumerate(messages):
        s=norm('\n'.join(strings(msg)));found={}
        for i in range(max(0,len(s)-159)):
            for expected,offset,origin in patterns.get(s[i:i+40],[]):
                if s[i:i+160]!=expected:continue
                key=h(json.dumps(origin,sort_keys=True,separators=(',',':')))
                q=found.setdefault(key,{'origin':origin,'anchors':0,'anchor_SHA_set':set(),'first_offset':i})
                q['anchors']+=1;q['anchor_SHA_set'].add(h(expected))
        for q in found.values():
            q['anchor_SHA_set']=sorted(q['anchor_SHA_set']);out.append({'message_index':mi,'message_role':msg.get('role'),**q})
    return out

def parse_native(ref):
    p=Path(ref['path']);assert pin(p)['sha256']==ref['sha256']
    msgs=[];lines=[];sid=None;errors=[]
    for ln,s in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
        try:v=json.loads(s)
        except ValueError:errors.append(ln);continue
        if v.get('type')=='session':sid=v.get('id')
        if v.get('type')=='message'and isinstance(v.get('message'),dict):msgs.append(v['message']);lines.append(ln)
    return {'messages':msgs,'source_event_lines':lines,'native_session_id':sid,'parse_error_lines':errors,'source_native':ref}

def resource_events(context,target_index):
    messages=context['messages'];ls=context['source_event_lines'];out=[]
    for i,m in enumerate(messages[:target_index+1]):
        for c in calls(m):
            a=args(c);command=a.get('command','');dest=a.get('path',a.get('file_path'))
            rr=[(j,q)for j,q in enumerate(messages[i+1:],i+1)if q.get('role')=='toolResult'and q.get('toolCallId')==c.get('id')]
            observations=[]
            for j,q in rr:
                t=text(q);observations.append({'message_index':j,'event_line':ls[j],
                  'is_before_or_at_target':j<=target_index,'isError':q.get('isError'),
                  'text_characters':len(t),'text_sha256':h(t),'message_SHA_sorted':h(json.dumps(q,ensure_ascii=False,separators=(',',':'),sort_keys=True))})
            out.append({'call_message_index':i,'call_event_line':ls[i],'call_id':c.get('id'),'name':c.get('name'),
              'is_target_call':i==target_index,'path_argument':dest,
              'command_characters':len(command),'command_sha256':h(command),
              'resource_path_mentions':sorted(set(re.findall(r'/(?:workspace|opt|tmp)/[^\s"\x27<>;|)]*',command))),
              'file_read_shell_keywords':sorted(set(re.findall(r'\b(?:cat|head|tail|sed|read_text|read_bytes|open|cp|readFile|readFileSync)\b',command))),
              'write_content_characters':len(a['content'])if isinstance(a.get('content'),str)else None,
              'write_content_sha256':h(a['content'])if isinstance(a.get('content'),str)else None,
              'actual_tool_feedback':observations,
              'read_name_and_path_do_not_prove_full_or_successful_body_delivery':True,
              'exec_path_mention_not_assumed_read':True})
    return out

def protected_package_texts(packages,producers):
    """Resource isolation only; never inspect protected reviewer/Q bodies."""
    texts=[];verified=[]
    for pkg in packages:
        pmeta=producers.get(pkg['episode_id'],{})
        if pmeta.get('strict_protected_boundary')is None and pmeta.get('method_only_candidate_boundary')is None:continue
        for f in pkg['files']:
            p=Path(f['physical_frozen_CAS_path']);b=p.read_bytes();assert h(b)==f['sha256']
            verified.append({'producer_episode_id':pkg['episode_id'],'tree_content_sha256':pkg['tree_content_sha256'],
              'relative_path':f['relative_path'],'bytes':len(b),'sha256':f['sha256']})
            try:t=b.decode('utf-8-sig').replace('\r\n','\n').strip()
            except UnicodeError:continue
            if len(t)>=100:texts.append((pkg['episode_id'],pkg['tree_content_sha256'],f['relative_path'],f['sha256'],t))
    return texts,verified

def package_prefix_matches(context,index,package_texts):
    matches=[]
    for i,m in enumerate(context['messages'][:index+1]):
        if m.get('role')not in {'user','toolResult','system'}:continue
        t=text(m).replace('\r\n','\n')
        for eid,tree,name,fh,body in package_texts:
            if body in t:
                matches.append({'input_message_index':i,'input_event_line':context['source_event_lines'][i],
                  'message_role':m['role'],'text_sha256':h(text(m)),
                  'producer_episode_id':eid,'tree_content_sha256':tree,
                  'relative_path':name,'resource_sha256':fh,
                  'full_normalized_line_text_match':True,
                  'full_match_is_isolation_candidate_not_automatic_private_ancestry':True})
    return matches

def targeted_0f1603(context,packages,producers):
    target=16;prefix=context['messages'][:target+1]
    oldmeta=load(ROOT/'output/20261031_wrd_next51_planning/gap_review/SLIDE_CURRENT_VIEW_RESOURCE_LINEAGE_METADATA.json')
    producer=oldmeta['edge_metadata']['producer_episode_ids'][0]
    pkg=next(x for x in packages if x['episode_id']==producer)
    files=[];contents=[]
    for f in pkg['files']:
        p=Path(f['physical_frozen_CAS_path']);b=p.read_bytes();assert h(b)==f['sha256']
        t=b.decode('utf-8-sig');contents.append((f['relative_path'],f['sha256'],t))
        files.append({'relative_path':f['relative_path'],'sha256':f['sha256'],'actual_CAS':pin(p)})
    request_path=Path('E:/skillloop_runs/workflow_library/episodes/77cd6b99f0693bf4/attempt_1/openclaw_transport/request.json')
    transport=request_path.parent;episode=transport.parent
    round1=[];captured_input=[]
    for name in ['request.json','evidence/prompts.json','evidence/metadata.json','evidence/manifest.json','evidence/events.jsonl','evidence/system-prompt.txt','skill_reads.json']:
        p=transport/name
        item={'path':str(p),'exists':p.is_file()}
        if p.is_file():
            item['pin']=pin(p)
            if name=='evidence/events.jsonl':
                ev=[json.loads(l)for l in p.read_text(encoding='utf-8-sig').splitlines()if l.strip()]
                item['event_types']=dict(collections.Counter(x.get('type')for x in ev))
                snapshots=[]
                for e in ev:
                    if e.get('type')not in {'context.compiled','prompt.submitted'}:continue
                    d=e['data'];snap={'seq':e['seq'],'type':e['type'],'timestamp':e.get('ts'),'data_keys':list(d)}
                    for k in ['systemPrompt','prompt','messages','tools']:
                        v=d.get(k);snap[k+'_type']=type(v).__name__
                        snap[k+'_length']=len(v)if isinstance(v,(str,list,dict))else None
                        if isinstance(v,str):snap[k+'_sha256']=h(v)
                    snapshots.append(snap)
                    captured_input.append({'type':e['type'],'seq':e['seq'],'fields':{k:d[k]for k in ['systemPrompt','prompt','messages']if k in d}})
                item['input_snapshots_metadata']=snapshots
                item['no_per_provider_step_request_event_found']=not any('request'in str(e.get('type')).lower()for e in ev)
            elif name=='skill_reads.json':
                d=load(p);item['successful_full_read_ids']=d.get('loaded_skill_ids',[]);item['read_count']=len(d.get('reads',[]))
            elif name=='request.json':
                d=load(p);declared=[]
                for skill in d.get('learned_skills',[]):
                    f=skill.get('files',{});declared.append({'id':skill.get('id'),'path':skill.get('path'),
                      'file_count':len(f),'file_identities':[{'relative_path':n,'text_sha256':h(t)if isinstance(t,str)else None,'matches_protected_package_file':any(n==fn and isinstance(t,str)and h(t)==fh for fn,fh,_ in contents)}for n,t in f.items()]if isinstance(f,dict)else[]})
                item['outer_declared_learned_skills']=declared
                item['outer_resource_declaration_is_not_model_delivery_evidence']=True
        round1.append(item)
    round2=[];p=ROOT/'output/20261030_wrd_gap08/corpus/audit_inputs/provider1536.pairs.original.jsonl.gz'
    pairs=rows(p);ids={m.get('responseId')for m in prefix if m.get('responseId')}
    matches=[x for x in pairs if x['provider_response_id']in ids]
    round2.append({'source_pin':pin(p),'groups_scanned':len(pairs),'recorded_native_response_ids':sorted(ids),
      'exact_recorded_response_id_match_count':len(matches),
      'matching_original_provider_response_ids':[x['provider_response_id']for x in matches],
      'no_output_similarity_or_clock_substitution_used':True})
    # Compare supplied input snapshots and prefix only for protected-file identity.
    delivered=[('native_prefix_'+str(i),text(m))for i,m in enumerate(prefix)if m.get('role')in {'user','toolResult','system'}]
    for snap in captured_input:
        delivered +=[(snap['type']+'_'+str(snap['seq']), '\n'.join(strings(snap['fields'])))]
    exact=[]
    for name,fh,t in contents:
        exact.append({'relative_path':name,'sha256':fh,
          'full_text_input_matches':[n for n,s in delivered if t and t in s],
          'full_normalized_lines_input_matches':[n for n,s in delivered if t and t.replace('\r\n','\n').strip()in s.replace('\r\n','\n')]})
    assert not matches
    assert not any(x['full_text_input_matches']or x['full_normalized_lines_input_matches']for x in exact)
    return {'view_id':'process09-0f1603b601613eac2fecb014','native_session_id':context['native_session_id'],
      'target_message_index':16,'target_event_line':context['source_event_lines'][16],
      'protected_producer_id':producer,'producer_boundary':{k:producers[producer].get(k)for k in ['strict_protected_boundary','method_only_candidate_boundary']},
      'known_package_tree_sha256':pkg['tree_content_sha256'],'protected_package_CAS_files':files,
      'round1_original_native_transport_and_export_root':round1,'round2_existing_provider_carrier_root':round2,
      'protected_whole_file_input_match_results':exact,
      'source_input_capture_new_observation':'Original runtime context.compiled snapshots recovered but not per-provider-step requests; metadata skills/prompting serialized strings, resumed tools snapshot string. Outer learned_skill resources were fully declared, successful native reads still0.',
      'decision':'HOLD_RESOURCE_ANCESTRY_UNRESOLVED_AFTER_TWO_BOUNDED_ROUNDS',
      'not_proven_contamination':True,'not_proven_clean':True,
      'new_active_whitelist_action':'TEMPORARILY_WITHDRAW_THIS_VIEW_ONLY_UNLESS_OTHER_ACTUAL_LINEAGE_EVIDENCE',
      'no_protected_grade_thought_or_review_body_used':True}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert h((MAIN/'TRAINING_MANIFEST.json').read_bytes())==BASE
    man=load(MAIN/'TRAINING_MANIFEST.json');records=[]
    for f in man['actual_train_files']:
        p=MAIN/f['path'];assert pin(p)['sha256']==f['sha256'];records+=rows(p)
    assert len(records)==595
    views={v['view_id']:v for v in rows(ROOT/'output/20261031_wrd_curation09/process/batch02/coverage_overlay/FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz')}
    overlay={r['canonical_owner_id']:r for r in rows(ROOT/'output/20261031_wrd_curation09/process/batch02/coverage_overlay/CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz')}
    assert {r['id']for r in records}==set(views)
    protected=original_user_basis();pp=protected['patterns'];ep,einfo=get_eval_basis()
    catalog=load(ROOT/'output/20261031_wrd_curation09/holdout/TASK_CATALOG_ALL36_05.json')
    reserved_sources={s for c in catalog for s in c['reserved_source_ids']}
    assert len(reserved_sources)==40
    action=[r for r in records if r['supervised_tokens_by_component'].get('A',0)>0]
    packages=rows(ROOT/'output/20261030_wrd_gap08/lineage/FROZEN_COMPLETE_PACKAGE_VERSIONS.jsonl.gz')
    producers={r['episode_id']:r for r in load(ROOT/'output/20261030_wrd_gap08/lineage/EPISODE_RECOVERY_46.json')['episodes']}
    package_texts,package_verifications=protected_package_texts(packages,producers)
    save('PROTECTED_PACKAGE_BYTE_IDENTITY_ISOLATION_ONLY.json',package_verifications)
    negative_sources=set(load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')['revoke_source_ids'])
    result=[];actionrows=[];contexts={};scanhits=[]
    for n,r in enumerate(records):
        v=views[r['id']];sources=set(r['source_ids']);direct=sorted(sources&protected['forbidden']);revoked=sorted(sources&negative_sources)
        reserved=sorted(sources&reserved_sources)
        pm=scan_messages(r['messages'],pp);em=scan_messages(r['messages'],ep)
        row={'view_id':r['id'],'bank':r['bank'],'stage':r['stage'],'source_ids':r['source_ids'],
          'source_group_id':r['source_group_id'],'supervised_tokens':r['supervised_tokens'],'input_tokens':r['total_tokens'],
          'components':r['supervised_tokens_by_component'],'native_owner_links':v['native_owner_links'],
          'external_historical_owner_links':v['external_historical_owner_links'],
          'view_conditioning':v['view_conditioning'],'direct_protected_source_ids':direct,
          'direct_reserved_source_ids':reserved,'prior23_revoked_closure_source_ids':revoked,
          'protected_original_user_content_match_pairs':len(pm),'reserved26_input_content_match_pairs':len(em),
          'match_classification':'NO_EXACT160_MATCH_NOT_GLOBAL_ANCESTRY_PROOF'if not pm and not em else'REVIEW_FINGERPRINT_MATCHES_WITH_FROZEN_GENERIC_CLASSIFICATION',
          'positive_tool_action_target':bool(r['supervised_tokens_by_component'].get('A',0)),
          'decision':'KEEP_EXISTING_SCOPED_CREDIT_NO_NEW_LABELLING_PENDING_KNOWN_ANCESTRY_EXCEPTIONS',
          'original_full_native_API_prompt_equivalence_claimed':False}
        for typ,mm in [('PROTECTED_ORIGINAL_USER',pm),('RESERVED26_REQUEST_OR_MATERIAL',em)]:
            for q in mm:scanhits.append({'view_id':r['id'],'kind':typ,**q})
        if row['positive_tool_action_target']:
            arow={**row,'native_owner_resources':[]}
            for oid in v['native_owner_links']:
                own=overlay[oid];key=own['episode_id']
                if key not in contexts:contexts[key]=parse_native(own['source_native'])
                ctx=contexts[key];idx=own['source_message_index']
                assert h(json.dumps(ctx['messages'][idx],ensure_ascii=False,separators=(',',':'),sort_keys=True))==own['original_message_sha256_sorted']
                arow['native_owner_resources'].append({'owner_id':oid,'episode_id':key,'source_native':own['source_native'],
                  'native_session_id':ctx['native_session_id'],'target_message_index':idx,
                  'target_event_line':ctx['source_event_lines'][idx],
                  'own_original_prefix_protected_sources':own.get('09_final_protected_sources',[]),
                  'own_original_prefix_reserved_sources':own.get('09_final_reserved_sources',[]),
                  'existing_scoped_credit_not_whole_prefix':True,
                  'observed_resource_events':resource_events(ctx,idx),
                  'protected_package_full_file_input_match_candidates':package_prefix_matches(ctx,idx,package_texts)})
            md=r['original_record_metadata'];arow['declared_action_owner']=md.get('owner_id')
            arow['authorship_provenance']=md.get('output_content_provenance',md.get('annotation_provenance'))
            arow['target_original_code_sha256']=md.get('target_original_code_sha256')
            arow['new_state_or_external_targets_are_not_new_native_tool_calls']=True
            actionrows.append(arow)
        result.append(row)
        if n%100==0:print(json.dumps({'progress_views':n,'scan_matches':len(scanhits)}),flush=True)
    assert len(actionrows)==99
    # Only extend the prior generic fingerprint classification after exact
    # fingerprint inclusion, never by assigning all content of a source generic.
    prior_class=load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')['generic_classes']
    oldhit={r['view_id']for r in result if r['view_id'].startswith('wrd10_evt_')and r['protected_original_user_content_match_pairs']}
    anchorbasis={a for q in scanhits if q['view_id']in oldhit for a in q['anchor_SHA_set']}
    classes=[]
    for r in result:
        hh=[q for q in scanhits if q['view_id']==r['view_id']]
        if not hh:continue
        assert set(r['source_ids'])<=set(prior_class),'NEW_MATCH_OUTSIDE_FROZEN_GENERIC_SOURCE_REQUIRES_REVIEW'
        assert all(q['kind']=='PROTECTED_ORIGINAL_USER'for q in hh),'NEW_RESERVED_TASK_OR_MATERIAL_MATCH_REQUIRES_REVIEW'
        aset={a for q in hh for a in q['anchor_SHA_set']}
        inherited=aset<=anchorbasis
        assert inherited,'NEW_NON_GENERIC_ANCHOR_REQUIRES_REVIEW'
        r['match_classification']='FROZEN_GENERIC_WRAPPER_OR_PERSONA_EXACT_FINGERPRINTS_ONLY_NOT_PRIVATE_BUSINESS'
        classes.append({'view_id':r['view_id'],'source_ids':r['source_ids'],
          'frozen_classes':{s:prior_class[s]for s in r['source_ids']},'exact_anchor_SHA_set':sorted(aset),
          'anchors_subset_of_existing_frozen_generic_contract_fingerprints':inherited,
          'all_source_content_not_globally_whitelisted':True})
    save('EXACT_MATCH_CLASSIFICATION.json',{'prior_frozen_classification_pin':pin(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json'),
      'views':classes,'classification_requires_exact_fingerprint_inclusion':True,
      'external_public_provenance_not_added':True,'private_protected_Q_or_thought_used':False})
    oid='0f1603b601613eac2fecb014';episode=overlay[oid]['episode_id']
    special=targeted_0f1603(contexts[episode],packages,producers)
    specialpin=save('0F1603_BOUNDED_RESOURCE_CLOSURE.json',special)
    selected=next(r for r in records if r['id']==special['view_id'])
    for r in result:
        if r['view_id']==special['view_id']:r['decision']=special['decision']
    assert not any(r['direct_protected_source_ids']or r['prior23_revoked_closure_source_ids']or r['direct_reserved_source_ids']for r in result)
    rev={'schema':'wrd10-p0-scoped-revocations-v1','status':'ROOT_REBASE_REQUIRED_NOT_MAIN_MUTATION',
      'baseline_manifest_sha256':BASE,'revoke_view_ids':[special['view_id']],
      'revoke_source_ids':[],'revoke_native_owner_ids':[oid],
      'reason':'Specific positive action has known protected-producer version linkage; actual resource delivery/derivation remains unresolved after two targeted roots. No contamination asserted; no entire source/episode withdrawal.',
      'counts':{'targets':1,'supervised_tokens':selected['supervised_tokens'],'input_tokens':selected['total_tokens'],
        'components':selected['supervised_tokens_by_component']},
      'conditional_rebased_before_any_new_rows':{'targets':594,'supervised_tokens':206249,'input_tokens':3500692,'process_targets':176},
      'original_R_withdrawn':0,'protected_Q_or_review_used_for_training':False,
      'main_unchanged':h((MAIN/'TRAINING_MANIFEST.json').read_bytes())==BASE,'training_started':False}
    rp=save('revocations.json',rev)
    outputs=[gzsave('CURRENT595_P0_VIEW_DECISIONS.metadata.jsonl.gz',result),
      gzsave('POSITIVE_A99_RESOURCE_EVENT_LINEAGE.metadata.jsonl.gz',actionrows),
      gzsave('CURRENT595_EXACT_CONTENT_ISOLATION_MATCHES.metadata.jsonl.gz',scanhits),specialpin,rp]
    qa={'schema':'wrd10-p0-isolation-and-resource-event-QA-v1','status':'PASS_CURRENT_SCOPED_AUDIT_WITH_ONE_SPECIFIC_HOLD_FOR_ROOT_REBASE',
      'main_manifest_sha256':BASE,'views':len(result),'positive_A_targets':len(actionrows),
      'distinct_native_positive_A_owners':len({o for v in actionrows for o in v['native_owner_links']}),
      'positive_A_views_with_native_owner_links':sum(bool(v['native_owner_links'])for v in actionrows),
      'positive_A_views_without_native_owner_links':sum(not v['native_owner_links']for v in actionrows),
      'native_episode_contexts_reparsed_and_target_hash_verified':len(contexts),
      'direct_protected_or_prior_revoked_or_reserved_source_hits':0,
      'protected_source_count':len(protected['forbidden']),'protected_original_user_message_count':protected['users'],
      'protected_pattern_count':protected['np'],'reserved_pattern_basis':einfo,
      'reserved_source_ids_checked':len(reserved_sources),
      'protected_package_CAS_files_SHA_verified':len(package_verifications),
      'protected_package_full_text_fingerprints_ge100chars':len(package_texts),
      'positive_A_owner_prefix_protected_package_full_file_match_candidates':sum(len(o['protected_package_full_file_input_match_candidates'])for v in actionrows for o in v['native_owner_resources']),
      'content_match_views':sorted({x['view_id']for x in scanhits}),
      'content_match_pairs':len(scanhits),'known_specific_unresolved_ancestry_views':1,
      'outputs':outputs,'main_manifest_unchanged':h((MAIN/'TRAINING_MANIFEST.json').read_bytes())==BASE,
      'new_business_calls':0,'training_started':False,'script_pin':pin(__file__),
      'limits':['No exact>=160 fingerprint match is not global clean-ancestry proof.',
        'Same episode/route/version label is not proof of model delivery.',
        'Current scoped view credit does not admit the full original prefix.',
        'New-authored projected actions are not new native calls.',
        'Protected package/source bytes used only for isolation metadata; no Q, thought or review labels.']}
    save('P0_QA.json',qa)
    print(json.dumps({k:qa[k]for k in ['views','positive_A_targets','distinct_native_positive_A_owners','native_episode_contexts_reparsed_and_target_hash_verified','content_match_views','content_match_pairs','known_specific_unresolved_ancestry_views']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
