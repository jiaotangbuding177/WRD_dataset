from pathlib import Path
import json,subprocess,sys
r=Path('/workspace/extra_type_checks');r.mkdir(exist_ok=True)
real='/workspace/inputs/task/materials/e474a80615c085d4.pdf'
cases={'item_integer':[42],'file_integer':[{'file':42,'quote':'海南大学','page':2}],'file_bool':[{'file':True,'quote':'海南大学','page':2}],'quote_bool':[{'file':real,'quote':True,'page':2}],'quote_none':[{'file':real,'quote':None,'page':2}],'page_true':[{'file':real,'quote':'付连军','page':True}],'page_float':[{'file':real,'quote':'海南大学','page':2.0}],'page_zero':[{'file':real,'quote':'海南大学','page':0}],'valid_int':[{'file':real,'quote':'海南大学','page':2}]}
rows=[]
for name,value in cases.items():
 p=r/(name+'.json');p.write_text(json.dumps(value,ensure_ascii=False))
 c=[sys.executable,'/workspace/skills/cv-jd-interview-screening/scripts/evidence_check.py',str(p)]
 a=subprocess.run(c,capture_output=True,text=True);rows.append({'case':name,'claims_path':str(p),'claims':value,'argv':c,'returncode':a.returncode,'stdout':a.stdout,'stderr':a.stderr})
(r/'ACTUAL_TYPE_RESULTS.json').write_text(json.dumps({'kind':'actual_old_resource_additional_type_probes_no_Agent','rows':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{'case':x['case'],'rc':x['returncode'],'traceback':'Traceback' in x['stderr']} for x in rows]))
