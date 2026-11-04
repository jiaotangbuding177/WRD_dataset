"""Clarify metadata scopes after actual-feature validation; preserve initial pins."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
import hashlib
import json
import shutil

ROOT=Path(r'D:\skillloop\output\20261101_wrd_final_audit58/active_dataset58/final1260')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p):return {'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def frac(value):return Fraction(Decimal(str(value)))
def dstr(v):return str(Decimal(v.numerator)/Decimal(v.denominator))
def scale(s):return Fraction(int(s['numerator']),int(s['denominator']))
hist=ROOT/'metadata_history58/initial_actual_feature_build'
assert not hist.exists()
hist.mkdir(parents=True)
files=['COURSE58.json','CONFIG58.json','FEATURE_TO_COURSE_LOSS_QA58.json','TRAINING_ENTRYPOINT58.json','CHECKPOINT_READY58.json']
initial={}
for name in files:
    shutil.copyfile(ROOT/name,hist/name);initial[name]=sha(ROOT/name)
course=load(ROOT/'COURSE58.json')
for profile,p in course['profiles'].items():
    for phase in p['phases']:
        em=Fraction(0);ea=Fraction(0);nt=Fraction(0);na=Fraction(0)
        for step in phase['steps']:
            mr=frac(step['original_real_weighted_mass']);ma=frac(step['original_auxiliary_weighted_mass']);alpha=scale(step['auxiliary_extra_loss_scale']);denom=step['valid_shifted_target_denominator']
            assert alpha<=1 and alpha>0 and ma*alpha<=mr/4
            if alpha<1:assert ma*alpha==mr/4
            this=mr+ma*alpha;em+=this;ea+=ma*alpha;nt+=this/denom;na+=ma*alpha/denom
        phase['effective_course_summary']={'weighted_mass':dstr(em),'auxiliary_weighted_mass':dstr(ea),'auxiliary_mass_fraction':float(ea/em),'sum_step_normalized_auxiliary_coefficient_fraction':float(na/nt),'original_bin_weights_unmodified':True,'coefficient_mass_not_CE_gradient_or_Adam':True}
        # Compatibility aliases name actual exposures, not new unique tasks.
        phase['summary'].update({'sequence_exposures':phase['summary']['unique_targets'],'sequence_tokens_unpadded':phase['summary']['sequence_tokens'],'positive_tokens_exposed':phase['summary']['positive_tokens'],'weighted_mass_exposed':phase['summary']['weighted_mass']})
    process=p['phases'][1];steps=process['steps'];mix=p['batch_mass_audit']
    fractions=[s['synthetic_fraction_of_weighted_mass']for s in steps]
    mix.update({'local_synthetic_fraction_over20percent_batches':sum(v>.2 for v in fractions),'local_synthetic_fraction100percent_batches':sum(v==1 for v in fractions),'max_local_synthetic_fraction':max(fractions),'step_extra_scale_batches':sum(scale(s['auxiliary_extra_loss_scale'])<1 for s in steps),'step_effective_aux_over_cap_batches':sum(s['effective_auxiliary_fraction_of_weighted_mass']>.2+1e-12 for s in steps),'max_step_effective_aux_mass_fraction':max(s['effective_auxiliary_fraction_of_weighted_mass']for s in steps),'uncapped_fields_are_original_array_weight_mass_not_applied_training_mass':True})
course['post_build_metadata_clarification']={'source_sha256':sha(Path(__file__)),'initial_course_sha256':initial['COURSE58.json'],'data_arrays_masks_and_ID_order_modified':False}
save(ROOT/'COURSE58.json',course)
config=load(ROOT/'CONFIG58.json')
config['loss']['numerator']='sum(original_span_weight_i * extra_course_scale_i * CE_i) across one accumulated optimizer step'
config['loss']['denominator']='count of all nonignored shifted targets across the accumulated optimizer step, unchanged by auxiliary scaling'
config['loss']['the_new627_weight005_is_base_array_weight_before_extra_course_scale']=True
config['loss']['per_step_synthetic_coefficient_mass_cap']=0.20
config['loss']['scale_numeric_representation']='Exact rational numerator/denominator in course; float64 supplied for runtime, allow only declared roundoff tolerance, do not approximate alpha by a new threshold.'
config['course_sha256']=sha(ROOT/'COURSE58.json');config['process_batch_mixing']=course['profiles']['budget_projection']['batch_mass_audit']
config['metadata_initial_actual_feature_build']={'config_sha256':initial['CONFIG58.json'],'course_sha256':initial['COURSE58.json'],'metadata_clarification_source_sha256':sha(Path(__file__))}
save(ROOT/'CONFIG58.json',config)
qa=load(ROOT/'FEATURE_TO_COURSE_LOSS_QA58.json')
qa.update({'course_sha256':sha(ROOT/'COURSE58.json'),'config_sha256':sha(ROOT/'CONFIG58.json'),'initial_actual_feature_QA_sha256':initial['FEATURE_TO_COURSE_LOSS_QA58.json'],'post_build_metadata_clarification_source_sha256':sha(Path(__file__)),'actual_feature_inputs_unchanged_by_clarification':True,'effective_phase_summaries':{p:{q['name']:q['effective_course_summary']for q in v['phases']}for p,v in course['profiles'].items()}})
save(ROOT/'FEATURE_TO_COURSE_LOSS_QA58.json',qa)
entry=load(ROOT/'TRAINING_ENTRYPOINT58.json')
for key,name in [('course','COURSE58.json'),('config','CONFIG58.json'),('course_QA','FEATURE_TO_COURSE_LOSS_QA58.json')]:entry[key]=ref(ROOT/name)
save(ROOT/'TRAINING_ENTRYPOINT58.json',entry)
ready=load(ROOT/'CHECKPOINT_READY58.json');ready['entrypoint']=ref(ROOT/'TRAINING_ENTRYPOINT58.json');ready['course_effective_summary']={p:v['effective_course_summary']for p,v in course['profiles'].items()};ready['phase_effective_summary']=qa['effective_phase_summaries'];save(ROOT/'CHECKPOINT_READY58.json',ready)
shutil.copyfile(Path(__file__),ROOT/'tooling/finalize_course_metadata58.py')
save(ROOT/'METADATA_SCOPE_FINALIZATION58.json',{'status':'PASS_METADATA_SCOPES_CLARIFIED_NO_ARRAY_OR_COURSE_ORDER_CHANGE','initial_pins':initial,'final_entrypoint':ref(ROOT/'TRAINING_ENTRYPOINT58.json'),'final_course':ref(ROOT/'COURSE58.json'),'final_config':ref(ROOT/'CONFIG58.json'),'source_sha256':sha(Path(__file__)),'training_started':False})
print(json.dumps({'entrypoint_sha256':sha(ROOT/'TRAINING_ENTRYPOINT58.json'),'course_sha256':sha(ROOT/'COURSE58.json'),'config_sha256':sha(ROOT/'CONFIG58.json'),'process_effective':course['profiles']['budget_projection']['phases'][1]['effective_course_summary'],'batch_mass_audit':course['profiles']['budget_projection']['batch_mass_audit'],'training_started':False},ensure_ascii=False))
