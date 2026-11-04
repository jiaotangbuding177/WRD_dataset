"""A-only full-resource construction; original response R is already exposed."""
from array import array
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if(p/'AGENTS.md').is_file());BASE=ROOT/'output/20261027_wrd_main_v10';OUT=HERE/'native_construction_01'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,v):
    with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:f.write(js(v)+'\n')
def binref(p,k,v):
    a=array(k,v)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes());return{'path':p.relative_to(OUT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size,'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[k]}
def main():
    assert not OUT.exists();OUT.mkdir();source=load(HERE/'SOURCE_REVIEW.json');qa=load(HERE/'FINITE_RESOURCE_QA.json');assert qa['status']=='PASS_BOUNDED_MATHEMATICAL_MODEL_ONLY';module=(HERE/'resources/proportional_split.py').read_text(encoding='utf-8');assert digest(HERE/'resources/proportional_split.py')==qa['new_complete_resource_sha256']
    capture=load(BASE/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json');fulltools=capture['tools'];core=[t for t in fulltools if t['function']['name']in{'apply_patch','edit','exec','ls','process','read','write'}];assert len(core)==7;save(OUT/'TOOLS_CAPTURE_53.json',capture)
    with gzip.open(BASE/'clean_inputs/source_scope.metadata.jsonl.gz','rt',encoding='utf-8')as f:scope=next(x for x in map(json.loads,f)if x['source_id']=='conv_1702b763a7ee')
    assert scope['status']=='TRAIN';assert not(HERE/'state_before_write/outputs/proportional_split.py').exists()
    user='制作一个可导入、也可从命令行调用的 Python 数学计算资源，写入 /workspace/outputs/proportional_split.py。outputs目录已存在，该文件尚未创建，当前没有其它输入文件。只使用Python标准库，不安装依赖。\n'
    user+='以下是本计算任务明示的模型假设和字段名称：I=increase_amount为正数，s=post_stake已经是(0,1)内的小数而非百分数字符串，C=pre_registered_capital可省略。金额必须使用一致单位。Post=I/s，Pre=Post-I。当C给定时本题限定0<C<=Pre，以保证所定义的余量非负；这是当前数学模型的约束，不从真实公司、财务制度或法律规则推断这个条件。\n'
    user+='提供 compute_valuation(increase_amount, post_stake, pre_registered_capital=None, tol=1e-6)，返回输入I/s及post_money_valuation、pre_money_valuation。若C给定，price_per_unit=Pre/C，new_registered_capital=I/price_per_unit，capital_reserve=I-new_registered_capital，implied_post_stake=new_registered_capital/(C+new_registered_capital)，并返回C。校验s*Post约等于I、New+Reserve约等于I、implied_post_stake约等于s。\n'
    user+='若C缺失，只能给出Post/Pre和formula对象，包含参数化new_registered_capital公式“I*C/Pre”、capital_reserve公式“I-New”及本题C<=Pre约束；不得擅定C或给出唯一数值拆分。输出formula中的字符串使用函数入参/结果字段名，不能写死样例数。\n'
    user+='调用者保证是有限浮点数，验证范围1<=I<=1000000、0.01<=s<=0.99；C若给定则1e-3<=C<=Pre，tol只使用默认1e-6。只需基本参数断言，不冒称完整JSON schema、所有类型、路径授权或极端数值均已验证。以正常Python运行，不用-O。函数应可独立导入，导入不能写文件或运行固定样例。\n'
    user+='提供main及CLI：--increase和--post-stake必需，--pre-registered可省略，--out为JSON输出路径、默认outputs/valuation_result.json。标准的分隔参数及--name=value写法都必须走同一参数解析；缺必需参数应由解析器报错，不能退回固定样例。调用者提供可写输出路径并负责路径权限；创建必要父目录，将同一结果以UTF-8 JSON写入该路径并打印到stdout。脚本标准入口调用main。\n'
    user+='工作目录/workspace，OpenClaw2026.9.5，Python /opt/eval-venv/bin/python；outputs可写，不能访问其它会话或凭据；无网络、外发和子Agent权限。总限1800秒、max_tokens32768，当前已用/剩余预算UNKNOWN，无后台进程。请先写出完整可运行资源，不能在编写前声称已试跑通过。'
    args={'path':'/workspace/outputs/proportional_split.py','content':module}
    from jsonschema import Draft202012Validator
    Draft202012Validator(next(t for t in fulltools if t['function']['name']=='write')['function']['parameters']).validate(args)
    target={'role':'assistant','content':'','reasoning_content':'','tool_calls':[{'id':'call_math_resource_write','type':'function','function':{'name':'write','arguments':js(args)}}]}
    raw={'schema_version':'wrd-explicit-functional-resource-construction-v1','id':'ewi_math_resource_01:core7','bank':'ewi_math_resource_construction_01','stage':'B_math_resource_construction','source_ids':['conv_1702b763a7ee'],'source_group_id':scope['component_id'],'split':'train','source_admission':'ADMIT_SOURCE_ONLY','training_admitted':False,'root_main_admission':False,'messages':[{'role':'system','content':'你在原生OpenClaw工具环境中将明确的计算方法整理成可复用程序。按已给定接口和适用范围构建完整资源，区分程序编写、真实执行结果和业务质量。'},{'role':'user','content':user},target],'tools':core,'message_loss_mask':[0,0,1],'approved_components':['A'],'loss_multiplier':.25,
      'annotation_provenance':'EXPLICIT_NEW_FUNCTIONAL_STATE_NATIVE_WRITE_OF_VERBATIM_TEACHER_FUNCTIONS_WITH_NEW_ENTRYPOINT','new_input_identity':'NEW_AUTHORED_FUNCTIONAL_REQUEST_NOT_ORIGINAL_TEACHER_INPUT_EQUIVALENT','resource_code_provenance':'TWO_ORIGINAL_TEACHER_FUNCTIONS_VERBATIM_FROM_LF_ACTION_STRING_PLUS_NEW_SCOPE_HEADER_IMPORTS_AND_STANDARD_DISPATCH','source_review_path':str(HERE/'SOURCE_REVIEW.json'),'source_review_sha256':digest(HERE/'SOURCE_REVIEW.json'),'resource_QA_path':str(HERE/'FINITE_RESOURCE_QA.json'),'resource_QA_sha256':digest(HERE/'FINITE_RESOURCE_QA.json'),'state_path':str(HERE/'state_before_write'),'source_scope_sha256':digest(BASE/'clean_inputs/source_scope.metadata.jsonl.gz'),
      'target_owner':{'canonical_original_action_owner_id':'historical_EWI_action:8856374c439400f01448d478','source_original_response_owner':'8856374c439400f01448d478','source_original_action_id':'try_w1_valuation_conv1702b763a7ee','original_R_same_response_already_supervised_in_existing26':True,'new_view_original_R_positive_tokens':0,'R_and_A_component_ownership_separate':True,'all_other_A_views_of_same_original_response_mutually_exclusive':True},'rationale_provenance':'NO_NEW_R_SUPERVISION_OR_DUPLICATION_OF_EXISTING_ORIGINAL_R','original_R_preserved_by_existing26_and_full_original_SSE_copy':True,'actual_native_tool_dispatch':False,'is_original_native_request_identical':False,'is_original_native_next_action_identical':False,'full_autonomous_execution_demonstration':False,'future_QA_credit_only_not_in_model_input':True,'financial_accounting_or_legal_gold':False,'human_gold':False,'training_started':False,'weights_loaded':False,'new_Agent_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
    full=deepcopy(raw);full['id']=full['id'].replace(':core7',':full53');full['tools']=fulltools;full['conditional_bank_only']=True
    causal=ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py';spec=importlib.util.spec_from_file_location('math_resource_causal',causal);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);compiler=m.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets');save(OUT/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,'compiler_sha256':digest(causal)});stats=[]
    for profile,row in[('core7',raw),('full53',full)]:
        dump(OUT/f'math_resource.{profile}.raw.jsonl.gz',row);c=compiler.compile_messages(row['messages'],row['tools'],{2:{'id':row['id'],'mechanical_usable':True}},independent=True);spans=[[a,b,k,.25]for a,b,k,w in c['supervision_spans']if k=='A'];assert spans
        c['supervision_spans']=spans;c['supervised_tokens']=sum(b-a for a,b,k,w in spans);c['supervised_tokens_by_component']={'A':c['supervised_tokens']}
        for t in c['targets']:t['owned_supervision_spans']=spans;t['supervised_tokens']=c['supervised_tokens']
        labels=[-100]*len(c['input_ids']);weights=[0.]*len(labels)
        for a,b,k,w in spans:
            for i in range(a,b):labels[i]=c['input_ids'][i];weights[i]=.25
        c.update({k:v for k,v in row.items()if k not in('messages','tools')});c.update(messages=row['messages'],tools=row['tools'],supervision_spans_sha256=hashlib.sha256(js(spans).encode()).hexdigest(),binary_arrays=[binref(OUT/'arrays'/profile/n,k,v)for n,k,v in[('input_ids.u32le.bin','I',c['input_ids']),('labels.i64le.bin','q',labels),('weights.f32le.bin','f',weights)]]);dump(OUT/f'math_resource.{profile}.compiled.jsonl.gz',c);stats.append({'profile':profile,'sequence_tokens':c['total_tokens'],'supervised_tokens':c['supervised_tokens'],'by_component':c['supervised_tokens_by_component']})
    save(OUT/'BUILD.json',{'schema':'wrd-EWI-scoped-math-resource-actual-build-v1','status':'ACTUAL_ARRAYS_ROOT_AND_PEER_PENDING','counts':stats,'target_resource_sha256':digest(HERE/'resources/proportional_split.py'),'original_teacher_R_not_reexposed':True,'new_R_tokens':0,'core_full_same_A_owner_mutually_exclusive':True,'new_source_or_independent_task_count':0,'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'new_Agent_calls':0,'script_sha256':digest(Path(__file__))});print(json.dumps(load(OUT/'BUILD.json')))
if __name__=='__main__':main()
