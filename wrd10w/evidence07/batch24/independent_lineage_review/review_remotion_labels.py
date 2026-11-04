"""Independent source-text, prefix and semantic QA, without producer imports."""
from pathlib import Path
import gzip,hashlib,json,sys

ROOT=Path('D:/skillloop');OUT=Path(__file__).resolve().parent
SRC=ROOT/'output/20261029_wrd_batch24/remotion'/('source_only02' if '--v2' in sys.argv else 'source_only')
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}

def main():
    raw=SRC/'source_only_controller.raw.jsonl.gz';bank=rows(raw)
    provenance=SRC.parent/'source_only' if '--v2' in sys.argv else SRC
    evpath=provenance/'LABEL_EVIDENCE.jsonl.gz';evidence={x['id']:x for x in rows(evpath)}
    convpath=provenance/'original_conversation.json';conv=j(convpath);ms=conv['messages']
    change=j(SRC/'CHANGE_RECEIPT.json') if '--v2' in sys.argv else None
    if change:
        assert pin(raw)==change['new_raw']
        assert pin(provenance/'source_only_controller.raw.jsonl.gz')==change['old_raw_preserved']
        oldbank={x['id']:x for x in rows(provenance/'source_only_controller.raw.jsonl.gz')}
        changed={x['id']:x for x in change['changed_targets']}
    scopepath=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz';scope=next(x for x in rows(scopepath) if x['source_id']=='conv_eaf2e429a225')
    originalsource=ROOT/'output/20261021_workflow_skill_library/sources/conv_eaf2e429a225/conversation.json'
    cleanedsource=ROOT/'output/20261027_wrd_main_v10/clean_inputs/sources/conv_eaf2e429a225/conversation.original.json'
    assert convpath.read_bytes()==originalsource.read_bytes()==cleanedsource.read_bytes()
    assert scope['status']=='TRAIN' and scope['component_id']=='v10_group_a70cbc484f2ae7bd0659'
    assert len(bank)==len(evidence)==6 and len(ms)==112
    reviews=[];proofcount=0
    for b in bank:
        e=evidence[b['id']];end=b['prefix_end_exclusive'];prompt=b['messages'][1]['content'];pos=prompt.find('\n[');assert pos>=0
        actualprefix=json.loads(prompt[pos+1:]);assert actualprefix==ms[:end]
        assert h(can(actualprefix))==b['original_input_prefix_sha256']==e['prefix_sha256']
        assert end==e['prefix_end_exclusive'] and len(e['all_input_message_proofs'])==end
        assert pin(convpath)==b['original_conversation_pin'] and pin(scopepath)==b['source_scope_pin']
        for i,p in enumerate(e['all_input_message_proofs']):
            m=ms[i];assert i==p['message_index'] and m['id']==p['message_id'] and m['role']==p['role'] and p['field']=='content' and p['start']==0 and p['end']==len(m['content'])
            assert h(m['content'].encode())==p['content_text_sha256'] and h(can(m))==p['message_canonical_sha256'];proofcount+=1
        target=b['messages'][-1]
        if change:
            c=changed[b['id']];old=oldbank[b['id']];ot=old['messages'][-1]
            assert h(ot['content'].encode())==e['new_decision_sha256'] and h(ot['reasoning_content'].encode())==e['new_rationale_sha256']
            assert c['old_new_decision_SHA256']==[h(ot['content'].encode()),h(target['content'].encode())]
            assert c['old_new_rationale_SHA256']==[h(ot['reasoning_content'].encode()),h(target['reasoning_content'].encode())]
            assert c['old_new_user_input_SHA256']==[h(old['messages'][1]['content'].encode()),h(b['messages'][1]['content'].encode())]
            assert c['original_projected_prefix_SHA_unchanged']==old['original_input_prefix_sha256']==b['original_input_prefix_sha256']
            assert '原生历史先后和回复对应未经认证' in prompt
        else:
            assert h(target['content'].encode())==e['new_decision_sha256'] and h(target['reasoning_content'].encode())==e['new_rationale_sha256']
        decision=json.loads(target['content']);assert decision['confirmed_execution'] is False and decision['qualified_skill'] is False
        assert b['annotation_provenance']=='NEW_AUTHORED_SOURCE_ONLY_DECISION_NOT_ORIGINAL_TEACHER_REASONING_OR_EXECUTION'
        assert b['tools']==[] and b['message_loss_mask']==[0,0,1] and b['loss_multiplier']==0.25 and b['actual_native_tool_dispatch'] is False and b['positive_skill_outcome_claimed'] is False
        assert not b['original226'] and not b['holdout12'] and not b['protected_sources_visible_prefix']
        name=b['id'].split(':',1)[1]
        if name=='entry_resource_spec':
            assert end==1 and ms[0]['role']=='user' and 'remotion-video-generator' in ms[0]['content'] and '数字人注意不要过小' in ms[0]['content']
            description='Proposed discovery/reuse/resource specification based on first user request. Proposed PIP/layout/QA resources are new design suggestions, not claims that source already contained them.';classify='PROPOSED_ENTRY_AND_RESOURCE_PLANNING'
        elif name=='reported_failure_evidence':
            assert end==59 and '404' in ms[38]['content'] and 'staticFile' in ms[43]['content'] and 'alpha' in ms[58]['content']
            description='Evidence sufficiency and credit judgment over reported diagnostics; no executable implementation or verified repair.';classify='EVIDENCE_EVALUATION_ONLY'
        elif name=='resume_timeout':
            assert end==60 and ms[59]['role']=='user' and 'failed or timed out' in ms[59]['content']
            description='Proposed resume scheduling under a user-reported interruption. Actual process status, resource state and budget remain unknown.';classify='PROPOSED_RESUME_SCHEDULING'
        elif name=='feedback_readability':
            assert end==80 and ms[79]['role']=='user' and '大到能看清内容' in ms[79]['content'] and 'QA 检查' in ms[78]['content']
            description='Proposed revision and same-version visual verification plan following explicit readability correction; metadata QA is not treated as content QA.';classify='PROPOSED_FEEDBACK_REVISION_PLAN'
        elif name=='latest_correction':
            assert end==111 and ms[110]['role']=='user' and all(x in ms[110]['content'] for x in ['1.5倍','字幕压在键盘','开头字还是重叠'])
            assert decision['correction_contract']['requested_scale']==1.5
            description='Preserves 1.5x request, keyboard-subtitle overlap allowance, opening-word collision fix, unknown reference version and prior presenter requirement. No later v3 claim enters this input.';classify='PROPOSED_PRECISE_REVISION_SPEC'
        elif name=='final_outcome_gate':
            assert end==112 and ms[111]['role']=='assistant' and 'v3.mp4' in ms[111]['content']
            description='Evidence/outcome admission judgment: final v3/QA claims are historical self-report without artifacts. HOLD and undefined cost denominator are justified; no qualified KEEP/code credit.';classify='EVIDENCE_EVALUATION_ONLY'
        else:raise AssertionError(name)
        reviews.append({'id':b['id'],'prefix_end_exclusive':end,'prefix_actual_message_count':len(actualprefix),'all_input_message_SHA_and_character_ranges_verified':True,'prefix_no_later_projection_message':True,'native_historical_order_or_reply_to_verified':False,'new_rationale_SHA256':h(target['reasoning_content'].encode()),'new_decision_SHA256':h(target['content'].encode()),'semantic_credit_class':classify,'semantic_review':description,'achieved_code_or_repair_credit':False,'original_CoT_credit':False,'autonomous_execution_demonstration':False})
    reported=next(x for x in bank if x['id'].endswith(':reported_failure_evidence'));resume=next(x for x in bank if x['id'].endswith(':resume_timeout'))
    finding1='相互矛盾的404归因' in reported['messages'][-1]['content']
    finding2='超时只说明前次运行未正常继续' in resume['messages'][-1]['reasoning_content']
    finding3=any('按导出出现顺序保留的原始会话前缀' in x['messages'][1]['content'] for x in bank)
    issues=[]
    if finding1:issues.append({'id':'SEMANTIC_404_CAUSE_OVERSTATEMENT','row':reported['id'],'required_change':'Replace contradictory-causes claim with different/unverified 404 attributions. Distinct versions/causes can coexist; source text does not prove contradiction.'})
    if finding2:issues.append({'id':'USER_REPORT_VS_ACTUAL_TIMEOUT','row':resume['id'],'required_change':'State that failure/timeout is user-reported and actual process terminal state is unknown.'})
    if finding3:issues.append({'id':'PROJECTED_ORDER_DISCLOSURE','rows':'all6','required_change':'Input must disclose user-occurrence/semantic-response-stage projection and unauthenticated native order/reply-to; do not call it authenticated original export chronology.'})
    status='REQUIRES_2_SCOPED_CORRECTIONS_AND_PROJECTED_ORDER_DISCLOSURE' if issues else 'PASS_BOUNDED_NEW_SOURCE_ONLY_DECISION_LABELS'
    if '--v2' in sys.argv:assert not issues,issues
    out={'schema':'wrd-remotion-source-label-independent-QA-v1','status':status,'reviewer':'scheduled_batch24 different agent, independent code; no generator import.','raw_bank':pin(raw),'label_evidence':pin(evpath),'actual_change_receipt':pin(SRC/'CHANGE_RECEIPT.json') if change else None,'old_evidence_plus_actual_changed_target_body_SHA_reverified':bool(change),'original_conversation':pin(convpath),'original_source_exact_byte_identity':pin(originalsource),'clean_input_original_exact_byte_identity':pin(cleanedsource),'source_scope':pin(scopepath),'independent_enterprise_sources':1,'authored_targets':6,'verified_input_message_proofs_including_repeated_prefix_exposure':proofcount,'new_original_CoT_targets':0,'new_actual_code_or_repair_targets':0,'new_autonomous_execution_chains':0,'semantic_classes':{'evidence_evaluation_only':2,'proposed_entry_resume_revision_plans':4},'rows':reviews,'required_corrections':issues,
      'order_and_causality_limit':'All exact prefix bounds are checked within the provided source projection. Its sequence_basis explicitly says semantic response stage reconstruction, native_reply_to_verified=false and historical_event_identity_verified=false. No native historical causality guarantee follows from these prefix checks.',
      'cost_accounting_boundary':{'new_agent_calls_zero_refers_only_to':'No newly dispatched business Teacher/Actor/model experiment sessions or training in this offline data pass.','AI_curation_and_labeling_occurred':True,'AI_curation_tokens_or_cash_cost':'UNKNOWN_NOT_ZERO','CPU_curation_cost':'UNKNOWN_NOT_ZERO','new_business_calls_in_this_review':0,'new_training_or_weights_loading':False},
      'interpretation':'Two evidence-evaluation labels must not be counted as code generation, actual diagnosis-repair success or demonstrated control. All six are newly authored source-only silver annotations; root admission and dual-tokenizer compilation are separate checks.'}
    name='REMOTION_SOURCE_LABEL_QA02.json' if '--v2' in sys.argv else 'REMOTION_SOURCE_LABEL_QA.json';p=OUT/name;p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':status,'input_message_proofs':proofcount,'issues':len(issues),'QA':pin(p)}))

if __name__=='__main__':main()
