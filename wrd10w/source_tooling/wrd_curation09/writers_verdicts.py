"""Explicit all-31 semantic dispositions and conservative version correction."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261031_wrd_curation09/writers'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def hs(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# These are actual current dispositions, not a claim that held material is
# inherently worthless. The complete body and all original feedback are kept.
HOLDS = {
 '36b278e3e411541fe6bffa61': ('HOLD_RESERVED_EVALUATION_SOURCE', 'conv_050cdce318d9 and its complete source-scope component were reserved for independent evaluation; do not construct new training labels.', []),
 '0e1577b9870786d7a729847b': ('HOLD_ORIGINAL_VERSION_OUTCOME_NOT_ISOLATED', 'This initial 31002-character renderer was overwritten by the second complete writer at index15 before the final render. Final MP4 success cannot label this first version. Original system incomplete; later failed publish/edit introduces additional actual-state ambiguity.', [15, 40, 42]),
 '2e7f6d8d43e3133718e867fd': ('HOLD_EXACT_EXECUTED_VERSION_AFTER_FAILED_PUBLISH_UNCLOSED', 'The 27798-character second write is complete and later rendering produced an MP4, but failed apply_patch/edit feedback contains a changed current-file state. Do not attribute final outcomes to this write until those mutations/readbacks are reconciled, or independently test this exact code.', [16, 40, 42, 60, 62]),
 'fa664bcae37f164a2e0dc3ec': ('HOLD_KNOWN_RUNTIME_ERROR_AND_MUTATION_CHAIN', 'Actual scene7 raises TypeError because alpha_composite receives float coordinates. A later failed patch/edit already shows int(...) in current-file feedback; failed ACK does not prove no mutation. Numerous later subtitle/scene changes are distinct versions.', [20, 22, 24]),
 '9c3b6410e2baf741a14a8a56': ('HOLD_KNOWN_RENDERER_KEY_ERROR', 'Original renderer raises KeyError 齐天大圣 through icon(c[2],...) in p2, p5 and product_sheet. Three successful local edits have been recovered, but this full initial writer is not a correct whole resource. Independent checks of repaired final geometry/source fidelity remain required.', [30, 34, 38, 46]),
 '1df772751ec99acb2aaa368b': ('HOLD_MALFORMED_IMAGE_CLI_AND_FALSE_DONE', 'All eight image calls omit the required image subcommand: python $IMG --text... is not the recorded CLI schema. set -u and final echo DONE permit success-like termination despite failures; actual image directory was empty.', [26]),
 'ef2ab09a32f64ca742f0e812': ('HOLD_SPEECH_DEPENDENCY_FAILURE_AND_FALSE_DONE', 'Actual audio/speech endpoint returns404 and the audio directory is empty although the shell ends DONE/exit0. The narration venue name also needs exact original source verification before any factual credit. No positive whole batch supervision.', [26]),
 '6a774c3501fbc16dc754c6ae': ('HOLD_ASSET_FAILURE_NOT_COMPLETION', 'gen_image/gen_speech swallow failures into log messages and finish assets done. The actual native follow-up exposes image/speech endpoint failure, so cached existence alone is not verified content or completion. Full before/log retained for future failure-control teaching.', [18, 20]),
 '496d13e3fd020ac5f85b9eaf': ('HOLD_MEDIA_DEPENDENCIES_AND_VERSIONED_REPAIR_REQUIRED', 'Clip builder depends on prompts.json, frames and real narration. Later native execution changes audio suffix/duration handling and triggers a new unmatched-bracket SyntaxError before further repair. Final83s video cannot approve this initial resource without binding assets and exact code version. No unknown media code executed here.', [84, 86, 88, 90, 92, 96, 98, 124]),
 '7c1737c14d72dd011faec8a6': ('HOLD_ORIGINAL_SYNTAX_AND_PARAMETER_ERRORS', 'Original code has invalid Chinese opening quote at line106. Once fixed, para(..., en=...) raises unexpected-keyword TypeError because its signature lacks en. Original bad complete writer remains zero; candidates02 contains a separate new-author three-edit repair with full before state and original SyntaxError.', [8, 10, 12, 14]),
 'a6a3ff55eeb6d9d521bad1bf': ('HOLD_WRONG_LEGAL_CLAUSE', 'The template expressly chooses non-full-time employment yet allows a probation period up to15 days; official Labour Contract Law article70 forbids probation for this category. It also has the typo 未经济可. A rendered DOCX does not establish contract legality; no whole legal-content positive loss.', [12, 14, 16]),
 'd56a25fa24852c7f50784c36': ('HOLD_UNSUPPORTED_CASH_REALISATION_ASSUMPTIONS', 'Arithmetic38400/month,591.2% three-year ROI and5.21months is conditionally consistent, but60% ticket automation does not prove cash payroll savings when freed staff are redeployed. The report calls savings certain, assumes training is included in200k, infers saturated workload/zero first response and fixed capacity without support. Tables may exceed default text width; resource success is not business correctness.', [14, 36]),
 '1178e97eae9a16340eb79560': ('HOLD_PRODUCT_CAPABILITY_INFERENCE_NOT_DISTINGUISHED', 'Public teacher-side capabilities are expanded into student shared-workspace/account/immediate-feedback scenarios and benefit claims; the document does not consistently distinguish verified student-product functions from teacher-mediated/inferred uses. Source pages and failed late edits are preserved, but full business factual/causal scope is not yet resolved.', [48, 50, 52, 54]),
 'e71fc8534ea4de00d2d4d79c': ('HOLD_RETRIEVAL_QUALITY_AND_QUERY_ASSUMPTION', 'Complete bounded browser retrieval helper is syntactically valid, but a query injects 深圳 without source support, prior search results are unrelated/blocked, and a network/offline browser test cannot establish authoritative listing-policy evidence. Could later admit a strictly scoped retrieval mechanism with the unsupported query masked after independent QA; not an IPO analysis positive.', [4, 6, 10]),
}
IMAGE_BATCH = ['d165b0cea2fe699ea8a7bfb9','46f6a1725d09adeec369e24d','e99c2d30367ec32f96e1e522','95303f981f752b93e75d1626','2284078afa2d46670eb496ca','62fa0d4ef00077d51a2a1d33']
for owner in IMAGE_BATCH:
    HOLDS[owner] = ('HOLD_UNAVAILABLE_IMAGE_SERVICE_AND_BATCH_OUTCOME',
      'This is a complete36-page image-service batching resource, not a36-page successful creation trace. Native logs expose repeated permanent image endpoint404; some scripts log DONE/all done with failures, skip by file size rather than source/config/content identity or retry repeatedly without a permanent-error stop. Source prompts and all original failure/recovery records are retained. Later unrelated local renderers are not evidence that this image-CLI batch worked.', [])


def main():
    idx = load(OUT / 'RECOVERY_INDEX.json')
    with gzip.open(OUT / 'candidates02/candidates.raw.jsonl.gz', 'rt', encoding='utf-8') as f:
        candidates = [json.loads(l) for l in f if l.strip()]
    original_views = {r['owner_id']: r for r in candidates if r['owner_id'] in {x['owner_id'] for x in idx['rows']}}
    assert len(original_views) == 11 and len(HOLDS) == 20
    assertions = []
    version_overlay = []
    for row in idx['rows']:
        owner = row['owner_id']; code = (OUT / row['code_ref']).read_text(encoding='utf-8')
        packet = load(OUT / row['packet_ref']); timeline = load(OUT / row['timeline_ref']) if 'timeline_ref' in row else load(OUT / 'episodes' / f"{row['episode_id']}.timeline.json")
        syntax = {'status': 'NOT_PYTHON'}
        if row['code_ref'].endswith('.py'):
            try: ast.parse(code); syntax = {'status': 'AST_PARSE_PASS_NOT_EXECUTION'}
            except SyntaxError as e: syntax = {'status': 'AST_PARSE_FAIL', 'line': e.lineno, 'message': e.msg}
        if owner in original_views:
            view = original_views[owner]
            disposition = 'BODY_CANDIDATE_WITH_PRECISE_NEGATIVE_MASKS_PENDING_ROOT_ADMISSION'
            reason = view['credit_scope']
            indices = [r['index'] for r in timeline if r['role'] == 'toolResult' and r['index'] > row['message_index']]
            mask = view['target_code_unicode_exclusions']
        else:
            disposition, reason, indices = HOLDS[owner]; mask = []
        evidence = []
        for event in timeline:
            if event['index'] in indices:
                evidence.append({'message_index': event['index'], 'role': event['role'],
                                 'text_utf8_sha256': hs(event['text']), 'text_characters': len(event['text']),
                                 'source_timeline_ref': f"episodes/{row['episode_id']}.timeline.json"})
        assertions.append({'owner_id': owner, 'episode_id': row['episode_id'], 'source_ids': row['source_ids'],
             'native_path': row['native_path'], 'whole_original_code_ref': row['code_ref'],
             'whole_original_code_sha256': row['code_sha256'], 'characters': row['characters'],
             'full_original_target_and_write_ack_packet': row['packet_ref'],
             'full_original_context_ref': f"episodes/{row['episode_id']}.context.original.json",
             'all_intermediate_tool_operations_feedback_and_R_preserved': True,
             'native_original_readable_R_blocks': 0, 'original_system_complete': False,
             'new_functional_state_required_for_any_candidate': True,
             'disposition': disposition, 'reason': reason, 'actual_evidence': evidence,
             'syntax': syntax, 'negative_code_ranges': mask,
             'whole_resource_or_whole_skill_quality_inferred_from_success': False,
             'training_admitted_by_child': False})
        chain = load(OUT / 'versions' / owner / 'VERSION_CHAIN.json')
        ambiguous = [x for x in chain['operations'] if x['outcome'] in {'FAILED_PATCH_NO_VERSION_CHANGE', 'FAILED_EDIT_NO_VERSION_CHANGE', 'PATCH_NEEDS_SEPARATE_EXACT_RECONSTRUCTION', 'EDIT_NOT_RECONSTRUCTED_NO_FALSE_VERSION'}]
        if ambiguous:
            version_overlay.append({'owner_id': owner, 'original_version_chain_ref': f'versions/{owner}/VERSION_CHAIN.json',
              'correction': 'FAILED_ACK_DOES_NOT_PROVE_NO_FILE_MUTATION; latest_exact means a literal transformation on the tracked text, not authenticated latest native filesystem bytes after an intervening uncertain mutation.',
              'uncertain_native_state_from_message_indices': [x['message_index'] for x in ambiguous],
              'later_acknowledged_edits_do_not_close_unobserved_prior_mutation': True,
              'original_write_body_hash_still_exact': True,
              'positive_training_admission_from_latest_reconstruction': False})
    save(OUT / 'VERSION_VALIDITY_CORRECTION02.json', {'status': 'CONSERVATIVE_CORRECTION_PRIOR_MECHANICAL_LABELS_PRESERVED',
        'reason': 'Actual failed staged publish may already mutate the file, as shown by native current-file readback. Do not equate tool error with rollback.',
        'rows': version_overlay})
    save(OUT / 'ALL31_SEMANTIC_VERDICTS.json', {'status': 'ALL31_EXPLICIT_DISPOSITIONS; NO_CHILD_TRAINING_ADMISSION',
       'counts': {'owners':31, 'episodes':26, 'source_ids':16, 'original_writer_functional_body_candidates':11,
                  'original_writers_held_for_specific_content_or_dependency_or_version_reasons':19,
                  'original_writer_held_reserved_evaluation':1, 'new_authored_local_repair_body_candidates':4,
                  'actual_raw_candidate_targets':15, 'original_R_blocks_recovered':0,
                  'root_main_admissions_by_this_child':0},
       'reservation_path': 'output/20261031_wrd_curation09/holdout/holdout_reservation.json',
       'reservation_sha256': hashlib.sha256((ROOT / 'output/20261031_wrd_curation09/holdout/holdout_reservation.json').read_bytes()).hexdigest(),
       'rows': assertions,
       'quality_references': [
          {'purpose':'Minimum text contrast','url':'https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum','scope':'4.5:1 normal text /3:1 large text, not whole theme quality'},
          {'purpose':'Non-full-time probation prohibition','url':'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_0abfdd261c03417b949df19d869add8d.html','scope':'Article70; not a complete legal review'},
          {'purpose':'Basic planetary teaching reference','url':'https://nssdc.gsfc.nasa.gov/planetary/factsheet/','scope':'Approximate teaching quantities, not accurate ephemerides'}],
       'cost': {'new_business_teacher_actor_calls':0,'training_started':False,'ai_cpu_curation_cost':'UNKNOWN_NOT_ZERO'}})
    save(OUT / 'QA_REQUESTS.json', {'fixed_environment':'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2',
       'network':'none','memory':'6g','cpus':4,'shm_size':'1g','chromium_executable':'/usr/bin/chromium',
       'packets': [
        {'owners':['0d78ae10be60edfdaba93dc0','7a6d2f63d0c34910127bb0d4'],'dependencies':['python-docx','Noto Sans CJK SC','LibreOffice for render'],'checks':'Generate and reopen DOCX, verify source business constraints /45-minute sum and oral activities; no future pedagogical effectiveness inferred.'},
        {'owners':['605cdf7450ad2d3ae8563788','b4c79fa37d65f5e447fbb9fc'],'dependencies':['python-pptx','LibreOffice','Noto'],'checks':'Reopen PPTX,1/3 slides, source-preserving text, shape bounds and PDF render; quoted article is not current external fact verification.'},
        {'owners':['215439ffa54ad7c5a9aa8502','257f6602661ce6bd0135926b','addbee2f3bff0cbfae1bb183'],'dependencies':['Chromium'],'checks':'Standalone SVG parse/render1080x600, expected theme text, bounds/clipping; no external network/API needed.'},
        {'owners':['0dd5502eec8fa8afa8343b48'],'dependencies':['Chromium'],'checks':'Interactive8 planets, pause/speed/labels; reproduce circular-path mismatch and verify exact solar_after elliptical repair.'},
        {'owners':['57bf5a6f4263f47514add40d','8a3958608262a264663a580d'],'dependencies':['CSS/sRGB checks','Chromium optional'],'checks':'Original bright-teal white text fails; two actual contrast_after files use deep text and preserve background; mask additional unreviewed dark-mode claims.'},
        {'owners':['4e819190cc4ca6bf54f21cfb'],'dependencies':['Chromium'],'checks':'Reproduce extra physics integration/static-arrow error; remove-b edit is only label repair and cannot approve dynamics.'},
        {'new_resource':'candidates02/lesson_after.py','dependencies':['python-docx','Noto','LibreOffice optional'],'checks':'Original syntax error and en keyword mismatch are fixed with three exact edits. Reopen generated DOCX; no content-quality or teaching-outcome gold.'}],
       'do_not_execute':['network/service batches without real endpoint and budgets','unbound media assets','initial known-bad legal template as legal gold'],
       'original_code_execution_performed_by_this_verdict_script':False})
    print(json.dumps({'all31':True,'writer_body_candidates':11,'held_original_writers':20,'new_local_repairs':4,'version_uncertainty_overlays':len(version_overlay)}))

if __name__ == '__main__': main()
