"""Independent, read-only semantic review; never executes captured programs."""
from pathlib import Path
import hashlib, json, struct

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261030_wrd_gap08'
SRC = BASE / 'semantic_root'
OUT = Path(__file__).resolve().parent


def digest(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
def pin(p):
    p = Path(p); b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': digest(b)}
def save(name, value):
    (OUT/name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())
def lf(p): return Path(p).read_bytes().decode('utf-8').replace('\r\n', '\n')
def body(m):
    c = m.get('content', [])
    return c if isinstance(c, str) else '\n'.join(x.get('text', '') for x in c if isinstance(x, dict))
def png_size(p):
    b = Path(p).read_bytes(); assert b[:8] == b'\x89PNG\r\n\x1a\n'
    return list(struct.unpack('>II', b[16:24]))


def main():
    game = load(BASE/'corpus/first6/ep_4aadd96d99f2c07543c7/GROUP.json')
    video = load(BASE/'corpus/first6/ep_4d412dca2c57480536e7/GROUP.json')
    poster = load(BASE/'corpus/first6/ep_2493f463fdf84d1ba740/GROUP.json')
    gm = game['original_context']['messages']; vm = video['original_context']['messages']
    pm = poster['original_context']['messages']
    recovery = load(SRC/'PROGRAM_VERSION_RECOVERY.json')
    checks = []; versions = []
    for tr in recovery['actual_native_edit_transitions']:
        old = lf(tr['before']['path']); new = lf(tr['after']['path']); applied = old
        msgs = gm if tr['episode'] == 'ep_4aadd96d99f2c07543c7' else vm
        call = next(x for x in msgs[tr['index']]['content'] if x.get('id') == tr['call_id'])
        assert call['arguments'] == tr['arguments']
        obs = next(m for m in msgs[tr['index']+1:] if m.get('toolCallId') == tr['call_id'])
        assert obs == tr['actual_observation'] and not obs.get('isError')
        for edit in tr['arguments']['edits']:
            assert applied.count(edit['oldText']) == 1
            applied = applied.replace(edit['oldText'], edit['newText'], 1)
        assert applied == new
        versions.append({'episode': tr['episode'], 'native_message_index': tr['index'],
                         'original_call_and_ACK_verified': True,
                         'before_QA_file': pin(tr['before']['path']),
                         'after_QA_file': pin(tr['after']['path']),
                         'before_canonical_utf8_LF': {'bytes': len(old.encode()), 'sha256': digest(old.encode())},
                         'after_canonical_utf8_LF': {'bytes': len(new.encode()), 'sha256': digest(new.encode())},
                         'QA_files_are_CRLF_derivatives_not_original_frozen_native_bytes': True})
    checks.append('All three native edit calls/ACKs match GROUP and exact LF text transformations.')
    v = SRC/'qa/workspace/versions'
    a = lf(v/'game_test_v0.js')
    old = "try{chromium=require('playwright');}catch(e){chromium=require('/usr/lib/node_modules/playwright');}"
    b = a.replace(old, "const chromium=require('playwright').chromium;", 1)
    c = '\n'.join(b.splitlines()[:1] + b.splitlines()[2:])+'\n'
    assert b == lf(v/'game_test_v1.js') and c == lf(v/'game_test_v2.js')
    assert 'launch is not a function' in body(gm[12]) and 'already been declared' in body(gm[16])
    assert "sed -i '2d'" in gm[17]['content'][0]['arguments']['command']
    assert gm[18]['details']['exitCode'] == 0 and 'ERRORS: none' in body(gm[18])
    assert 'enemies' in body(gm[34]) and 'STATE:' in body(gm[34])
    checks.append('Game idx 12 failure -> idx 15 faulty import fix -> idx 16 duplicate declaration -> idx 17 deletion -> idx 18 retest; idx 31 spawn edit -> idx 34 state retest.')
    assert 'Invalid stream specifier: vbase' in body(vm[64])
    assert 'EXIT=0' in body(vm[64]) and 'FINAL:' in body(vm[68])
    assert '□' in body(vm[82]) and '没有方块占位符' in body(vm[88])
    checks.append('Video idx 64 actual filter error despite pipeline EXIT=0 -> edit 65 -> actual FINAL 68; tofu feedback 82 -> SVG edit 83 -> no-tofu report 88.')
    result = load(SRC/'qa/workspace/qa_outputs/RESULT.json')
    assert result['status'] == 'FAIL_PRESERVED'
    assert sum(x['pass'] is True for x in result['results']) == 12
    assert sum(x['pass'] is False for x in result['results']) == 1
    repair = load(SRC/'overlay_viewport_repair/REPAIR_EVIDENCE.json')
    edit = load(SRC/'overlay_viewport_repair/NEW_NATIVE_EDIT_ARGUMENTS.json')['edits'][0]
    before = lf(SRC/'overlay_viewport_repair/before.py')
    after = lf(SRC/'overlay_viewport_repair/workspace/tmp/archery/render_overlays.py')
    assert before.count(edit['oldText']) == 1 and before.replace(edit['oldText'], edit['newText'], 1) == after
    assert before == lf(v/'ep_4d412dca2c57480536e7_83_after.py')
    assert png_size(SRC/'qa/workspace/tmp/archery/win.png') == [2000,500]
    assert png_size(SRC/'overlay_viewport_repair/workspace/tmp/archery/win.png') == [2000,520]
    retest = load(SRC/'overlay_viewport_repair/workspace/RESULT.json')
    assert retest['status'] == 'PASS_LOCAL_VIEWPORT_REPAIR'
    assert not repair['native_OpenClaw_dispatch_performed'] and not repair['original_reasoning_recovered']
    checks.append('Viewport new edit is exact successor of original recorded edit83; actual PNG header 500 -> 520 and same repair retest passes. New curation authorship only.')
    jd = body(pm[6]); assert '上海闵行' in jd and '年薪 18 万' in jd and '30+' in jd
    checks.append('Poster Shanghai/salary/team-patent wording is grounded in original JD read at idx6, rather than fabricated merely because finite QA did not fact-check it.')

    # These are mandatory negative exclusions, not approval of the complement.
    spans = []
    def add(target, lines, reason, kind='KNOWN_BAD_OR_UNRESOLVED_CODE'):
        t = next(t for g in [game,video,poster] for t in g['original_targets_with_feedback'] if t['original_target_id'] == target)
        p = Path(t['original_code_file']['path']); code = p.read_bytes().decode('utf-8')
        ls = code.splitlines(keepends=True); lo, hi = lines
        start = sum(map(len,ls[:lo-1])); end = sum(map(len,ls[:hi]))
        fragment = code[start:end]
        spans.append({'original_target_id': target, 'original_code': pin(p), 'coordinate_system':'zero_based_unicode_char_in_original_code_half_open',
                      'start':start,'end':end,'lines_1based_inclusive':[lo,hi], 'span_sha256_utf8':digest(fragment.encode()),
                      'loss_multiplier':0, 'reason':reason, 'kind':kind})
    add('3eae9267e8fa6dd367e217e2',(1,37),'Whole initial harness fails before browser launch; repaired later versions do not make this original write positive.')
    add('874f734c5198497a8a3cda31',(133,140),'Original single-coordinate spawn skips start-area ground gap; actual edit31 and finite old/new [0,1] show local counterexample.')
    add('874f734c5198497a8a3cda31',(125,125),'lives starts at3; decrement then <0 permits play at0 and terminates on fourth loss. No explicit reserve-life contract or termination QA establishes intended correctness.','UNRESOLVED_LIFE_CONTRACT_NOT_CLAIMED_REPRODUCED_FAILURE')
    add('dfae97ac14b1178cab99a232',(36,40),'pan/pan2 construct x/y in z, then append cx with duplicate x/y; center-in test and original successful encode do not establish intended camera pan.')
    add('dfae97ac14b1178cab99a232',(50,50),'Original overlay result unlabeled while [vbase] consumed again; actual vbase error and original edit65.')
    add('dfae97ac14b1178cab99a232',(69,69),'Second consumer of [vbase] without split; original edit65 removes it; synthetic matched probe fails before and passes after.')
    add('8ca599bed99ea8dea4a3b05e',(9,9),'Emoji end card has original historical tofu feedback; edit83 uses font-independent SVG.')
    add('8ca599bed99ea8dea4a3b05e',(23,23),'Viewport500 is shorter than intended clip520; real local QA PNG500, newly authored viewport resize produces520. Mask this in original and recorded post83 unchanged body.')
    add('31a48213070396936f8a9452',(174,187),'Decorative QR-looking SVG contains no encoded application destination. No URL is supplied; final original answer calls it a placeholder. Cannot supervise it as functional application QR.')
    add('31a48213070396936f8a9452',(173,173),'User names target campuses, not verified dedicated campus sessions. Withhold unsupported specific-session phrasing unless provenance is added. Other JD-supported facts are not rejected wholesale.','UNVERIFIED_EVENT_ASSERTION')
    save('MANDATORY_LOSS0_SPANS.json', {'status':'NEGATIVE_EXCLUSIONS_ONLY_NOT_POSITIVE_COMPLEMENT_ADMISSION','spans':spans,
          'original_text_preserved':True,'source_scope_independently_required':True,'new_labels_or_training_arrays_emitted':False})
    save('VERSION_TEXT_AND_BYTE_CHECKS.json', {'status':'PASS_EXACT_TEXT_WITH_CRLF_DERIVATIVE_DISCLOSURE','versions':versions,'checks':checks,
          'captured_programs_executed_by_this_reviewer':False,'new_model_calls':0,'training_started':False})
    reviewed = [SRC/'PROGRAM_VERSION_RECOVERY.json',SRC/'qa/workspace/qa_outputs/RESULT.json',
                SRC/'overlay_viewport_repair/REPAIR_EVIDENCE.json',ROOT/'research/data_prep/wrd_gap08/resource_qa.py',
                ROOT/'research/data_prep/wrd_gap08/overlay_viewport_repair.py',SRC/'qa/EXECUTION_RECEIPT.json',
                SRC/'overlay_viewport_repair/EXECUTION_RECEIPT.json',SRC/'overlay_viewport_repair/workspace/RESULT.json']
    save('PEER.json', {
      'status':'PASS_SCOPED_SEMANTIC_CREDIT_WITH_EXPLICIT_EXCLUSIONS_AND_BYTE_DISCLOSURE',
      'reviewer':'independent child /root/remotion_batch24', 'reviewed_files':[pin(p) for p in reviewed],
      'independent_checks':checks,
      'per_repair_credit':[
        {'episode':'ep_4aadd96d99f2c07543c7','index':17,'credit':'ORIGINAL_LOCAL_HARNESS_CORRECTION','scope':'Remove actual duplicate declaration; corrected harness runs. Pixel average/no errors alone does not prove game success.','original_R':'No recovered hidden reasoning field; do not fabricate.'},
        {'episode':'ep_4aadd96d99f2c07543c7','index':31,'credit':'ORIGINAL_LOCAL_SPAWN_REPAIR','scope':'Native successful edit plus state retest and finite fixture establish gap spawning repair; not whole gameplay, all terrain, life rule, full skill or independent Q.','original_R':'Observable original commentary exists; it is not hidden CoT.'},
        {'episode':'ep_4d412dca2c57480536e7','index':65,'credit':'ORIGINAL_LOCAL_FILTER_REPAIR','scope':'Bind failing vbase output and exact call/ACK to subsequent successful encode. Current synthetic in+title probe is a new local test, not original media replay; pan remains unproven.','original_R':'No recovered hidden reasoning; action itself retained.'},
        {'episode':'ep_4d412dca2c57480536e7','index':83,'credit':'ORIGINAL_LOCAL_SVG_REPLACEMENT','scope':'Original same terminal-frame time80.5 feedback changes tofu to visible bow graphic after real recomposition; visual helper is a recorded fallible observation, not independent Q.','original_R':'Original visible commentary retained, not inferred internal reasoning.'},
        {'episode':'ep_4d412dca2c57480536e7','index':None,'credit':'NEW_AUTHORED_FINITE_VIEWPORT_REPAIR','scope':'500 -> 520 actual output and exact same renderer plus one resize insertion. New author and new local QA; neither historical Teacher nor native Agent dispatch.','new_R':'Only explicitly new authored explanation, no reconstructed original reasoning.'}],
      'findings':[
        {'id':'F1','priority':'P2','status':'REQUIRES_DISCLOSURE_OR_CANONICAL_PIN_BEFORE_BYTE_EXACT_CLAIM','path':'research/data_prep/wrd_gap08/resource_qa.py','lines':[72,73],
         'finding':'Windows write_text converts LF to CRLF. Current version-file SHA pins tested derivatives, not historical output bytes. The LF-normalized transformations are exact. Game after31 LF14136 bytes matches historical ls14136, while QA CRLF14507 bytes differs.',
         'action':'Keep existing artifacts; add explicit canonical UTF8-LF pins and derivative status. Do not silently rename/rewrite history. Canonical pins are supplied in VERSION_TEXT_AND_BYTE_CHECKS.json.'},
        {'id':'F2','priority':'P2','status':'MANDATORY_NEGATIVE_MASKS_SPECIFIED','finding':'Initial harness, original spawn, life boundary, original FFmpeg graph, pan branch, viewport500, decorative QR and unverified campus-session claim cannot receive blanket positive loss.',
         'action':'Use MANDATORY_LOSS0_SPANS.json; these are exclusions only. Independently justify each admitted positive complement span.'},
        {'id':'F3','priority':'P2','status':'RETAIN_ORIGINAL_AS_HISTORY_MASK_UNSUPPORTED_FINAL_CLAIM','finding':'Poster original final says A3 2480x3508px 300dpi. Those pixels are A4 at300dpi or A3 at about212dpi; ratio alone supports A3 proportion, not A3 physical300dpi. Actual PNG DPI metadata was not established by this harness.',
         'action':'Mask the original A3-300dpi completion claim in any final-summary target; no need to reject supported salary/location/JD extraction or A-series aspect-ratio layout.'},
        {'id':'F4','priority':'P2','status':'SCOPE_BOUNDARY_REQUIRED','finding':'NEW_NATIVE_EDIT_ARGUMENTS is schema-shaped new curation output; no native OpenClaw edit dispatch/ACK occurred. Current receipts correctly say false.',
         'action':'Keep new authorship; if turned into SFT response use new authored action proposal/current evidence, not original native repair. Retest belongs only to future metadata when supervising the proposal.'}],
      'training_boundaries':{
        'main_manifest_modified':False,'training_started':False,'new_Teacher_or_Agent_calls':0,
        'admissions_performed_by_reviewer':0,'full_autonomous_A_to_D_demonstrations_proven':0,'qualified_KEEP_proven':0,
        'source_protection_226_H_static':'Unchanged; finite correctness never overrides source contamination.',
        'prompt_causality':'Action input ends before action; subsequent ACK/retest/Q only label metadata. Viewport new case may see actual first failed local QA, never corrected retest beforehand.',
        'original_system':'Capture incomplete; reconstructed native coding schema is not original captured system/schema. Any approved wrapper must disclose this and avoid equivalence claims.',
        'authors':'Original tool arguments and visible commentary stay original; any rationale added by current curator is new silver, never original hidden R.',
        'quality':'Finite code checks support bounded functional or repair credit; no automatic whole resource, business fact truth beyond supplied JD, skill usefulness, cost advantage or autonomous scheduling conclusion.'},
      'supplementary_artifacts':[pin(OUT/'MANDATORY_LOSS0_SPANS.json'),pin(OUT/'VERSION_TEXT_AND_BYTE_CHECKS.json')]
    })
    print(json.dumps({'status':'PEER_COMPLETE','checks':len(checks),'negative_spans':len(spans),'peer':pin(OUT/'PEER.json')},ensure_ascii=False))


if __name__ == '__main__': main()
