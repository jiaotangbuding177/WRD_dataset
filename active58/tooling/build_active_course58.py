"""Build new WRD58 active data and a source-identical, batch-capped course. CPU only."""
from pathlib import Path
from array import array
from collections import Counter
from decimal import Decimal
from fractions import Fraction
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import shutil
import sys

sys.dont_write_bytecode=True
REPO=Path(r'D:\skillloop')
OLD=REPO/'output/20261101_wrd_increment57/active_dataset57/native_bfc_checkpoint01'
BANK=REPO/'output/20261101_wrd_final_audit58/training_runtime/bfc_protocol_bank58'
OUT=REPO/'output/20261101_wrd_final_audit58/active_dataset58/final1260'
BASE=REPO/'output/wrd10root01'
PACKAGE=REPO/'output/wrd11publicroot01'
LOADER=REPO/'research/data_prep/wrd_increment57/active_loader57.py'
IMMUTABLE=REPO/'research/data_prep/wrd_curation11/curriculum_loader11.py'
HELPER=REPO/'research/data_prep/wrd_increment57/assemble_active57.py'
REV='5.0.58';CHANGE='ALG-20261102-01'

def require(v,m):
    if not v:raise ValueError(m)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def ref(p,root=OUT):return {'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cp(src,dst):
    require(src.is_file() and not src.is_symlink(),'SOURCE_NOT_ORDINARY_FILE')
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);require(sha(src)==sha(dst),'COPY_SHA_MISMATCH')
def module(p,name,expected):
    require(sha(p)==expected,'REVIEWED_SOURCE_PIN_CHANGED')
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def fraction(value):return Fraction(Decimal(str(value)))
def number(v):return float(v)
def decimal_string(v):return str(Decimal(v.numerator)/Decimal(v.denominator))
def ratio(v):return {'numerator':str(v.numerator),'denominator':str(v.denominator),'float64':float(v)}
def summarise(records):
    r=helper.summarize(records)
    r['valid_shifted_target_denominator']=sum(x['shifted_valid_target_count'] for x in records)
    r['effective_mass_is_course_dependent_not_in_array']=True
    return r
def pin_manifest(manifest):
    save(OUT/'ACTIVE_DATASET_MANIFEST57.json',manifest)
    cp(OUT/'ACTIVE_DATASET_MANIFEST57.json',OUT/'ACTIVE_DATASET_MANIFEST58.json')
    pin={'manifest_bytes':(OUT/'ACTIVE_DATASET_MANIFEST57.json').stat().st_size,'manifest_sha256':sha(OUT/'ACTIVE_DATASET_MANIFEST57.json'),'active_loader_sha256':sha(OUT/'tooling/active_loader57.py')}
    save(OUT/'ACTIVE_DATASET_PIN57.json',pin);cp(OUT/'ACTIVE_DATASET_PIN57.json',OUT/'ACTIVE_DATASET_PIN58.json')

require(not sys.flags.optimize,'OPTIMIZED_PYTHON_REJECTED')
require(not OUT.exists(),'NEW_ROOT_REQUIRED_NO_OVERWRITE')
require(sha(OLD/'ACTIVE_DATASET_MANIFEST57.json')=='87d6bbc67269783aef5a4a015f8ad57ba9f4f49f3e4d36a1e2a32991ef1f86d6','OLD_MANIFEST_CHANGED')
require(sha(OLD/'COURSE57_NATIVE.json')=='06b15abbbbe4870db0240d06f2a47956248796465e534c9fbe4a4699136327ff','OLD_COURSE_CHANGED')
require(sha(BANK/'BANK_ENTRYPOINT58.json')=='75356074732af43dd6578ee09d44c1b28b37741ae2356a518a5453b0d86f1033','NEW_BANK_ENTRY_CHANGED')
loader=module(LOADER,'reviewed_active58_compatible57','8b107ec2cb6ed1af29cbf4c25bd2158884097aab05cf0d8e31efbc944115c27a')
old=module(IMMUTABLE,'reviewed_immutable58','a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c')
helper=module(HELPER,'reviewed_metadata_helpers58','a287ff020d2e9a8a6d6a419ca92c8e34cfbc35becf92d8b3ec6873dfcd08a926')
OUT.mkdir(parents=True)
cp(LOADER,OUT/'tooling/active_loader57.py');cp(IMMUTABLE,OUT/'tooling/immutable_curriculum_loader11.py')
for src in (OLD/'provenance').iterdir():
    if src.is_file():cp(src,OUT/'provenance'/src.name)
manifest=load(OLD/'ACTIVE_DATASET_MANIFEST57.json')
for bank in manifest['incremental_banks'][:-1]:
    source=OLD/'banks'/bank['bank_id'];dest=OUT/'banks'/bank['bank_id']
    shutil.copytree(source,dest)
    require(all(sha(p)==sha(dest/p.relative_to(source))for p in source.rglob('*')if p.is_file()),'OLD21_BANK_COPY_CHANGED')
bank_entry=load(BANK/'BANK_ENTRYPOINT58.json')
newbankdir=OUT/'banks/bfc_protocol58';newbankdir.mkdir(parents=True)
rows=[];compiled_refs=[]
for r in bank_entry['train_files']:
    source=BANK/r['path'];require(source.stat().st_size==r['bytes']and sha(source)==r['sha256'],'NEW_COMPILED_PIN_CHANGED')
    compiled_refs.append({'path':str(source),'bytes':r['bytes'],'sha256':r['sha256']})
    with gzip.open(source,'rb')as f:
        for i,line in enumerate(f):
            if line.strip():rows.append((json.loads(line),line,compiled_refs[-1],i))
require(len(rows)==33 and {r['id']for r,_,_,_ in rows}==set(bank_entry['active_ids']),'NEW_BANK_IDS')
datafile=newbankdir/'active.train.jsonl.gz'
with datafile.open('wb')as raw:
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0)as zipped:
        for row,line,_,_ in rows:zipped.write(line if line.endswith(b'\n')else line+b'\n')
entries=[]
for i,(row,line,source_ref,source_index)in enumerate(rows):
    f=old.standard(row);loader.validate_features(row,f);stem=hashlib.sha256(row['id'].encode()).hexdigest()[:24];arrays={}
    for field,kind in [('input_ids','I'),('labels','q'),('loss_weights','f')]:
        values=array(kind,f[field]);require(values.itemsize=={'I':4,'q':8,'f':4}[kind],'ARRAY_ITEM_SIZE')
        if sys.byteorder!='little':values.byteswap()
        path=newbankdir/'arrays'/(stem+'.'+field+'.bin');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(values.tobytes());arrays[field]=ref(path)
    entry={'id':row['id'],'source_train_file':datafile.relative_to(OUT).as_posix(),'source_record_index':i,'arrays':arrays,'original_compiled_source_ref':source_ref,'original_compiled_source_record_index':source_index,'original_decompressed_line_sha256':hashlib.sha256(line).hexdigest()}
    require(old.binary(OUT,entry,row)==f,'NEW_BANK_BINARY_STANDARD_DIFFERS');entries.append(entry)
indexfile=newbankdir/'ARRAY_INDEX58.json';save(indexfile,{'schema':'wrd58-increment-canonical-arrays-v1','records':entries,'count':33})
reviewed=[]
for filename in ['BANK_ENTRYPOINT58.json','COMPILATION_REPORT.json','PROTOCOL_MASK_POLICY_AND_EXACT_RANGES58.json']:
    dest=newbankdir/'reviewed_QA'/filename;cp(BANK/filename,dest);reviewed.append(ref(dest))
prior=manifest['incremental_banks'][-1]
require(set(prior['active_ids'])==set(bank_entry['active_ids']),'REPLACEMENT_MUST_SAME_IDS')
manifest['incremental_banks'][-1]={'bank_id':'bfc_protocol58','format':'compiled_spans_canonical_binary_v1','active_ids':sorted(bank_entry['active_ids']),'target_count':33,'train_files':[ref(datafile)],'array_index':ref(indexfile),'frozen_TRAIN_source_ids':prior['frozen_TRAIN_source_ids'],'frozen_TRAIN_source_groups':prior['frozen_TRAIN_source_groups'],'source_compiled_files':compiled_refs,'reviewed_QA':reviewed,'root_admission':'ROOT_APPROVED31_VALID_ACK_CALL_PROTOCOL_F_ONLY_API5_AND33_MASK_UNCHANGED_NO_NEW_R_A_D_OR_EXPERIENCE','all_selected_rows_independently_dual_tokenized':True}
manifest.update({'design_revision':REV,'change_id':CHANGE,'schema_version':'workflow-pipeline-v1','data_revision':58,'date':'2026-11-02','compatibility_filenames_57_hold58_contents':True,'baseline57_manifest_sha256':sha(OLD/'ACTIVE_DATASET_MANIFEST57.json'),'same1260_target_IDs_and_sources':True,'new_native_or_model_calls':0,'step_auxiliary_scaling_is_in_course_not_arrays':True})
for count in manifest['actual_counts'].values():
    count['positive_tokens']+=650;count['weighted_mass']=str(Decimal(count['weighted_mass'])+Decimal('162.50'));count['positive_by_component']['F']+=650
pin_manifest(manifest)
component_map=load(OUT/'provenance/SOURCE_COMPONENT_MAP57.json')['source_to_component']
actual={};metrics={}
for profile in manifest['profiles']:
    actual[profile]=[];metrics[profile]={}
    for pool,source,entry,row in loader.iter_records(OUT,BASE,PACKAGE,profile=profile,immutable_loader_path=IMMUTABLE,expected_manifest_sha256=sha(OUT/'ACTIVE_DATASET_MANIFEST58.json')):
        f=old.binary(source,entry,row);loader.validate_features(row,f);stat=helper.record_stats(pool,row,f,component_map)
        actual[profile].append(stat)
        positive=[(token,weight)for token,label,weight in zip(f['input_ids'][1:],f['labels'][1:],f['loss_weights'][1:])if label!=-100]
        metrics[profile][row['id']]={'mass':sum((fraction(w)for _,w in positive),Fraction(0)),'denominator':len(positive),'proxy_weighted_CE_sum':sum(w*(1+(token%17)/17)for token,w in positive)}
    summary=helper.summarize(actual[profile]);require(summary==manifest['actual_counts'][profile],'NEW_MANIFEST_ACTUAL_FEATURE_COUNTS_DIFFER')
require({r['id']:(r['positive_tokens'],r['positive_token_ids_sha256_u32le'])for r in actual['budget_projection']}=={r['id']:(r['positive_tokens'],r['positive_token_ids_sha256_u32le'])for r in actual['full_native53']},'CROSS_PROFILE_POSITIVE_PAYLOAD_DIFFERS')
save(OUT/'ACTIVE_TARGET_LEDGER58.json',{'schema':'wrd58-actual-feature-ledger-v1','profiles':actual})
oldcourse=load(OLD/'COURSE57_NATIVE.json');course=copy.deepcopy(oldcourse)
course.update({'schema':'wrd58-protocol-and-local-aux-capped-onepass-course-not-launcher','design_revision':REV,'change_id':CHANGE,'data_revision':58,'baseline57_course_sha256':sha(OLD/'COURSE57_NATIVE.json'),'original241_batch_ID_order_preserved':True,'synthetic_scale_is_extra_loss_coefficient_not_in_array':True})
qa_steps=[];allalpha=[]
for profile,p in course['profiles'].items():
    lookup={r['id']:r for r in actual[profile]};p['active_manifest_sha256']=sha(OUT/'ACTIVE_DATASET_MANIFEST58.json')
    effective_total=Fraction(0);effective_aux=Fraction(0);norm_total=Fraction(0);norm_aux=Fraction(0)
    for phase in p['phases']:
        phase_records=[]
        for step in phase['steps']:
            mr=Fraction(0);ma=Fraction(0);denom=0
            for row in step['microbatches']:
                stat=lookup[row['id']];metric=metrics[profile][row['id']]
                for key in ['pool','stage','bank','sequence_tokens','positive_tokens','weighted_mass','positive_token_ids_sha256_u32le']:
                    row[key]=stat[key]
                row['valid_shifted_target_count']=stat['shifted_valid_target_count'];row['positive_by_component']=stat['positive_by_component'];denom+=metric['denominator']
                if row['pool']=='synthetic':ma+=metric['mass']
                else:mr+=metric['mass']
                phase_records.append(stat)
            alpha=min(Fraction(1),mr/(4*ma))if ma else Fraction(1)
            require(mr>0 and denom>0,'REAL_ANCHOR_OR_VALID_DENOMINATOR_MISSING')
            em=mr+alpha*ma;ea=alpha*ma
            require(alpha>0 and alpha<=1 and ea<=mr/4,'AUXILIARY_CAP_FAILED')
            if alpha<1:require(ea==mr/4,'CAPPED_STEP_NOT_BOUNDARY')
            for row in step['microbatches']:
                scale=alpha if row['pool']=='synthetic'else Fraction(1)
                row['extra_course_loss_scale']=ratio(scale);row['effective_weighted_mass']=decimal_string(metrics[profile][row['id']]['mass']*scale)
            step.update({'valid_shifted_target_denominator':denom,'weighted_mass':decimal_string(mr+ma),'synthetic_weighted_mass':decimal_string(ma),'synthetic_fraction_of_weighted_mass':number(ma/(mr+ma)),'original_array_weighted_mass':decimal_string(mr+ma),'original_real_weighted_mass':decimal_string(mr),'original_auxiliary_weighted_mass':decimal_string(ma),'auxiliary_extra_loss_scale':ratio(alpha),'effective_weighted_mass':decimal_string(em),'effective_auxiliary_weighted_mass':decimal_string(ea),'effective_auxiliary_fraction_of_weighted_mass':number(ea/em),'coefficient_mass_cap_not_CE_gradient_or_Adam_update_cap':True})
            # Independent invariants are computed from actual labels/weights,
            # not from the course summaries or selected positive-token counts.
            check_mr=sum((metrics[profile][r['id']]['mass']for r in step['microbatches']if r['pool']!='synthetic'),Fraction(0))
            check_ma=sum((metrics[profile][r['id']]['mass']for r in step['microbatches']if r['pool']=='synthetic'),Fraction(0))
            require(check_mr==mr and check_ma==ma and sum(metrics[profile][r['id']]['denominator']for r in step['microbatches'])==denom,'FEATURE_COURSE_DENOMINATOR_OR_MASS_DIFFERS')
            exact_effective=sum((metrics[profile][r['id']]['mass']*(alpha if r['pool']=='synthetic'else 1)for r in step['microbatches']),Fraction(0));require(exact_effective==em,'EXTRA_SCALE_REAPPLIED_OR_OMITTED')
            proxy=sum(metrics[profile][r['id']]['proxy_weighted_CE_sum']*(float(alpha)if r['pool']=='synthetic'else 1)for r in step['microbatches'])/denom
            require(math.isfinite(proxy)and proxy>0,'REFERENCE_SCALAR_LOSS_NOT_FINITE')
            qa_steps.append({'profile':profile,'global_step':step['global_step_one_based'],'real_array_mass':decimal_string(mr),'aux_array_mass':decimal_string(ma),'alpha':ratio(alpha),'actual_shifted_target_denominator':denom,'effective_aux_fraction':float(ea/em),'effective_mass':decimal_string(em),'deterministic_proxy_CE_loss_not_model_loss':proxy})
            effective_total+=em;effective_aux+=ea;norm_total+=em/denom;norm_aux+=ea/denom
            if phase['name']=='process':allalpha.append((profile,alpha))
        phase['summary']=summarise(phase_records)
    p['summary']=summarise(actual[profile]);p['effective_course_summary']={'weighted_mass':decimal_string(effective_total),'auxiliary_weighted_mass':decimal_string(effective_aux),'auxiliary_mass_fraction':float(effective_aux/effective_total),'step_normalized_objective_auxiliary_coefficient_fraction':float(norm_aux/norm_total),'coefficient_not_CE_gradient_or_Adam':True}
    oldmix=p['batch_mass_audit'];oldmix.update({'array_weight_batch_mass_audit_is_uncapped':True,'step_effective_aux_mass_cap':0.2,'step_effective_aux_over_cap_batches':0,'step_extra_scale_batches':sum(alpha<1 for name,alpha in allalpha if name==profile),'max_step_effective_aux_mass_fraction':max(s['effective_auxiliary_fraction_of_weighted_mass']for phase in p['phases']for s in phase['steps'])})
    current_order=[[r['id']for r in s['microbatches']]for phase in p['phases']for s in phase['steps']]
    previous_order=[[r['id']for r in s['microbatches']]for phase in oldcourse['profiles'][profile]['phases']for s in phase['steps']]
    require(current_order==previous_order and len(current_order)==241,'ORIGINAL_BATCH_ID_ORDER_CHANGED')
save(OUT/'COURSE58.json',course)
config=load(OLD/'CONFIG57_NATIVE.json')
config.update({'schema':'wrd58-protocol-and-local-aux-capped-sft-config-not-launcher','design_revision':REV,'change_id':CHANGE,'schema_version':'workflow-pipeline-v1','data_revision':58,'dataset_manifest':'ACTIVE_DATASET_MANIFEST58.json','dataset_manifest_sha256':sha(OUT/'ACTIVE_DATASET_MANIFEST58.json'),'dataset_loader':'tooling/active_loader57.py','course_file':'COURSE58.json','course_sha256':sha(OUT/'COURSE58.json'),'positive_tokens_exposed':295478,'default_training_entrypoint':'TRAINING_ENTRYPOINT58.json','candidate_checkpoint_global_steps':[0,26,80,134,188,241],'base_checkpoint_step0_is_not_an_optimizer_update':True,'checkpoint_selection':'FROZEN_DEV_CLOSED_LOOP_TSR_Q_COST_PARETO_NO_TEST_SELECTION','course_version':'58_same241_ID_order_with31_valid_call_F_and_per_step_aux_cap'})
config['loss'].update({'extra_synthetic_course_scale':'alpha=min(1, M_real/(4*M_aux)); M from unscaled canonical span weight mass in this optimizer step; alpha=1 if M_aux=0','extra_scale_source':'COURSE58.json phase.steps[].auxiliary_extra_loss_scale','extra_scale_applies_only_to_synthetic_pool':True,'actual_loss_numerator':'sum_i(original_span_weight_i * extra_course_scale_for_row * CE_i) over all nonignored shifted targets in one accumulated optimizer step','denominator_unchanged':'count of all nonignored shifted targets across that optimizer step, including synthetic targets before scaling','no_divide_by_sum_weights_or_extra_accumulation':True,'bin_weights_are_unscaled_and_must_not_be_rewritten_or_scaled_twice':True,'cap_is_coefficient_mass_not_CE_gradient_or_Adam_update':True})
config['process_batch_mixing']=course['profiles']['budget_projection']['batch_mass_audit']
save(OUT/'CONFIG58.json',config)
qa={'schema':'wrd58-real-features-to-course-loss-contract-qa-v1','status':'PASS_ACTUAL1260_BOTH_PROFILES_FEATURES_AND241_STEPS_PER_PROFILE_LOSS_CONTRACT','design_revision':REV,'actual_counts':manifest['actual_counts'],'frozen57_data_unchanged':sha(OLD/'ACTIVE_DATASET_MANIFEST57.json')==manifest['baseline57_manifest_sha256'],'frozen57_course_unchanged':sha(OLD/'COURSE57_NATIVE.json')==course['baseline57_course_sha256'],'same1260_IDs_same241_batch_order':True,'actual_four_features_read':True,'positive_protocol_F_added_only':650,'new_sources_or_native_calls':0,'all482_optimizer_step_contracts_from_real_features_checked':len(qa_steps)==482,'all_effective_auxiliary_fractions_le20percent':all(s['effective_aux_fraction']<=0.2+1e-12 for s in qa_steps),'original_bin_mass_and_effective_mass_separate':True,'proxy_CE_is_only_CPU_contract_probe_not_model_loss':True,'course_sha256':sha(OUT/'COURSE58.json'),'config_sha256':sha(OUT/'CONFIG58.json'),'source_sha256':sha(Path(__file__)),'loader_sha256':sha(LOADER),'training_started':False,'model_weights_loaded':False}
save(OUT/'FEATURE_TO_COURSE_LOSS_QA58.json',qa);save(OUT/'PER_STEP_LOSS_CONTRACT58.json',{'schema':'wrd58-actual-feature-step-objective-contract-v1','steps':qa_steps})
entry={'schema':'wrd58-audited-training-entrypoint-not-launcher','design_revision':REV,'change_id':CHANGE,'schema_version':'workflow-pipeline-v1','dataset_manifest':ref(OUT/'ACTIVE_DATASET_MANIFEST58.json'),'compatibility_manifest':ref(OUT/'ACTIVE_DATASET_MANIFEST57.json'),'dataset_pin':ref(OUT/'ACTIVE_DATASET_PIN58.json'),'compatibility_pin':ref(OUT/'ACTIVE_DATASET_PIN57.json'),'loader':ref(OUT/'tooling/active_loader57.py'),'immutable_loader':ref(OUT/'tooling/immutable_curriculum_loader11.py'),'course':ref(OUT/'COURSE58.json'),'config':ref(OUT/'CONFIG58.json'),'course_QA':ref(OUT/'FEATURE_TO_COURSE_LOSS_QA58.json'),'default_profile':'budget_projection','profiles_are_mutually_exclusive':True,'unique_targets':1260,'positive_tokens':295478,'raw_array_weighted_mass':'85003.30','candidate_optimizer_updates':241,'compatibility_manifest_bytes_identical_to_canonical58':True,'training_execution_authorized':False,'training_started':False}
save(OUT/'TRAINING_ENTRYPOINT58.json',entry)
cp(Path(__file__),OUT/'tooling/build_active_course58.py')
save(OUT/'CHECKPOINT_READY58.json',{'schema':'wrd58-active1260-feature-and-course-ready-v1','status':'PASS_ACTUAL_DATA_AND_LOSS_CONTRACT_NO_MODEL_TRAINING','entrypoint':ref(OUT/'TRAINING_ENTRYPOINT58.json'),'counts':manifest['actual_counts'],'course_effective_summary':{p:v['effective_course_summary']for p,v in course['profiles'].items()},'source_root':str(OUT),'old57_data_or_masks_changed':False,'training_started':False})
print(json.dumps({'status':qa['status'],'root':str(OUT),'entrypoint_sha256':sha(OUT/'TRAINING_ENTRYPOINT58.json'),'counts':manifest['actual_counts'],'effective':{p:v['effective_course_summary']for p,v in course['profiles'].items()},'training_started':False},ensure_ascii=False))
