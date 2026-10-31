"""Read only path/call/byte identity. Never print resource, thought or Q text."""
from pathlib import Path
import json,re,hashlib,gzip
ROOT=Path('D:/skillloop');OUT=Path(__file__).parent
def h(b):return hashlib.sha256(b if isinstance(b,bytes)else b.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8-sig')if l.strip()]
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def main():
 path=ROOT/'output/20261031_wrd_curation09/process/packets/0f1603b601613eac2fecb014.json';q=load(path);ctx=q['original_context'];target=q['owner']['source_message_index'];out=[]
 for j,m in enumerate(ctx['messages'][:target+1]):
  blocks=m.get('content',[]);blocks=[{'type':'text','text':blocks}]if isinstance(blocks,str)else blocks;calls=[]
  for c in blocks:
   if c.get('type')=='toolCall':
    a=c.get('arguments',{});cmd=a.get('command','')
    calls.append({'name':c['name'],'id':c['id'],'path':a.get('path'),'command_chars':len(cmd),'command_sha256':h(cmd),
      'resource_path_mentions':sorted(set(re.findall(r'/(?:workspace|opt|tmp)/[^\s"\x27<>;|)]*',cmd))),
      'file_read_shell_keywords':sorted(set(re.findall(r'\b(?:cat|head|tail|sed|read_text|read_bytes|open|cp|readFile|readFileSync)\b',cmd)))})
  text='\n'.join(b.get('text','')for b in blocks if b.get('type')=='text')
  out.append({'message_index':j,'source_event_line':ctx['source_event_lines'][j],'role':m['role'],'calls':calls,
   'tool_call_id':m.get('toolCallId'),'tool_name':m.get('toolName'),'isError':m.get('isError'),
   'text_characters':len(text),'text_sha256':h(text),'skill_md_literal_present':bool(re.search(r'SKILL\.md',text))})
 d=ROOT/'output/20261030_wrd_gap08/lineage';edges=rows(d/'SAME_VERSION_TRIAL_AND_REVIEW_EDGES.audit.jsonl.gz')
 edge=next(e for e in edges if e['actor_episode_id']==ctx['episode_id']);packages=rows(d/'FROZEN_COMPLETE_PACKAGE_VERSIONS.jsonl.gz')
 pkg=next(p for p in packages if p['episode_id']==edge['producer_episode_ids'][0]);eps=load(d/'EPISODE_RECOVERY_46.json')['episodes'];ep=next(e for e in eps if e['episode_id']==pkg['episode_id'])
 delivered=[(j,'\n'.join(b.get('text','')for b in (m.get('content',[])if isinstance(m.get('content',[]),list)else [{'type':'text','text':m.get('content','')}])if b.get('type')=='text'))for j,m in enumerate(ctx['messages'][:target+1])if m.get('role')in ('user','toolResult','system')]
 exact_file_delivery=[]
 for f in pkg['files']:
  fp=Path(f['physical_frozen_CAS_path']); raw=fp.read_bytes(); txt=raw.decode('utf-8-sig')
  exact_file_delivery.append({'relative_path':f['relative_path'],'file_sha256_declared':f['sha256'],'file_sha256_actual':h(raw),
   'bytes':len(raw),'exact_full_text_in_recorded_model_input_message_indices':[j for j,t in delivered if txt and txt in t],
   'exact_normalized_lines_full_text_in_recorded_model_input_message_indices':[j for j,t in delivered if txt and txt.replace('\r\n','\n').strip() in t.replace('\r\n','\n')]})
 result={'status':'METADATA_PATH_CALL_AND_BYTE_IDENTITY_ONLY_NOT_SEMANTIC_OR_TRAINING_ADMISSION','current_owner_id':q['owner']['owner_id'],
  'current_view_id':'process09-0f1603b601613eac2fecb014','current_positive_A_tokens':9905,'actor_episode_id':ctx['episode_id'],'target_index':target,
  'original_native_pin':ctx['source_native'],'packet_pin':pin(path),'prefix_messages_metadata':out,
  'original_system_capture_status':ctx['system_capture_status'],'captured_system_message_count':len(ctx['system_messages_original']),
  'same_episode_API_capture_count':ctx['same_episode_API_capture_count'],'api_request_captures_metadata':ctx['api_request_captures'],
  'edge_metadata':{k:edge[k]for k in ['edge_id','actor_episode_id','producer_episode_ids','reviewer_episode_id','tree_content_sha256','candidate_tree_matches_consumed_complete_tree']},
  'actual_full_SKILL_delivery_record_count':len(edge['actual_full_SKILL_delivery']),
  'producer_metadata':{k:ep[k]for k in ['episode_id','route_id','strict_protected_boundary','method_only_candidate_boundary','missing_original_system','training_admitted']},
  'package_metadata':{k:pkg[k]for k in ['episode_id','tree_content_sha256','file_count','files','output_skill_root_physical_path']},
  'package_files_exact_full_text_delivery_checks':exact_file_delivery,
  'no_historical_review_or_grade_fields_used':True,'same_episode_or_disk_tree_identity_not_model_delivery_proof':True,'main_modified':False,'training_started':False}
 p=OUT/'SLIDE_CURRENT_VIEW_RESOURCE_LINEAGE_METADATA.json';p.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'prefix':out,'system':result['original_system_capture_status'],'system_count':result['captured_system_message_count'],
  'api_capture_count':result['same_episode_API_capture_count'],'api_request_capture_keys':[list(x)for x in result['api_request_captures_metadata']],
  'package_file_count':pkg['file_count'],'package_file_entry_keys':list(pkg['files'][0]),'output_pin':pin(p)},ensure_ascii=False))
if __name__=='__main__':main()
