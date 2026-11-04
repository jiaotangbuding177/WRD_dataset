"""Independent byte/identity/partition recount of the sealed08 corpus.

Does not import the corpus producer. Protected originals are hashed or compared
as exact recorded fields only, never semantically approved for training here.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json,tarfile,struct

ROOT=Path('D:/skillloop');B=ROOT/'output/20261030_wrd_gap08/corpus';OUT=Path(__file__).resolve().parent
def H(v):return hashlib.sha256(v).hexdigest()
def C(v,sort=True):return json.dumps(v,ensure_ascii=False,sort_keys=sort,separators=(',',':')).encode()
def J(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def Z(p):
 with gzip.open(p,'rt',encoding='utf-8-sig') as f:
  for s in f:yield json.loads(s)
def P(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def checkpin(p,v):
 p=Path(p);assert p.stat().st_size==v['bytes'] and H(p.read_bytes())==v['sha256'],str(p)
def codeargs(x):
 a=x.get('arguments',{});return json.loads(a) if isinstance(a,str) else a
def main():
 OUT.mkdir(exist_ok=True);manifest_start=P(B/'MANIFEST.json');manifest=J(B/'MANIFEST.json');files=manifest['files'];assert len(files)==manifest['file_count']==1124
 for f in files:checkpin(B/f['path'],f)
 assert sum(f['bytes'] for f in files)==manifest['bytes']==372107103
 baseline=J(B/'BASELINE01_FROZEN_FILES.json')
 for p in baseline['files']:checkpin(p['path'],p)
 assert P(B/'BASELINE_MANIFEST_552.json')['sha256']==baseline['original_552_manifest_source_sha256']=='94770ad82f082c55cf780f8a85108b9429cfa9ee5ee168c43198878f18633541'
 scopep=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz';scope={r['source_id']:r for r in Z(scopep)}
 labels_path=ROOT/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz';labels={r['id']:r for r in Z(labels_path)};p226={s for r in labels.values() for s in r['original226']};h12={s for r in labels.values() for s in r['holdout12']};assert len(p226)==226 and len(h12)==12
 legacy={r['id']:r for r in Z(ROOT/'output/20261025_wrd_training_preflight/prepared_gated/public/audit/eligibility.jsonl.gz')};legacy_unreviewed={k for k,v in legacy.items() if v['semantic_review']=='not_ai_semantically_reviewed'};assert len(legacy)==7117 and len(legacy_unreviewed)==6692
 owners={};pop=Counter();disp=Counter();source_disp=Counter();legacy_disp=Counter();sub=defaultdict(Counter);all_closed_sids=set();closed_scope_count=0
 for r in Z(B/'CORPUS_OWNER_COVERAGE.native.jsonl.gz'):
  oid=r['canonical_owner_id'];assert oid not in owners and oid==H((r['episode_id']+':'+str(r['source_message_index'])).encode())[:24];assert r['no_new_positive_loss'] is True
  owners[oid]={k:r[k] for k in ['episode_id','source_message_index','source_event_line','original_message_sha256_sorted','original_message_sha256_insertion_order','original_content_sha256_sorted','source_native','source_ids','source_disposition','current_disposition','population','original_R_disposition','original_A_disposition']}
  pop[r['population']]+=1;disp[r['current_disposition']]+=1;source_disp[r['source_disposition']]+=1;sub[r['current_disposition']]['nonempty_source_ids' if r['source_ids'] else 'protocol_only_no_source_ids']+=1
  if oid in legacy_unreviewed:legacy_disp[r['current_disposition']]+=1
  if r['source_disposition']=='SCOPE_CLOSED_SEMANTIC_PENDING':
   assert r['source_ids'] and all(s not in p226|h12 and scope.get(s,{}).get('status')=='TRAIN' for s in r['source_ids']);all_closed_sids.update(r['source_ids']);closed_scope_count+=1
 assert len(owners)==34616 and sum(pop.values())==34616 and pop['V9_OLD1763']==32342 and pop['V9_OLD1763']+pop['V9_SUPPLEMENT80']==34239
 assert not (set(legacy)-set(owners));assert closed_scope_count==1363 and len(all_closed_sids)==62
 episodes={r['episode_id']:r for r in Z(B/'EPISODE_CAPTURE_COVERAGE.jsonl.gz')};assert len(episodes)==1871;bysha=defaultdict(list)
 for e in episodes.values():bysha[e['source_native']['sha256']].append(e)
 assert len(bysha)==1871
 codes=list(Z(B/'RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz'));assert len(codes)==653 and len({r['canonical_owner_id'] for r in codes})==653
 codeby={r['canonical_owner_id']:r for r in codes};codefound=set();full_closed=[r for r in codes if r['source_disposition']=='SCOPE_CLOSED_SEMANTIC_PENDING'];assert len(full_closed)==40 and len({s for r in full_closed for s in r['source_ids']})==21
 for r in codes:
  assert r['positive_loss']==0 and r['whole_tool_write_content_recovered'] is True and H(r['full_code'].encode())==r['original_content_utf8_SHA256'] and len(r['full_code'])==r['characters'];assert owners[r['canonical_owner_id']]['source_disposition']==r['source_disposition']
 for r in full_closed:
  lab=labels[r['canonical_owner_id']];assert lab['source_admission']=='ADMIT' and not lab['original226'] and not lab['holdout12'] and not lab['protected_sources_visible_prefix'] and set(r['source_ids'])==set(owners[r['canonical_owner_id']]['source_ids'])
 nindex=J(B/'NATIVE1871_ORIGINAL_CARRIER_ARCHIVE_INDEX.json');checkpin(nindex['archive']['path'],nindex['archive']);n_members={r['archive_member']:r for r in nindex['members']};assert len(n_members)==1871 and {r['sha256'] for r in n_members.values()}==set(bysha)
 bodyhashes={};native_owner_seen=set();parse_errors=0;raw_messages=0
 with tarfile.open(nindex['archive']['path'],'r|gz') as tar:
  for member in tar:
   assert member.isfile() and member.name in n_members;mi=n_members[member.name];data=tar.extractfile(member).read();assert len(data)==mi['bytes']==member.size and H(data)==mi['sha256'];e=bysha[mi['sha256']][0];messages=[];event_lines=[]
   for line_no,line in enumerate(data.splitlines(),1):
    try:v=json.loads(line)
    except ValueError:parse_errors+=1;continue
    if isinstance(v.get('message'),dict):messages.append(v['message']);event_lines.append(line_no)
   raw_messages+=len(messages);bodyhashes[e['episode_id']]=H(C(messages));assert len(messages)==e['messages']
   assistant_count=0
   for i,m in enumerate(messages):
    if m.get('role')!='assistant':continue
    assistant_count+=1;oid=H((e['episode_id']+':'+str(i)).encode())[:24];r=owners[oid];assert r['source_message_index']==i and r['source_event_line']==event_lines[i] and H(C(m))==r['original_message_sha256_sorted'] and H(C(m,False))==r['original_message_sha256_insertion_order'] and H(C(m.get('content')))==r['original_content_sha256_sorted'];native_owner_seen.add(oid)
    if oid in codeby:
     z=codeby[oid];tc=[x for x in m.get('content',[]) or [] if isinstance(x,dict) and x.get('type')=='toolCall' and x.get('id')==z['original_tool_call_id']];assert len(tc)==1 and tc[0]['name']=='write';a=codeargs(tc[0]);assert a['path']==z['native_path'] and a['content']==z['full_code'];codefound.add(oid)
   assert assistant_count==e['assistant_positions']
 assert native_owner_seen==set(owners) and codefound==set(codeby)
 context_seen=set()
 for f in {e['raw_context_file'] for e in episodes.values()}:
  for c in Z(B/f):assert H(C(c['messages']))==bodyhashes[c['episode_id']];context_seen.add(c['episode_id'])
 assert context_seen==set(episodes)
 overlay=list(Z(B/'NATIVE73_STATIC_SCOPE_OVERLAY02.jsonl.gz'));assert len(overlay)==73;over_ids={x['canonical_owner_id'] for x in overlay};six={x['episode_id'] for x in overlay};expected_static={k for k,v in owners.items() if v['episode_id'] in six and v['source_message_index']>0};assert over_ids==expected_static
 for r in overlay:assert r['positive_loss']==0 and r['actual_protected_observation_index']==0 and r['original_message_index']>0 and r['old_base01_disposition']==owners[r['canonical_owner_id']]['current_disposition'];checkpin(r['proof_path'],{'bytes':Path(r['proof_path']).stat().st_size,'sha256':r['proof_sha256']})
 after=disp.copy()
 for r in overlay:after[r['old_base01_disposition']]-=1;after[r['current_disposition']]+=1
 assert after['UNKNOWN_SUPPLEMENTAL_PREFIX_NOT_AUDITED']==2173 and after['ISOLATED_PROTECTED_FROZEN_STATIC_EVAL_TASK_PREFIX']==73
 # Parsed provider pairs and native owners remain different populations.
 pp=B/'audit_inputs/provider1536.pairs.original.jsonl.gz'
 if not pp.exists():pp=ROOT/'output/20261026_wrd_dataset_v9/recovery/provider_pairs.original.jsonl.gz'
 pairs=list(Z(pp));assert len(pairs)==1536;expected_provider={}
 for r in pairs:
  expected_provider[r['response_source']['sha256']]=r['response_source']
  for q in r['request_variants']:expected_provider[q['source']['sha256']]=q['source']
 pindex=J(B/'PROVIDER1536_ORIGINAL_CARRIER_ARCHIVE_INDEX.json');checkpin(pindex['archive']['path'],pindex['archive']);p_members={r['archive_member']:r for r in pindex['members']};assert len(p_members)==len(expected_provider)==2990 and {x['sha256'] for x in p_members.values()}==set(expected_provider)
 pseen=set()
 with tarfile.open(pindex['archive']['path'],'r|gz') as tar:
  for m in tar:
   assert m.isfile() and m.name in p_members;r=p_members[m.name];raw=tar.extractfile(m).read();assert H(raw)==r['sha256'] and len(raw)==m.size==r['bytes'];pseen.add(r['sha256'])
 assert pseen==set(expected_provider)
 restor=J(B/'EXACT_JSON_CARRIER_RESTORATION.json');restored=restor['restored'];assert len(restored)==781;needed={x['source_record_id'] for x in restored};oldpath=Path(restored[0]['source_preserved_json_record_file']['path']);oldrecords={r['id']:r for r in Z(oldpath) if r['id'] in needed};assert set(oldrecords)==needed;restkind=Counter()
 for r in restored:
  assert r['source_preserved_json_record_file']['path']==str(oldpath);recipe=r['recipe'];val=oldrecords[r['source_record_id']][r['source_json_field']];opts={k:recipe[k] for k in ['ensure_ascii','indent','sort_keys']};opts['separators']=tuple(recipe['separators']) if recipe['separators'] is not None else None;rebuilt=(json.dumps(val,**opts)+recipe['ending']).encode();original=r['original_pin'];actual=Path(r['recovered_actual_bytes']['path']).read_bytes();assert rebuilt==actual and H(actual)==original['sha256']==r['recovered_actual_bytes']['sha256'] and len(actual)==original['bytes']==r['recovered_actual_bytes']['bytes'] and H(actual) in pseen;restkind[r['source_json_field']]+=1
 snapshots=J(B/'CURRENT552_COMPILED_SNAPSHOT_INDEX.json');baseline_manifest=J(B/'BASELINE_MANIFEST_552.json');compiled={};components=Counter();tokens=0
 for f in snapshots['files']:
  actual=f['actual_frozen_copy'];checkpin(actual['path'],actual);assert actual['sha256']==f['original_compiled_file']['sha256']
  for r in Z(actual['path']):
   assert r['id'] not in compiled;assert H(struct.pack('<'+'I'*len(r['input_ids']),*r['input_ids']))==r['input_ids_sha256_u32le'];spans=r['supervision_spans'];co=Counter();seen=set()
   for a,b,k,w in spans:assert a<b and not seen.intersection(range(a,b));seen.update(range(a,b));co[k]+=b-a
   assert dict(co)==r['supervised_tokens_by_component'] and sum(co.values())==r['supervised_tokens'];components.update(co);tokens+=r['supervised_tokens'];compiled[r['id']]={'source_ids':r['source_ids'],'component_tokens':dict(co),'tokens':r['supervised_tokens'],'rendered_SHA':r['rendered_sha256'],'span':spans,'source_file':f['original_compiled_file']['path'],'R_fields':{i:m.get('reasoning_content','') for i,m in enumerate(r['messages']) if m.get('reasoning_content')}}
 assert len(compiled)==552 and tokens==150674 and components=={'F':2616,'D':74936,'R':56500,'A':16622}
 views=list(Z(B/'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz'));assert len(views)==552 and {x['view_id'] for x in views}==set(compiled);alias=J(B/'CURRENT552_ALIAS_COMPONENT_OVERLAY02.json');partition=Counter();native_links=set();ext_links=set();native_conditions=Counter();original_native_R=set();original_native_A=set();approved_ranges=0
 for r in views:
  q=compiled[r['view_id']];assert r['component_tokens']==q['component_tokens'] and r['actual_supervised_tokens']==q['tokens'] and r['actual_token_supervision_spans']==q['span'] and r['rendered_sha256']==q['rendered_SHA'] and r['source_ids']==q['source_ids'];assert all(s not in p226|h12 and scope[s]['status']=='TRAIN' for s in r['source_ids'])
  for a in r['approved_field_ranges']:
   assert a['field']=='reasoning_content';s=q['R_fields'][a['message_index']];assert H(s[a['start']:a['end']].encode())==a['text_sha256'];approved_ranges+=1
  if r['native_owner_links']:
   partition['native_message_linked']+=1;native_links.update(r['native_owner_links']);assert set(r['native_owner_links'])<=set(owners);native_conditions[r['view_conditioning']]+=1
   if r['view_conditioning']=='DECLARED_NATIVE_SCOPED_VIEW':
    if q['component_tokens'].get('R'):original_native_R.update(r['native_owner_links'])
    if q['component_tokens'].get('A'):original_native_A.update(r['native_owner_links'])
  elif r['external_historical_owner_links']:partition['external_historical']+=1;ext_links.update(r['external_historical_owner_links'])
  elif r['view_id']==alias['wire_only_alias']['view_id']:
   partition['compatible_wire_only']+=1;wire=alias['wire_only_alias']['wire']['source'];checkpin(wire['path'],wire);assert alias['wire_only_alias']['complete_original_R_matches_wire'] is True;parts=[]
   for line in Path(wire['path']).read_text(encoding='utf8').splitlines():
    if line.startswith('data:') and '[DONE]' not in line:
     frame=json.loads(line[5:].lstrip())
     for ch in frame.get('choices',[]):
      if ch.get('index',0)==0:parts.append(ch.get('delta',{}).get('reasoning_content') or '')
   captured=''.join(parts);assert captured==alias['wire_only_alias']['wire']['parsed_original_response_fields']['reasoning_content'] and captured in q['R_fields'].values() and q['component_tokens']['R']==40
  else:assert r['new_authored_view_does_not_require_original_native_owner'] is True;partition['new_authored_no_original_owner']+=1
 assert partition=={'native_message_linked':58,'external_historical':33,'compatible_wire_only':1,'new_authored_no_original_owner':460};assert len(original_native_R)==37 and len(original_native_A)==33 and approved_ranges==216
 assert P(B/'MANIFEST.json')==manifest_start
 report={'schema':'wrd-gap08-sealed-corpus-independent-author-QA-v1','status':'PASS_INDEPENDENT_ACTUAL_BYTES_OWNERS_SOURCES_CODE_CARRIERS_AND_BASELINE552_PARTITIONS','reviewer':'scheduled_batch24','independent_from_corpus_producer_crossroutes_batch24':True,'producer_module_imported_or_called':False,'manifest':manifest_start,'actual_manifest_file_count':1124,'actual_manifest_bytes':372107103,'baseline01_15_file_pins_unchanged':True,'native':{'owner_rows':len(owners),'actual_original_carriers_reparsed':1871,'actual_messages_reparsed':raw_messages,'raw_invalid_JSON_line_count_preserved_not_fabricated':parse_errors,'populations':dict(pop),'base_current_dispositions':dict(disp),'original_source_dispositions':dict(source_disp),'after_static73_overlay_dispositions':dict(after),'current_disposition_source_presence_split':{k:dict(v) for k,v in sub.items()},'legacy7117_all_joined':True,'legacy6692_definition':'semantic_review == not_ai_semantically_reviewed; not training_eligible','legacy7117_training_eligible_true':sum(bool(v['training_eligible']) for v in legacy.values()),'legacy6692_dispositions':dict(legacy_disp),'original_full_carrier_file_completeness_is_not_complete_system_or_thought_capture_guarantee':True},'source_closed':{'nonempty_allowed_source_owner_rows':1363,'distinct_source_ids':62,'final_SOURCE_CLOSED_SEMANTIC_PENDING_1229_is_not_all_business':dict(sub['SOURCE_CLOSED_SEMANTIC_PENDING']),'all_source_ids_currentTRAIN_and_not226_H':True,'new_semantic_or_training_admission':0},'complete_code':{'full_write_rows':653,'distinct_owner_ids':653,'distinct_original_code_SHA':len({r['original_content_utf8_SHA256'] for r in codes}),'all_exact_original_write_call_content_and_path_rechecked':True,'source_closed_rows':40,'source_closed_distinct_sources':21,'source_closed40_actual_upstream_scope_labels_checked':True,'syntax_semantics_Q_skill_value_not_approved_here':True},'provider':{'parsed_groups_not_additive_native_tasks':1536,'exact_raw_carriers_read_from_archive':2990,'restored_exact_JSON_carriers':781,'restoration_fields':dict(restkind),'all781_reconstructed_bytes_recomputed_from_original_full_JSON_field_and_recipe_and_prior_SHA':True,'new_original_teacher_calls':0},'baseline552':{'view_rows':552,'supervised_tokens':tokens,'component_tokens':dict(components),'partition':dict(partition),'native_linked_view_conditioning_counts':dict(native_conditions),'approved_actual_R_character_range_SHA_checks':approved_ranges,'actual_token_array_SHA_and_nonoverlap_spans_recounted':True,'not_current569_manifest_or_new_training_entry':True,'native_or_wire_original_R_scope_counts_independently_recounted':{'declared_native_message_original_R_owners':len(original_native_R),'wire_only_call':1,'total_calls':38,'declared_native_same_condition_A_owners':len(original_native_A)},'wire_only_capture_finish_length_is_observed_prefix_not_complete_lifetime_thought':True,'native58_views_are_not58_full_autonomous_tasks':True},'protected_R_not_semantically_reviewed_or_reused_for_training':True,'no_old_Agent_or_business_model_execution':True,'training_started':False,'AI_curation_cost':'UNKNOWN_NOT_ZERO','limitations':['This is the sealed registered1871-carrier population, not proof all175physical roots or all disk files have been exhaustively discovered.','Source closure is different from semantic correctness, successful resource usage, qualifiedKEEP or whole autonomous pipeline.','BASELINE01 labels remain frozen; explicit sidecars supply73 static dispositions and1 genuine wire-only alias without adding loss.','The552 snapshot is the pre-gap08 baseline. Root owns the separate17 increment/current569 manifest, loader and canonical-array admission.'],'script':P(__file__)}
 report['reviewer_origin_boundary']={'independent_author_from_sealed_corpus_ledger_archive_producer':True,'static6_prefix_proof_previously_curated_by_this_reviewer':True,'static73_overlay_owner_set_recounted_here_but_not_a_second_independent_author_for_original_static6_proof':True,'root_independently_confirmed_static_test_policy_application':True,'all_original_carriers_and_compiled_snapshot_bytes_reparsed_without_producer_import':True}
 p=OUT/'ROOT_PEER_QA.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'QA':P(p),'status':report['status']}))

if __name__=='__main__':main()
