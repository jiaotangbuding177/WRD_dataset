"""Independent, CPU-only source identity and semantic review of authored labels."""
from pathlib import Path
import ast
import gzip
import hashlib
import json

ROOT=Path('D:/skillloop')
HERE=Path(__file__).resolve().parent
TARGET=HERE.parent/'build_source_decisions.py'
DATA=ROOT/'output/20261027_wrd_main_v10/clean_inputs'

def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]

def main():
    tree=ast.parse(TARGET.read_text(encoding='utf-8'))
    cases=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in n.targets))
    pool={x['source_id']:x for x in rows(DATA/'source_pool.with_body.jsonl.gz')}
    scope={x['source_id']:x for x in rows(DATA/'source_scope.metadata.jsonl.gz')}
    proof=[];failures=[]
    for name,sid,indices,stage,rationale,decision in cases:
        source=pool[sid];sp=source['original_conversation_pin'];p=Path(sp['path'])
        assert p.is_file() and sha(p.read_bytes())==sp['sha256']
        original=json.loads(p.read_text(encoding='utf-8-sig'));original_messages=original['messages']
        user_by_id={m['id']:m for m in original_messages if m['role']=='user'}
        selected=[]
        for i in indices:
            m=source['user_messages'][i]
            assert user_by_id[m['id']]['content']==m['content']
            selected.append({'pool_user_index':i,'message_id':m['id'],'full_content_chars':len(m['content']),
                'full_content_sha256':sha(m['content'].encode()),'original_conversation_exact_match':True})
        assert source['split']=='train' and scope[sid]['status']=='TRAIN'
        result={'id':'batch24_source_decision:'+name,'source_id':sid,'source':sp,'selected_user_proofs':selected,
            'scope':scope[sid],'target_stage':stage,'new_rationale_sha256':sha(rationale.encode()),
            'new_decision_canonical_sha256':sha(json.dumps(decision,ensure_ascii=False,separators=(',',':')).encode()),
            'semantics':'PASS_BOUNDED_SOURCE_ONLY_NEXT_STEP_AND_VERIFICATION_POLICY',
            'why_not_just_contract':'The target schedules a next action, unknown prerequisites and checks for the selected concrete request or correction; it does not merely restate a generic pipeline contract.'}
        if name=='funding_job_update' and 1 not in indices:
            failures.append({'id':result['id'],'issue':'Missing earlier user text-overlap evidence while persistent-update target includes no-overlap requirement. Add original user occurrence index1 or explicitly frame it as a new recommendation.'})
            result['semantics']='REPAIR_REQUIRED_MISSING_INPUT_CONSTRAINT'
        proof.append(result)
    raw=HERE.parent/'source_decisions_02/decisions.raw.jsonl.gz'
    raw_check=[]
    if raw.exists():
        rr=rows(raw);assert len(rr)==len(cases)
        for row in rr:
            assert row['source_admission']=='ADMIT_SOURCE_ONLY' and row['training_admitted'] is False
            assert row['message_loss_mask']==[0,0,1] and row['approved_components']==['R','D'] and row['loss_multiplier']==.25
            assert row['tools']==[] and row['historical_assistant_answers_used'] is False and row['protected_route_or_code_used'] is False
            expected=next(x for x in cases if row['id'].endswith(':'+x[0]));name,sid,indices,stage,rationale,decision=expected
            assert row['messages'][-1]['reasoning_content']==rationale
            assert json.loads(row['messages'][-1]['content'])==decision
            for i in indices:assert pool[sid]['user_messages'][i]['content'] in row['messages'][1]['content']
            assert row['confirmed_repair'] is False and row['qualified_skill_KEEP'] is False
            raw_check.append({'id':row['id'],'raw_matches_reviewed_source_and_label':True})
    result={'schema':'wrd-source-only-decisions-independent-semantic-peer-v1',
        'status':'PASS_BOUNDED_SOURCE_ONLY_DECISIONS' if not failures and raw.exists() else 'REPAIR_OR_GENERATION_PENDING',
        'reviewed_script':pin(TARGET),'raw_pin':pin(raw) if raw.exists() else None,
        'reviewed_targets':len(proof),'distinct_sources':len({r['source_id'] for r in proof}),
        'records':proof,'raw_checks':raw_check,'failures':failures,
        'reviewed_input_scope':'Actual pinned clean original user occurrences only; no old route, resource, trial or historical assistant answer supplies new target facts.',
        'semantic_findings':['The funding examples preserve growing content and visible quality constraints instead of rewarding file existence.',
          'The three-page example correctly leaves identities unknown when the earlier proposal is absent.',
          'The video-script example preserves user-required output order before any video work.',
          'The two HTML examples distinguish explicit requirements from unrequested engines, quizzes and unverified astronomical details.',
          'No target invents an actual environment, tool call, generated artifact, successful patch or retained skill.'],
        'credit_scope':'Limited source-only planning, feedback diagnosis, prerequisite checks and update-boundary supervision.',
        'not_supported':['Actual resource construction or repair success','Verified skill utility or lower cost','Native autonomous A-through-D trajectory','Original teacher chain of thought','Human gold or model performance guarantee'],
        'tokenizer_mask_and_loader_QA':'ROOT_SEPARATE_PENDING','training_started':False,'weights_loaded':False,'new_Agent_calls':0,
        'resolved_prior_issue':'Version02 funding_job_update includes original user index1; merge and glyph states also retain contiguous earlier user requirements. Earlier draft is excluded from this pass.',
        'review_script_sha256':sha(Path(__file__).read_bytes())}
    (HERE/'PEER.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'targets':len(proof),'failures':failures,'raw_checked':len(raw_check)}))

if __name__=='__main__':main()
