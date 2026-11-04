"""Run four source-preserving, explicitly new program corrections in fixed97a0."""
from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261030_wrd_gap08/semantic_root/docx_source_corrections'
PEER=ROOT/'output/20261030_wrd_gap08/semantic_peer/SOURCE_GROUNDED_CORRECTION_PROPOSALS.json'
IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

DRIVER=r'''from pathlib import Path
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
raise SystemExit(0 if out['status'].startswith('PASS')else1)
'''

def main():
 OUT.mkdir(parents=True,exist_ok=False);ws=OUT/'workspace'
 for n in ['programs','outputs','tmp','content']:(ws/n).mkdir(parents=True,exist_ok=True)
 proposals=json.loads(PEER.read_bytes());cases=[]
 output_files={
  'befe257a688eb74361966e52':'机械设计工程师岗位JD（完善版）.docx',
  '50a3b236baa2f7324e247fba':'AI产品经理岗位_分析推荐报告.docx',
  'c9753a249f6f08a9c7726efa':'候选人左_终面面试提纲.docx',
  'f78b5c3163c5516f9b7db22a':'EvoMind云服务版使用说明书_企业用户_修订版V2.docx'}
 for p in proposals['programs']:
  original=Path(p['original_program']['path']);fixed=Path(p['proposed_program']['path'])
  assert sha(original)==p['original_program']['sha256'] and sha(fixed)==p['proposed_program']['sha256']
  code=original.read_text(encoding='utf-8')
  for change in p['changes']:
   assert code.count(change['oldText'])==1
   code=code.replace(change['oldText'],change['newText'],1)
  assert code==fixed.read_text(encoding='utf-8')
  name=p['original_owner_id']+'.py';(ws/'programs'/name).write_bytes(code.encode('utf-8'))
  cases.append({'owner':p['original_owner_id'],'filename':name,'output':'outputs/'+output_files[p['original_owner_id']],
                'changes':[{k:x[k]for k in ['oldText','newText']}for x in p['changes']]})
 save(ws/'cases.json',cases);(ws/'qa_driver.py').write_text(DRIVER.replace('else1','else 1'),encoding='utf-8',newline='')
 argv=['docker','run','--rm','--network','none','--memory','6g','--cpus','4','--shm-size','1g',
       '--mount',f'type=bind,source={ws.resolve()},target=/workspace','--workdir','/workspace',
       '--entrypoint','/opt/eval-venv/bin/python',IMAGE,'/workspace/qa_driver.py']
 start=time.monotonic();p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=330)
 save(OUT/'EXECUTION_RECEIPT.json',{'argv':argv,'exit_code':p.returncode,'wall_seconds':time.monotonic()-start,
  'stdout':p.stdout,'stderr':p.stderr,'script_sha256':sha(__file__),'new_business_Teacher_Actor_calls':0,
  'native_OpenClaw_Agent_dispatch':False,'AI_curation_cost':'UNKNOWN_NOT_ZERO','training_started':False})
 print(p.stdout.strip());print('container_exit',p.returncode)
 raise SystemExit(p.returncode)

if __name__=='__main__':main()
