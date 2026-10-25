"""Persist the assistant's bounded six-example semantic reading, not a model judge."""
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashed_text(s):return hashlib.sha256(s.encode()).hexdigest()
def spans(s,terms):
    result=[]
    for tag,term in terms:
        i=s.find(term)
        if i>=0:result.append({'label':tag,'reasoning_character_start':i,'reasoning_character_end':i+len(term)})
    return result
def main():
    inp=OUT/'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz';planp=OUT/'SSE_SEMANTIC_SAMPLE_PLAN.json';plan=json.loads(planp.read_text(encoding='utf-8'))
    rows={r['id']:r for r in map(json.loads,gzip.open(inp,'rt',encoding='utf-8'))}
    outcomes={r['id']:r for r in map(json.loads,gzip.open(OUT/'controlled/sse_action_outcome.labels.jsonl.gz','rt',encoding='utf-8'))}
    notes=[
      {'phases':['A','C'],'purpose':'Acquire source evidence and preserve an explicit user correction before constructing a reusable method.',
       'process_disposition':'process_silver_requires_current_protocol_projection',
       'basis':['The original source has three user turns, including a correction and complaint that a promised edit was not present.',
                'The actual selected action reads exactly those three source turns and the original event is OBSERVED.',
                'The original current state has no input assets or workflows; future script execution in the reasoning is planning, not observed execution.'],
       'limits':['The 56966-character reasoning repeatedly drafts unexecuted scripts and future decisions before ultimately choosing READ. It is not a concise reasoning gold target.',
                 'Business accounting rules discussed in hypothetical drafts were not independently verified in this review.'],
       'terms':[('user_correction_tracking','The key user correction:'),('unavailable_resources','there are no actual files to inspect'),('one_action_final_selection','this first response, I should return D1')]},
      {'phases':['C','D'],'purpose':'Stop after bounded local validation while preserving unresolved methodological limits.',
       'process_disposition':'process_silver_requires_current_protocol_projection',
       'basis':['The original state includes a registered executed generator, recorded local assertions and an explicitly DEFERRED non-blocking issue.',
                'The reasoning recognizes the execution-branch budget is exhausted and chooses a FINISH action rather than claiming further trials occurred.',
                'The target explicitly defines READY as structural trial readiness, not task success or library admission; original event is FINISHED.'],
       'limits':['The original input material is synthetic_previous_version and recorded code assertions are not independent business quality assessment.',
                 'READY must not be relabeled current WRD retain/K_Q/K_R/K_G. The budget-allocation assumption remains unverified.'],
       'terms':[('budget_bound','bounded local run cap exhausted'),('structural_boundary','READY means structurally ready for independent consumption'),('deferred_issue_retained','u2 is DEFERRED')]},
      {'phases':['A','C'],'purpose':'Distinguish unrelated requests and check actual tool capability before trusting historical image interpretation.',
       'process_disposition':'process_silver_requires_current_protocol_projection',
       'basis':['The original user source contains an image-diagnosis request and a separate financial request.',
                'The current tool catalog says image inspection supplies dimensions without OCR; the original action therefore requests an inspection of the actual declared resource.',
                'The reasoning treats the historical claimed image diagnosis as unverified rather than importing it as fact; original event is OBSERVED.'],
       'limits':['The current source image has synthetic material identity, not authenticated historical bytes.',
                 'Extended hypothetical finance calculations and future TRY/UPDATE plans are not verified by this image-inspection action; some drafted future ordering conflicts with the create-workflow-before-TRY rule.'],
       'terms':[('historical_answer_not_ground_truth','we cannot verify the image content'),('capability_boundary','no OCR'),('chosen_inspection','Let me start with INSPECT')]},
      {'phases':['B','C'],'purpose':'Diagnose missing libraries and propose an alternative XLSX/XML and DOCX capability probe.',
       'process_disposition':'reject_as_positive_action_use_failure_repair',
       'basis':['The preceding original observation really contains ModuleNotFoundError for the missing spreadsheet library.',
                'The proposed standard-library fallback is relevant to resource diagnosis, but the emitted ActionProposal.arguments is a list.',
                'The original decision transcript rejects this exact action with arguments must be an object; the next decision revises the proposal and is OBSERVED.'],
       'limits':['This response cannot be a correct-action positive even though its reasoning is authentic, complete and tokenizable.',
                 'A draft XML parser also uses a literal namespaced attribute spelling that does not resolve the actual relationship attribute. It was not executed because the earlier schema check rejected the action.'],
       'terms':[('observed_error_condition','INSPECT attempt failed with ModuleNotFoundError'),('fallback_choice','zipfile+XML'),('unverified_future_success','If TRY succeeds')]},
      {'phases':['A','B'],'purpose':'Build a parameterized workflow from the full source while retaining user-specific constraints and unresolved input-version ambiguity.',
       'process_disposition':'process_silver_requires_current_protocol_projection',
       'basis':['The original goal requests a particular output workflow and explicit source-specific constraints; the current state has no source input assets or existing workflow.',
                'The target creates parameterized steps, evidence references, checks and an OPEN issue about unresolved multiple-version handling; asset_refs remain empty.',
                'Original event is APPLIED, indicating state update acceptance rather than proof of resource or business correctness.'],
       'limits':['The reasoning repeatedly plans a synthetic self-test; neither those future tests nor dependency availability have occurred at this decision.',
                 'The output refers to a target application without validating an application-compatible import format. Current WRD skill packaging and actual resource reproduction still need separate evidence.'],
       'terms':[('absent_input_assets','input_assets: []'),('source_specific_constraints','Key user requirements:'),('create_before_try','UPDATE first, then TRY')]},
      {'phases':['A','B','C'],'purpose':'Recover reporting constraints and plan around a missing dependency, with an unresolved boundary between requested scenario adjustments and factual usage measurements.',
       'process_disposition':'needs_context_and_data_faithfulness_boundary',
       'basis':['The original user really supplies multiple formatting and reporting corrections; the target preserves many of these constraints and creates a workflow before a proposed probe.',
                'The source explicitly asks for replacing a usage aggregate, and the reasoning notices this is a form of fabrication but generalizes it as a stable preference for realistic numbers.',
                'The resulting workflow proposes recomputing reported metrics around the override without clearly separating measured data from an adjusted scenario; original event APPLIED only checks structure.'],
       'limits':['This must not be taught as an unconditional rule to make observed business figures look realistic.',
                 'A valid derived training view would need an explicit measured-versus-user-adjusted scenario boundary and preserve original measurements; this review does not invent such a corrected original response.',
                 'Dependency fallback planning remains useful but is not proof the final report or whole skill is correct.'],
       'terms':[('recognition_of_fabrication','which is a fabrication of data'),('unsafe_generalization','The stable preference:'),('source_override','Apply user-specified overrides')]}
    ]
    reviewed=[]
    for item,note in zip(plan['sample'],notes):
        r=rows[item['id']];reason=r['original_response']['choices'][0]['message']['reasoning_content'];q=r['original_request'];u=json.loads(q['messages'][1]['content'])
        reviewed.append({**item,'reviewer':'assistant_raw_thinking_locator_v4','review_type':'bounded_process_relevance_and_action_consistency_ai_review_not_human_gold',
            'human_gold':False,'original_reasoning_read_complete':True,'original_system_and_source_user_goal_read':True,
            'full_original_request_all_embedded_history_read':False,
            'reviewed_request_scope':['original_system','original_source_user_requirements','current_state_workflows_issues_and_resource_identity_as_needed','observed_parsed_output','original_action_outcome'],
            'domain_or_business_correctness_independently_validated':False,'task_family':'workflow_and_resource_distillation_not_personal_or_organization_adoption',
            'current_wrd_phase_mapping':note['phases'],'reasoning_process_purpose':note['purpose'],'process_disposition':note['process_disposition'],
            'evidence_supported_observations':note['basis'],'material_limitations':note['limits'],
            'source_reasoning_sha256':hashed_text(reason),'source_request':r['source_request'],'source_sse':r['source_sse'],
            'source_original_parsed':r['source_parsed'],'original_outcome':outcomes[item['id']],
            'reasoning_evidence_spans':spans(reason,note['terms']),
            'native_protocol_compatible_without_adaptation':False,'current_protocol_projection_must_be_declared_derived':True,
            'full_rationale_and_action_semantic_admission':'reject_positive_action' if note['process_disposition'].startswith('reject_') else 'needs_context_or_further_scope_review',
            'training_admitted':False})
    report={'schema_version':'wrd-sse-semantic-sample-review-v4','fixed_sample_plan_sha256':sha(planp),'input_sha256':sha(inp),
        'sample_count':len(reviewed),'different_source_ids':len({r['episode_id'] for r in reviewed}),
        'selection_policy':plan['selection_policy'],'sample_reviews':reviewed,
        'summary':dict(Counter(r['process_disposition'] for r in reviewed)),
        'scope':'Six selected authentic reasoning/action records; no extension of review decisions to all 45/68 or the native corpus.',
        'all_original_source_fields_and_reasoning_retained':True,'hidden_or_missing_reasoning_invented':False,
        'no_new_teacher_or_judge_model_calls':True,'training_started':False,'script_sha256':sha(Path(__file__))}
    (OUT/'SSE_SEMANTIC_SAMPLE_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sample_count':len(reviewed),'summary':report['summary'],'human_gold':False,'training_admitted':0}))

if __name__=='__main__':main()
