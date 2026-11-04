"""Independent post-build real-feature/course loss-contract verification. CPU only."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import argparse
import hashlib
import importlib.util
import json
import math
import sys

sys.dont_write_bytecode=True
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(v,m):
    if not v:raise ValueError(m)
def exact(v):return Fraction(Decimal(str(v)))
def decode_scale(v):
    r=Fraction(int(v['numerator']),int(v['denominator']))
    require(abs(float(r)-v['float64'])<1e-14,'SCALE_FLOAT_FRACTION_DIFFERS')
    return r
def main():
    require(not sys.flags.optimize,'OPTIMIZED_PYTHON_REJECTED')
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--base-root',type=Path,required=True);ap.add_argument('--package11-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    root=a.root.resolve();require(not a.out.exists(),'PRESERVE_PRIOR_QA')
    entry=load(root/'TRAINING_ENTRYPOINT58.json')
    for key in ['dataset_manifest','compatibility_manifest','dataset_pin','compatibility_pin','loader','immutable_loader','course','config','course_QA']:
        ref=entry[key];p=root/ref['path'];require(p.is_file()and p.stat().st_size==ref['bytes']and sha(p)==ref['sha256'],'ENTRY_PIN_MISMATCH:'+key)
    require((root/'ACTIVE_DATASET_MANIFEST57.json').read_bytes()==(root/'ACTIVE_DATASET_MANIFEST58.json').read_bytes(),'COMPATIBLE_MANIFEST_NOT_BYTE_IDENTICAL')
    p=root/entry['loader']['path'];require(sha(p)=='8b107ec2cb6ed1af29cbf4c25bd2158884097aab05cf0d8e31efbc944115c27a','ACTIVE_PARSER_NOT_REVIEWED')
    old=root/entry['immutable_loader']['path'];require(sha(old)=='a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c','LEGACY_PARSER_NOT_REVIEWED')
    spec=importlib.util.spec_from_file_location('trusted_readonly_active58_feature_reader',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    course=load(root/'COURSE58.json');config=load(root/'CONFIG58.json');manifest=load(root/'ACTIVE_DATASET_MANIFEST58.json')
    prior=load(root/'PER_STEP_LOSS_CONTRACT58.json');prior_steps={(r['profile'],r['global_step']):r for r in prior['steps']}
    reports={};profiles_positive={}
    for profile,pc in course['profiles'].items():
        records={};sequence=0;positive=0;mass=Fraction(0)
        for item in m.iter_features(root,a.base_root,a.package11_root,profile=profile,immutable_loader_path=old,with_metadata=True,expected_manifest_sha256=entry['dataset_manifest']['sha256']):
            f=item['features'];rid=item['id'];require(rid not in records,'DUPLICATE_ACTIVE_ID')
            positions=[i for i,label in enumerate(f['labels'])if label!=-100]
            require(positions and 0 not in positions,'INVALID_SHIFTED_TARGET')
            require(all(f['labels'][i]==f['input_ids'][i]and f['loss_weights'][i]>0 for i in positions),'INVALID_POSITIVE_TOKEN')
            n=len(positions);mr=sum((exact(f['loss_weights'][i])for i in positions),Fraction(0))
            proxy=math.fsum(f['loss_weights'][i]*(1+(f['input_ids'][i]%17)/17)for i in positions)
            payload=hashlib.sha256(b''.join(int(f['labels'][i]).to_bytes(4,'little')for i in positions)).hexdigest()
            records[rid]={'pool':item['pool'],'n':n,'mass':mr,'proxy':proxy,'positive_sha':payload};sequence+=len(f['input_ids']);positive+=n;mass+=mr
        require(len(records)==1260 and positive==295478 and mass==exact('85003.30'),'ACTIVE_COUNTS_OR_ARRAY_WEIGHT_MASS')
        profiles_positive[profile]={rid:(v['n'],v['positive_sha'])for rid,v in records.items()}
        stepids=[];max_fraction=Fraction(0);effective_mass=Fraction(0);effective_aux=Fraction(0);scaled=0
        for phase in pc['phases']:
            for step in phase['steps']:
                stepids.extend(r['id']for r in step['microbatches']);n=sum(records[r['id']]['n']for r in step['microbatches'])
                mr=sum((records[r['id']]['mass']for r in step['microbatches']if r['pool']!='synthetic'),Fraction(0));ma=sum((records[r['id']]['mass']for r in step['microbatches']if r['pool']=='synthetic'),Fraction(0));alpha=decode_scale(step['auxiliary_extra_loss_scale'])
                require(n==step['valid_shifted_target_denominator']and mr>0,'SHIFTED_DENOMINATOR_OR_REAL_ANCHOR')
                require(mr==exact(step['original_real_weighted_mass'])and ma==exact(step['original_auxiliary_weighted_mass']),'ARRAY_MASS_NOT_ACTUAL_FEATURES')
                require(0<alpha<=1 and ma*alpha<=mr/4,'EFFECTIVE_AUXILIARY_MASS_CAP')
                require((alpha==1 and ma<=mr/4)or(alpha<1 and ma*alpha==mr/4),'ALPHA_NOT_MAXIMAL_ALLOWED_UNDER_DECLARED_CAP')
                numerator=0.0
                for r in step['microbatches']:
                    record=records[r['id']];s=decode_scale(r['extra_course_loss_scale']);require(s==(alpha if r['pool']=='synthetic'else 1),'WRONG_POOL_EXTRA_SCALE')
                    require(r['positive_tokens']==record['n']and r['positive_token_ids_sha256_u32le']==record['positive_sha'],'MICROBATCH_POSITIVE_IDS_DIFFER')
                    numerator+=record['proxy']*float(s)
                probe=numerator/n;first=prior_steps[(profile,step['global_step_one_based'])]
                require(math.isclose(probe,first['deterministic_proxy_CE_loss_not_model_loss'],rel_tol=1e-11,abs_tol=1e-12),'INDEPENDENT_PROXY_LOSS_DIFFERS')
                total=mr+alpha*ma;aux=alpha*ma;fraction=aux/total
                max_fraction=max(max_fraction,fraction);effective_mass+=total;effective_aux+=aux;scaled+=alpha<1
        require(len(stepids)==len(set(stepids))==1260,'COURSE_NOT_EXACT_SINGLE_PASS')
        require(len([s for ph in pc['phases']for s in ph['steps']])==241,'WRONG_UPDATE_COUNT')
        require(not set(stepids)&set(manifest['excluded_original_primary_ids']),'EXCLUDED_SOURCE_TARGET_REINTRODUCED')
        reports[profile]={'unique_targets':len(records),'positive_tokens':positive,'sequence_tokens':sequence,'array_weighted_mass':str(Decimal(mass.numerator)/Decimal(mass.denominator)),'course_effective_weighted_mass':str(Decimal(effective_mass.numerator)/Decimal(effective_mass.denominator)),'course_effective_auxiliary_mass':str(Decimal(effective_aux.numerator)/Decimal(effective_aux.denominator)),'maximum_step_effective_auxiliary_fraction':float(max_fraction),'steps_scaled':scaled,'optimizer_steps':241,'source_of_checks':'actual_binary_four_features_then_independent_invariants_and_variable_per_token_CPU_loss_probe'}
    require(profiles_positive['budget_projection']==profiles_positive['full_native53'],'CROSS_PROFILE_SUPERVISED_PAYLOADS')
    require(config['candidate_checkpoint_global_steps']==[0,26,80,134,188,241],'CHECKPOINT_SELECTION_CONTRACT_CHANGED')
    result={'schema':'wrd58-independent-post-build-feature-course-loss-qa-v1','status':'PASS_REAL1260_FOUR_FEATURES_AND_PER_STEP_LOSS_CAP_DENOMINATOR_SCALES_BOTH_PROFILES','profiles':reports,'new_model_or_native_calls':0,'proxy_probe_not_model_loss_or_accuracy':True,'entrypoint_sha256':sha(root/'TRAINING_ENTRYPOINT58.json'),'course_sha256':sha(root/'COURSE58.json'),'config_sha256':sha(root/'CONFIG58.json'),'verifier_source_sha256':sha(Path(__file__)),'training_started':False}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
