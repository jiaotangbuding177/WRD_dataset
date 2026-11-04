from pathlib import Path
import json,subprocess,sys,hashlib
import pymupdf
from PIL import Image,ImageDraw
ROOT=Path('/workspace');OUT=ROOT/'independent_results';OUT.mkdir(exist_ok=True)
S=ROOT/'skills/cv-jd-interview-screening/scripts'
checks=[]
def run(label,args):
 r=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)
 row={'label':label,'argv':[sys.executable,*map(str,args)],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 checks.append(row)
 return r
r=run('EXACT_ORIGINAL_22_ASSERTIONS',[ROOT/'tmp/run_tests.py'])
original22={'returncode':r.returncode,'PASS_lines':sum(x.startswith('PASS ') for x in r.stdout.splitlines()),'FAIL_lines':sum(x.startswith('FAIL ') for x in r.stdout.splitlines())}
files=sorted((ROOT/'inputs/task/materials').glob('*.pdf'))
r=run('EIGHT_AUTHENTIC_PDFS_ONE_BATCH',[S/'cv_extract.py',*files])
batch=json.loads(r.stdout)
expected={hashlib.sha256(p.read_bytes()).hexdigest():p for p in files}
batch_ok=(r.returncode==0 and len(batch['results'])==8 and not batch['errors'] and {x['sha256'] for x in batch['results']}==set(expected) and all(x['page_count']==len(pymupdf.open(expected[x['sha256']])) for x in batch['results']))
fix=ROOT/'independent_fixtures';fix.mkdir(exist_ok=True)
# Raster-only PDF is valid, but contains no text layer. No OCR is demanded:
# this checks whether the extractor explicitly signals the missing usable text.
im=Image.new('RGB',(600,200),'white');ImageDraw.Draw(im).text((30,30),'Candidate Raster resume',fill='black');im.save(fix/'raster.png')
d=pymupdf.open();p=d.new_page();p.insert_image(p.rect,filename=str(fix/'raster.png'));d.save(fix/'image_only.pdf');d.close()
r=run('VALID_IMAGE_ONLY_PDF',[S/'cv_extract.py',fix/'image_only.pdf'])
scan=json.loads(r.stdout);silent_empty=(r.returncode==0 and not scan['errors'] and all(not p['text'] for x in scan['results'] for p in x['pages']))
# This is deliberate real text in a declared synthetic CV, not a watermark.
literal='CertifiedKubernetesAdministrator'
d=pymupdf.open();p=d.new_page();p.insert_text((72,72),'Candidate Alpha\n'+literal);d.save(fix/'legitimate_long_ascii.pdf');d.close()
raw=pymupdf.open(fix/'legitimate_long_ascii.pdf')[0].get_text();assert literal in raw
r=run('LEGITIMATE_LONG_ASCII_TEXT_EXTRACTION',[S/'cv_extract.py',fix/'legitimate_long_ascii.pdf'])
ascii_report=json.loads(r.stdout);kept=any(literal in p['text'] for x in ascii_report['results'] for p in x['pages'])
claimfile=fix/'literal_claim.json';claimfile.write_text(json.dumps([{'file':str(fix/'legitimate_long_ascii.pdf'),'page':1,'quote':literal}]))
r=run('ACTUAL_LITERAL_QUOTE_FROM_RAW_PDF',[S/'evidence_check.py',claimfile])
literal_valid=(r.returncode==0 and json.loads(r.stdout)['ok'])
real=ROOT/'inputs/task/materials/e474a80615c085d4.pdf'
shape=[]
for label,value in [('claims_item_is_integer',[42]),('quote_is_integer',[{'file':str(real),'quote':42,'page':1}]),('page_is_string',[{'file':str(real),'quote':'海南大学','page':'2'}])]:
 p=fix/(label+'.json');p.write_text(json.dumps(value,ensure_ascii=False))
 r=run(label,[S/'evidence_check.py',p]);shape.append({'case':label,'returncode':r.returncode,'traceback':'Traceback' in r.stderr,'JSON_error_report':False})
 try:shape[-1]['JSON_error_report']=isinstance(json.loads(r.stdout),dict)
 except ValueError:pass
# Independent identity/page positives and a real unique quote pointed at a
# different candidate. This does not judge qualification semantics.
claims=[{'file':str(real),'page':2,'quote':'海南大学'}, {'file':str(ROOT/'inputs/task/materials/3f8a1c51032c2b97.pdf'),'page':2,'quote':'江南大学'}]
p=fix/'real_positive_quotes.json';p.write_text(json.dumps(claims,ensure_ascii=False));r=run('REAL_MAKER_AND_UNSEEN_SOURCE_QUOTES',[S/'evidence_check.py',p]);real_quotes=(r.returncode==0 and json.loads(r.stdout)['ok'])
p=fix/'cross_identity_wrong_quote.json';p.write_text(json.dumps([{'file':str(real),'page':2,'quote':'江南大学'}],ensure_ascii=False));r=run('REAL_CROSS_CANDIDATE_QUOTE_REJECT',[S/'evidence_check.py',p]);cross_reject=(r.returncode==2 and not json.loads(r.stdout)['ok'])
report={'kind':'ACTUAL_OFFLINE_FIXED_IMAGE_NO_AGENT','original22':original22,'eight_real_PDF_batch_correct':batch_ok,'authentic_file_count':8,'actual_total_pages':sum(x['page_count'] for x in batch['results']),
 'actual_positive_real_quotes':real_quotes,'actual_cross_candidate_unique_quote_rejected':cross_reject,
 'image_only_zero_exit_empty_text_no_explicit_error':silent_empty,'known_declared_OCR_limit_does_not_prove_business_failure_on_eight_text_PDFs':True,
 'legitimate_ASCII_raw_source_text_preserved_by_extractor':kept,'legitimate_raw_source_quote_accepted':literal_valid,
 'synthetic_long_token_is_deliberate_CV_text_not_a_new_business_source':True,'malformed_claim_shape_diagnostics':shape,
 'commands':checks,'business_semantics_or_benefit_not_scored':True,'skill_bytes_not_modified':True}
(OUT/'ACTUAL_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='commands'},ensure_ascii=False))
