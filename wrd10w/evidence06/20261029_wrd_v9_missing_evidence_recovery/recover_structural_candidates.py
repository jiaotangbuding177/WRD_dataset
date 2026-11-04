"""Recover exact original write bytes and same-SHA ancestor references only."""
from pathlib import Path
from collections import defaultdict
import gzip,hashlib,json
ROOT=Path('D:/skillloop');BASE=ROOT/'output';OUT=Path(__file__).parent;V9=BASE/'20261026_wrd_dataset_v9'
def sha(b):return hashlib.sha256(b).hexdigest()
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8')))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    dest=OUT/'scheduled_program_recovery';dest.mkdir(exist_ok=False)
    ep=next(x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz') if x['episode_id']=='ep_04149c237fc7afb2bd67')
    native=Path(ep['source_native']['path']);assert pin(native)['sha256']==ep['source_native']['sha256']
    ev={i:json.loads(x) for i,x in enumerate(native.open(encoding='utf-8'),1)};found=[]
    versions=[x for x in rows(V9/'outcomes/recomputed_scope_overlay/produced_versions.jsonl.gz') if x['episode_id']==ep['episode_id']]
    for index in [71,73]:
        eventline=ep['source_event_lines'][index];m=ev[eventline]['message'];call=next(x for x in m['content'] if x.get('type')=='toolCall' and x['name']=='write');args=call['arguments'];body=args['content'].encode()
        name=Path(args['path']).name;f=dest/name;f.write_bytes(body)
        follow=ev[ep['source_event_lines'][index+1]]['message'];assert follow['role']=='toolResult' and follow['toolCallId']==call['id'] and follow['isError'] is False
        ack='\n'.join(x['text'] for x in follow['content'] if x.get('type')=='text');assert 'Successfully wrote' in ack and args['path'] in ack
        matches=[x for v in versions for x in v['files'] if x['sha256']==sha(body)];assert len(matches)==1
        # Full original arguments preserved, not replaced by later snapshot text.
        af=dest/(name+'.original_write_arguments.json');save(af,args)
        entry={'episode_id':ep['episode_id'],'source_message_index':index,'source_event_line':eventline,'tool_call_id':call['id'],'actual_native_tool':'write','original_arguments':pin(af),
            'complete_original_program':pin(f),'original_program_characters':len(args['content']),'native_path':args['path'],'original_native_source':pin(native),
            'actual_next_tool_observation_message_index':index+1,'actual_next_tool_observation_event_line':ep['source_event_lines'][index+1],'actual_write_ack':ack,
            'exact_same_SHA_final_snapshot_file':matches[0],'source_scope_status':'HOLD_MISSING_EVIDENCE_UNTIL_ALL_OTHER_ANCESTORS_CLOSED','semantic_program_quality':'NOT_REVIEWED','positive_loss':0}
        found.append(entry)
    save(dest/'ORIGINAL_WRITE_RECOVERY.json',{'status':'ORIGINAL_NATIVE_TWO_COMPLETE_WRITES_RECOVERED_SOURCE_SCOPE_AND_SEMANTICS_HELD','records':found,
        'total_original_program_characters':sum(x['original_program_characters'] for x in found),'not_future_snapshot_substitution':True,
        'specific_source_reader_runtime_edge_candidate':pin(OUT/'SCHEDULED_READER_BINDING_CANDIDATE.json'),'whole56_targets_not_admitted':True,'original_R_remains_in_full_original_native_record':True,
        'new_native_Agent_model_business_training_runs':0,'curation_cost':'UNKNOWN_NOT_ZERO'})
    # Same-byte carriers are useful search edges, not unique causal producers.
    selected=[x for x in rows(OUT/'MAKE_PRIOR_RESOURCES.metadata.jsonl.gz') if x['episode_id']=='ep_5b5e58ac2499ea46957b' and x['native_path'] in ['/workspace/inputs/route.json','/workspace/inputs/previous_feedback.json','/workspace/inputs/previous_skill/SKILL.md']]
    need={x['file_identity']['sha256'] for x in selected};aliases=defaultdict(list)
    index=BASE/'20261025_wrd_training_dataset/bundle/archive/file_index.jsonl'
    for line in index.open(encoding='utf-8'):
        if not any(s in line for s in need):continue
        d=json.loads(line)
        if d['sha256'] in need:aliases[d['sha256']].append(d)
    allversions=rows(V9/'outcomes/recomputed_scope_overlay/produced_versions.jsonl.gz');meta={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    outcomes={x['episode_id']:x for x in rows(V9/'outcomes/recomputed_scope_overlay/episode_outcomes.jsonl.gz')}
    matches=[]
    for r in selected:
        s=r['file_identity']['sha256'];candidates=[]
        for v in allversions:
            if any(f['sha256']==s for f in v['files']):
                candidates.append({'episode_id':v['episode_id'],'tree_content_sha256':v['tree_content_sha256'],'source_scope_metadata':outcomes[v['episode_id']]['source_scope'],
                    'source_native':meta[v['episode_id']]['source_native'],'old_episode_source_ids_metadata':meta[v['episode_id']]['old_episode_source_ids_metadata']})
        matches.append({'native_path':r['native_path'],'node_id':r['node_id'],'expected_sha256':s,'archive_exact_same_SHA_aliases':aliases[s],
            'program_tree_possible_producers_not_unique_causality_proof':candidates,'actual_exact_input_bytes_are_available':any(x['matches_expected_sha256'] for x in r['carriers']),
            'remaining_required':'Bind actual dispatch/copy and specific original producer prefix, plus feedback/trial runtime source closure; same SHA alone is not unique causal identity.','positive_loss':0})
    save(OUT/'REMOTION_ANCESTOR_SAME_SHA_SEARCH.json',{'episode_id':'ep_5b5e58ac2499ea46957b','held_targets':13,'resource_ancestor_search':matches,
        'archive_index':pin(index),'protected_body_read':False,'body_semantics_read':False,'TRAIN_reclassification':False,'positive_loss':0})
    save(OUT/'STRUCTURAL_RECOVERY_MANIFEST.json',{'files':[pin(p) for p in [Path(__file__),dest/'ORIGINAL_WRITE_RECOVERY.json',OUT/'REMOTION_ANCESTOR_SAME_SHA_SEARCH.json',*[x for x in dest.iterdir() if x.name!='ORIGINAL_WRITE_RECOVERY.json']]],
        'source_scope_and_quality_not_admitted':True,'frozen05_modified':False,'training_started':False})
    print(json.dumps({'original_complete_programs':len(found),'original_program_characters':sum(x['original_program_characters'] for x in found),'write_recovery_sha256':pin(dest/'ORIGINAL_WRITE_RECOVERY.json')['sha256'],'remotion_same_SHA_reference_rows':sum(len(x['archive_exact_same_SHA_aliases']) for x in matches)}))

if __name__=='__main__':main()
