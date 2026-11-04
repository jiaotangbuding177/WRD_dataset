import hashlib,importlib.util,json,math,subprocess,sys,time
from fractions import Fraction
from pathlib import Path
ROOT=Path('/workspace');OLD=ROOT/'qa_private/old_probe.py';NEW=ROOT/'qa_private/proportional_split.py';steps=[];checks=0
def verify(condition,label):
    global checks
    assert condition,label
    checks+=1
def run(label,script,args,wanted):
    folder=ROOT/label;folder.mkdir();t=time.monotonic();r=subprocess.run([sys.executable,str(script),*args],cwd=folder,capture_output=True,text=True);(folder/'stdout.txt').write_text(r.stdout);(folder/'stderr.txt').write_text(r.stderr);steps.append({'label':label,'expected_exit':wanted,'actual_exit':r.returncode,'wall_seconds':time.monotonic()-t});verify(r.returncode==wanted,label);return folder,r
# Reproduce only the old CLI-dispatch defect, not a business task or loop.
old,r=run('old_equals_flags',OLD,['--increase=100','--post-stake=0.25','--pre-registered=100','--out=outputs/requested.json'],0)
verify(json.loads(r.stdout)['increase_amount']==480.0,'old silently used fixed sample');verify(not(old/'outputs/requested.json').exists(),'old ignored requested output')
new,r=run('new_equals_flags',NEW,['--increase=100','--post-stake=0.25','--pre-registered=100','--out=outputs/requested.json'],0);result=json.loads(r.stdout);verify(result==json.loads((new/'outputs/requested.json').read_text()),'CLI stdout=file');verify(result['increase_amount']==100.0 and result['post_money_valuation']==400.0 and result['pre_money_valuation']==300.0,'explicit CLI values')
missing,r=run('new_missing_C',NEW,['--increase','100','--post-stake','0.25','--out','outputs/result.json'],0);result=json.loads(r.stdout);verify('formula'in result and'new_registered_capital'not in result and'capital_reserve'not in result,'missing C stays symbolic')
noflags,r=run('new_required_flags',NEW,[],2);verify(not(noflags/'outputs').exists(),'missing CLI flags have no sample side effect')
invalid,r=run('new_invalid_domain',NEW,['--increase','100','--post-stake','1','--out','outputs/result.json'],1);verify(not(invalid/'outputs/result.json').exists(),'invalid s no result written')
spec=importlib.util.spec_from_file_location('scoped_math',NEW);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parameters=0
for i in(1,7,100,999999):
    for s in(Fraction(1,100),Fraction(1,8),Fraction(1,4),Fraction(1,2),Fraction(99,100)):
        post=Fraction(i)/s;pre=post-i
        for factor in(Fraction(1,10),Fraction(1,2),Fraction(1)):
            c=pre*factor;r=module.compute_valuation(float(i),float(s),float(c));parameters+=1
            expected={'post_money_valuation':post,'pre_money_valuation':pre,'price_per_unit':pre/c,'new_registered_capital':Fraction(i)*c/pre,'capital_reserve':Fraction(i)-Fraction(i)*c/pre,'implied_post_stake':s}
            for key,v in expected.items():verify(math.isclose(r[key],float(v),rel_tol=1e-10,abs_tol=1e-10),'fraction:'+key)
        r=module.compute_valuation(float(i),float(s),None);verify('formula'in r and'new_registered_capital'not in r,'symbolic no invented split')
        verify(math.isclose(r['post_money_valuation'],float(post),rel_tol=1e-10),'symbolic still computes post')
# A changed divide formula must fail an independent rational oracle.
text=NEW.read_text();bad=text.replace('post_money = increase_amount / post_stake','post_money = increase_amount * post_stake');verify(text!=bad,'mutation unique');namespace={'__name__':'wrd_negative_oracle'};exec(compile(bad,'arithmetic_mutant','exec'),namespace)
detected=False
try:r=namespace['compute_valuation'](100.0,.25,100.0);detected=not math.isclose(r['post_money_valuation'],400.0)
except AssertionError:detected=True
verify(detected,'wrong arithmetic mutant rejected')
result={'schema':'wrd-scoped-arithmetic-resource-finite-QA-v1','status':'PASS_BOUNDED_MATHEMATICAL_MODEL_ONLY','checks_passed':checks,'fraction_oracle_parameter_cases':parameters,'steps':steps,'wrong_arithmetic_mutant_detected':True,'original_exact_CRLF_program_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),'new_complete_resource_sha256':hashlib.sha256(NEW.read_bytes()).hexdigest(),'old_dispatch_defect_reproduced':True,'new_explicit_CLI_and_missing_C_verified':True,'financial_accounting_or_legal_gold':False,'qualified_skill_or_unseen_generalization_certified':False,'Agent_sessions':0,'model_calls':0,'training':False,'python':sys.version}
(ROOT/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
