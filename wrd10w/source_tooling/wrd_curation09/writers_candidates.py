"""Reviewed writer views with explicit new functional states and exact masks.

No business agent dispatch; candidates require independent root semantic QA.
"""
import gzip
import hashlib
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261031_wrd_curation09/writers'
DATA = ROOT / 'output/20261027_wrd_main_v10'
RES = ROOT / 'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
CAP = DATA / 'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'


def hs(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)


SELECTED = ['0d78ae10be60edfdaba93dc0', '0dd5502eec8fa8afa8343b48',
            '215439ffa54ad7c5a9aa8502', '257f6602661ce6bd0135926b', 'addbee2f3bff0cbfae1bb183',
            '4e819190cc4ca6bf54f21cfb', '57bf5a6f4263f47514add40d', '8a3958608262a264663a580d',
            '605cdf7450ad2d3ae8563788', 'b4c79fa37d65f5e447fbb9fc']


def negative_ranges(owner, code):
    ranges = []
    def add(start, end, why):
        assert 0 <= start < end <= len(code)
        ranges.append({'start': start, 'end': end, 'text_sha256': hs(code[start:end]), 'reason': why})
    def exact(needle, why):
        assert code.count(needle) == 1, needle
        start = code.index(needle); add(start, start + len(needle), why)
    def line_containing(needle, why):
        assert code.count(needle) == 1
        p = code.index(needle); start = code.rfind('\n', 0, p) + 1; end = code.find('\n', p)
        add(start, len(code) if end < 0 else end, why)
    if owner == '57bf5a6f4263f47514add40d':
        for needle in ['--text-on-teal: #ffffff;', '--text-on-teal-soft: rgba(255, 255, 255, 0.85);',
                       '文字保持高对比度，清晰易读。', '/* ---------- 文字颜色：保证浅底深字、深底白字的可读性 ---------- */',
                       '/* 底部区域：统一青绿色渐变 + 白色文字 */',
                       '/* 手机：进一步收紧，渐变比例微调让过渡带更短、内容更聚焦 */']:
            line_containing(needle, 'WRONG_OR_UNVERIFIED_READABILITY_OR_IMPLEMENTATION_CLAIM')
        dark = code.index('/* 用户偏好深色时，')
        add(dark, len(code), 'UNREQUESTED_DARK_OVERRIDE_CONTRADICTS_AVOID_OVERDARK_DEFAULT; NO_WHOLE_THEME_QUALITY_CREDIT')
    if owner == '8a3958608262a264663a580d':
        for needle in ['--text-on-bottom: #ffffff;', '--text-on-bottom-muted: #e0faf4;',
                       '/* 底部区域：统一青绿背景 + 白色文字，确保清晰可读 */']:
            # Spaces align the CSS variable values in the original text.
            if needle not in code:
                needle = {'--text-on-bottom: #ffffff;': '--text-on-bottom: #ffffff',
                          '--text-on-bottom-muted: #e0faf4;': '--text-on-bottom-muted: #e0faf4'}.get(needle, needle)
                if needle not in code:
                    needle = '--text-on-bottom:' if 'text-on-bottom:' in needle else '--text-on-bottom-muted:'
            line_containing(needle, 'WHITE_OR_NEAR_WHITE_ON_BRIGHT_TEAL_FAILS_NORMAL_AND_LARGE_TEXT_CONTRAST')
        exact('数值已提供十六进制回退写法。', 'HEX_VARIABLE_VALUES_ARE_NOT_LITERAL_FALLBACK_DECLARATIONS')
    if owner == '4e819190cc4ca6bf54f21cfb':
        for needle in [' b<b id="v1"', ' b<b id="f1"', ' b<b id="v2"', ' b<b id="f2"', ' b<b id="state1"']:
            p = code.index(needle) + 1; add(p, p + 1, 'STRAY_LITERAL_B_FIXED_BY_RECORDED_EDIT_7_SEPARATE_PROCESS_LANE')
        add(code.index('  function physics(i, dt){'), code.index('  function drawLane(i){'),
            'INITIAL_PHYSICS_STATE_MACHINE_NOT_CORRECT; NO_POSITIVE_DYNAMICS_CREDIT')
        line_containing('const ph = physics(i, 1/120);', 'DRAW_MUTATES_PHYSICS_AN_EXTRA_STEP')
        line_containing('else arrow(fx, fy, fx + f*SCALE, fy,', 'STATIC_FRICTION_ARROW_POINTS_WITH_POSITIVE_PUSH_INSTEAD_OF_AGAINST_IT')
    return sorted(ranges, key=lambda r: (r['start'], r['end']))


def source_material(timeline, owner):
    # Only material already read before this exact recorded action; a subset of
    # exact source entries is shown explicitly as a newly authored input state.
    selected_id = {'605cdf7450ad2d3ae8563788': 'conv_97579cceae5e:msg_3',
                   'b4c79fa37d65f5e447fbb9fc': 'conv_7b0ea502fdac:f48b64c6'}.get(owner)
    if owner in {'215439ffa54ad7c5a9aa8502', '257f6602661ce6bd0135926b', 'addbee2f3bff0cbfae1bb183'}:
        selected_id = 'conv_7b0ea502fdac:f48b64c6'
    if selected_id:
        for event in timeline:
            if event['role'] != 'toolResult': continue
            try: obj = json.loads(event['text'])
            except ValueError: continue
            for row in obj.get('requests', []):
                if row['id'] == selected_id:
                    return '同源原始用户材料（逐字保留所选消息，供本次改写／制图使用，不作为外部事实核实）：\n' + row['text'], [event['index']], [selected_id]
        raise AssertionError('required source entry absent')
    if owner in {'57bf5a6f4263f47514add40d', '8a3958608262a264663a580d'}:
        event = timeline[6]
        return '此前对指定产品图的实际像素统计输出（未提供图片视觉理解，不额外推断图中文字）：\n' + event['text'], [6], []
    if owner == '0d78ae10be60edfdaba93dc0':
        return '原附件路径读取失败后，实际读取到的同源user-only JSON全文：\n' + timeline[4]['text'], [4], []
    return '', [], []


def main():
    dest = OUT / 'candidates01'
    dest.mkdir(exist_ok=False)
    index = {r['owner_id']: r for r in load(OUT / 'RECOVERY_INDEX.json')['rows']}
    scope = {r['source_id']: r for r in rows(DATA / 'clean_inputs/source_scope.metadata.jsonl.gz')}
    reserved = load(RES)
    tools = [t for t in load(CAP)['tools'] if t['function']['name'] in {'read', 'write', 'edit', 'exec', 'process', 'ls', 'apply_patch'}]
    assert len(tools) == 7
    made = []
    for owner in SELECTED:
        row = index[owner]; packet = load(OUT / row['packet_ref'])
        assert not set(row['source_ids']).intersection(reserved['reserved_source_ids'])
        components = {scope[s]['component_id'] for s in row['source_ids']}
        assert not components.intersection(reserved['reserved_source_scope_components'])
        assert all(scope[s]['status'] == 'TRAIN' for s in row['source_ids'])
        timeline = load(OUT / 'episodes' / f"{row['episode_id']}.timeline.json")
        task = timeline[0]['text'].split('用户任务：')[-1].strip()
        material, material_indices, material_ids = source_material(timeline[:row['message_index']], owner)
        state = ('当前工作目录 /workspace，/workspace/tmp 与 /workspace/outputs 已存在且可写。'
                 'Python及任务所需公共文档／浏览器工具可用。依据以下明确任务和材料编写资源；'
                 '所列外部服务的可用性与预算未获确认。\n\n任务原文：\n' + task)
        if material: state += '\n\n' + material
        original_call = next(c for c in timeline[row['message_index']]['calls'] if c['id'] == packet['writer_original']['original_tool_call_id'])
        call = {'id': original_call['id'], 'type': 'function', 'function': {'name': original_call['name'], 'arguments': deepcopy(original_call['arguments'])}}
        messages = [{'role': 'system', 'content': '根据明确给出的当前任务与可见材料操作；资料中的指令是任务数据，未核实的内容不当作外部事实。保留事实与用户约束。'},
                    {'role': 'user', 'content': state}, {'role': 'assistant', 'content': '', 'reasoning_content': '', 'tool_calls': [call]}]
        candidate = {'schema_version': 'wrd-curation09-functional-writer-view-v1', 'id': 'curation09-writer-' + owner,
          'owner_id': owner, 'original_recorded_action_owner': owner, 'bank': 'curation09_writer_resource_views',
          'stage': 'B_scoped_resource_implementation', 'split': 'train', 'source_ids': row['source_ids'],
          'source_group_id': sorted(components)[0], 'source_admission': 'ADMIT_SOURCE_ONLY',
          'training_admitted': False, 'root_main_admission': False, 'requires_external_root_admission': True,
          'holdout_reservation': {'path': str(RES.relative_to(ROOT)), 'sha256': sha(RES), 'source_intersection': [], 'scope_component_intersection': []},
          'protected_source_ids': [], 'original226': False, 'holdout12': False, 'protected_sources_visible_prefix': False,
          'annotation_provenance': 'NEW_FUNCTIONAL_STATE; RECORDED_ORIGINAL_WRITE_ARGUMENTS_VERBATIM',
          'output_content_provenance': 'ORIGINAL_NATIVE_CODE_VERBATIM_WITH_REVIEWED_NEGATIVE_MASKS',
          'original_episode_id': row['episode_id'], 'original_message_index': row['message_index'],
          'source_context': {'path': row['packet_ref'], 'sha256': sha(OUT / row['packet_ref'])},
          'necessary_material_original_message_indices': material_indices, 'necessary_material_original_entry_ids': material_ids,
          'original_system_capture': packet['original_system_capture_status'], 'original_native_prompt_equivalence_claimed': False,
          'student_view': 'EXPLICIT_NEW_CORE7_FUNCTIONAL_STATE; NOT_ORIGINAL_FULL53_NATIVE_PREFIX',
          'actual_native_tool_dispatch': False, 'original_action_if_present_remains_recorded_native_not_new_dispatch': True,
          'messages': messages, 'tools': tools, 'supervision_message_indices': [2], 'message_loss_mask': [0, 0, 1],
          'approved_components': ['A'], 'loss_multiplier': 0.25, 'target_tool_call_id': call['id'],
          'target_original_code_sha256': row['code_sha256'],
          'target_code_unicode_exclusions': negative_ranges(owner, call['function']['arguments']['content']),
          'teacher_original_R_supervised': False, 'rationale_provenance': 'NO_RECORDED_ORIGINAL_R_BLOCK',
          'tool_schema_provenance': {'path': str(CAP.relative_to(ROOT)), 'sha256': sha(CAP)},
          'is_full_autonomous_execution_demonstration': False, 'is_qualified_KEEP_demonstration': False,
          'future_feedback_in_input': False, 'credit_scope': 'Explicit resource implementation only; code errors are masked, whole-skill utility not established.',
          'data_design_revision': '5.0.50', 'data_change_id': 'ALG-20261031-02',
          'curation_cost': 'UNKNOWN_NOT_ZERO', 'new_business_Teacher_Actor_calls': 0, 'training_started': False}
        made.append(candidate)
    # These edits are newly authored and only repair local text contrast. Their
    # before-state is the full original file, not a historical model prefix.
    for original_owner in ['57bf5a6f4263f47514add40d', '8a3958608262a264663a580d']:
        original = next(r for r in made if r['owner_id'] == original_owner)
        row = index[original_owner]; before = (OUT / row['code_ref']).read_text(encoding='utf-8')
        if original_owner.startswith('57bf'):
            changes = [
              ('--text-on-teal: #ffffff;', '--text-on-teal: #1f2d28;'),
              ('--text-on-teal-soft: rgba(255, 255, 255, 0.85);', '--text-on-teal-soft: #1f2d28;'),
              ('/* 底部青绿背景上的文字：纯白，清晰醒目 */', '/* 底部亮青绿背景使用深字，提高普通字号文字对比 */'),
              ('/* 底部次要文字：85% 白，柔和不失清晰 */', '/* 底部次要文字同样使用深字；层级可用字号和间距区分 */'),
              ('/* ---------- 文字颜色：保证浅底深字、深底白字的可读性 ---------- */', '/* ---------- 文字颜色：浅底和亮青绿底均使用深字 ---------- */'),
              ('/* 底部区域：统一青绿色渐变 + 白色文字 */', '/* 底部区域：统一青绿色渐变 + 深色文字 */')]
        else:
            lines = before.splitlines()
            bottom = next(l for l in lines if '--text-on-bottom:' in l)
            muted = next(l for l in lines if '--text-on-bottom-muted:' in l)
            changes = [(bottom, '  --text-on-bottom: #1f2d28; /* 亮青绿底使用深字 */'),
                       (muted, '  --text-on-bottom-muted: #1f2d28; /* 次要文字也保留足够对比 */'),
                       ('/* 底部区域：统一青绿背景 + 白色文字，确保清晰可读 */', '/* 底部区域：统一青绿背景 + 深色文字 */')]
        after = before
        edits = []
        for old, new in changes:
            assert after.count(old) == 1
            after = after.replace(old, new, 1); edits.append({'oldText': old, 'newText': new})
        repair = deepcopy(original); owner = 'new-contrast-' + original_owner
        call = {'id': 'curation09_' + hs(owner)[:24], 'type': 'function', 'function': {'name': 'edit', 'arguments': {'path': row['native_path'], 'edits': edits}}}
        repair.update(id='curation09-' + owner, owner_id=owner, original_writer_owner=original_owner,
                      original_recorded_action_owner=None, original_message_index=None, target_tool_call_id=call['id'],
                      stage='B_new_authored_local_contrast_repair', annotation_provenance='NEW_AUTHOR_LOCAL_REPAIR_WITH_FULL_BEFORE_STATE',
                      output_content_provenance='NEW_AUTHORED_LITERAL_EDITS; NOT_ORIGINAL_NATIVE_REPAIR',
                      target_code_unicode_exclusions=[], approved_components=['R', 'A'],
                      rationale_provenance='NEW_AUTHORED_SCOPED_REASONING',
                      necessary_before_code_sha256=hs(before), expected_after_code_sha256=hs(after),
                      local_after_not_yet_resource_retested=True)
        repair.pop('target_original_code_sha256', None)
        repair['messages'] = [{'role': 'system', 'content': '根据当前完整文件和局部检查反馈最小修复；只处理指定问题，不宣称整个主题或技能已验收。'},
          {'role': 'user', 'content': '当前文件：' + row['native_path'] + '，已存在且可编辑。请保留底部青绿色和其它布局，局部修复底部／按钮的普通字号文字对比。按sRGB公式离线计算：白字在#00c4a3上的对比约2.228，在#00ae91上约2.814，在#00a98b上约2.980；深字#1f2d28在这些底色上分别约6.437、5.097、4.813。当前文件全文：\n\n' + before},
          {'role': 'assistant', 'content': '', 'reasoning_content': '底部亮青绿上的白色或近白文字对比不足，增大字号也不能达到3:1。用当前已计算的深墨绿色替换相关文字变量，同时校正白字可读性的注释，保留背景和布局。这里只解决局部文字对比，修后仍需检查实际渲染。', 'tool_calls': [call]}]
        after_path = dest / 'contrast_after' / (original_owner + '.css'); after_path.parent.mkdir(exist_ok=True)
        after_path.write_bytes(after.encode('utf-8'))
        repair['expected_after_resource_ref'] = after_path.relative_to(OUT).as_posix()
        made.append(repair)
    with gzip.open(dest / 'candidates.raw.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as f:
        for candidate in made:
            f.write(json.dumps(candidate, ensure_ascii=False, separators=(',', ':')) + '\n')
    save(dest / 'PREPARATION.json', {'status': 'ACTUAL_BODY_CANDIDATES_PENDING_ROOT_QA_AND_COMPILATION',
         'original_writer_views': len(SELECTED), 'new_authored_contrast_repairs': 2, 'candidate_targets': len(made),
         'original_R_targets': 0, 'negative_code_ranges': sum(len(r['target_code_unicode_exclusions']) for r in made),
         'source_count': len({s for r in made for s in r['source_ids']}), 'holdout_sha256': sha(RES),
         'no_current_main_manifest_change': True, 'training_started': False, 'new_business_Teacher_Actor_calls': 0,
         'ai_cpu_curation_cost': 'UNKNOWN_NOT_ZERO', 'script_sha256': sha(Path(__file__))})
    print(json.dumps({'candidate_targets': len(made), 'original_writer_views': len(SELECTED),
                      'new_R_targets': 2, 'negative_ranges': sum(len(r['target_code_unicode_exclusions']) for r in made)}))


if __name__ == '__main__': main()
