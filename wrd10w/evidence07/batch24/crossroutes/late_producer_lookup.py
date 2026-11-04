"""Bounded extra native route batches omitted by v9; no old tools executed."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
R=Path('D:/skillloop'); B=Path(__file__).parent.parent;O=B/'late_producer_closure'
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8-sig')))
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def native(p):
 z=[]
 for ln,line in enumerate(Path(p).read_text(encoding='utf-8-sig').splitlines(),1):
  e=json.loads(line)
  if e.get('type')=='message' and isinstance(e.get('message'),dict):z.append({'event_line':ln,'message':e['message']})
 return z
def text(m):
 c=m.get('content',[]);return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def calls(m):return [x for x in m.get('content',[]) if isinstance(x,dict) and x.get('type')=='toolCall'] if isinstance(m.get('content'),list) else []
def args(c):a=c.get('arguments',{});return json.loads(a) if isinstance(a,str) else a
def walk(v,path='$'):
 if isinstance(v,dict):
  if isinstance(v.get('id'),str):yield path,v
  for k,x in v.items():yield from walk(x,path+'.'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from walk(x,path+'['+str(i)+']')
def strs(v,path='$'):
 if isinstance(v,str):yield path,v
 elif isinstance(v,dict):
  for k,x in v.items():yield from strs(x,path+'.'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from strs(x,path+'['+str(i)+']')
def save(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 O.mkdir(exist_ok=True);(O/'objects').mkdir(exist_ok=True)
 scopefile=R/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz';scope={x['source_id']:x for x in rows(scopefile)}
 historical_scope=R/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'
 historical_labels=rows(historical_scope)
 fixed226={s for x in historical_labels for s in x['original226']}; h12={s for x in historical_labels for s in x['holdout12']}
 assert len(fixed226)==226 and len(h12)==12
 previous=load(B/'remaining76/ROUTE_PRODUCER_CLOSURE.json')['episodes']; ts=rows(B/'remaining76/TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz')
 pending=[x for x in ts if x['current_decision']=='HOLD_ANCESTRY_NOT_CLOSED'];assert len(pending)==249
 wanted={x['route_id'] for x in pending}; catalog=[];carriers=[];batches=[]
 def copy(p):
  p=Path(p);b=p.read_bytes();s=h(b);q=O/'objects'/s
  if not q.exists():q.write_bytes(b)
  d={'original':pin(p),'copied':pin(q)};carriers.append(d);return d
 roots=[Path('E:/skillloop_runs/20261021_workflow_library_parallel4/native_episodes'),Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes')]
 for root in roots:
  for base in sorted(root.glob('route_batch_*')):
   nf=base/'openclaw_transport/session_events.jsonl';pf=base/'workspace/inputs/compact_proposals.json'
   if not nf.exists() or not pf.exists():continue
   ms=native(nf);source=load(pf);input_receipts=[]
   for i,z in enumerate(ms):
    for c in calls(z['message']):
     if c.get('name')!='read' or args(c).get('path')!='/workspace/inputs/compact_proposals.json':continue
     ack=next(((j,q) for j,q in enumerate(ms[i+1:],i+1) if q['message'].get('toolCallId')==c['id']),None)
     if not ack:continue
     obs=text(ack[1]['message'])
     try:observed=json.loads(obs)
     except ValueError:continue
     if observed!=source:continue
     ids=sorted({p['source_id'] for x in source.get('proposals',[]) for p in x.get('previews',[])})
     statuses={s:'ORIGINAL226_PROTECTED' if s in fixed226 else 'H12_PROTECTED' if s in h12 else scope.get(s,{}).get('status','MISSING_CURRENT_SCOPE') for s in ids}
     protected=[s for s,v in statuses.items() if v.startswith('HOLD_') or v in ['ORIGINAL226_PROTECTED','H12_PROTECTED']]
     input_receipts.append({'read_message_index':i,'read_event_line':z['event_line'],'observation_message_index':ack[0],
      'observation_event_line':ack[1]['event_line'],'tool_call_id':c['id'],'observation_sha256':h(obs.encode()),
      'original_file_CRLF_to_LF_outer_trim_equal':pf.read_text(encoding='utf-8-sig').strip()==obs.strip(),
      'actual_observed_JSON_value_exact_equal_to_input':True,'actually_received_source_ids':ids,'source_statuses':statuses,'protected_or_static_sources':protected})
   cards=[]
   for i,z in enumerate(ms):
    for c in calls(z['message']):
     a=args(c)
     if c.get('name')!='write' or not isinstance(a.get('content'),str):continue
     try:obj=json.loads(a['content'])
     except ValueError:continue
     ack=next(((j,q) for j,q in enumerate(ms[i+1:],i+1) if q['message'].get('toolCallId')==c['id']),None)
     if not ack or ack[1]['message'].get('isError') is not False:continue
     for path,card in walk(obj):
      if card['id'] not in wanted:continue
      known=[r for r in input_receipts if r['observation_message_index']<i and r['protected_or_static_sources']]
      d={'producer_native':pin(nf),'producer_is_omitted_from_prior_v9_episode_table':True,'input_file':pin(pf),'actual_input_receipts_before_write':input_receipts,
       'write_message_index':i,'write_event_line':z['event_line'],'write_call_id':c['id'],'write_path':a.get('path'),
       'whole_write_content_sha256':h(a['content'].encode()),'ack_message_index':ack[0],'ack_event_line':ack[1]['event_line'],'ack_sha256':h(can(ack[1]['message'])),
       'card_id':card['id'],'card_json_pointer':path,'card_canonical_sha256':h(can(card)),'proven_protected_before_write':bool(known),
       'first_protected_input_observation_index':min((r['observation_message_index'] for r in known),default=None)}
      catalog.append((d,card));cards.append(d)
   batches.append({'native':pin(nf),'input':pin(pf),'actual_input_receipts':input_receipts,'matched_unclosed_route_cards':cards,
    'script_created_JSON_not_automatically_assumed_proven':any(c.get('name')=='write' and str(args(c).get('path','')).endswith('.py') for z in ms for c in calls(z['message']))})
   if cards:copy(nf);copy(pf)
 links=[];overlay=[]
 for ep in previous:
  local=[x for x in pending if x['episode_id']==ep['episode_id']]
  if not local:continue
  ms=native(ep['native']['path']);possible=[]
  for inputref in ep['route_links']:
   p=Path(inputref['input_carrier']['original']['path']);v=load(p)
   for producer,card in catalog:
    if v.get('id')!=card.get('id'):continue
    # A copied pair of complete nontrivial core objects suffices to prove a
    # dependency. Other normalized fields do not need to be treated as equal.
    fields=[k for k in ['value_plan','route_signature'] if v.get(k)==card.get(k) and isinstance(card.get(k),dict)]
    if len(fields)!=2:continue
    visible=[]
    for obs in inputref['actual_receipts']:
     om=ms[obs['observation_message_index']]['message'];s=text(om).replace('\r\n','\n');rs=[]
     for field in fields:
      for path,value in strs(card[field],'$.'+field):
       if len(value)<32:continue
       quoted=json.dumps(value,ensure_ascii=False);start=s.find(quoted)
       if start>=0:rs.append({'original_field_path':path,'value_sha256':h(value.encode()),'quoted_sha256':h(quoted.encode()),
         'normalized_observation_start':start,'normalized_observation_end':start+len(quoted),'quoted_chars':len(quoted)})
     full=p.read_text(encoding='utf-8-sig').strip() in s
     if rs or full:visible.append({'observation_message_index':obs['observation_message_index'],'observation_text_sha256':h(text(om).encode()),
       'entire_normalized_input_received':full,'original_scalar_receipts':rs,'tool_call_id':obs['tool_call_id']})
    if not visible:continue
    boundary=min(x['observation_message_index'] for x in visible)
    link={'episode_id':ep['episode_id'],'route_id':ep['route_id'],'input_file':pin(p),'exact_original_core_fields':fields,
      'original_field_sha256':{k:h(can(card[k])) for k in fields},'producer':producer,'actual_downstream_receipts':visible,
      'protected_exposure_boundary':boundary if producer['proven_protected_before_write'] else None,
      'no_semantic_gold_or_positive_loss_claimed':True}
    # Also preserve adjacent existing normalization objects without claiming
    # their success status as semantic quality.
    adj=[]
    for q in (R/'output/20261021_pipeline_infra_audit/route_recovery').glob('batch_*/card_*/raw_card.json'):
     raw=load(q)
     if raw.get('id')==card['id'] and raw==card:
      adj.extend(copy(f) for f in q.parent.glob('*.json'))
    link['adjacent_raw_derived_audit_copies']=adj;links.append(link);possible.append(link);copy(p)
  boundary=min((x['protected_exposure_boundary'] for x in possible if x['protected_exposure_boundary'] is not None),default=None)
  for t in local:
   if boundary is not None and t['source_message_index']>boundary:
    overlay.append({'id':t['id'],'episode_id':t['episode_id'],'source_message_index':t['source_message_index'],'old_decision':'HOLD_ANCESTRY_NOT_CLOSED',
      'new_decision':'HOLD_PROTECTED_ACTUAL_LATE_ROUTE_PRODUCER','protected_input_observation_index':boundary,'positive_loss':0})
 ids={x['id'] for x in overlay};assert len(ids)==len(overlay) and ids<={x['id'] for x in pending}
 save('LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json',{'status':'ACTUAL_ADDITIONAL_PRODUCER_LOOKUP_OVERLAY_ORIGINAL_76_SEALED_FILES_UNCHANGED',
  'fixed_search_roots':[str(x) for x in roots],'source_scope':pin(scopefile),'fixed226_H12_scope_source':pin(historical_scope),
  'fixed226_metadata_union_size':len(fixed226),'H12_metadata_union_size':len(h12),'batches_checked':batches,'links':links,
  'target_overlays':overlay,'old_pending':249,'newly_proven_protected':len(overlay),'remaining_unknown':249-len(overlay),
  'clean_original_producers_found':[p for p,c in catalog if not p['proven_protected_before_write']],
  'actual_source_carriers':carriers,'no_new_training_admissions':True,'no_original76_file_modified':True,
  'protected_source_content_not_used_for_semantic_labels':True,'no_old_commands_executed':True,'no_native_or_training':True,'script':pin(__file__)})
 print(json.dumps({'batches_checked':len(batches),'matched_route_cards':len(catalog),'actual_consumer_links':len(links),'newly_protected':len(overlay),'remaining_unknown':249-len(overlay)}))
if __name__=='__main__':main()
