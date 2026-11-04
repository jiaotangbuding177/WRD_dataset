import copy,hashlib,importlib.util,json,sys
from pathlib import Path
from datetime import datetime
import openpyxl
spec=importlib.util.spec_from_file_location('h','masking_helpers.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
checks=[]
def check(name,ok):assert ok,name;checks.append(name)
Path('abc.bin').write_bytes(b'abc')
check('streaming_sha_known_vector',h.sha256_file(Path('abc.bin'))=='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
check('relative_path',h.resolve_path(Path('/work'), 'sub/a.xlsx')==Path('/work/sub/a.xlsx'))
check('absolute_path',h.resolve_path(Path('/work'), '/else/a.xlsx')==Path('/else/a.xlsx'))
req={'schema_version':'data_field_mask_request_v1','input_workbook':'in.xlsx','output_workbook':'out.xlsx','report_file':'report.json','worksheets':[{'name':'S','header_row':1,'data_start_row':2,'data_end_row':3,'columns':['客户']}],'masking':{'prefix_chars':2,'suffix_chars':2,'replacement':'***'}}
h.validate_request(req);checks.append('valid_basic_request')
bad=[]
for name,mutate in [('missing_required',lambda r:r.pop('input_workbook')),('wrong_version',lambda r:r.update(schema_version='x')),('empty_path',lambda r:r.update(output_workbook='')),('empty_worksheets',lambda r:r.update(worksheets=[])),('row_reversed',lambda r:r['worksheets'][0].update(data_end_row=1)),('duplicate_column',lambda r:r['worksheets'][0].update(columns=['客户','客户'])),('boolean_prefix',lambda r:r['masking'].update(prefix_chars=True)),('negative_suffix',lambda r:r['masking'].update(suffix_chars=-1)),('large_prefix',lambda r:r['masking'].update(prefix_chars=9)),('empty_replacement',lambda r:r['masking'].update(replacement='')),('long_replacement',lambda r:r['masking'].update(replacement='x'*17))]:
    r=copy.deepcopy(req);mutate(r)
    try:h.validate_request(r)
    except h.ContractError:bad.append(name)
    else:raise AssertionError('not rejected:'+name)
checks+=['invalid_basic_'+n for n in bad]
# Document the known API limit; it is not counted as a correctness pass.
extra=copy.deepcopy(req);extra['not_in_schema']=1;h.validate_request(extra)
limits={'additional_properties_not_rejected':True,'full_schema_validation_required_upstream':True,'arbitrary_output_path_safety_not_provided':True}
cases=[('ABCDE',2,2,'***','AB***DE'),('ABCD',2,2,'***','ABCD'),('ABCDE',0,0,'***','***'),('ABCDE',2,0,'***','AB***'),('ABCDE',0,2,'***','***DE'),(' 北京某公司 ',2,2,'***',' 北***司 '),('甲乙丙丁戊',1,1,'#','甲#戊'),('A\u0301BC',1,1,'#','A#C'),('😀甲乙丙🙂',1,1,'#','😀#🙂')]
for i,(value,p,s,rep,want) in enumerate(cases):check('mask_'+str(i),h.mask_text(value,p,s,rep)==want)
check('same_parameters_idempotent',all(h.mask_text(h.mask_text(v,p,s,r),p,s,r)==want for v,p,s,r,want in cases))
# Bad implementations must be detected by explicit requirements/oracles.
mutant_strip=lambda v,p,s,r:h.mask_text(v.strip(),p,s,r)
check('reject_trim_mutant',mutant_strip(' 北京某公司 ',2,2,'***')!=' 北***司 ')
mutant_suffix_zero=lambda v,p,s,r:v[:p]+r+v[-s:]
check('reject_negative_zero_slice_mutant',mutant_suffix_zero('ABCDE',2,0,'***')!='AB***')
wb=openpyxl.Workbook();ws=wb.active;ws.title='S';ws.append(['金额','客户','销售'])
check('header_exact_shifted',h.locate_columns(ws,{'header_row':1,'columns':['客户','金额']})=={'客户':2,'金额':1})
for name,cols in [('missing',['客户 ']),('duplicate',['客户'])]:
    if name=='duplicate':ws['D1']='客户'
    try:h.locate_columns(ws,{'header_row':1,'columns':cols})
    except h.ContractError:checks.append('header_'+name+'_rejected')
    else:raise AssertionError('header accepted:'+name)
values=[(None,'blank'),('','blank'),('张三','text'),(1,'non_text'),(True,'non_text'),(datetime(2026,1,2),'non_text'),('=1+1','formula')]
for i,(v,want) in enumerate(values):ws.cell(2,i+1).value=v;check('classify_'+str(i),h.classify(ws.cell(2,i+1))==want)
base=h.layout_sig(ws);ws.freeze_panes='B2';check('fingerprint_freeze_delta',h.layout_sig(ws)!=base)
base=h.layout_sig(ws);ws.column_dimensions['B'].width=42;check('fingerprint_width_delta',h.layout_sig(ws)!=base)
base=h.layout_sig(ws);ws.row_dimensions[2].height=34;check('fingerprint_height_delta',h.layout_sig(ws)!=base)
base=h.layout_sig(ws);ws.merge_cells('F4:G4');check('fingerprint_merge_delta',h.layout_sig(ws)!=base)
Path('RESULT.json').write_text(json.dumps({'status':'PASS_SCOPED_HELPERS','checks':checks,'checks_passed':len(checks),'limitations_observed':limits,'python':sys.version,'openpyxl':openpyxl.__version__,
    'module_sha256':hashlib.sha256(Path('masking_helpers.py').read_bytes()).hexdigest(),'Agent_sessions':0,'model_calls':0,'training':False},indent=2))
