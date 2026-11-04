"""Bind original historical R to original proposals and actual old feedback.

All links are audit/context, not permission to teach the old executor ABI.
Post-target feedback is kept outside target input. No captured code is run.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/20261031_wrd_curation10/reasoning'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 inv=load(OUT/'INVENTORY.json');edges=[];episodes={}
 for meta in inv['rows']:
  owner=meta['owner_id'];folder=OUT/'owners'/owner;r=load(folder/'ORIGINAL_RECORD.json')
  request=r['original_request'];assert request['messages'][-1]['role']=='user';u=json.loads(request['messages'][-1]['content'])
  proposal=r['observed_parsed_output'];episode=Path(meta['source_request']['path']).parents[2]
  eventpath=episode/'events.jsonl';transcript=episode/'decision_transcript.json'
  events=[json.loads(l)for l in eventpath.read_text(encoding='utf-8-sig').splitlines()if l.strip()]
  exact=[e for e in events if e.get('action_id')==proposal['action_id']]
  assert len(exact)==1
  event=exact[0];parsed=Path(r['source_parsed']['path']);assert pin(parsed)['sha256']==r['source_parsed']['sha256']
  recordedparsed=load(parsed);assert recordedparsed==proposal
  original_request_path=Path(meta['source_request']['path']);assert pin(original_request_path)['sha256']==meta['source_request']['sha256']
  assert load(original_request_path)==request
  proposalpath=Path(event['proposal_ref']);assert pin(proposalpath)['sha256']==event['proposal_sha256']
  assert load(proposalpath)==proposal
  source=u['complete_source'];assert source['source_id']==meta['source_id']
  captured_state=u['state'];args=proposal.get('arguments',{})
  code=args.get('code');versions=[]
  epkey=source['source_id']
  if epkey not in episodes:
   bundle={'source_id':epkey,'condition':'HISTORICAL_CUSTOM_EXECUTOR_NOT_NATIVE_OPENCLAW',
     'events':events,'events_pin':pin(eventpath),'transcript_pin':pin(transcript),
     'original_complete_source':source,'original_complete_source_declared_sha256':u.get('original_complete_source_sha256'),
     'source_includes_synthetic_inputs_if_marked':True,'no_new_agent_or_tool_execution':True}
   dump(OUT/'episodes'/epkey/'AUDIT_ORIGINALS.json',bundle);episodes[epkey]=bundle
  field={'schema':'wrd-historical-R-action-feedback-causal-edge10-v1','owner_id':owner,'source_id':epkey,
    'decision':meta['decision'],'source_condition':'HISTORICAL_CUSTOM_EXECUTOR_NOT_NATIVE_OPENCLAW',
    'request_pin':meta['source_request'],'response_pin':meta['source_response'],
    'original_R_pin':meta['original_R'],'original_proposal_pin':pin(proposalpath),
    'original_proposal':proposal,'target_time_state':captured_state,
    'observed_post_target_event':event,'post_target_event_not_added_to_target_input':True,
    'event_pin':pin(eventpath),'event_match_basis':'exact proposal SHA + parsed JSON equality + unique action ID',
    'request_identity':'exact captured request SHA and decoded JSON equality',
    'original_action_kind':proposal['kind'],'body_code_sha256':sha(code.encode())if code else None,
    'evidence_credit':{'SOURCE_FAITHFUL':'REQUIRES_CLAIM_SPECIFIC_REVIEW','LOCAL_EXECUTABLE':'NOT_INFERRED_FROM_APPLIED',
      'CASE_VERIFIED':'NOT_PROVEN_BY_STRUCTURE','UTILITY_SUPPORTED':False,'native_dispatch':False},
    'current_default_action_loss':0,'new_R_credit_this_join':0,'training_started':False}
  dump(folder/'R_ACTION_FEEDBACK_EDGE.json',field)
  if code:(folder/'ORIGINAL_PROPOSED_CODE.py').write_bytes(code.encode())
  edges.append({'owner_id':owner,'source_id':epkey,'kind':proposal['kind'],'observed_status':event.get('status'),
    'code_chars':len(code or ''),'code_sha256':field['body_code_sha256'],'edge_pin':pin(folder/'R_ACTION_FEEDBACK_EDGE.json'),
    'feedback_fields':list(event.get('transition',{})),'asof_recent_interactions':len(u.get('recent_interactions',[])),
    'asof_materials':[{'name':a.get('name'),'sha256':a.get('sha256_actual')or a.get('sha256'),
      'material_identity':a.get('material_identity'),'historical_byte_identity_verified':a.get('historical_byte_identity_verified')}
      for a in captured_state.get('input_assets',[])]})
 report={'status':'PASS_EXACT_CAPTURED_REQUEST_PROPOSAL_AND_ACTUAL_HISTORICAL_EVENT_LINK_NOT_ACTION_CREDIT',
   'owner_count':len(edges),'source_count':len(episodes),'by_kind':dict(Counter(r['kind']for r in edges)),
   'by_observed_status':dict(Counter(r['observed_status']for r in edges)),'edges':edges,
   'full_native_autonomy':0,'qualified_KEEP':0,'new_train_targets':0,'new_business_calls':0,'training_started':False,
   'script_pin':pin(__file__)}
 dump(OUT/'CAUSAL_EDGE_REPORT.json',report)
 print(json.dumps({k:v for k,v in report.items()if k not in ['edges','script_pin']}))
if __name__=='__main__':main()
