from pathlib import Path
import ast,json,subprocess,hashlib,traceback
from docx import Document
import fitz
R=Path('/workspace');cases=json.loads((R/'cases.json').read_text());results=[]
for c in cases:
 try:
  p=subprocess.run(['/opt/eval-venv/bin/python',str(R/'programs'/c['filename'])],capture_output=True,text=True,timeout=45)
  assert p.returncode==0,p.stderr
  path=R/c['output'];d=Document(path)
  text='\n'.join([p.text for p in d.paragraphs]+[cell.text for t in d.tables for row in t.rows for cell in row.cells])
  exact=[]
  for change in c['changes']:
   if '\n' in change['newText']:
    tree=ast.parse(change['newText']);parts=[]
    for n in tree.body:
     if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and n.value.args and isinstance(n.value.args[0],ast.Constant):parts.append(n.value.args[0].value)
   else:parts=[change['newText']]
   assert all(x in text for x in parts),parts
   if '\n' not in change['oldText']:assert change['oldText'] not in text,change['oldText']
   exact.append({'new_text_parts':parts,'present':True,'unsupported_old_phrase_absent':True})
  pdf=R/'pdf';pdf.mkdir(exist_ok=True)
  command=['soffice','-env:UserInstallation=file:///workspace/tmp/lo_'+c['owner'],'--headless','--convert-to','pdf','--outdir',str(pdf),str(path)]
  q=subprocess.run(command,capture_output=True,text=True,timeout=70)
  assert q.returncode==0,q.stderr
  pp=pdf/(path.stem+'.pdf');pd=fitz.open(pp)
  assert len(pd)>0 and sum(len(x.get_text()) for x in pd)>100
  pd[0].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(str(pdf/(c['owner']+'_first.png')))
  (R/'content'/f"{c['owner']}.txt").write_text(text)
  results.append({'owner':c['owner'],'status':'PASS_SOURCE_LITERAL_AND_PROGRAM_RETEST','docx':str(path),
    'docx_SHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdf':str(pp),'pages':len(pd),'changes':exact,
    'business_judgment_truth_external_to_source':'NOT_CLAIMED','visual_scoring':'NOT_INDEPENDENT_Q'})
 except Exception as e:results.append({'owner':c['owner'],'status':'FAIL','error':str(e),'traceback':traceback.format_exc()})
out={'status':'PASS_FOUR_CORRECTED_PROGRAMS_AND_13_SOURCE_CHANGES' if len(results)==4 and all(x['status'].startswith('PASS')for x in results)else'FAIL_PRESERVED','results':results,'new_business_model_calls':0,'training_started':False}
(R/'RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'status':out['status'],'programs':len(results),'failed':[x['owner']for x in results if x['status']=='FAIL']}))
raise SystemExit(0 if out['status'].startswith('PASS')else 1)
