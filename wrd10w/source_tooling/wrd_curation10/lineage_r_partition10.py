"""Join existing explicit R reviews to actual R fields; no new credit."""
from pathlib import Path
import collections,gzip,hashlib,json
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/reasoning_native10'
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);return{'path':str(p),'sha256':h(p.read_bytes()),'bytes':p.stat().st_size}
def save(n,d):(OUT/n).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
api=[json.loads(l)for l in gzip.open(OUT/'API67_R_A_FEEDBACK.original.audit.jsonl.gz','rt',encoding='utf-8-sig')]
bp=ROOT/'output/20261027_wrd_main_v10/b_reasoning_review_01/REVIEW.json';br=load(bp)
ap=ROOT/'output/20261027_wrd_main_v10/a_reasoning_review_03/REVIEW.json';ar=load(ap)
parts=[];counts=collections.Counter();per=[]
for a in api:
    r=a['original_R'];prior=[]
    if a['stage']=='B_make_report_02':
        for q in br['ranges']:
            if q['call_id']!=a['call_id']:continue
            assert h(r[q['start']:q['end']])==q['sha256']
            prior.append({'start':q['start'],'end':q['end'],'old_decision':q['decision'],
              'old_mask':q['mask'],'prior_review_pin':pin(bp),'range_id':q['id']})
    if a['stage']=='A_screen_narrative_01'and a['call_id']==ar['call_id']:
        for q in ar['ranges']:
            assert h(r[q['start']:q['end']])==q['text_sha256']
            prior.append({'start':q['start'],'end':q['end'],'old_decision':q['type'],
              'old_mask':1,'prior_review_pin':pin(ap),'range_id':q['range_id']})
    positive=a['existing_positive_R_approved_unicode_ranges']
    bounds=sorted({0,len(r),*(n for q in prior for n in [q['start'],q['end']]),*(n for pair in positive for n in pair)})
    cc=collections.Counter();pp=[]
    for start,end in zip(bounds,bounds[1:]):
        if start==end:continue
        active=any(lo<=start<end<=hi for lo,hi in positive)
        old=[q for q in prior if q['start']<=start<end<=q['end']]
        neg=any(q['old_mask']==0 for q in old)
        assert not(active and neg),'ACTIVE_CREDIT_OVERLAPS_PRIOR_EXPLICIT_ZERO_REQUIRES_REVIEW'
        cl='CURRENT595_APPROVED_R'if active else'PRIOR_EXPLICIT_ZERO_NEGATIVE_OR_UNKNOWN'if neg else'PRIOR_SILVER_POSITIVE_NOT_CURRENT_MAIN_REQUIRES_ROOT_REVIEW'if old else'UNAPPROVED_OR_UNREVIEWED_ZERO_LOSS'
        cc[cl]+=end-start;counts[cl]+=end-start
        pp.append({'start':start,'end':end,'characters':end-start,'text_sha256':h(r[start:end]),
          'classification':cl,'prior_range_ids':[q['range_id']for q in old],
          'prior_decisions':[q['old_decision']for q in old],
          'new_positive_loss_granted':False})
    parts.append({'stage':a['stage'],'episode_id':a['episode_id'],'call_id':a['call_id'],'response_id':a['response_id'],
      'original_R_field':'reasoning_content','full_R_sha256':h(r),'original_R_characters':len(r),
      'triage_class':a['R_triage_class'],'partition':pp,
      'public_visible_content_separate_characters':len(a['visible_public_text']),
      'short_transition_in_R_field_not_automatically_private_CoT_or_public_E':True,
      'prior_reviews':list({x['prior_review_pin']['path']:x['prior_review_pin']for x in prior}.values())})
    per.append({'stage':a['stage'],'call_id':a['call_id'],'R_characters':len(r),'counts':dict(cc)})
assert sum(counts.values())==161174 and counts['CURRENT595_APPROVED_R']==19374
save('R67_COMPLETE_CHARACTER_PARTITION.metadata.json',{'schema':'wrd10-API67-original-R-character-credit-partition-v1',
  'total_original_R_characters':161174,'counts':dict(counts),'responses':parts,
  'current595_R_unicode_credit_is_not_exact_token_count':True,
  'no_prior_silver_positive_automatically_admitted':True,'new_positive_loss_granted':False})
save('R67_PARTITION_SUMMARY.json',{'counts':dict(counts),'per_call':per,
  'prior_review_pins':[pin(ap),pin(bp)],'new_business_calls':0,'training_started':False,'script_pin':pin(__file__)})
print(json.dumps({'counts':dict(counts),'sum':sum(counts.values())}))
