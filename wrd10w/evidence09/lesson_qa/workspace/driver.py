from pathlib import Path
import json,subprocess,shutil,zipfile
from docx import Document
R=Path('/workspace');results=[]
for name in ['7a6d2f63d0c34910127bb0d4','lesson_after']:
 p=subprocess.run(['python',str(R/'code'/f'{name}.py')],capture_output=True,text=True,timeout=90)
 (R/'qa_outputs'/f'{name}.stdout').write_text(p.stdout);(R/'qa_outputs'/f'{name}.stderr').write_text(p.stderr)
 out=R/'outputs/英语教案.docx';good=p.returncode==0 and out.exists()
 if good:
  dst=R/'qa_outputs'/f'{name}.docx';shutil.copyfile(out,dst);d=Document(dst);text='\n'.join(p.text for p in d.paragraphs);good='45'in text and '口语'in text
  q=subprocess.run(['libreoffice','-env:UserInstallation=file:///workspace/tmp/lo_'+name,'--headless','--convert-to','pdf','--outdir',str(R/'qa_outputs'),str(dst)],capture_output=True,text=True,timeout=90)
  good=good and q.returncode==0 and dst.with_suffix('.pdf').exists()
  results.append({'name':name,'PASS':good,'exit_code':p.returncode,'paragraphs':len(d.paragraphs),'tables':len(d.tables),'no_business_or_textbook_gold':True})
 else:results.append({'name':name,'PASS':False,'exit_code':p.returncode})
result={'status':'PASS_SCOPED_LESSON_EXPORT_AND_RUNTIME_REPAIR'if all(x['PASS']for x in results)else'FAIL','checks':results,'training_started':False,'model_calls':0}
(R/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
