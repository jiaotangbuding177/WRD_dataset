"""Read-only structural/exact-source proofs for the process follow-up outputs."""
import gzip,json
from pathlib import Path
from collections import Counter
from process_batch02_candidates import OUT,sha,h

def rows(path):return list(map(json.loads,gzip.open(path,'rt',encoding='utf8')))
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    paths=[OUT/'SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz',OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v3.jsonl.gz']
    candidates=[r for p in paths for r in rows(p)];assert len(candidates)==len({r['owner_id']for r in candidates})==17
    proofs=[]
    for row in candidates:
        packet=json.loads(Path(row['source_context']['path']).read_text(encoding='utf8'))
        target=row['messages'][2];raw=packet['original_target']
        original=[b for b in raw['content']if b['type']=='toolCall']
        assert len(original)==len(target['tool_calls'])==1
        call=target['tool_calls'][0];args=json.loads(call['function']['arguments'])
        assert call['id']==original[0]['id'] and call['function']['name']==original[0]['name'] and args==original[0]['arguments']
        for field,value,ex in [('content',target['content'],row['target_content_unicode_exclusions']),
                (row.get('target_exclusion_argument_name','content'),args.get(row.get('target_exclusion_argument_name','content'),''),row['target_code_unicode_exclusions'])]:
            last=0
            for span in ex:
                lo,hi=span['start'],span['end'];assert last<=lo<hi<=len(value) and h(value[lo:hi])==span['text_sha256']
                if 'text'in span:assert value[lo:hi]==span['text']
                last=hi
        assert not target['reasoning_content'] and not row['teacher_original_R_supervised']
        assert row['message_loss_mask']==[0,0,1] and row['supervision_message_indices']==[2]
        assert all(m['index']<row['original_message_index']for m in packet['selected_before_observations']+packet['selected_before_resources'])
        assert sha(row['source_context']['path'])==row['source_context']['sha256']
        proofs.append({'owner_id':row['owner_id'],'id':row['id'],'exact_native_args_verified':True,'packet_sha256':row['source_context']['sha256'],
            'target_field':row.get('exclusion_target_field','messages[2].tool_calls[0].function.arguments'),
            'negative_public_spans':len(row['target_content_unicode_exclusions']),'negative_argument_spans':len(row['target_code_unicode_exclusions'])})
    resolution=[{'owner_id':row['owner_id'],'resolution':'COMPLETE_VIEW_DELIVERED_FOR_ROOT_FINAL_ADMISSION','candidate_id':row['id'],
        'candidate_file':str(next(p for p in paths if row['owner_id']in {r['owner_id']for r in rows(p)}))}for row in candidates]
    resolution +=[
        {'owner_id':'fe6facbf46882ca14fc4cd17','resolution':'EXCLUDE_PROTECTED_SOURCE_COMPONENT','source_id':'conv_7ba0e0439045','evidence':'../holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json','reason':'No training projection produced despite useful renderer mechanism; source/user privacy boundary takes precedence.'},
        {'owner_id':'849d27a9b60c2756601d87bd','resolution':'HOLD_MISSING_REQUIREMENTS_AND_INCONSISTENT_UNSOURCED_TARGET_COUNTS','reason':'Missing explicit half-football-field and five-arrows-per-person corrections; shot2 two targets versus shot5 three without source. Masking target counts does not repair omissions.'},
    ]
    dump(OUT/'CANDIDATE19_EXPLICIT_RESOLUTION.json',{'status':'ALL19_PRIOR_SCOPED_PROPOSALS_HAVE_EXPLICIT_RESOLUTION','total':19,'complete_delivered':17,'protected':1,'specific_hold':1,'root_main_admission_external':True,'resolutions':resolution})
    dump(OUT/'FINAL17_SOURCE_AND_MASK_VALIDATION.json',{'status':'PASS_EXACT_ARGUMENTS_AND_EXCLUSION_CHARACTER_GEOMETRY_NOT_TOKEN_OR_SEMANTIC_ADMISSION',
        'count':17,'proofs':proofs,'candidate_files':[{'path':str(p),'sha256':sha(p)}for p in paths],
        'original_R':0,'new_R':0,'no_recorded_code_executed':True,'training_started':False,'curation_cost':'UNKNOWN_NOT_ZERO'})
    ledger=rows(OUT/'OWNER1321_DISPOSITION09_v2.jsonl.gz');assert len(ledger)==len({r['owner_id']for r in ledger})==1321
    assert not any(r['processing_disposition']=='HOLD_NEEDS_SEMANTIC_REVIEW'for r in ledger)
    print('PASS',len(candidates),'exact-source candidates,',len(ledger),'unique owner ledger,19/19 resolved')

if __name__=='__main__':main()
