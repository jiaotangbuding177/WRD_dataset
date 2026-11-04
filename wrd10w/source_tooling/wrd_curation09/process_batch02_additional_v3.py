"""Extend one exact command exclusion to cover the misleading average comment."""
import gzip,json
from process_batch02_candidates import OUT,sha,h,dump

def main():
    src=OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v2.jsonl.gz';dest=OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v3.jsonl.gz'
    rows=list(map(json.loads,gzip.open(src,'rt',encoding='utf8')));proof=None
    for row in rows:
        if row['owner_id']!='66e542b63e52392b7e1dbfc2':continue
        command=json.loads(row['messages'][2]['tool_calls'][0]['function']['arguments'])['command']
        needle='# top region / middle / bottom rows average\n';lo=command.index(needle)
        old=row['target_code_unicode_exclusions'];assert len(old)==1 and lo+len(needle)==old[0]['start']
        hi=old[0]['end'];span={'start':lo,'end':hi,'text':command[lo:hi],'text_sha256':h(command[lo:hi]),
            'reason':'Historical average comment is misleading: resize1x1 computes representative resized colors, not an arithmetic pixel mean. Also excludes unused statistics import and finite five-iteration redundant no-output crop loop with misleading wrong comment; not an infinite loop.'}
        row['target_code_unicode_exclusions']=[span]
        proof={'owner_id':row['owner_id'],'previous_range':old[0],'replacement_range':span,
            'added_literal':needle,'added_literal_start':lo,'added_literal_end':lo+len(needle),'added_literal_sha256':h(needle),
            'original_command_unchanged':True,'command_sha256':h(command)}
    with gzip.open(dest,'wt',encoding='utf8')as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    dump(OUT/'CANDIDATE_ADDITIONAL03_v3_TRANSFORM.json',{'status':'FROZEN_EXACT_COMMAND_EXCLUSION_EXTENSION_ONLY',
        'source':{'path':str(src),'sha256':sha(src)},'output':{'path':str(dest),'sha256':sha(dest)},'proof':proof,
        'all_other_candidate_fields_unchanged':True,'new_R':0,'new_business_calls':0,'training_started':False})
    print(json.dumps({'path':str(dest),'sha256':sha(dest)},ensure_ascii=False))
if __name__=='__main__':main()
