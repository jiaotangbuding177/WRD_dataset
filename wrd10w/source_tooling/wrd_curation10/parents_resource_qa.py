"""Independent bounded CPU checks for the recovered meeting formatter.

Run with the already bundled Python containing python-docx 1.2.0. All fixture
creation and original-program output stays below resource_review10. No Agent,
model, business evaluation, native runtime or trainer is started.
"""
from pathlib import Path
import argparse,ast,hashlib,json,shutil,subprocess,sys,time,zipfile
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation10/resource_review10/meeting_gen01'
OLD=Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes/meeting-minutes-formatting_gen_01/workspace/outputs')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def original_feedback(idx):
 t=json.loads((OUT/'TIMELINE.original.audit.json').read_text(encoding='utf-8'))
 return t[idx]['text']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--program',type=Path,default=OUT/'original_writes/027_apply_minutes_format.py');ap.add_argument('--variant',default='original27');a=ap.parse_args()
 program=a.program.resolve();ast.parse(program.read_text(encoding='utf-8'))
 work=OUT/'cpu_qa'/a.variant;work.mkdir(parents=True,exist_ok=True)
 runs=[];checks=[]
 def run(label,inp,*extra):
  dest=work/(label+'.docx');report=work/(label+'.report.json')
  assert not dest.exists(),'FRESH_OUTPUT_REQUIRED'
  command=[sys.executable,'-X','utf8',str(program),str(inp),'--out',str(dest),'--report',str(report),*extra]
  start=time.monotonic();p=subprocess.run(command,capture_output=True,timeout=12,cwd=work)
  (work/(label+'.stdout.txt')).write_bytes(p.stdout);(work/(label+'.stderr.txt')).write_bytes(p.stderr)
  runs.append({'case':label,'program':pin(program),'argv':command,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,
   'input_pin':pin(inp) if inp.exists() else None,'output_pin':pin(dest) if dest.exists() else None,
   'report_pin':pin(report) if report.exists() else None})
  return dest,p.returncode
 def check(name,condition,expected,observed,scope):
  checks.append({'name':name,'pass':bool(condition),'expected':expected,'observed':observed,'scope':scope})
 # Copy exact original Teacher synthetic fixtures; they are not historical
 # business originals. Their genuine historical byte SHA is already pinned.
 inputs=work/'original_teacher_synthetic_fixtures';inputs.mkdir(exist_ok=True)
 for name in ['meeting_minutes.docx','boundary_meeting_minutes.docx','invalid_input.docx']:
  b=(OLD/'reproduction_inputs'/name).read_bytes();(inputs/name).write_bytes(b)
 normal,code=run('normal',inputs/'meeting_minutes.docx','--remove-stars')
 n=Document(normal);summary=json.loads((work/'normal.report.json').read_text())
 before=Document(inputs/'meeting_minutes.docx')
 expected=[p.text.lstrip()[1:].lstrip(' \u3000') if p.text.lstrip().startswith('*') else p.text for p in before.paragraphs]
 check('ordinary_source_derived_fixture_text',code==0 and [p.text for p in n.paragraphs]==expected,expected,[p.text for p in n.paragraphs],'local_plain_paragraph_content_only')
 check('ordinary_stars_removed',summary['stars_removed']==3,3,summary['stars_removed'],'local_fixture_only')
 r=n.paragraphs[1].runs[0];fonts=r._element.rPr.rFonts.attrib
 check('font_metadata_CN_and_western',fonts.get(qn('w:eastAsia'))=='楷体' and fonts.get(qn('w:ascii'))=='Times New Roman',{'CN':'楷体','western':'Times New Roman'},dict(fonts),'DOCX_XML_not_rendered_font_availability')
 check('body_size_12pt',r.font.size.pt==12,12,r.font.size.pt,'DOCX_XML')
 bdoc,code=run('boundary',inputs/'boundary_meeting_minutes.docx')
 bn=Document(bdoc)
 check('heading_explicit_size_kept',bn.paragraphs[0].runs[0].font.size.pt==16,16,bn.paragraphs[0].runs[0].font.size.pt,'known_Heading1_style_fixture')
 check('default_does_not_strip_stars',bn.paragraphs[1].text=='*   ','*   ',bn.paragraphs[1].text,'remove_stars_false')
 bad,bad_code=run('invalid_existing',inputs/'invalid_input.docx')
 check('invalid_existing_rejected_without_output',bad_code==2 and not bad.exists(),{'exit':2,'output':False},{'exit':bad_code,'output':bad.exists()},'invalid_DOCX_byte_fixture')
 absent,absent_code=run('missing_input',inputs/'never_existed.docx')
 check('missing_input_rejected_without_output',absent_code==2 and not absent.exists(),{'exit':2,'output':False},{'exit':absent_code,'output':absent.exists()},'missing_path')
 composed,c=run('composition_songti',normal,'--cn-font','宋体')
 cn=Document(composed)
 check('second_pass_text_preserved',[p.text for p in cn.paragraphs]==[p.text for p in n.paragraphs],[p.text for p in n.paragraphs],[p.text for p in cn.paragraphs],'local_two_pass_only')
 check('second_pass_songti',all(r._element.rPr.rFonts.get(qn('w:eastAsia'))=='宋体' for p in cn.paragraphs for r in p.runs),'all_visible_runs_Songti','checked_all_runs','DOCX_XML')
 fixtures=work/'new_curator_counterexamples';fixtures.mkdir(exist_ok=True)
 # Heading had an existing indent: original says headings get no first-line
 # indent but only refrains from setting a new value, leaving the old one.
 d=Document();p=d.add_paragraph('Heading text',style='Heading 1');p.runs[0].font.size=Pt(16)
 p._p.get_or_add_pPr().get_or_add_ind().set(qn('w:firstLineChars'),'300')
 f=fixtures/'heading_preindented.docx';d.save(f);dest,c=run('heading_preindented',f)
 h=Document(dest).paragraphs[0]._p.pPr.ind
 val=h.get(qn('w:firstLineChars')) if h is not None else None
 check('heading_existing_first_indent_cleared',val in {None,'0'},'absent_or_0',val,'counterexample_to_header_no_heading_indent_claim')
 # Existing hanging state must not silently coexist with a requested first
 # line state. This checks XML, not a claim about actual Word visual layout.
 d=Document();p=d.add_paragraph('Body summary');p._p.get_or_add_pPr().get_or_add_ind().set(qn('w:hanging'),'480')
 f=fixtures/'hanging_indent.docx';d.save(f);dest,c=run('hanging_indent',f)
 ind=Document(dest).paragraphs[0]._p.pPr.ind
 check('hanging_indent_conflict_removed',ind.get(qn('w:hanging')) is None,'no_hanging_with_requested_firstLineChars',dict(ind.attrib),'XML_conflict_boundary_not_rendered_visual_claim')
 # Hyperlink text is in Paragraph.text but not Paragraph.runs in python-docx
 # 1.2.0. The original remover therefore erases unrelated following text.
 d=Document();p=d.add_paragraph();link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),'internal_target')
 rr=OxmlElement('w:r');tt=OxmlElement('w:t');tt.text='* ';tt.set(qn('xml:space'),'preserve');rr.append(tt);link.append(rr);p._p.append(link)
 p.add_run('Complete summary');f=fixtures/'hyperlink_star_prefix.docx';d.save(f);dest,c=run('hyperlink_star_prefix',f,'--remove-stars')
 got=Document(dest).paragraphs[0].text
 check('hyperlink_prefix_no_text_corruption',got=='Complete summary','Complete summary',got,'actual_visible_text_counterexample')
 # Assignment to run.text clears other run XML such as fields even when the
 # only intended edit was removing a prefix. Preserve exact field nodes.
 d=Document();p=d.add_paragraph();r=p.add_run('* ');fld=OxmlElement('w:fldChar');fld.set(qn('w:fldCharType'),'begin');r._r.append(fld)
 instr=OxmlElement('w:instrText');instr.text='PAGE';r._r.append(instr);p.add_run('Summary')
 f=fixtures/'field_node_star_prefix.docx';d.save(f);dest,c=run('field_node_star_prefix',f,'--remove-stars')
 xml=Document(dest).paragraphs[0]._p
 count=sum(1 for x in xml.iter(qn('w:fldChar')))
 check('field_nodes_survive_prefix_edit',count==1,1,count,'actual_XML_field_loss_counterexample')
 result={'schema':'wrd10-recovered-formatter-independent-CPU-QA-v1','status':'PASS_LOCAL_AND_COUNTEREXAMPLES_OBSERVED_NOT_BUSINESS_OR_SKILL_ACCEPTANCE',
  'variant':a.variant,'program_pin':pin(program),'python_version':sys.version,'python_docx_version':__import__('docx').__version__,
  'runs':runs,'checks':checks,'checks_passed':sum(x['pass'] for x in checks),'checks_failed':sum(not x['pass'] for x in checks),
  'original_teacher_fixture_pins':[pin(p) for p in inputs.iterdir() if p.is_file()],
  'new_fixture_authorship':'NEW_CURATOR_DIAGNOSTIC_COUNTEREXAMPLES_NOT_HISTORICAL_CASES',
  'original_code_or_feedback_not_modified':True,'rendering_or_business_Q_performed':False,
  'new_Agent_or_model_or_native_calls':0,'training_started':False,'script_pin':pin(Path(__file__))}
 save(work/'CPU_QA.json',result)
 print(json.dumps({'variant':a.variant,'checks':len(checks),'pass':result['checks_passed'],'fail':[x['name'] for x in checks if not x['pass']],
  'runs':len(runs),'program_sha256':sha(program),'receipt_sha256':sha(work/'CPU_QA.json')},ensure_ascii=False))
if __name__=='__main__':main()
