"""CPU-verified synthetic resource repair and evidence-limited decision cases.

This is an offline fixture builder, not an Agent executor. It executes only the
transparent new standard-library programs authored in this file. No model,
enterprise data, OpenClaw session, training, or business quality score is used.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, os, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = ROOT/'output/20261031_wrd_curation11/resource_cases'
SCHEMA = 'wrd11-new-authored-cpu-resource-counterfactual-v1'
PROVENANCE = 'NEW_AUTHORED_SYNTHETIC_CPU_VERIFIED_NOT_NATIVE_TRACE'


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsave(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists(), 'DO_NOT_OVERWRITE_EXISTING_RUN'
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def pin(path):
    return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':sha(path)}


def source(body):
    return ('import sys, json\n'+body.strip()+'\n\n'
            'if __name__ == "__main__":\n'
            '    data = json.loads(sys.stdin.read())\n'
            '    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))\n')


def families():
    """Different semantic contracts, not paraphrases of a single template."""
    rows=[]
    def add(key, mechanism, fixtures, expected, bad, good, regression, diagnosis, repair):
        assert len(fixtures)==len(expected) and len(fixtures)>=3
        rows.append(dict(family_id=key,mechanism=mechanism,fixtures=fixtures,expected=expected,
            versions={'v0':source(bad),'noop':source(bad),'v1':source(good),'regression':source(regression)},
            diagnosis=diagnosis,repair=repair))

    capture_common='''
import subprocess
def captured(item, capture_stderr=True, check_exit=True):
    child = "import sys;sys.stdout.write('synthetic stdout');sys.stderr.write('synthetic diagnostic');sys.exit("+str(item['actual_exit'])+")"
    completed = subprocess.run([sys.executable, '-c', child], capture_output=True, text=True, timeout=5)
    stderr = completed.stderr if capture_stderr else None
    exit_ok = completed.returncode == item['expected_exit'] if check_exit else True
    needle_found = stderr is not None and item['needle'] in stderr
    return {'exit_ok':exit_ok,'needle_found':needle_found,'stderr_saved':stderr is not None,'check_pass':exit_ok and needle_found}
'''
    add('stderr_exit','保存真实stderr并独立验证退出码',
        [{'actual_exit':7,'expected_exit':7,'needle':'synthetic diagnostic'},
         {'actual_exit':7,'expected_exit':0,'needle':'synthetic diagnostic'},
         {'actual_exit':0,'expected_exit':0,'needle':'missing diagnostic'}],
        [{'exit_ok':True,'needle_found':True,'stderr_saved':True,'check_pass':True},
         {'exit_ok':False,'needle_found':True,'stderr_saved':True,'check_pass':False},
         {'exit_ok':True,'needle_found':False,'stderr_saved':True,'check_pass':False}],
        capture_common+'\ndef transform(item):\n    return captured(item, capture_stderr=False)\n',
        capture_common+'\ndef transform(item):\n    return captured(item)\n',
        capture_common+'\ndef transform(item):\n    return captured(item, check_exit=False)\n',
        '原实现没有保留stderr，错误输出中的断言因此失败；期望失败的测试也必须继续核对真实退出码。',
        '同时保存stdout和stderr，再分别计算退出码与内容断言；禁止把返回码检查设为无条件通过。')

    refs_base='''
def walk(node, refs, lists=True):
    if isinstance(node, dict):
        if '$ref' in node: refs.add(node['$ref'])
        for value in node.values(): walk(value, refs, lists)
    elif lists and isinstance(node,list):
        for value in node: walk(value, refs, lists)
def answer(item, refs):
    return {'references':sorted(refs),'missing':sorted(refs-set(item['resources']))}
'''
    add('nested_references','递归检查字典与列表中的资源引用而不掩盖缺项',
        [{'document':{'step':{'$ref':'guide.md'}},'resources':['guide.md']},
         {'document':{'steps':[{'$ref':'a.md'},{'$ref':'absent.md'}]},'resources':['a.md']},
         {'document':{'$ref':'root.md','children':[{'inner':{'$ref':'leaf.md'}}]},'resources':['root.md','leaf.md']}],
        [{'references':['guide.md'],'missing':[]},
         {'references':['a.md','absent.md'],'missing':['absent.md']},
         {'references':['leaf.md','root.md'],'missing':[]}],
        refs_base+"\ndef transform(item):\n    refs=set()\n    if '$ref' in item['document']: refs.add(item['document']['$ref'])\n    return answer(item,refs)\n",
        refs_base+"\ndef transform(item):\n    refs=set();walk(item['document'],refs)\n    return answer(item,refs)\n",
        refs_base+"\ndef transform(item):\n    refs=set();walk(item['document'],refs,lists=False)\n    return answer(item,refs)\n",
        '仅检查顶层会漏掉嵌套引用；原fixture中既有合法深层引用，也有必须报告的缺失引用。',
        '递归遍历字典和列表，返回所有引用与真实缺失集合；不能用静态true代替检查。')

    xml_base='''
import xml.etree.ElementTree as ET
import re
def summary(root):
    return {'visible_text':''.join(n.text or '' for n in root.iter('t')),
            'field_nodes':len(list(root.iter('fldChar'))),
            'instructions':[n.text or '' for n in root.iter('instrText')]}
def trim_prefix(nodes):
    text=''.join(n.text or '' for n in nodes)
    match=re.match(r'^\\s*\\d+[.、]\\s*', text)
    left=match.end() if match else 0
    for n in nodes:
        old=n.text or ''; take=min(left,len(old));n.text=old[take:];left-=take
'''
    add('xml_field_preservation','删除跨run/超链接编号但保全字段XML',
        [{'xml':'<p><r><t>1. </t></r><r><fldChar/><instrText>PAGE</instrText><t>Body</t></r></p>'},
         {'xml':'<p><hyperlink><r><t>2.</t></r></hyperlink><r><t> Linked</t><fldChar/></r></p>'},
         {'xml':'<p><r><t>3</t><fldChar/></r><r><t>、 Split</t><instrText>REF item</instrText><fldChar/></r></p>'}],
        [{'visible_text':'Body','field_nodes':1,'instructions':['PAGE']},
         {'visible_text':'Linked','field_nodes':1,'instructions':[]},
         {'visible_text':'Split','field_nodes':2,'instructions':['REF item']}],
        xml_base+"\ndef transform(item):\n    root=ET.fromstring(item['xml']);text=''.join(n.text or '' for n in root.iter('t'))\n    root.clear();ET.SubElement(ET.SubElement(root,'r'),'t').text=re.sub(r'^\\s*\\d+[.、]\\s*','',text)\n    return summary(root)\n",
        xml_base+"\ndef transform(item):\n    root=ET.fromstring(item['xml']);trim_prefix(list(root.iter('t')))\n    return summary(root)\n",
        xml_base+"\ndef transform(item):\n    root=ET.fromstring(item['xml']);trim_prefix(root.findall('r/t'))\n    return summary(root)\n",
        '重写整段可丢失fldChar/instrText；只处理顶层run又会漏掉超链接内或跨run编号。',
        '只在可见t节点上消耗匹配前缀长度，保留原字段和超链接结构，不重建整段。')

    indent_base='''
import xml.etree.ElementTree as ET
def start(item):
    root=ET.fromstring(item['xml']);ind=root.find('ind')
    if ind is None: ind=ET.SubElement(root,'ind')
    ind.set('firstLine',str(item['first_line_twips']))
    return root,ind
'''
    add('indent_conflict','首行缩进与悬挂/字符缩进互斥属性',
        [{'xml':'<pPr><ind hanging="240" left="120"/></pPr>','first_line_twips':480},
         {'xml':'<pPr><ind firstLineChars="200" hangingChars="100"/></pPr>','first_line_twips':0},
         {'xml':'<pPr><ind firstLine="900" firstLineChars="50"/></pPr>','first_line_twips':240}],
        [{'firstLine':'480','left':'120'},{'firstLine':'0'},{'firstLine':'240'}],
        indent_base+"\ndef transform(item):\n    root,ind=start(item)\n    return dict(ind.attrib)\n",
        indent_base+"\ndef transform(item):\n    root,ind=start(item)\n    for k in ['hanging','hangingChars','firstLineChars']:ind.attrib.pop(k,None)\n    return dict(ind.attrib)\n",
        indent_base+"\ndef transform(item):\n    root,ind=start(item)\n    for k in ['hanging','hangingChars']:ind.attrib.pop(k,None)\n    return dict(ind.attrib)\n",
        '设置firstLine没有消除既有悬挂或字符单位缩进，属性冲突仍在；标题零缩进也可能继承旧值。',
        '明确采用twips首行单位并删除冲突的hanging/hangingChars/firstLineChars，保留无关left属性。')

    add('structured_table','表格单元格保留JSON值类型与嵌套数据',
        [{'columns':['name','count','meta'],'records':[{'name':'A','count':0,'meta':{'status':'pending'}}]},
         {'columns':['enabled','items'],'records':[{'enabled':False,'items':['x','y']}]},
         {'columns':['name','missing'],'records':[{'name':'Unicode 例','missing':None}]}],
        [[['A',0,{'status':'pending'}]],[[False,['x','y']]],[['Unicode 例',None]]],
        "def transform(item):\n    return [[str(row.get(k,'')) for k in item['columns']] for row in item['records']]\n",
        "def transform(item):\n    return [[row.get(k,None) for k in item['columns']] for row in item['records']]\n",
        "def transform(item):\n    return [[row.get(k,None) or '' for k in item['columns']] for row in item['records']]\n",
        '字符串化破坏嵌套字典、列表和布尔的结构；使用or空串又会吞掉有效的0、False和None。',
        '按显式列顺序原样投影JSON值，用null表示缺项，保留数值、布尔、数组和对象的类型。')

    facts_base='''
def bucket(records, classifier):
    result={'fact':[],'plan':[],'uncertain':[]}
    for row in records:
        group=classifier(row)
        result[group].append({'id':row['id'],'text':row['text']})
    return result
'''
    add('fact_plan','事实/计划/未决的原状态不能被措辞猜测覆盖',
        [{'records':[{'id':'r1','status':'plan','text':'计划在已购服务器部署。'},{'id':'r2','status':'fact','text':'确认测试文件已生成。'}]},
         {'records':[{'id':'r3','status':'uncertain','text':'是否按期交付仍待核实。'}]},
         {'records':[{'id':'r4','status':'fact','text':'当前版本通过三个本地检查。'},{'id':'r5','status':'plan','text':'下周完成独立消费测试。'}]}],
        [{'fact':[{'id':'r2','text':'确认测试文件已生成。'}],'plan':[{'id':'r1','text':'计划在已购服务器部署。'}],'uncertain':[]},
         {'fact':[],'plan':[],'uncertain':[{'id':'r3','text':'是否按期交付仍待核实。'}]},
         {'fact':[{'id':'r4','text':'当前版本通过三个本地检查。'}],'plan':[{'id':'r5','text':'下周完成独立消费测试。'}],'uncertain':[]}],
        facts_base+"\ndef transform(item):\n    return bucket(item['records'],lambda row:'fact')\n",
        facts_base+"\ndef transform(item):\n    return bucket(item['records'],lambda row:row['status'] if row['status'] in ['fact','plan'] else 'uncertain')\n",
        facts_base+"\ndef transform(item):\n    return bucket(item['records'],lambda row:'fact' if '已' in row['text'] else row['status'])\n",
        '把全部记录放入完成事实，或依一个已字猜状态，都会把计划提前写成既成事实。',
        '以输入已声明的fact/plan/uncertain分桶，原文和ID不改；未知状态进入uncertain。')

    add('decimal_rounding','十进制字符串按显式HALF_UP规则处理',
        [{'value':'2.675'},{'value':'1.005'},{'value':'-1.005'},{'value':'9007199254740993.005'}],
        ['2.68','1.01','-1.01','9007199254740993.01'],
        "def transform(item):\n    return format(round(float(item['value']),2),'.2f')\n",
        "from decimal import Decimal, ROUND_HALF_UP\ndef transform(item):\n    return format(Decimal(item['value']).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'.2f')\n",
        "from decimal import Decimal, ROUND_HALF_UP\ndef transform(item):\n    return format(Decimal(float(item['value'])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'.2f')\n",
        '二进制float在边界和大数上失去原十进制值；从float再构造Decimal也恢复不了精度。',
        '直接从输入字符串构造Decimal，并显式用ROUND_HALF_UP量化到两位，不经过float。')

    add('typed_boolean','布尔协议不能使用Python真值掩盖未知',
        [{'value':'false'},{'value':False},{'value':' TRUE '},{'value':2},{'value':None},{'value':0}],
        [{'valid':True,'value':False},{'valid':True,'value':False},{'valid':True,'value':True},
         {'valid':False,'value':None},{'valid':False,'value':None},{'valid':True,'value':False}],
        "def transform(item):\n    return {'valid':True,'value':bool(item['value'])}\n",
        "def transform(item):\n    v=item['value']\n    if type(v) is bool:return {'valid':True,'value':v}\n    if type(v) is int and v in [0,1]:return {'valid':True,'value':v==1}\n    if isinstance(v,str) and v.strip().lower() in ['true','false']:return {'valid':True,'value':v.strip().lower()=='true'}\n    return {'valid':False,'value':None}\n",
        "def transform(item):\n    v=item['value']\n    if isinstance(v,str):return {'valid':True,'value':v.strip().lower()=='true'}\n    return {'valid':True,'value':bool(v)}\n",
        '字符串false本身为真值；宽松转换还会把2和null等未定义输入伪装成有效布尔。',
        '只接受真正bool、整数0/1及显式true/false字符串，其余返回valid=false、value=null。')

    names_base='''
from pathlib import PurePosixPath
import hashlib
def encoded(path):
    return hashlib.sha256(path.encode()).hexdigest()[:8]+'_'+PurePosixPath(path).name
'''
    fixtures=[{'paths':['alpha/report.md','beta/report.md']},
              {'paths':['résumé/a file.md','tables/data.csv']},
              {'paths':['same/report.md','SAME/report.md']},
              {'paths':['safe/../escape.md']}]
    expect=[{'outputs':[{'source':p,'output':hashlib.sha256(p.encode()).hexdigest()[:8]+'_'+Path(p).name} for p in f['paths']],'error':None} for f in fixtures[:2]]
    expect += [{'outputs':[],'error':'CASE_ALIAS_SOURCE'},{'outputs':[],'error':'UNSAFE_RELATIVE_PATH'}]
    add('output_identity','避免同名输出覆盖、大小写别名和路径穿越',fixtures,expect,
        names_base+"\ndef transform(item):\n    outputs={}\n    for p in item['paths']:outputs[PurePosixPath(p).name]={'source':p,'output':PurePosixPath(p).name}\n    return {'outputs':list(outputs.values()),'error':None}\n",
        names_base+"\ndef transform(item):\n    seen=set();outputs=[]\n    for p in item['paths']:\n        q=PurePosixPath(p)\n        if q.is_absolute() or '..' in q.parts:return {'outputs':[],'error':'UNSAFE_RELATIVE_PATH'}\n        if p.casefold() in seen:return {'outputs':[],'error':'CASE_ALIAS_SOURCE'}\n        seen.add(p.casefold());outputs.append({'source':p,'output':encoded(p)})\n    return {'outputs':outputs,'error':None}\n",
        names_base+"\ndef transform(item):\n    outputs=[]\n    for p in item['paths']:\n        q=PurePosixPath(p)\n        if q.is_absolute() or '..' in q.parts:return {'outputs':[],'error':'UNSAFE_RELATIVE_PATH'}\n        outputs.append({'source':p,'output':encoded(p)})\n    return {'outputs':outputs,'error':None}\n",
        '只用basename会覆盖不同来源的同名产物；相对路径也仍可能含穿越和大小写别名。',
        '先拒绝绝对/穿越路径和大小写别名，再以完整相对路径指纹构造稳定不冲突的输出名。')

    add('html_escape','链接文本与属性分别转义并拒绝非HTTP(S)scheme',
        [{'label':'A&B','url':'https://example.invalid/a?q=1&b=2'},
         {'label':'<check>','url':'https://example.invalid/" data-x="bad'},
         {'label':'blocked','url':'javascript:alert(1)'}],
        ['<a href="https://example.invalid/a?q=1&amp;b=2">A&amp;B</a>',
         '<a href="https://example.invalid/&quot; data-x=&quot;bad">&lt;check&gt;</a>',
         '<span>blocked</span>'],
        "def transform(item):\n    return '<a href=\"'+item['url']+'\">'+item['label']+'</a>'\n",
        "import html\nfrom urllib.parse import urlsplit\ndef transform(item):\n    label=html.escape(item['label'],quote=True)\n    if urlsplit(item['url']).scheme.lower() not in ['http','https']:return '<span>'+label+'</span>'\n    return '<a href=\"'+html.escape(item['url'],quote=True)+'\">'+label+'</a>'\n",
        "import html\nfrom urllib.parse import urlsplit\ndef transform(item):\n    label=html.escape(item['label'],quote=True)\n    if urlsplit(item['url']).scheme.lower() not in ['http','https']:return '<span>'+label+'</span>'\n    return '<a href=\"'+item['url']+'\">'+label+'</a>'\n",
        '正文和href属性都可能被特殊字符破坏，修复正文不能替代属性转义；非HTTP(S)链接也不能直出。',
        '对标签文本与带引号属性分别转义，显式检查scheme，其余只输出无链接span。')
    return rows


def run_version(program, fixtures, expected, output):
    """Real CPU child program; none of these calls is a native Agent tool event."""
    started=time.perf_counter()
    completed=subprocess.run([sys.executable,str(program)],input=canonical(fixtures).encode(),
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8'))
    elapsed=time.perf_counter()-started
    output.mkdir(parents=True,exist_ok=False)
    (output/'stdout.bin').write_bytes(completed.stdout)
    (output/'stderr.bin').write_bytes(completed.stderr)
    try:
        actual=json.loads(completed.stdout)
        parsed=True
    except Exception:
        actual=None;parsed=False
    checks=[]
    for i,wanted in enumerate(expected):
        got=actual[i] if isinstance(actual,list) and i<len(actual) else None
        checks.append({'fixture_index':i,'ok':parsed and canonical(got)==canonical(wanted),
                       'expected':wanted,'actual':got})
    result={'schema':'wrd11-real-local-cpu-fixture-result','tool_identity':'PYTHON_SUBPROCESS_NOT_OPENCLAW',
        'program':pin(program),'input_sha256':hashlib.sha256(canonical(fixtures).encode()).hexdigest(),
        'explicit_child_encoding':{'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'},
        'actual_exit_code':completed.returncode,'json_parse_ok':parsed,
        'output_length_ok':isinstance(actual,list) and len(actual)==len(expected),
        'passed':sum(c['ok'] for c in checks),'total':len(checks),'checks':checks,
        'all_passed':completed.returncode==0 and parsed and isinstance(actual,list) and len(actual)==len(expected) and all(c['ok'] for c in checks),
        'stdout':pin(output/'stdout.bin'),'stderr':pin(output/'stderr.bin'),
        'elapsed_seconds_observed_local_CPU':elapsed,
        'business_Q_measured':False,'business_qualified_KEEP':False,'model_tokens_or_GPU_energy_measured':False}
    jsave(output/'CPU_RESULT.json',result)
    return result


def summarize_result(result):
    return {k:result[k] for k in ['tool_identity','program','input_sha256','actual_exit_code','passed','total','checks','all_passed','business_Q_measured','business_qualified_KEEP']}


def evidence(path):
    return {'kind':'ACTUAL_LOCAL_CPU_OBSERVATION','pin':pin(path),'not_native_agent_feedback':True}


def case_record(family, case_kind, point, target_R, target_D, negative, pins, action=None):
    key=f"cpu11-{family['family_id']}-{case_kind}"
    target={'R':target_R,'D':target_D,'new_author_reasoning':True}
    if action is not None:target['resource_action_projection']=action
    return {'schema':SCHEMA,'id':key,'family_id':family['family_id'],
        'synthetic_root_id':'cpu11-family-'+family['family_id'],
        'enterprise_source_ids':[],'independence_unit':'SYNTHETIC_MECHANISM_FAMILY_NOT_ENTERPRISE_SOURCE',
        'stage':('B' if action else 'D' if case_kind=='cost_unknown_hold' else 'C'),
        'provenance':{'kind':PROVENANCE,'recorded_teacher_R':False,'recorded_native_execution':False,
                      'all_text_new_authored':True,'enterprise_content_copied':False,
                      'mechanism_reference_only':['WRD10-local-formatter-counterexample','WRD10-verifier-stderr-and-exit-check'],
                      'proposed_supervision_weight':0.05},
        'point_time_state':point,'available_evidence_pins':pins,
        'target':target,'rejected_alternative':negative,
        'validation':{'rule':'Only facts present in point_time_state may determine current decision; future runs are credit evidence only.',
            'business_qualified_KEEP_supported':False,'full_native_WRD_chain_demonstrated':False,
            'root_admission_required':True,'training_admitted':False},
        'not_independent_from_other_cases_in_same_family':True}


def build(output):
    output=output.resolve();assert not output.exists(),'NEW_OUTPUT_ROOT_REQUIRED'
    output.mkdir(parents=True)
    data=families(); records=[]; index=[]
    for f in data:
        root=output/'families'/f['family_id'];root.mkdir(parents=True)
        jsave(root/'FIXTURES.json',{'scope':'NEW_SYNTHETIC_INPUTS_AND_DECLARED_EXPECTED_OUTPUTS','inputs':f['fixtures'],'expected':f['expected']})
        jsave(root/'CONTRACT.json',{'family_id':f['family_id'],'mechanism':f['mechanism'],
            'all_cases_derive_from_this_single_synthetic_family':True,'domain_business_Q_not_claimed':True})
        results={}
        for version, text in f['versions'].items():
            program=root/'versions'/version/'resource.py';program.parent.mkdir(parents=True)
            program.write_bytes(text.encode())
            results[version]=run_version(program,f['fixtures'],f['expected'],root/'runs'/version)
        assert not results['v0']['all_passed'] and not results['noop']['all_passed']
        assert results['v1']['all_passed'] and not results['regression']['all_passed'], f['family_id']
        assert results['v0']['program']['sha256']==results['noop']['program']['sha256']
        assert results['v0']['checks']==results['noop']['checks']
        base={'fixture_scope':'SYNTHETIC_RESOURCE_COMPONENT_ONLY','family_id':f['family_id'],
            'resource_contract':f['mechanism'],'declared_fixture_inputs':f['fixtures'],
            'expected_local_outputs':f['expected'],'native_or_teacher_execution_observed':False,
            'independent_business_consumer_trials':[],'business_quality_Q':None,
            'total_per_qualified_skill_cost':None,'qualified_KEEP_count':0}
        def point(version, history=()):
            return {**base,'current_version':version,'resource_file':{'path':'resources/'+f['family_id']+'/resource.py',
                'content':f['versions'][version],'sha256':results[version]['program']['sha256']},
                'visible_run':summarize_result(results[version]),'visible_prior_runs':[summarize_result(results[v]) for v in history]}
        def pins(versions):return [evidence(root/'runs'/v/'CPU_RESULT.json') for v in versions]
        fail_count=results['v0']['total']-results['v0']['passed']
        failure_R=f"当前版本在{results['v0']['total']}个明确合同检查中有{fail_count}个失败。{f['diagnosis']}应先针对已观察失败修订，再用相同输入复验；退出码或外层成功状态不能覆盖这些失败。"
        records.append(case_record(f,'diagnose_v0',point('v0'),failure_R,
            {'decision':'REVISE_RESOURCE','scope':'LOCAL_RESOURCE_CORRECTNESS','next_step':'REPAIR_AND_RECHECK_SAME_INPUTS'},
            {'decision':'ACCEPT_RESOURCE','why_rejected':'真实合同检查至少一项失败。'},pins(['v0'])))
        repair_R=f"失败与输入合同已明确。{f['repair']}只替换当前资源程序，后续同输入测试结果仍需实际取得，不能提前宣称通过或KEEP。"
        repair_case=case_record(f,'write_verified_repair',point('v0'),repair_R,
            {'decision':'REPLACE_RESOURCE','scope':'LOCAL_RESOURCE_REPAIR','next_step':'RUN_SAME_INPUT_CHECKS'},
            {'decision':'KEEP','why_rejected':'修复动作之前没有修复版试跑结果，更无独立消费、Q或总成本。'},pins(['v0']),
            {'kind':'NEW_FUNCTIONAL_STATE_WRITE_PROJECTION','path':'resources/'+f['family_id']+'/resource.py',
             'content':f['versions']['v1'],'content_sha256':results['v1']['program']['sha256'],
             'not_recorded_native_tool_call':True})
        repair_case['validation']['future_same_input_credit_evidence']=evidence(root/'runs/v1/CPU_RESULT.json')
        records.append(repair_case)
        records.append(case_record(f,'noop_repair_still_fails',point('noop',['v0']),
            f"所谓修订版程序SHA与原版相同，复跑失败项也相同；修改了状态名不能当作修复。{f['repair']}再次改资源后仍须同输入复验。",
            {'decision':'REVISE_RESOURCE','scope':'NOOP_REPAIR_REJECTED','next_step':'CHANGE_RESOURCE_AND_RECHECK'},
            {'decision':'ACCEPT_REVISION','why_rejected':'仅版本标签变化，字节与失败证据未变。'},pins(['v0','noop'])))
        records.append(case_record(f,'regression_detected',point('regression',['v1']),
            f"曾通过检查的v1不能替后来的不同SHA版本背书；当前回归版本实际只通过{results['regression']['passed']}/{results['regression']['total']}项。{f['diagnosis']}保留历史正确版本，针对当前失败修订。",
            {'decision':'REVISE_RESOURCE','scope':'CURRENT_VERSION_REGRESSION','next_step':'RESTORE_VERIFIED_BEHAVIOR_AND_RECHECK'},
            {'decision':'INHERIT_PASS_FROM_V1','why_rejected':'当前资源SHA不同且同输入实测失败。'},pins(['v1','regression'])))
        records.append(case_record(f,'local_pass_needs_consumption',point('v1',['v0']),
            f"当前SHA版本在已声明的{results['v1']['total']}个本地合同检查全部通过，支持局部资源正确性。它还没有独立业务消费轨迹、校准Q或完整成本，下一步应取独立同类输入进行消费评价，不能升级为合格技能KEEP。",
            {'decision':'REQUEST_INDEPENDENT_CONSUMPTION','scope':'LOCAL_CHECKS_PASSED_UTILITY_UNKNOWN','next_step':'COLLECT_INDEPENDENT_SAME_VERSION_CONSUMER_EVIDENCE'},
            {'decision':'KEEP','why_rejected':'本地fixture全过不等于独立业务效用已证。'},pins(['v0','v1'])))
        cost_point=point('v1',['v0']);cost_point['requested_closure']='Report total cost per qualified skill now.'
        cost_point['cost_ledger']={'local_CPU_checks_observed':True,'AI_curation_cash_or_tokens':'UNKNOWN_NOT_ZERO',
            'model_training_cost':None,'independent_evaluation_cost':None,'business_generation_and_repair_cost':None,
            'qualified_skill_count':0,'reported_unit_cost':'UNDEFINED_K_ZERO'}
        records.append(case_record(f,'cost_unknown_hold',cost_point,
            '本地检查通过，但合格技能数仍为0且采集、AI整理、训练、独立评价与生成修订总成本尚未齐全。分母为0时每合格技能成本未定义；未知费用不能填0，也不能用本地程序耗时替代整体成本。',
            {'decision':'HOLD','scope':'TOTAL_QUALIFIED_SKILL_COST_UNDEFINED','qualified_skill_count':0,
             'unit_cost':None,'missing':['independent_consumer_evidence','calibrated_quality_Q','complete_cost_ledger']},
            {'decision':'REPORT_ZERO_UNIT_COST','why_rejected':'K=0且成本缺失，不能声称单位成本为0。'},pins(['v0','v1'])))
        index.append({'family_id':f['family_id'],'fixtures':len(f['fixtures']),'expected_outputs':len(f['expected']),
            'versions':{v:{'source':results[v]['program'],'passed':results[v]['passed'],'total':results[v]['total'],
                            'all_passed':results[v]['all_passed'],'result':pin(root/'runs'/v/'CPU_RESULT.json')} for v in results},
            'same_input_noop_detected':True,'same_input_regression_detected':True,'business_KEEP_supported':False})
    raw=output/'CASES.jsonl';raw.write_bytes(b''.join((canonical(x)+'\n').encode() for x in records))
    ids=[x['id'] for x in records];assert len(ids)==len(set(ids))
    for r in records:
        assert r['provenance']['kind']==PROVENANCE and not r['enterprise_source_ids']
        assert r['validation']['business_qualified_KEEP_supported'] is False
        for e in r['available_evidence_pins']:
            p=Path(e['pin']['path']);assert sha(p)==e['pin']['sha256']
        if 'future_same_input_credit_evidence' in r['validation']:
            future=r['validation']['future_same_input_credit_evidence']['pin']
            assert all(x['pin']['sha256']!=future['sha256'] for x in r['available_evidence_pins'])
            assert all(x['program']['sha256']!=r['target']['resource_action_projection']['content_sha256']
                       for x in r['point_time_state']['visible_prior_runs'])
            assert r['point_time_state']['current_version']=='v0'
    qa={'schema':SCHEMA,'status':'PASS_CPU_OBSERVATIONS_NEW_AUTHORED_CASES_PENDING_ROOT_SEMANTIC_AND_TOKEN_ADMISSION',
        'families':len(data),'cases':len(records),'family_correlated_cases_not_independent_enterprise_examples':True,
        'real_CPU_program_invocations':len(data)*4,'local_fixture_checks_per_version':sum(len(x['fixtures']) for x in data),
        'actual_total_local_fixture_checks':sum(len(x['fixtures'])*4 for x in data),
        'by_case_kind':dict(Counter(x['id'].rsplit('-',1)[-1] for x in records)),
        'by_stage':dict(Counter(x['stage'] for x in records)),
        'all_v0_and_noop_fail':all(not x['versions']['v0']['all_passed'] and not x['versions']['noop']['all_passed'] for x in index),
        'all_v1_pass':all(x['versions']['v1']['all_passed'] for x in index),
        'all_regression_fail':all(not x['versions']['regression']['all_passed'] for x in index),
        'cases_file':pin(raw),'source_code':pin(Path(__file__)),
        'proposed_synthetic_weight':0.05,'original_teacher_R_added':0,'original_native_A_added':0,
        'business_qualified_KEEP_added':0,'full_native_WRD_chains_added':0,
        'training_admitted':False,'model_or_training_started':False,'native_business_sessions_started':0,
        'GPU_or_token_cost_measured':False,'cost_unknown_is_not_zero':True,
        'independent_peer_QA_required':True,'families_index':index}
    jsave(output/'CPU_CASES_QA.json',qa)
    jsave(output/'CASE_INDEX.json',{'schema':SCHEMA,'cases':[{'id':r['id'],'family_id':r['family_id'],'stage':r['stage'],
        'decision':r['target']['D']['decision'],'synthetic_root_id':r['synthetic_root_id']} for r in records]})
    text=('本目录是新作者合成的离线资源组件数据，不是原生Agent轨迹。\n\n'
          f'实际{len(data)}个机制family、{len(records)}个相关点时case，{len(data)*4}次真实CPU程序运行。'
          '原版/无效修订/回归均有实际失败，正确版同输入全部通过。\n'
          '每个family只有一个合成独立单元，不能把60个case当60企业来源；资源程序、fixture、输出、stderr、版本hash与真实反馈齐备。\n'
          'write_verified_repair输入只有v0及已发生失败；v1结果只作为包外信用验证字段，不进point_time_state。'
          '全R均新作者简短决策依据，建议初始权重0.05并受总合成有效监督占比上限约束，等待根语义及双token/mask准入；这里不批准训练。\n'
          '所有业务Q、合格KEEP、完整原生自主链均未构造或声称已证；K=0单位成本未定义。'
          '本地通过只支持局部合同，不代表真实业务效用。\n')
    (output/'README.md').write_bytes(text.encode())
    print(json.dumps({k:qa[k] for k in ['status','families','cases','real_CPU_program_invocations','actual_total_local_fixture_checks','by_stage','training_admitted','model_or_training_started']},ensure_ascii=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=DEFAULT_OUT)
    build(ap.parse_args().out)
