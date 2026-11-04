"""Root-reviewed original read/ls decisions with original compatible R.

Keeps complete system/history and only declares the existing core7 catalog view.
Later observations are grading metadata; never appended to earlier prompts.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation10'
DATA=ROOT/'output/20261027_wrd_main_v10';OUT=WORK/'early_reads'
CORE={'ls','read','write','edit','apply_patch','exec','process'}
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 assert not (OUT/'CANDIDATES.raw.jsonl.gz').exists()
 path=WORK/'reasoning_native10/EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz'
 raw=list(rows(path));assert len(raw)==15
 scopes={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 newreserved=load(WORK/'parent_inputs/reservation.json')
 assert 'conv_34b56ae9c535' in json.dumps(newreserved)
 main=load(DATA/'TRAINING_MANIFEST.json');known_calls=set();known_ids=set()
 for ref in main['actual_train_files']:
  assert pin(DATA/ref['path'])['sha256']==ref['sha256']
  for r in rows(DATA/ref['path']):
   known_ids.add(r['id'])
   if r['supervised_tokens_by_component'].get('A'):
    for t in r['targets']:
     if any(s[2]=='A'for s in t['owned_supervision_spans']):
      known_calls.update(c['id']for c in r['messages'][t['message_index']].get('tool_calls',[]))
 out=[];review=[];jobs={}
 for r in raw:
  assert r['event_crosswalk_status']=='EXACT_RID_VISIBLE_OUTPUT_AND_ORIGINAL_RUN_CONDITION'
  assert r['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']is True
  assert r['request_and_response_unrewritten']is True
  assert r['existing_positive_R_approved_unicode_characters']==0
  assert all(scopes[s]['status']=='TRAIN'for s in r['source_ids'])
  assert 'conv_34b56ae9c535'not in r['source_ids']
  reqpin=r['source_compatible_API_request'];assert pin(reqpin['path'])==reqpin
  respin=r['source_compatible_API_response'];assert pin(respin['path'])==respin
  request=load(reqpin['path']);message=deepcopy(r['original_response'])
  assert message.get('reasoning_content','')==r['original_R']
  assert h(r['original_R'].encode())==r['original_R_sha256']
  calls=message['tool_calls'];assert len(calls)==1
  call=calls[0];name=call['function']['name'];args=call['function']['arguments']
  if isinstance(args,str):args=json.loads(args)
  assert name in {'read','ls'}and set(args)<={'path','offset','limit'}
  assert args['path'].startswith('/workspace/inputs/')or args['path']=='/workspace/outputs'
  assert call['id']not in known_calls
  assert len(r['actual_native_tool_feedback'])==1
  feedback=r['actual_native_tool_feedback'][0]
  actual=feedback['message']if 'message'in feedback else feedback
  assert actual.get('isError')is False and actual.get('toolCallId')==call['id']
  messages=deepcopy(request['messages'])+[message];projections=[]
  for i,m in enumerate(messages):
   if isinstance(m.get('content'),list):
    blocks=m['content'];assert all(b.get('type')=='text'and isinstance(b.get('text'),str)for b in blocks)
    m['content']='\n'.join(b['text']for b in blocks)
    projections.append({'message_index':i,'rule':'JOIN_COMPLETE_TEXT_BLOCKS_WITH_NEWLINE','blocks_sha256':h(json.dumps(blocks,ensure_ascii=False,separators=(',',':')).encode())})
  assert {c['function']['name']for m in messages for c in m.get('tool_calls',[])}<=CORE
  stage=r['stage'];jobpath=DATA/'runtime_preflight/episodes'/stage/'job.json';job=load(jobpath)
  if stage not in jobs:
   checks=[]
   for ref in job['resources']:
    pp=pin(ref['path']);assert pp['sha256']==ref['sha256'];checks.append({**pp,'mount':ref['mount']})
   for refname,shaname in [('source_allowlist_receipt','source_allowlist_sha256'),('resource_ancestry_receipt','resource_ancestry_sha256')]:
    pp=pin(job[refname]);assert pp['sha256']==job[shaname];checks.append(pp)
   jobs[stage]={'job':pin(jobpath),'resources_and_ancestry':checks,'bounded_known_input_scope_not_universal_ancestor_proof':True}
  identity='native10-read-'+r['owner_id'];assert identity not in known_ids
  candidate={'id':identity,'owner_id':r['owner_id'],'source_ids':r['source_ids'],
   'source_group_id':'v10_native_group_'+h(json.dumps(sorted(r['source_ids']),ensure_ascii=False,separators=(',',':')).encode())[:20],
   'split':'train','stage':'A'if stage.startswith('A_')else'B','original_stage':stage,'bank':'native_recovered_read_process10',
   'source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,
   'requires_external_root_admission':True,'supervision_message_indices':[len(messages)-1],
   'message_loss_mask':[0]*(len(messages)-1)+[1],'messages':messages,
   'tools':[t for t in request['tools']if t['function']['name']in CORE],
   'approved_components':['R','A'],'loss_multiplier':1.0,'allow_reviewed_completion_prefix':False,
   'tool_schema_provenance':{'path':reqpin['path'],'sha256':reqpin['sha256']},
   'student_view':'DECLARED_CORE7_TOOL_CATALOG_PROJECTION_FULL_SYSTEM_AND_PAST_MESSAGES_RETAINED',
   'complete_text_block_projection':projections,'is_original_native_request_identical':False,
   'actual_native_tool_dispatch':True,'teacher_original_R_supervised':bool(r['original_R']),
   'original_R_provenance':'VERBATIM_CAPTURED_NATIVE_COMPATIBLE_API_REASONING_CONTENT; hidden upstream private CoT not inferred',
   'canonical_response_owner':r['source_compatible_API_response']['sha256'],
   'original_recorded_action_owner':r['owner_id'],'original_native_session_id':r['native_session_id'],
   'original_native_message_index':r['native_message_index'],'evidence':{k:r[k]for k in ['source_native','source_compatible_API_request','source_compatible_API_response','original_receipt_pin','native_message_SHA_sorted']},
   'future_feedback_in_model_input':False,'actual_feedback_for_credit_only':r['actual_native_tool_feedback'],
   'credit':['SOURCE_FAITHFUL_LOCAL_NEXT_INPUT_DISCOVERY','EXACT_OBSERVED_NATIVE_CALL_AND_SUCCESSFUL_READ_ONLY'],
   'local_plan_not_claimed_as_finished_workflow':True,'full_pipeline_or_skill_utility_approved':False,
   'new_authored_R_tokens':0,'model_weights_loaded':False,'training_started':False}
  out.append(candidate)
  review.append({'id':identity,'owner':r['owner_id'],'R_text':r['original_R'],'R_characters':len(r['original_R']),
   'call':{'name':name,'arguments':args,'original_id':call['id']},'decision':'ADMIT_LOCAL_R_AND_ACTUAL_READ_LS_ONLY',
   'rationale':'The R is a local plan or task restatement, not a success/quality claim. Input path is explicitly commissioned/provided; actual same-call feedback confirms readable input. Prior source-only and synthetic counterexample origins remain declared. No generated file content, later correctness/KEEP, or whole-pipeline credit inferred.',
   'source_job':pin(jobpath),'actual_feedback_not_in_prompt':True})
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/'CANDIDATES.raw.jsonl.gz').open('wb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0)as g:
   for r in out:g.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 save(OUT/'ROOT_SEMANTIC_READ_REVIEW.json',{'status':'ADMIT_ROOT_REVIEWED_ORIGINAL_LOCAL_R_ACTUAL_INPUT_READS_ONLY',
   'rows':review,'input_packets':pin(path),'source_jobs':jobs,'original226_not_used':True,
   'whole_NATIVE_A_D_or_KEEP':False,'new_business_calls':0,'training_started':False,'script':pin(__file__)})
 print(json.dumps({'new_candidates':len(out),'original_compatible_R_characters':sum(len(r['R_text'])for r in review),
    'local_R_A_pairs':sum(bool(r['R_text'])for r in review),'new_independent_sources':0,'main_not_yet_modified':True}))
if __name__=='__main__':main()
