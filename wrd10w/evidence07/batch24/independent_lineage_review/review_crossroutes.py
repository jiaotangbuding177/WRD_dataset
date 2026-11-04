"""Independent direct-byte reviewer for crossroutes frozen 17/269 artifacts.

No import of the producing script, no historical program execution and no labels.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,re

R=Path('D:/skillloop'); C=R/'output/20261029_wrd_batch24/crossroutes'; O=Path(__file__).resolve().parent
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def text(m):
    v=m.get('content');return v if isinstance(v,str) else '\n'.join(c.get('text','') for c in v or [] if isinstance(c,dict))
def calls(m):return [c for c in m.get('content',[]) if isinstance(c,dict) and c.get('type')=='toolCall']
def ms(p):
    return [{'event_line':i,'message':e['message']} for i,e in enumerate((json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines()),1) if isinstance(e.get('message'),dict)]
def pathget(v,path):
    assert path.startswith('$')
    for key,index in re.findall(r'\.([^.[\]]+)|\[(\d+)\]',path[1:]):v=v[int(index)] if index else v[key]
    return v

def main():
    O.mkdir(parents=True,exist_ok=True)
    closurepath=C/'ROUTE_PRODUCER_CLOSURE.json'; closure=j(closurepath)
    targets=rows(C/'TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz')
    orig_targets={(t['episode_id'],t['source_message_index']):t for t in rows(R/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz')}
    scope=j(R/'research/plans/20261029_wrd_next_data/PLANNED_SCOPE.json')
    selected=[x for x in scope['first_batch'] if x['route_id'] not in ['scheduled-task-config','remotion-explainer-video']]
    assert len(selected)==17 and len(targets)==269
    assert {t['id'] for t in targets}=={i for e in selected for i in e['candidate_target_ids']}
    assert len({t['id'] for t in targets})==269
    checks=[];cache={};producerchecks={};targetcheck=[]
    def native(p):
        s=p['sha256']
        if s not in cache:
            assert pin(p['path'])==p
            cache[s]=ms(p['path'])
        return cache[s]
    for e in closure['episodes']:
        actual=native(e['native']); boundaries=[]
        for link in e['route_links']:
            inp=link['input_carrier']['original']; cp=link['input_carrier']['copied'];assert pin(inp['path'])==inp and pin(cp['path'])==cp
            assert inp['sha256']==cp['sha256'];iv=j(cp['path']); assert h(can(iv))==link['canonical_input_sha256']
            protected_producers=[]
            for p in link['producer_matches']:
                pm=native(p['native']);i=p['message_index'];m=pm[i]['message'];c=next(c for c in calls(m) if c['id']==p['tool_call_id']);a=c['arguments'];a=json.loads(a) if isinstance(a,str) else a
                assert c['name']=='write' and a['path']==p['write_path'] and h(a['content'].encode())==p['write_content_sha256']
                v=json.loads(a['content']);obj=pathget(v,p['json_object_path']);assert h(can(obj))==p['object_canonical_sha256']
                assert pm[i]['event_line']==p['event_line'];ack=pm[p['ack_message_index']]['message'];assert ack['toolCallId']==c['id'] and ack.get('isError') is False and h(can(ack))==p['ack_message_sha256']
                assert p['producer_scope']==orig_targets[(p['episode_id'],i)]
                assert p['producer_scope']['source_message_index']==i and p['producer_scope']['source_event_line']==pm[i]['event_line']
                assert p['producer_scope']['source_admission']=='HOLD_PROTECTED' and p['producer_scope']['protected_source_ids']
                stripped={k:v for k,v in iv.items() if k!='candidate_gate'};mode=p['match_mode']
                if mode=='EXACT_ALL_ORIGINAL_FIELDS_PLUS_CANDIDATE_GATE':assert stripped==obj
                elif mode=='ALL_INPUT_FIELDS_EXACT_IN_PRODUCER':assert all(obj[k]==v for k,v in stripped.items())
                elif mode=='EXACT_ORIGINAL_OBJECT_PLUS_EMPTY_CONFLICTS_DEFAULT':assert set(stripped)==set(obj)|{'conflicts'} and stripped['conflicts']==[] and all(stripped[k]==v for k,v in obj.items())
                elif mode=='EXACT_SIX_ORIGINAL_FIELDS_PLUS_STEPS_COPIED_FROM_ROUTE_SIGNATURE':
                    assert set(stripped)=={'id','name','category','source_ids','steps','route_signature','value_plan'}
                    assert all(stripped[k]==obj[k] for k in ['id','name','category','source_ids','route_signature','value_plan']) and stripped['steps']==obj['route_signature']['steps']
                else:raise AssertionError(('unsupported_mode',mode))
                assert {k:h(can(v)) for k,v in obj.items()}==p['original_object_field_value_sha256']
                # Recheck at least one protected seed occurs in original already-visible
                # metadata/text; never import a later read to support this writer.
                prior='\n'.join(text(z['message']) for z in pm[:i]); visible=set(re.findall(r'conv_[a-f0-9]{12}',prior));seeds=set(p['producer_scope']['protected_source_ids'])&visible
                assert seeds,(p['episode_id'],'no_earlier_protected_identifier')
                key=(p['episode_id'],i);producerchecks[str(key)]={'episode_id':p['episode_id'],'write_message_index':i,'native_sha256':p['native']['sha256'],'actual_write_ACK_verified':True,'scope_exact_final_v9_row':True,'protected_seeds_visible_before_write':len(seeds),'original226_seeds_visible_before_write':len(set(p['producer_scope']['original226'])&visible)}
                protected_producers.append((p,obj))
            receipts=[]
            for q in link['actual_receipts']:
                ci=q['call_message_index'];oi=q['observation_message_index'];call=next(c for c in calls(actual[ci]['message']) if c['id']==q['tool_call_id']);a=call['arguments'];a=json.loads(a) if isinstance(a,str) else a
                nativepath='/workspace/inputs/'+link['input_name'];assert a.get('path',a.get('file_path'))==nativepath or nativepath in a.get('command','')
                observation=actual[oi]['message'];assert observation['toolCallId']==call['id'] and ci<oi and h(can(observation))==q['observation_message_sha256']
                ob=text(observation);assert h(ob.encode())==q['observation_text_sha256'];norm=ob.replace('\r\n','\n');raw=Path(inp['path']).read_bytes().decode('utf-8-sig');whole=raw in ob;normalized=raw.replace('\r\n','\n').strip() in norm
                assert whole==q['entire_original_file_text_contiguous_in_actual_observation'] and normalized==q['entire_file_after_CRLF_to_LF_and_outer_whitespace_normalization_contiguous']
                scalarok=0
                for z in q['received_protected_original_scalar_proofs']:
                    pp,obj=next((p,v) for p,v in protected_producers if p['episode_id']==z['producer_episode_id'] and p['message_index']==z['producer_message_index'])
                    value=pathget(obj,z['original_field_path']);enc=json.dumps(value,ensure_ascii=False);s=z['normalized_observation_character_start'];end=z['normalized_observation_character_end']
                    assert norm[s:end]==enc and enc in raw.replace('\r\n','\n') and h(value.encode())==z['scalar_UTF8_sha256'] and h(enc.encode())==z['quoted_scalar_sha256'] and len(enc)==z['quoted_scalar_characters']
                    scalarok+=1
                proven=bool(protected_producers and (whole or normalized or scalarok))
                if proven:receipts.append(oi)
                checks.append({'episode_id':e['episode_id'],'route_id':e['route_id'],'input_name':link['input_name'],'producer_derivations_verified':len(protected_producers),'actual_call_index':ci,'actual_observation_index':oi,'whole_file_OR_normalized_whole_file_received':whole or normalized,'actual_exact_protected_field_scalars_checked':scalarok,'scope_propagation_proven':proven})
            boundary=min(receipts) if receipts else None;assert boundary==link['earliest_proven_protected_exposure_observation_index']
            if boundary is not None:boundaries.append(boundary)
        boundary=min(boundaries) if boundaries else None;assert boundary==e['proven_protected_boundary']
        et=[t for t in targets if t['episode_id']==e['episode_id']];assert len(et)==e['scope_targets']
        for t in et:
            i=t['source_message_index'];assert t['original_message']==actual[i]['message'] and t['source_event_line']==actual[i]['event_line'] and h(can(actual[i]['message']))==t['original_message_sha256']
            expected='HOLD_PROTECTED_ACTUAL_ROUTE_PRODUCER' if boundary is not None and i>boundary else 'HOLD_ANCESTRY_NOT_CLOSED'
            assert expected==t['current_decision'] and t['protected_dependency_observation_index']==boundary and t['positive_loss']==0
            targetcheck.append({'id':t['id'],'episode_id':t['episode_id'],'source_message_index':i,'actual_exposure_observation_index':boundary,'decision_independently_recomputed':expected})
    counts=dict(Counter(x['decision_independently_recomputed'] for x in targetcheck));assert counts=={'HOLD_ANCESTRY_NOT_CLOSED':3,'HOLD_PROTECTED_ACTUAL_ROUTE_PRODUCER':266}
    out={'schema':'wrd-crossroutes-independent-byte-and-boundary-review-v1','status':'PASS_FIXED17_EPISODES269_TARGETS','reviewer':'scheduled_batch24 agent; different agent and independent code, no producer-code import.','input_closure_pin':pin(closurepath),'input_target_bank_pin':pin(C/'TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz'),'episodes':17,'targets':269,'decisions':counts,'actual_producer_writers_checked':len(producerchecks),'actual_source_input_receipt_checks':checks,'producer_write_and_scope_checks':list(producerchecks.values()),'every_target_strict_after_actual_observation_recomputed':targetcheck,'new_positive_loss':0,'no_native_model_resource_execution_or_training':True,'limitations':['Supports provenance/isolation decisions, not semantic correctness or skill outcome.','Partial actual receipts use verified exact original-field scalar positions; not represented as whole-file receipt.','Three targets before or at protected receipt remain unknown, not clean training.']}
    (O/'CROSSROUTES_INDEPENDENT_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':out['status'],'producers':len(producerchecks),'decisions':counts,'receipt_checks':len(checks),'qa_pin':pin(O/'CROSSROUTES_INDEPENDENT_QA.json')}))

if __name__=='__main__':main()
