import ast,copy,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
from pathlib import Path
import openpyxl
BASE=Path('/workspace');steps=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(name,command,wanted):
    t=time.monotonic();r=subprocess.run(command,cwd=BASE,capture_output=True,text=True)
    Path('outputs/'+name+'.stdout.txt').write_text(r.stdout,encoding='utf-8');Path('outputs/'+name+'.stderr.txt').write_text(r.stderr,encoding='utf-8')
    steps.append({'name':name,'expected_exit':wanted,'actual_exit':r.returncode,'wall_seconds':time.monotonic()-t})
    assert r.returncode==wanted,(name,r.returncode,r.stdout,r.stderr)
    return json.loads(r.stdout)
target=Path('outputs/candidate/scripts/run.py');target.parent.mkdir(parents=True);shutil.copyfile('qa_private/old_run.py',target)
input_before=sha('inputs/dev_input.xlsx')
cmd=[sys.executable,str(target),'--request','inputs/dev_request.json','--output-root','outputs/style_trial']
old=run('old_false_style_rejection',cmd,3)
assert next(c for c in old['checks'] if c['name']=='styles_and_layout_preserved')['status']=='FAIL'
assert all(c['status']=='PASS' for c in old['checks'] if c['name']!='styles_and_layout_preserved')
# Snapshot only current old file/input/failure. No future new program, edit
# answer or successful verification report is part of this curated state.
state=Path('state_before_edit');state.mkdir()
for d in ('inputs','outputs','evidence'):shutil.copytree(d,state/d)
edit=json.loads(Path('qa_private/edit.json').read_text());text=target.read_text()
for e in edit['edits']:assert text.count(e['oldText'])==1
for e in edit['edits']:text=text.replace(e['oldText'],e['newText'])
target.write_text(text,encoding='utf-8',newline='\n')
assert ast.dump(ast.parse(text),include_attributes=False)==ast.dump(ast.parse(Path('qa_private/new_run.py').read_text()),include_attributes=False)
new=run('new_copy_style_check',cmd,0);assert all(c['status']=='PASS' for c in new['checks'])
assert sha('inputs/dev_input.xlsx')==input_before
req=json.loads(Path('inputs/dev_request.json').read_text());src=openpyxl.load_workbook('inputs/dev_input.xlsx',data_only=False)
out=openpyxl.load_workbook(new['delivery']['output_workbook'],data_only=False);count=0
assert src.sheetnames==out.sheetnames
for title in src.sheetnames:
    a,b=src[title],out[title]
    assert a.freeze_panes==b.freeze_panes and set(map(str,a.merged_cells.ranges))==set(map(str,b.merged_cells.ranges)) and a.sheet_state==b.sheet_state
    for row in a.iter_rows():
        for cell in row:
            other=b[cell.coordinate];count+=1
            for attr in ('font','fill','border','alignment','number_format'):assert copy.copy(getattr(cell,attr))==copy.copy(getattr(other,attr)),(title,cell.coordinate,attr)
module=importlib.util.module_from_spec(spec:=importlib.util.spec_from_file_location('patched',target));spec.loader.exec_module(module)
c1=src[src.sheetnames[0]]['A1'];c2=out[out.sheetnames[0]]['A1']
assert module.style_sig(c1)==module.style_sig(c2)
from openpyxl.styles import Font
mutated=copy.copy(c2.font);mutated.name='WRD_STYLE_MUTANT';c2.font=mutated
assert module.style_sig(c1)!=module.style_sig(c2),'A different font must not pass repaired comparator'
# Independent negative oracle also rejects the changed property, whereas a
# comparator returning a constant would fail this required distinction.
assert copy.copy(c1.font)!=copy.copy(c2.font)
steps.append({'name':'changed_font_negative_case','detected':True})
Path('RESOURCE_QA_RESULT.json').write_text(json.dumps({'status':'PASS','steps':steps,'openpyxl_version':openpyxl.__version__,'python':sys.version,'reopened_style_cells':count,
    'input_sha256':input_before,'new_projection_program_sha256':sha(target),'literal_original_program_AST_equal':True,
    'scope':'Finite exact-input false style rejection and copy comparator correction; no complete report schema/all inputs/Word rendering/qualified skill proof.',
    'Agent_sessions':0,'model_calls':0,'training':False},indent=2))
