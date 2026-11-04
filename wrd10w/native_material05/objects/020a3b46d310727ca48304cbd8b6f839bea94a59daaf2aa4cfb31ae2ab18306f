from pathlib import Path
import json,subprocess,sys
import pymupdf
W=Path('/workspace');S=W/'outputs/skill/scripts';O=W/'independent_results';O.mkdir(exist_ok=True);rows=[]
def run(label,args):
 r=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)
 row={'label':label,'argv':[sys.executable,*map(str,args)],'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr};rows.append(row);return r,row
r,row=run('EXACT_UNCHANGED_ORIGINAL22',[W/'tmp/run_tests.py']);original={'rc':r.returncode,'PASS':sum(s.startswith('PASS ') for s in r.stdout.splitlines()),'FAIL':sum(s.startswith('FAIL ') for s in r.stdout.splitlines())}
r,row=run('EXACT_UNCHANGED_NEW17',[W/'inputs/independent/repair_contract_tests.py']);new17=json.loads((W/'outputs/independent_retest/RESULTS.json').read_text());assert r.returncode==0 and new17['pass']==new17['total']==17
# Fresh independent literal and two pages: neither supplied literal nor Maker
# identity can be used as a hardcoded exception to the old watermark heuristic.
literal='EnterpriseIntegrationArchitectExpert'
p=O/'different_two_page.pdf';d=pymupdf.open();pg=d.new_page();pg.insert_text((72,72),'Independent Alpha');pg=d.new_page();pg.insert_text((72,72),literal+'\nNew independent literal evidence');d.save(p);d.close()
r,row=run('UNSEEN_LITERAL_FULL_RAW_EXTRACTION',[S/'cv_extract.py',p,'--raw']);extract=json.loads(r.stdout);expected=[x.get_text() for x in pymupdf.open(p)];actual=[x.get('raw_text') for x in extract['results'][0]['pages']];raw_equal=actual==expected
claims=[]
for label,page,expected_rc in [('UNSEEN_QUOTE_CORRECT_PAGE',2,0),('UNSEEN_QUOTE_WRONG_PAGE',1,2),('UNSEEN_QUOTE_WITHOUT_PAGE',None,0)]:
 claim={'file':str(p),'quote':literal}
 if page is not None:claim['page']=page
 cp=O/(label+'.json');cp.write_text(json.dumps([claim]));r,row=run(label,[S/'evidence_check.py',cp]);rep=json.loads(r.stdout);row['independent_expected_rc']=expected_rc;row['independent_ok']=r.returncode==expected_rc and (rep['ok'] is (expected_rc==0))
 if expected_rc==2:row['independent_ok']=row['independent_ok'] and rep['claims'][0]['found_pages']==[2]
 claims.append(row['independent_ok'])
real=W/'inputs/task/materials/e474a80615c085d4.pdf';r,row=run('EXACT_FULL_MAKER_RAW_TEXT',[S/'cv_extract.py',real,'--raw']);report=json.loads(r.stdout);maker_raw_equal=[x.get('raw_text') for x in report['results'][0]['pages']]==[x.get_text() for x in pymupdf.open(real)]
result={'kind':'ACTUAL_INDEPENDENT_OFFLINE_NO_AGENT','original22':original,'new17':{'pass':new17['pass'],'total':new17['total']},'new_two_page_raw_equals_actual_PDF_text':raw_equal,'full_Maker_raw_equals_actual_PDF_text':maker_raw_equal,'unseen_quote_correct_wrong_and_optional_page':all(claims),'commands':rows,'business_hiring_or_retention_not_scored':True}
(O/'ACTUAL_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='commands'}));assert original=={'rc':0,'PASS':22,'FAIL':0} and raw_equal and maker_raw_equal and all(claims)
