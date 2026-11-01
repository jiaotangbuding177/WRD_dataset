"""Exercise objective_adapter58 against every actual WRD58 optimizer step."""
from pathlib import Path
from array import array
from fractions import Fraction
from decimal import Decimal
import gc
import hashlib
import importlib.util
import json
import math
import sys

sys.dont_write_bytecode=True
ROOT=Path(r'D:\skillloop\output\20261101_wrd_final_audit58/active_dataset58/final1260')
OUT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def weights_sha(values):
    v=array('d',values)
    if sys.byteorder!='little':v.byteswap()
    return hashlib.sha256(v.tobytes()).hexdigest()
def feature_fingerprint(features):
    result={}
    for key,kind in [('input_ids','I'),('labels','q'),('attention_mask','B'),('loss_weights','d')]:
        values=array(kind,features[key])
        if sys.byteorder!='little'and values.itemsize>1:values.byteswap()
        result[key]=hashlib.sha256(values.tobytes()).hexdigest()
    return result
def expect_rejection(fn):
    try:fn()
    except ValueError:return True
    raise AssertionError('ADAPTER_DID_NOT_REJECT_INVALID_OR_REPEATED_INPUT')
def exact(v):return Fraction(Decimal(str(v)))
def scale(v):return Fraction(int(v['numerator']),int(v['denominator']))
entry=load(ROOT/'TRAINING_ENTRYPOINT58.json');course=load(ROOT/'COURSE58.json')
assert sha(ROOT/'TRAINING_ENTRYPOINT58.json')=='1e12ff09193d8548673e9ec47cc8486c1a4aacf1782f5dfccba7435a26b38bcd'
lp=ROOT/entry['loader']['path'];assert sha(lp)=='8b107ec2cb6ed1af29cbf4c25bd2158884097aab05cf0d8e31efbc944115c27a'
loader=mod(lp,'reviewed58_adapter_feature_loader');adapter=mod(OUT/'objective_adapter58.py','objective_adapter58_under_test')
oracle=load(ROOT/'PER_STEP_LOSS_CONTRACT58.json');oracle={(r['profile'],r['global_step']):r for r in oracle['steps']}
profiles={};base=Path(r'D:\skillloop\output\wrd10root01');package=Path(r'D:\skillloop\output\wrd11publicroot01')
for profile,pc in course['profiles'].items():
    cache={}
    for value in loader.iter_features(ROOT,base,package,profile=profile,immutable_loader_path=ROOT/entry['immutable_loader']['path'],with_metadata=True,expected_manifest_sha256=entry['dataset_manifest']['sha256']):
        cache[value['id']]=value
    assert len(cache)==1260
    checks=[];double_rejected=0;stripped_marker_rejected=0;scaled_count=0;no_aux=0
    for phase in pc['phases']:
        for step in phase['steps']:
            loaded=[cache[r['id']]for r in step['microbatches']]
            before=[feature_fingerprint(r['features'])for r in loaded]
            prepared=adapter.prepare_optimizer_step(step,loaded)
            assert prepared['denominator']==sum(sum(v!=-100 for v in r['features']['labels'][1:])for r in loaded)
            ce={r['id']:[1+(token%17)/17 for token in r['features']['input_ids']]for r in loaded}
            measured=adapter.reference_step_loss(prepared,ce)
            reference=oracle[(profile,step['global_step_one_based'])]['deterministic_proxy_CE_loss_not_model_loss']
            assert math.isclose(measured,reference,rel_tol=1e-11,abs_tol=1e-12)
            for original,effective in zip(loaded,prepared['microbatches']):
                for key in ['input_ids','labels','attention_mask']:assert original['features'][key]is effective['features'][key]
                assert original['features']['loss_weights']is not effective['features']['loss_weights']
            assert before==[feature_fingerprint(r['features'])for r in loaded]
            double_rejected+=expect_rejection(lambda:adapter.prepare_optimizer_step(step,prepared['microbatches']))
            alpha=scale(step['auxiliary_extra_loss_scale']);scaled_count+=alpha<1;no_aux+=not any(r['pool']=='synthetic'for r in loaded)
            if alpha<1:
                stripped=[dict(r,features={k:v for k,v in r['features'].items()if k!=adapter.APPLIED_MARKER})for r in prepared['microbatches']]
                stripped_marker_rejected+=expect_rejection(lambda:adapter.prepare_optimizer_step(step,stripped))
            # The cap is checked independently from adapter metadata using the
            # actual returned weights and each microbatch's declared pool.
            actual_mass=math.fsum(w for r in prepared['microbatches']for label,w in zip(r['features']['labels'][1:],r['features']['loss_weights'][1:])if label!=-100)
            actual_aux=math.fsum(w for r in prepared['microbatches']if r['pool']=='synthetic'for label,w in zip(r['features']['labels'][1:],r['features']['loss_weights'][1:])if label!=-100)
            assert actual_aux/actual_mass<=0.2+1e-12
            checks.append({'global_step':step['global_step_one_based'],'microbatches':len(loaded),'denominator':prepared['denominator'],'scaled':alpha<1,'effective_aux_fraction':actual_aux/actual_mass,'proxy_loss_match':True,'base_features_unchanged':True,'double_scaling_rejected':True})
    assert len(checks)==241 and scaled_count==92 and no_aux==26
    assert checks[25]['microbatches']==1 and checks[-1]['microbatches']==3
    assert double_rejected==241 and stripped_marker_rejected==92
    profiles[profile]={'actual_feature_targets':1260,'optimizer_steps_checked':len(checks),'scaled_steps_checked':scaled_count,'no_auxiliary_steps_checked':no_aux,'tail_contract_microbatches':checks[25]['microbatches'],'tail_process_microbatches':checks[-1]['microbatches'],'maximum_effective_auxiliary_fraction_from_returned_weights':max(r['effective_aux_fraction']for r in checks),'duplicate_scale_rejections':double_rejected,'removed_marker_already_scaled_rejections':stripped_marker_rejected,'all_variable_CE_oracles_match':True,'all_base_arrays_unchanged':True}
    del cache,loaded,prepared,ce
    gc.collect()
result={'schema':'wrd58-actual-features-objective-adapter-qa-v1','status':'PASS_ACTUAL1260_BOTH_PROFILES_ALL241_STEPS_EXECUTABLE_OBJECTIVE_ADAPTER','profiles':profiles,'all_four_base_features_SHA_checked_before_and_after_every_step':True,'float64_coefficient_mass_roundoff_tolerance':1e-12,'source_adapter_sha256':sha(OUT/'objective_adapter58.py'),'source_verifier_sha256':sha(Path(__file__)),'frozen_entrypoint_sha256':sha(ROOT/'TRAINING_ENTRYPOINT58.json'),'frozen_course_sha256':sha(ROOT/'COURSE58.json'),'independent_variable_CE_oracle_sha256':sha(ROOT/'PER_STEP_LOSS_CONTRACT58.json'),'original205_active_freeze_modified':False,'CPU_reference_is_not_model_loss_or_accuracy':True,'model_or_native_calls':0,'training_started':False}
(OUT/'OBJECTIVE_ADAPTER_QA58.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
