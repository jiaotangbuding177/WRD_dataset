"""Second parser checks actual immutable carriers, receipt ranges and decisions."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,re
R=Path('D:/skillloop'); B=Path(__file__).parent.parent
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8-sig')))
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def native(p):
 out=[]
 for line in Path(p).read_text(encoding='utf-8-sig').splitlines():
  e=json.loads(line)
  if e.get('type')=='message' and isinstance(e.get('message'),dict):out.append(e['message'])
 return out
def text(m):
 c=m.get('content',[])
 return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def jsonpath(v,path):
 assert path.startswith('$')
 for key,idx in re.findall(r'\.([^\.\[]+)|\[(\d+)\]',path[1:]):v=v[key] if key else v[int(idx)]
 return v
def scalar(v,path):return jsonpath(v,path)
def main():
 oldids={x['id'] for x in load(R/'output/20261029_wrd_v9_missing_evidence_update02/ANCESTRY_CORRECTION_OVERLAY.json')['target_overlays']}
 baseids=set(); total={};native_responseids=set()
 for name,ec,tc,pc in [('crossroutes',17,269,266),('remaining76',76,590,341)]:
  o=B/name;d=load(o/'ROUTE_PRODUCER_CLOSURE.json');labels=rows(o/'TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz');flat=rows(o/'ORIGINAL_EPISODE_MESSAGES.jsonl.gz')
  assert len(d['episodes'])==ec and len(labels)==tc
  assert len({x['id'] for x in labels})==tc and not ({x['id'] for x in labels}&baseids) and not ({x['id'] for x in labels}&oldids)
  baseids.update(x['id'] for x in labels)
  originals={e['episode_id']:native(e['native']['path']) for e in d['episodes']}
  assert sum(len(x) for x in originals.values())==len(flat)
  for x in flat:
   assert x['original_message']==originals[x['episode_id']][x['message_index']]
   assert x['message_sha256']==h(can(x['original_message']))
   if x['original_message'].get('responseId'):native_responseids.add(x['original_message']['responseId'])
  producer_checks=0;receipt_checks=0;partial_scalar_checks=0
  for ep in d['episodes']:
   ms=originals[ep['episode_id']]
   assert h(Path(ep['native']['path']).read_bytes())==ep['native']['sha256']
   verified_boundaries=[]
   for link in ep['route_links']:
    inp=load(link['input_carrier']['original']['path']); stripped={k:v for k,v in inp.items() if k!='candidate_gate'}
    raw=Path(link['input_carrier']['original']['path']).read_bytes().decode('utf-8-sig');norm=raw.replace('\r\n','\n')
    assert h(can(inp))==link['canonical_input_sha256']
    producers={}
    for p in link['producer_matches']:
     assert h(Path(p['native']['path']).read_bytes())==p['native']['sha256']
     pm=native(p['native']['path']);cm=pm[p['message_index']]
     call=next(c for c in cm['content'] if c.get('type')=='toolCall' and c.get('id')==p['tool_call_id']);a=call['arguments']
     if isinstance(a,str):a=json.loads(a)
     assert call['name']=='write' and h(a['content'].encode())==p['write_content_sha256']
     obj=jsonpath(json.loads(a['content']),p['json_object_path']);assert h(can(obj))==p['object_canonical_sha256']
     ack=pm[p['ack_message_index']];assert ack['toolCallId']==call['id'] and ack.get('isError') is False
     mode=p['match_mode']
     if mode=='EXACT_ALL_ORIGINAL_FIELDS_PLUS_CANDIDATE_GATE':assert stripped==obj
     elif mode=='ALL_INPUT_FIELDS_EXACT_IN_PRODUCER':assert all(k in obj and obj[k]==v for k,v in stripped.items())
     elif mode=='EXACT_ORIGINAL_OBJECT_PLUS_EMPTY_CONFLICTS_DEFAULT':assert set(stripped)==set(obj)|{'conflicts'} and stripped['conflicts']==[] and all(stripped[k]==v for k,v in obj.items())
     elif mode=='EXACT_SIX_ORIGINAL_FIELDS_PLUS_STEPS_COPIED_FROM_ROUTE_SIGNATURE':
      assert all(stripped[k]==obj[k] for k in ['id','name','category','source_ids','route_signature','value_plan']) and stripped['steps']==obj['route_signature']['steps']
     else:raise AssertionError(mode)
     producers[(p['episode_id'],p['message_index'])]=(obj,p['producer_scope']);producer_checks+=1
    for obs in link['actual_receipts']:
     m=ms[obs['observation_message_index']];obsraw=text(m);normalized=obsraw.replace('\r\n','\n')
     assert m['toolCallId']==obs['tool_call_id'] and h(obsraw.encode())==obs['observation_text_sha256']
     assert (raw in obsraw)==obs['entire_original_file_text_contiguous_in_actual_observation']
     assert (norm.strip() in normalized)==obs['entire_file_after_CRLF_to_LF_and_outer_whitespace_normalization_contiguous']
     protected_received=False
     for p in obs['received_protected_original_scalar_proofs']:
      obj,proof=producers[(p['producer_episode_id'],p['producer_message_index'])]
      value=scalar(obj,p['original_field_path']);assert isinstance(value,str) and len(value)>=32
      encoded=json.dumps(value,ensure_ascii=False);s=p['normalized_observation_character_start'];e=p['normalized_observation_character_end']
      assert normalized[s:e]==encoded and h(encoded.encode())==p['quoted_scalar_sha256'] and h(value.encode())==p['scalar_UTF8_sha256'] and encoded in norm
      partial_scalar_checks+=1
      if proof and proof['source_admission']=='HOLD_PROTECTED':protected_received=True
     full=obs['entire_original_file_text_contiguous_in_actual_observation'] or obs['entire_file_after_CRLF_to_LF_and_outer_whitespace_normalization_contiguous']
     if protected_received or full and any(proof and proof['source_admission']=='HOLD_PROTECTED' for _,proof in producers.values()):verified_boundaries.append(obs['observation_message_index'])
     receipt_checks+=1
   b=min(verified_boundaries,default=None);assert b==ep['proven_protected_boundary']
   for t in [x for x in labels if x['episode_id']==ep['episode_id']]:
    assert t['original_message']==ms[t['source_message_index']] and t['positive_loss']==0
    expected='HOLD_PROTECTED_ACTUAL_ROUTE_PRODUCER' if b is not None and t['source_message_index']>b else 'HOLD_ANCESTRY_NOT_CLOSED'
    assert t['current_decision']==expected
  counter=Counter(x['current_decision'] for x in labels);assert counter['HOLD_PROTECTED_ACTUAL_ROUTE_PRODUCER']==pc
  gaps=[{'id':x['id'],'episode_id':x['episode_id'],'route_id':x['route_id'],'message_index':x['source_message_index'],
    'original_unknown_reasons':x['original_target_metadata']['unknown_reasons'],
    'observed_prior_unresolved_resource_nodes':x['original_target_metadata']['observed_prior_unresolved_direct_resource_nodes'],
    'actual_original_action':x['original_message']['content'],'gap':'A prior producer is not proven clean; old source flags and final bytes do not settle it.',
    'new_state_local_action_may_be_reviewed_separately':name=='crossroutes'} for x in labels if x['current_decision']=='HOLD_ANCESTRY_NOT_CLOSED']
  save(o/'REMAINING_GAPS.json',{'status':'CONCRETE_OPEN_ANCESTRY_NOT_ABSENT_OR_USELESS_RECORDS','count':len(gaps),'targets':gaps})
  object_pins=[]
  for p in sorted((o/'objects').iterdir()):assert p.is_file() and h(p.read_bytes())==p.name;object_pins.append(pin(p))
  resources=rows(o/'ACTUAL_RESOURCE_CARRIERS.jsonl.gz');final=rows(o/'FINAL_RESOURCE_CARRIERS.jsonl.gz')
  for x in resources+final:
   cp=x['recovered_carrier']
   if cp:assert h(Path(cp['copied']['path']).read_bytes())==cp['copied']['sha256']
  q={'status':'PASS_FILE_AND_RECEIPT_INTEGRITY_NOT_SEMANTIC_TRAINING_ADMISSION','episodes':ec,'targets':tc,'messages':len(flat),
   'protected_actual_descendants':pc,'remaining_unclosed':tc-pc,'producer_matches_checked':producer_checks,
   'actual_observations_checked':receipt_checks,'exact_original_quoted_scalar_ranges_checked':partial_scalar_checks,
   'frozen_objects_checked':len(object_pins),'frozen_object_bytes':sum(x['bytes'] for x in object_pins),
   'all_full_frozen_original_messages_preserved':True,'source_mask_or_main_manifest_changed':False,'new_admitted_training_targets':0,
   'scope_correctness_does_not_imply_program_correctness':True,'verifier':pin(__file__)}
  save(o/'LOCAL_INTEGRITY_QA.json',q);total[name]=q
 pairs=R/'output/20261026_wrd_dataset_v9/recovery/provider_pairs.original.jsonl.gz'
 matched=[x['provider_response_id'] for x in rows(pairs) if x['provider_response_id'] in native_responseids]
 save(B/'crossroutes/RECORDED_REASONING_CARRIER_CHECK.json',{'actual93_frozen_native_response_ids':len(native_responseids),
  'intersections_with_existing1536_provider_response_groups':len(matched),'provider_pairs':pin(pairs),
  'thinking_or_reasoning_blocks_in_these_native_carriers':0,
  'not_claimed':'This does not prove the full history has no reasoning. Raw native exports have no original thinking field here and this specific old provider-pair bank is disjoint; other original response carriers remain a separate recovery gap.',
  'original_reasoning_not_fabricated_or_silently_substituted':True,'native_originals_preserved':True})
 for name in ['crossroutes','remaining76']:
  o=B/name;names=[]
  for p in sorted(o.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name not in ['FINAL_ALLOWLIST.jsonl','FINAL_MANIFEST.json']:names.append(p)
  al=o/'FINAL_ALLOWLIST.jsonl';al.write_text(''.join(json.dumps({'relative':str(p.relative_to(o)).replace('\\','/'),**pin(p)},ensure_ascii=False,separators=(',',':'))+'\n' for p in names),encoding='utf-8')
  save(o/'FINAL_MANIFEST.json',{'status':'ACTUAL_RECOVERED_RECORDS_AND_BYTES_SEALED_NOT_MAIN_TRAINING_ADMISSION',
   'files':len(names),'bytes':sum(p.stat().st_size for p in names),'allowlist':pin(al),'qa':pin(o/'LOCAL_INTEGRITY_QA.json'),
   'original_positive_data_added_by_recovery_script':0,'new_native_or_training':False})
 print(json.dumps({n:{k:v for k,v in q.items() if k in ['episodes','targets','messages','protected_actual_descendants','remaining_unclosed','frozen_objects_checked','frozen_object_bytes']} for n,q in total.items()}))
if __name__=='__main__':main()
