from pathlib import Path
from array import array
import gzip, hashlib, json
import numpy as np

ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261027_wrd_main_v10'
OUT=BASE/'c_review_dataset_01';COM=BASE/'compiled/c_review_dataset_01'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sha(t):return hashlib.sha256(t.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size}
rows=[json.loads(line) for p in sorted(COM.glob('*.jsonl.gz')) if p.name!='held.jsonl.gz' for line in gzip.open(p,'rt',encoding='utf-8')]
tensors={};receipts=[]
for i,row in enumerate(rows):
    ids=np.asarray(row['input_ids'],dtype=np.uint32)
    labels=np.full(len(ids),-100,dtype=np.int64);weights=np.zeros(len(ids),dtype=np.float32)
    mask=np.zeros(len(ids),dtype=np.uint8)
    for a,b,_,w in row['supervision_spans']:
        assert not mask[a:b].any();labels[a:b]=ids[a:b];weights[a:b]=w;mask[a:b]=1
    assert mask.sum()==row['supervised_tokens'] and len(ids)<=32768
    assert (labels[mask==0]==-100).all() and (labels[mask==1]==ids[mask==1]).all()
    assert row['original_record_metadata']['root_main_admission'] is False
    prefix=f'r{i:02}'
    tensors.update({prefix+'_input_ids':ids,prefix+'_labels':labels,prefix+'_loss_weights':weights,prefix+'_loss_mask':mask})
    receipts.append({'array_prefix':prefix,'id':row['id'],'input_tokens':len(ids),'supervised_tokens':int(mask.sum()),
        'input_ids_u32le_sha256':hashlib.sha256(ids.astype('<u4').tobytes()).hexdigest(),
        'labels_i64le_sha256':hashlib.sha256(labels.astype('<i8').tobytes()).hexdigest(),
        'loss_weights_f32le_sha256':hashlib.sha256(weights.astype('<f4').tobytes()).hexdigest(),
        'loss_mask_u8_sha256':hashlib.sha256(mask.tobytes()).hexdigest()})
        
np.savez_compressed(OUT/'actual_unshifted_token_labels_masks.npz',**tensors)
with np.load(OUT/'actual_unshifted_token_labels_masks.npz',allow_pickle=False) as f:
    assert set(f.files)==set(tensors)
    for key,value in tensors.items():assert np.array_equal(f[key],value)
save(OUT/'DENSE_ARRAY_RECEIPT.json',{'schema':'v10-C-explicit-dense-array-materialization-v1','status':'PASS_LOCAL_ROUNDTRIP',
    'source_compilation_report':pin(COM/'COMPILATION_REPORT.json'),'array_file':pin(OUT/'actual_unshifted_token_labels_masks.npz'),
    'label_definition':'unshifted labels=input_ids at owned spans, otherwise -100; causal next-token shift belongs to future trainer',
    'no_model_or_trainer_called':True,'root_main_admission':False,'records':receipts})

originals=[json.loads(x) for x in gzip.open(OUT/'C_review.original_responses.jsonl.gz','rt',encoding='utf-8')]
by_seq={int(x['call_id'][:4]):x for x in originals}
review=load(OUT/'ORIGINAL_R_LOCAL_REVIEW.json')
errors=[]
def rzero(seq,substring,kind):
    row=by_seq[seq];r=row['message']['reasoning_content'];a=r.index(substring);b=a+len(substring)
    assert not any(p['call_id']==row['call_id'] and max(a,p['start'])<min(b,p['end']) for p in review['positive_ranges'])
    errors.append({'call_id':row['call_id'],'field':'reasoning_content','start':a,'end':b,'sha256':sha(r[a:b]),'text':r[a:b],
        'mask':0,'category':kind,'request_sha256':row['request_sha256'],'response_sha256':row['response_sha256']})
rzero(15,'Total development+trial costs enormous (~6.8M tokens)','WRONG_OR_UNVERIFIED_CUMULATIVE_COST_ESTIMATE')
rzero(15,'within noise of an uncalibrated eval','NOISE_MAGNITUDE_NOT_MEASURED')
rzero(20,'within uncalibrated noise.','NOISE_MAGNITUDE_NOT_MEASURED')
rzero(20,'Development+trial≈6.97M tokens (excluding unknown).','WRONG_CUMULATIVE_COST_ESTIMATE')
rzero(20,'skill arm took ~5.3x more tokens and calls per task','CALL_MULTIPLIER_INCORRECT_4_29_NOT_5_3')
rzero(21,'Sum known≈6,968,097 tokens','WRONG_INTERMEDIATE_ARITHMETIC_BEFORE_SELF_CORRECTION')
art=OUT/'preserved_original_artifacts'
for name,ptr,kind in [('decision.json',['rationale',2],'PRE_REVIEW_COST_INCORRECTLY_DESCRIBED_AS_INCLUDING_REVIEW'),
    ('decision.json',['quality_evidence_uncalibrated','note'],'NOISE_MAGNITUDE_NOT_MEASURED'),
    ('feedback.json',['same_version_concrete_issues',1,'issue'],'BODY_BOUNDARY_VS_WHITESPACE_COUNT_CONFLATION'),
    ('feedback.json',['same_version_concrete_issues',2,'issue'],'DECLARED_SEMANTIC_LIMIT_NOT_AUTOMATIC_CODE_BUG')]:
    p=art/name;value=load(p)
    for k in ptr:value=value[k]
    errors.append({'artifact':pin(p),'field_json_path':ptr,'start':0,'end':len(value),'sha256':sha(value),'text':value,'mask':0,'category':kind,
        'range_coordinates':'decoded JSON string field, not JSON-escaped byte offsets'})
last=by_seq[24]
errors.append({'call_id':last['call_id'],'field':'content','start':0,'end':len(last['message']['content']),
    'sha256':sha(last['message']['content']),'text':last['message']['content'],'mask':0,
    'category':'UNAPPROVED_ORIGINAL_FINAL_INCLUDING_BROAD_CUMULATIVE_COST_WORDING','response_sha256':last['response_sha256']})
save(OUT/'EXPLICIT_ZERO_ERROR_RANGES.json',{'schema':'v10-C-original-known-error-zero-spans-v1','default_all_unreviewed_mask':0,
    'does_not_claim_every_wrong_or_unapproved_span_listed_individually':True,'exact_known_spans':errors,
    'full_original_R_mask_partition':pin(OUT/'ORIGINAL_R_LOCAL_REVIEW.json'),'all_original_decision_feedback_actions_zero_loss':True,
    'new_authored_state_is_separate_owner_and_state':True})

held=[json.loads(x) for x in gzip.open(COM/'held.jsonl.gz','rt',encoding='utf-8')]
coverage={'schema':'v10-C-dataset-compiled-coverage-v1','root_main_admission':False,
    'compilation_report':pin(COM/'COMPILATION_REPORT.json'),'dual_tokenizer_QA':pin(OUT/'INDEPENDENT_DUAL_TOKENIZER_QA.json'),
    'actual_compiled_records':[{'id':r['id'],'bank':r['bank'],'input_tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],
       'components':r['supervised_tokens_by_component'],'loss_multiplier':r['original_record_metadata']['loss_multiplier']} for r in rows],
    'held':held,'no_past_input_removed_to_fit':True,'no_original_target_tool_field_repaired_or_deleted_for_admission':True,
    'full53_long_candidates':pin(OUT/'original_native.full53.long_candidates.jsonl.gz'),
    'full53_not_currently_compiled_or_admitted':True,'core7_full53_same_owners_mutually_exclusive':True,
    'source_group_id':rows[0]['source_group_id'],'actual_sequences':len(rows),'actual_input_tokens':sum(r['total_tokens'] for r in rows),
    'actual_supervised_tokens':sum(r['supervised_tokens'] for r in rows),'weighted_supervised_token_equivalents':sum((b-a)*w for r in rows for a,b,_,w in r['supervision_spans']),
    'auxiliary_read_ls_not_added_as_main':True,'new_authored_R_is_not_original_teacher_R':True,'training_started':False}
save(OUT/'COMPILED_COVERAGE.json',coverage)
print(json.dumps({k:coverage[k] for k in ['actual_sequences','actual_input_tokens','actual_supervised_tokens','weighted_supervised_token_equivalents']},ensure_ascii=False))
