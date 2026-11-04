"""Scan real native prefixes through each original target, not new states.

Uses the research audit's original-role=user protected fingerprints; never
executes original native actions, saved programs, models, or agent loops.
"""
import collections,contextlib,gzip,hashlib,io,json,runpy
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout'
with contextlib.redirect_stdout(io.StringIO()):
 basis=runpy.run_path(str(ROOT/'research/data_prep/wrd_curation09/holdout_protected_vs_train.py'))
patterns=basis['patterns'];norm=basis['norm'];strings=basis['strings'];sha=basis['sha']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pin(p):return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
owners={};rows=[];cache={}
for lane,folder in [('writers','writers/packets'),('process','process/packets'),
 ('process_visible12','process/visible_decision_packets'),('process_batch02_9','process/batch02/packets')]:
 base=ROOT/'output/20261031_wrd_curation09'/folder.split('/')[0]
 for path in sorted((ROOT/'output/20261031_wrd_curation09'/folder).glob('*.json')):
  packet=read(path)
  if lane=='writers':
   owner=packet['canonical_owner_id'];proof=packet['owner_proof_original'];index=proof['source_message_index']
   ctxpath=base/packet['context_ref'];context=cache.setdefault(str(ctxpath),read(ctxpath))
   target_sha=proof['original_message_sha256_sorted'];sids=proof['source_ids'];episode=proof['episode_id']
  else:
   proof=packet['owner'];owner=proof['owner_id'];index=proof['source_message_index'];context=packet['original_context'];ctxpath=None
   target_sha=proof['target_original_SHA256_sorted'];sids=proof['source_ids'];episode=proof['episode_id']
  actual_target=sha(json.dumps(context['messages'][index],ensure_ascii=False,separators=(',',':'),sort_keys=True))
  assert actual_target==target_sha,(lane,owner,index)
  hits=[];scanned_chars=0
  for mi,msg in enumerate(context['messages'][:index+1]):
   text=norm('\n'.join(strings(msg)));scanned_chars+=len(text);found=collections.defaultdict(list);origins={}
   for offset in range(len(text)-159):
    options=patterns.get(text[offset:offset+40])
    if options:
     actual=text[offset:offset+160]
     for expected,p,origin in options:
      if actual==expected:
       k=(origin['protected_source_id'],origin['protected_message_index']);origins[k]=origin
       found[k].append({'protected_user_normalized_offset':p,'native_message_normalized_offset':offset,'exact160char_anchor':actual,'anchor_sha256':sha(actual)})
   for k,anchors in found.items():hits.append({'native_message_index':mi,'native_message_role':msg.get('role'),
    'native_message_SHA_sorted':sha(json.dumps(msg,ensure_ascii=False,separators=(',',':'),sort_keys=True)),
    'native_event_line':context.get('source_event_lines',[None]*len(context['messages']))[mi],
    'at_target_not_pretarget':mi==index,'protected_original_user_origin':origins[k],'anchors':anchors})
  row={'lane':lane,'original_owner_id':owner,'episode_id':episode,'source_ids':sids,'target_message_index':index,
   'original_target_SHA_verified':actual_target,'packet_pin':pin(path),'context_pin':pin(ctxpath) if ctxpath else None,
   'context_episode_id':context['episode_id'],'prefix_messages_scanned_including_target':index+1,
   'future_messages_excluded':len(context['messages'])-index-1,'normalized_chars_scanned':scanned_chars,
   'system_capture_status':context.get('system_capture_status'),'matches':hits,
   'exact_private_vs_generic_semantic_status':'UNREVIEWED' if hits else 'NO_160_EXACT_MATCH_NOT_GLOBAL_CLEAN_PROOF',
   'new_functional_state_does_not_remove_original_code_ancestry':True}
  rows.append(row);owners.setdefault(owner,[]).append(row)
assert len([r for r in rows if r['lane']=='writers'])==31
assert len([r for r in rows if r['lane']=='process'])==66
staging_path=ROOT/'output/20261031_wrd_curation09/compiled_staging01/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
staging=[json.loads(s) for s in gzip.open(staging_path,'rt',encoding='utf-8-sig')]
links=[]
for target in staging:
 linked={}
 for field in ['original_recorded_action_owner','owner_id']:
  value=target.get(field)
  if value in owners:linked[value]=[field+'_EXACT_OWNER']
 episode=target.get('original_episode_id');index=target.get('original_message_index')
 if episode is not None and index is not None:
  for r in rows:
   if r['episode_id']==episode and r['target_message_index']==index:
    linked.setdefault(r['original_owner_id'],[]).append('EXACT_EPISODE_AND_ORIGINAL_MESSAGE_INDEX')
 # New resource repairs can refer to their original resource producer through
 # explicit owner/source_context. Candidate strings alone are not promoted.
 context=target.get('source_context',{})
 if isinstance(context,dict) and context.get('path'):
  filename=Path(context['path']).stem
  if filename in owners:linked.setdefault(filename,[]).append('EXACT_PACKET_PATH_STEM')
 links.append({'staging_id':target['id'],'source_ids':target['source_ids'],'stage':target['stage'],
  'original_episode_id':episode,'original_message_index':index,
  'exact_prefix_owner_links':[{'owner_id':o,'link_evidence':e,'matched_native_prefix':any(r['matches'] for r in owners[o])} for o,e in linked.items()],
  'unlinked_requires_producer_resource_proof':not linked})
report={'schema':'wrd09-protected-original-user-vs-real-native-prefix-v1','status':'RAW_PREFIXES_SCANNED_NOT_NEW_STATE_LAUNDERED',
 'protected_pattern_basis_script_pin':pin(ROOT/'research/data_prep/wrd_curation09/holdout_protected_vs_train.py'),
 'protected_user_sources':len(basis['forbidden']),'protected_original_users':basis['users'],'patterns':basis['np'],
 'native_packet_targets':len(rows),'unique_original_owners':len(owners),'writer31':31,'process66':66,
 'visible_decision_packets12':12,'batch02_packets9':9,
 'matching_target_count':sum(bool(r['matches']) for r in rows),'targets':rows,'staging32_owner_prefix_links':links,
 'staging_pin':pin(staging_path),'script_pin':pin(Path(__file__).resolve()),
 'limits':['Exact normalized160chars, material start stride40; no match does not close other unknown resource producers or byte/image-only ancestry.',
 'All messages only through target included. Later observations were excluded; target matches indicate code/action content, not earlier observation.',
 'Missing original system capture remains missing. No original native input equivalence or business correctness inferred.',
 'Protected pattern source is only original user input, never heldout thought, assistant answer, evaluation result or score.']}
path=OUT/'PROTECTED_USER_VS_REAL_NATIVE_PREFIXES02.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pin':pin(path),'targets':len(rows),'matching_targets':sum(bool(r['matches']) for r in rows),
 'matches':[{'lane':r['lane'],'owner':r['original_owner_id'],'sources':r['source_ids'],'native_match_indices':sorted({m['native_message_index'] for m in r['matches']}),'protected_sources':sorted({m['protected_original_user_origin']['protected_source_id'] for m in r['matches']})} for r in rows if r['matches']],
 'unlinked_staging':[x['staging_id'] for x in links if x['unlinked_requires_producer_resource_proof']]},ensure_ascii=False))
