"""Correct projected edit ABI against the cited actual native schema.

Preserve failed v1 candidates. Original replacement strings/versions do not
change; only the explicitly new projected call envelope changes.
"""
from pathlib import Path
from copy import deepcopy
import gzip,hashlib,json
from jsonschema import Draft202012Validator

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity_semantic'
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}

def main():
 src=OUT/'CANDIDATES.raw.jsonl.gz';dst=OUT/'CANDIDATES_TOOL_ABI_V2.raw.jsonl.gz'
 assert not dst.exists(),'PRESERVE_PREVIOUS_V2'
 before_pin=pin(src)
 original=[json.loads(l)for l in gzip.open(src,'rt',encoding='utf-8')if l.strip()]
 assert len(original)==3
 revised=deepcopy(original);checks=[]
 for prior,r in zip(original,revised):
  if 'A'not in r['approved_components']:continue
  message=r['messages'][r['supervision_message_indices'][0]]
  old_calls=message['tool_calls'];schema=next(t['function']['parameters']for t in r['tools']if t['function']['name']=='edit')
  assert schema['required']==['path','edits']
  validator=Draft202012Validator(schema)
  old_validation_errors=sum(1 for c in old_calls for _ in validator.iter_errors(c['function']['arguments']))
  assert old_validation_errors>0,'V1_REJECTION_MUST_BE_REPRODUCIBLE'
  path={c['function']['arguments']['path']for c in old_calls};assert len(path)==1
  replacements=[{'oldText':c['function']['arguments']['oldText'],'newText':c['function']['arguments']['newText']}for c in old_calls]
  payload={'path':next(iter(path)),'edits':replacements};validator.validate(payload)
  message['tool_calls']=[{'id':'call-'+r['id']+'-abi2','type':'function','function':{'name':'edit','arguments':payload}}]
  version_name='verifier_before_path_fix.py'if r['id']=='identity10-verifier-path-repair'else'verifier_after_path_fix.py'
  before=(OUT/version_name).read_text(encoding='utf-8')
  positions=[]
  for pair in replacements:
   assert before.count(pair['oldText'])==1
   start=before.index(pair['oldText']);positions.append((start,start+len(pair['oldText']),pair))
  positions.sort();assert all(x[1]<=y[0]for x,y in zip(positions,positions[1:])), 'ACTUAL_TOOL_REQUIRES_ORIGINAL_NONOVERLAPPING_EDITS'
  after=before
  for start,end,pair in reversed(positions):after=after[:start]+pair['newText']+after[end:]
  assert h(before)==r['version_before_sha256']and h(after)==r['version_after_sha256']
  if r['id']=='identity10-verifier-stderr-repair':
   assert after.encode()==(OUT/'verifier_after_stderr_fix.py').read_bytes()
  r['tool_ABI_projection_revision']=2
  r['tool_ABI_v1_failure_preserved']={'candidate_file':before_pin,'status':'REJECTED_TOOL_ARGUMENT_SCHEMA_INVALID_NOT_TRAINABLE'}
  r['projected_target_call_envelope']='ACTUAL_CAPTURED_edit(path, edits=[{oldText,newText},...])'
  checks.append({'id':r['id'],'v1_schema_errors':old_validation_errors,'v2_schema_validation':'PASS',
    'v1_call_count':len(old_calls),'v2_call_count':1,'literal_replacement_pairs':len(replacements),
    'literal_replacement_pairs_sha256_before':h(js([{'oldText':c['function']['arguments']['oldText'],
      'newText':c['function']['arguments']['newText']}for c in prior['messages'][2]['tool_calls']])),
    'literal_replacement_pairs_sha256_after':h(js(replacements)),
    'actual_schema_sha256':h(js(schema)),
    'oldText_unique_and_edits_nonoverlapping_against_original':True,
    'version_before_sha256':h(before),'version_after_sha256':h(after),
    'new_projection_not_original_dispatch':True,'compiled_this_helper':False})
 with dst.open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for r in revised:f.write((js(r)+'\n').encode())
 assert pin(src)==before_pin,'V1_MUST_REMAIN_UNCHANGED'
 assert original[2]==revised[2],'RECORDED_HOLD_CANDIDATE_NOT_CHANGED'
 qa={'status':'PASS_V2_ACTUAL_CAPTURED_TOOL_SCHEMA_AND_UNCHANGED_LITERAL_CODE_NOT_COMPILED',
   'source_v1_rejected_A_preserved':before_pin,'corrected_v2':pin(dst),'rows':checks,
   'original_tool_schema_provenance':original[0]['tool_schema_provenance'],
   'tool_schema_provenance_actual_file_verified':pin(original[0]['tool_schema_provenance']['path'])['sha256']==original[0]['tool_schema_provenance']['sha256'],
   'HOLD_unchanged':True,'compiled_targets_reported_by_this_helper':0,'new_business_calls':0,'training_started':False,
   'script_pin':pin(__file__)}
 assert all(r['literal_replacement_pairs_sha256_before']==r['literal_replacement_pairs_sha256_after']for r in checks)
 (OUT/'TOOL_ABI_V2_FIX_REVIEW.json').write_bytes((json.dumps(qa,ensure_ascii=False,indent=2)+'\n').encode())
 print(js({'status':qa['status'],'v2':qa['corrected_v2'],'corrected_A_candidates':len(checks),'unchanged_D_candidates':1,'compiled_by_helper':0}))

if __name__=='__main__':main()
