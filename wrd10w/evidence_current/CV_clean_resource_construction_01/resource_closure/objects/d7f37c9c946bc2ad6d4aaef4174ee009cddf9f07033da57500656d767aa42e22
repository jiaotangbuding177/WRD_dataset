from pathlib import Path
import json,re,subprocess,sys
S=Path('/workspace/outputs/skill/scripts')
F=Path('/workspace/independent_fixtures')
T=Path('/workspace/extra_type_checks')
out=Path('/workspace/outputs/independent_retest');out.mkdir(parents=True,exist_ok=True)
rows=[]
def run(label,*args):
 r=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)
 row={'label':label,'argv':[sys.executable,*map(str,args)],'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr};rows.append(row)
 try:o=json.loads(r.stdout)
 except ValueError:o=None
 return r,o,row
def mark(row,ok,expected):row.update(pass_=bool(ok),expected=expected)
# Read only diagnostic fields, bound to the same claim. Echoed file/quote/value
# fields are deliberately excluded. This accepts the original claims report or
# nested structured errors without requiring one replacement output schema.
def claim_index(node,inherited=None):
 for key in ('index','claim_index','item_index'):
  value=node.get(key)
  if type(value) is int:return value
 path=node.get('path',node.get('instance_path',node.get('loc')))
 if isinstance(path,list):
  for value in path:
   if type(value) is int:return value
 if isinstance(path,str):
  match=re.search(r'(?:claims?\s*)?(?:\[|/|\.)(\d+)(?:\]|/|\.|$)',path)
  if match:return int(match.group(1))
 return inherited
def diagnostics(report):
 found=[]
 def visit(node,idx=None):
  if isinstance(node,list):
   for child in node:visit(child,idx)
  elif isinstance(node,dict):
   idx=claim_index(node,idx)
   words=[]
   for key in ('reason','error','message','detail','code','type'):
    value=node.get(key)
    if isinstance(value,str):words.append(value)
   # A field/path can identify a diagnostic, but cannot itself prove a type
   # error; no words are taken from the echoed input file or quote.
   locations=[]
   for key in ('field','path','instance_path','loc'):
    value=node.get(key)
    if isinstance(value,(str,list)):locations.append(str(value))
   if words:found.append((idx,' '.join(locations).lower(),' '.join(words).lower()))
   for key in ('claims','errors','diagnostics','results','error','details'):
    value=node.get(key)
    if isinstance(value,(dict,list)):visit(value,idx)
 visit(report)
 return found
def typed_diagnostic(report,index,field,kind='type'):
 for idx,location,reason in diagnostics(report):
  if idx!=index:continue
  if field=='claim':
   field_ok=any(x in reason+location for x in ('claim','item','object','mapping','dict','对象'))
   expected=any(x in reason for x in ('object','mapping','dict','对象'))
  else:
   field_ok=field in reason+location
   if field in ('file','quote'):
    expected=any(x in reason for x in ('string','str type','字符串'))
   elif kind=='range':
    expected=any(x in reason for x in ('positive','range','greater than 0','greater than zero','>= 1','>=1','> 0','>0','正整数','大于0','大于 0','范围'))
   else:
    expected=any(x in reason for x in ('integer','int type','整数'))
  if field_ok and expected:return True
 return False
def rejected(r,o,index,field,kind='type'):
 return r.returncode==2 and isinstance(o,dict) and o.get('ok') is False and 'Traceback' not in r.stderr and typed_diagnostic(o,index,field,kind)
# Oracle canaries are newly authored tests of this test, not Teacher evidence.
# Index0 has several bad fields: any genuine first diagnostic is sufficient;
# an error belonging to index1 must never supply its missing type proof.
canaries=[
 ('echo_keys_are_not_diagnostics',not typed_diagnostic({'ok':False,'claims':[{'index':0,'file':'file string','quote':'quote string','ok':False,'reason':'not found'}]},0,'file')),
 ('unrelated_claim_type_reason_rejected',not typed_diagnostic({'ok':False,'claims':[{'index':0,'file':42,'quote':None,'reason':'not found'},{'index':1,'reason':'file must be a string'}]},0,'file')),
 ('cross_field_message_rejected',not typed_diagnostic({'ok':False,'errors':[{'index':0,'field':'quote','reason':'must be string'}]},0,'file')),
 ('legacy_reason_supported',typed_diagnostic({'ok':False,'claims':[{'index':0,'ok':False,'reason':'file must be a nonempty string'}]},0,'file')),
 ('structured_path_supported',typed_diagnostic({'ok':False,'errors':[{'path':['claims',0,'page'],'message':'Expected positive integer'}]},0,'page')),
 ('zero_is_range_not_string',not typed_diagnostic({'ok':False,'claims':[{'index':0,'reason':'page must be string'}]},0,'page','range')),
]
rows.append({'label':'ORACLE_CANARIES','new_authored_oracle_self_test':True,'cases':[{'name':n,'pass':bool(v)} for n,v in canaries],'pass_':all(v for _,v in canaries),'expected':'No echoed-field, cross-claim or cross-field credit; accept legacy and explicit nested diagnostics.'})
assert all(v for _,v in canaries),'oracle self-test failed'
r,o,row=run('legitimate_ASCII_source_retained',S/'cv_extract.py',F/'legitimate_long_ascii.pdf','--raw')
mark(row,r.returncode==0 and 'CertifiedKubernetesAdministrator' in json.dumps(o,ensure_ascii=False),'Original literal remains available with page/source provenance; display filtering must not erase it irretrievably.')
r,o,row=run('literal_raw_quote_accepted',S/'evidence_check.py',F/'literal_claim.json')
mark(row,r.returncode==0 and o and o.get('ok') is True,'True raw PDF quote on correct page accepted, regardless of display-watermark heuristics.')
r,o,row=run('image_only_explicit_needs_OCR',S/'cv_extract.py',F/'image_only.pdf')
text=json.dumps(o,ensure_ascii=False).lower()
mark(row,r.returncode==2 and o and any(x in text for x in ['ocr','no text','no_text','unreadable','无文本','不可读']),'Valid image-only file explicitly requires OCR/unusable text; all unusable keeps exit2, no fabricated empty success.')
real='/workspace/inputs/task/materials/e474a80615c085d4.pdf'
r,o,row=run('mixed_good_and_scan_partial',S/'cv_extract.py',real,F/'image_only.pdf')
mark(row,r.returncode==3 and o and any(x.get('sha256','').startswith('e474a806') for x in o.get('results',[])),'Good candidate retained with exact identity, unusable scan explicit, partial exit3.')
fields={'item_integer':'claim','file_integer':'file','file_bool':'file','quote_bool':'quote','quote_none':'quote','page_true':'page','page_float':'page','page_zero':'page'}
for name,field in fields.items():
 r,o,row=run(name,S/'evidence_check.py',T/(name+'.json'))
 mark(row,rejected(r,o,0,field,'range' if name=='page_zero' else 'type'),'This same claim0 has an actual diagnostic for '+field+(' positive/range constraint.' if name=='page_zero' else ' type; echoed fields, other claim errors and file-not-found do not count.'))
r,o,row=run('valid_int_kept',S/'evidence_check.py',T/'valid_int.json')
mark(row,r.returncode==0 and o and o.get('ok') is True,'Original valid Maker quote/page2 remains valid.')
r,o,row=run('page_string',S/'evidence_check.py',F/'page_is_string.json')
mark(row,rejected(r,o,0,'page'),'Numeric string page has a same-claim page/integer diagnostic.')
multi=out/'multiple_wrong_fields.json';multi.write_text(json.dumps([{'file':42,'quote':None,'page':True}]))
r,o,row=run('one_claim_multiple_wrong_fields',S/'evidence_check.py',multi)
mark(row,any(rejected(r,o,0,f) for f in ('file','quote','page')),'At least one real type diagnostic belongs to claim0; a documented first-error short circuit is allowed.')
paired=out/'different_claim_field_errors.json';paired.write_text(json.dumps([{'file':42,'quote':'valid literal','page':1},{'file':real,'quote':None,'page':1}]))
r,o,row=run('different_claim_errors_stay_paired',S/'evidence_check.py',paired)
mark(row,rejected(r,o,0,'file') and rejected(r,o,1,'quote'),'Claim0 file type and claim1 quote type each diagnosed on its own object, never cross-matched.')
report={'new_authored_test_not_original_Teacher':True,'tests':rows,'pass':sum(x['pass_'] for x in rows),'total':len(rows)}
(out/'RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['pass','total']}))
raise SystemExit(0 if report['pass']==report['total'] else 1)
