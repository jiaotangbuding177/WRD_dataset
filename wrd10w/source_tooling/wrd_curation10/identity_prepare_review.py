"""Preserve exact recovered clean-named supplemental targets for root review.

No target is admitted; unknown resource ancestry remains explicit. Future
feedback is stored only in grading packets and is not made a prior input.
"""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,json

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity'
p=ROOT/'research/data_prep/wrd_curation10/identity_recover.py'
s=importlib.util.spec_from_file_location('identity10',p);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)

def main():
 owners=[r for r in a.rows(OUT/'OWNER7357_IDENTITY_FIRST_PASS.metadata.jsonl.gz')
   if r['09_effective_queue']in {'unreviewed_supplemental_prefix','lineage8_specific_missing_evidence'}
   and r['identity10_disposition']=='IDENTITY_RECOVERED_TRAIN_NAMED_SOURCES_ANCESTRY_CONTENT_STILL_REQUIRED']
 byep=defaultdict(list)
 for r in owners:byep[r['episode_id']].append(r)
 contexts={}
 for n in ['audit_inputs/native1843.contexts.original.jsonl.gz','EXTRA_NATIVE_CONTEXTS.original.jsonl.gz']:
  for c in a.rows(a.CORPUS/n):
   if c['episode_id']in byep:contexts[c['episode_id']]=c
 em={e['episode_id']:e for e in a.load(OUT/'EPISODE_IDENTITY_RECOVERED.metadata.json')['episodes']}
 bindings=a.load(ROOT/'output/20261021_workflow_skill_library/source_bindings.json')
 index=[]
 for eid,c in sorted(contexts.items()):
  base=OUT/'content_review'/eid
  base.mkdir(parents=True,exist_ok=True)
  assert not (base/'TARGETS.with_original_feedback.audit.jsonl.gz').exists()
  a.gz(base/'CONTEXT.original.audit.jsonl.gz',[c]);native=a.preserve(c['source_native'])
  ts=[]
  for r in byep[eid]:
   i=r['source_message_index'];m=c['messages'][i];ca=a.calls(m);callids={x.get('id')for x in ca};feedback=[]
   for j,z in enumerate(c['messages'][i+1:],i+1):
    if z.get('role')=='assistant':break
    if z.get('role')=='toolResult'and z.get('toolCallId')in callids:
     feedback.append({'message_index':j,'event_line':c.get('source_event_lines',[None]*len(c['messages']))[j],
       'message':z,'message_sha256_sorted':a.h(a.js(z,True))})
   components=Counter(b.get('type')for b in a.blocks(m)if isinstance(b,dict))
   writechars=sum(len(a.args(x).get('content',''))for x in ca if isinstance(a.args(x).get('content'),str))
   commandchars=sum(len(a.args(x).get('command',''))for x in ca if isinstance(a.args(x).get('command'),str))
   ts.append({'owner_id':r['canonical_owner_id'],'source_message_index':i,'original_target_message':m,
     'original_target_sha256_sorted':r['identity10_original_target_sha256_sorted'],'actual_tool_names':[x.get('name')for x in ca],
     'immediate_actual_tool_feedback':feedback,'original_component_types':dict(components),
     'write_content_characters':writechars,'command_characters':commandchars,'source_ids':r['identity10_source_ids'],
     'source_statuses':r['identity10_source_statuses'],'state_before_target_end_exclusive':i,
     'actual_prior_named_source_read_receipts':r['identity10_observed_read_receipts_before_target'],
     'future_observations_for_grading_only_not_input':True,'training_admitted':False,'positive_loss':0,
     'complete_prefix_ancestry_and_semantic_approval_required':True})
  a.gz(base/'TARGETS.with_original_feedback.audit.jsonl.gz',ts)
  sources=sorted(set(s for r in byep[eid]for s in r['identity10_source_ids']))
  preserved=[]
  for sid in sources:
   if sid in bindings:preserved.append({'source_id':sid,**a.preserve(bindings[sid]['conversation'])})
  a.save(base/'SCOPE_AND_ACTUAL_RESOURCES.json',{'episode_metadata':em[eid],
    'source_named_scope_only_not_whole_prefix_clearance':True,'native_entity':native,
    'actual_source_conversation_entities':preserved,'source_ids':sources,
    'known_source_entity_identity_is_not_native_historical_order_certification':True,
    'same_response_API_capture_count':c.get('same_episode_API_capture_count',0),
    'api_request_captures':c.get('api_request_captures',[]),
    'original_native_context_all_fields_preserved':True,'new_admitted_targets':0})
  # Compact readable review includes only originally named TRAIN targets. No
  # local transformation, tool execution or generated reasoning is introduced.
  index.append({'episode_id':eid,'stage':c.get('stage'),'route':c.get('route_id'),'source_ids':sources,
    'targets':len(ts),'write_content_characters':sum(t['write_content_characters']for t in ts),
    'command_characters':sum(t['command_characters']for t in ts),
    'component_types':dict(sum((Counter(t['original_component_types'])for t in ts),Counter())),
    'target_index':a.pin(base/'TARGETS.with_original_feedback.audit.jsonl.gz'),
    'context':a.pin(base/'CONTEXT.original.audit.jsonl.gz'),'source_and_resource_metadata':a.pin(base/'SCOPE_AND_ACTUAL_RESOURCES.json'),
    'status':'EXACT_ORIGINAL_CONTENT_ROOT_ANCESTRY_AND_SEMANTIC_REVIEW_PENDING'})
 a.save(OUT/'CONTENT_REVIEW_INDEX.json',{'episodes':index,'targets':len(owners),'training_admitted':0,'new_business_calls':0,'training_started':False})
 print(a.js({'episodes':len(index),'targets':len(owners),'summary':[{k:v for k,v in x.items()if k not in ['target_index','context','source_and_resource_metadata']}for x in index]}))

if __name__=='__main__':main()
