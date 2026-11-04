import hashlib,json,subprocess,sys,time
from pathlib import Path
import openpyxl
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
target=Path('/workspace/outputs/validation_history/edge_case_tests.py');program=Path('/workspace/outputs/candidate/scripts/run.py');before=sha(program);steps=[]
def run(name,wanted):
    t=time.monotonic();r=subprocess.run([sys.executable,str(target)],capture_output=True,text=True,cwd='/workspace');Path('qa_private/'+name+'.stdout.txt').write_text(r.stdout);Path('qa_private/'+name+'.stderr.txt').write_text(r.stderr);steps.append({'name':name,'expected_exit':wanted,'actual_exit':r.returncode,'wall_seconds':time.monotonic()-t});assert r.returncode==wanted,(name,r.stdout,r.stderr);return r.stdout
old=run('old_test_two_oracle_failures',1);assert '共 31 项检查，失败 2 项' in old and '[FAIL] edge_transposed_masked' in old and '[FAIL] edge_transposed_nontarget' in old
args=json.loads(Path('qa_private/edit.json').read_text());text=target.read_text()
for e in args['edits']:assert text.count(e['oldText'])==1
for e in args['edits']:text=text.replace(e['oldText'],e['newText'])
target.write_text(text,encoding='utf-8',newline='\n');assert sha(target)==sha('qa_private/new_expected.py')
new=run('new_test_two_oracle_corrections',0);assert '共 31 项检查，失败 0 项' in new and '[FAIL]' not in new;assert sha(program)==before
folder=target.parent/'testdata';src=openpyxl.load_workbook(folder/'edge_transposed.xlsx')['S'];out=openpyxl.load_workbook(folder/'edge_transposed_out.xlsx')['S'];req=json.loads((folder/'req_edge_transposed.json').read_text())
assert req['worksheets'][0]['data_start_row']==2 and req['worksheets'][0]['data_end_row']==3 and '客户名称' in req['worksheets'][0]['columns']
assert src['C1'].value=='客户名称' and src['C2'].value==' 北京某某科技有限公司 ' and src['C3'].value=='上海某某厂'
# Independent expected literals and direct codepoint rule, not stdout green.
assert (src['C2'].value[:2],src['C2'].value[-2:])==(' 北','司 ')
assert src['C2'].value[:2]+'***'+src['C2'].value[-2:]==' 北***司 '==out['C2'].value
assert src['C3'].value[:2]+'***'+src['C3'].value[-2:]=='上海***某厂'==out['C3'].value
assert out['A2'].value=='TE***-1' and out['B2'].value==100 and out['D2'].value=='张测试'
# Two original incorrect oracles must still reject the same actual outputs.
assert out['C2'].value!=' 北京***公司 ' and out['C3'].value!='上海某某厂'
result={'status':'PASS_SCOPED_TWO_TEST_ORACLES','steps':steps,'reopened_C2_C3_rule_and_region_verified':True,'original_wrong_oracles_rejected':2,'candidate_program_sha256_before_after':before,'candidate_program_unchanged':True,'native_edit_exact_original_literals':True,'new_test_sha256':sha(target),'old_failure_count':2,'new_failure_count':0,'finite_checks_after':31,'whole_candidate_quality_or_all_inputs_approved':False,'Agent_sessions':0,'model_calls':0,'training':False,'python':sys.version,'openpyxl':openpyxl.__version__}
Path('RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
