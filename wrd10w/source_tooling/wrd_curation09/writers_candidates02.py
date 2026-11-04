"""Append reviewed lesson writer and explicit new local repairs; preserve 01."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261031_wrd_curation09/writers'

def hs(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    dest = OUT / 'candidates02'; dest.mkdir(exist_ok=False)
    with gzip.open(OUT / 'candidates01/candidates.raw.jsonl.gz', 'rt', encoding='utf-8') as f:
        made = [json.loads(l) for l in f if l.strip()]
    index = {r['owner_id']: r for r in load(OUT / 'RECOVERY_INDEX.json')['rows']}
    solar = next(r for r in made if r['owner_id'] == '0dd5502eec8fa8afa8343b48')
    code = solar['messages'][2]['tool_calls'][0]['function']['arguments']['content']
    needle = 'ctx.arc(CX,CY,p.orbit,0,Math.PI*2);'; assert code.count(needle) == 1
    a = code.index(needle)
    solar['target_code_unicode_exclusions'].append({'start': a, 'end': a + len(needle),
        'text_sha256': hs(needle), 'reason': 'CIRCULAR_ORBIT_PATH_DOES_NOT_MATCH_PLANET_Y_RADIUS_MULTIPLIED_BY_0_92'})
    r = deepcopy(solar); owner = 'new-solar-orbit-alignment'
    new = 'ctx.ellipse(CX,CY,p.orbit,p.orbit*0.92,0,0,Math.PI*2);'
    call = {'id': 'curation09_' + hs(owner)[:24], 'type': 'function', 'function': {'name': 'edit', 'arguments': {'path': index[solar['owner_id']]['native_path'], 'edits': [{'oldText': needle, 'newText': new}]}}}
    r.update(id='curation09-' + owner, owner_id=owner, original_writer_owner=solar['owner_id'],
        original_recorded_action_owner=None, original_message_index=None, target_tool_call_id=call['id'],
        stage='B_new_authored_orbit_geometry_repair', annotation_provenance='NEW_AUTHOR_LOCAL_REPAIR_WITH_FULL_BEFORE_STATE',
        output_content_provenance='NEW_AUTHORED_LITERAL_EDIT; NOT_ORIGINAL_NATIVE_REPAIR',
        target_code_unicode_exclusions=[], approved_components=['R', 'A'],
        rationale_provenance='NEW_AUTHORED_GEOMETRY_REASONING', necessary_before_code_sha256=hs(code),
        expected_after_code_sha256=hs(code.replace(needle, new)), local_after_not_yet_resource_retested=True)
    r.pop('target_original_code_sha256', None)
    r['messages'] = [{'role': 'system', 'content': '根据完整当前文件作最小局部修复，不把几何修正当作全页验收或完整技能KEEP。'},
      {'role': 'user', 'content': '当前文件：' + call['function']['arguments']['path'] + '，已存在且可编辑。行星y坐标乘以0.92，但显示轨道用完整圆。请使轨道和行星实际路径相符，保留其余交互与教学内容。完整文件：\n\n' + code},
      {'role': 'assistant', 'content': '', 'reasoning_content': '行星横向半径是orbit，纵向半径是orbit乘0.92，路径因此为椭圆。轨道线仍画同半径圆会偏离路径。将这一次轨道绘制换成纵半径同样乘0.92的ellipse，不改行星位置或其它圆形图案。', 'tool_calls': [call]}]
    p = dest / 'solar_after.html'; p.write_bytes(code.replace(needle, new).encode('utf-8')); r['expected_after_resource_ref'] = p.relative_to(OUT).as_posix()
    made.append(r)
    # A complete user-authorized lesson-design resource. Unsupported student
    # profile, exact textbook mapping and numeric speaking-share are masked.
    owner = '7a6d2f63d0c34910127bb0d4'; row = index[owner]; packet = load(OUT / row['packet_ref'])
    timeline = load(OUT / 'episodes' / f"{row['episode_id']}.timeline.json")
    code = (OUT / row['code_ref']).read_text(encoding='utf-8')
    original_call = next(c for c in timeline[row['message_index']]['calls'] if c['id'] == packet['writer_original']['original_tool_call_id'])
    r = deepcopy(next(x for x in made if x['owner_id'] == '0d78ae10be60edfdaba93dc0'))
    r.update(id='curation09-writer-' + owner, owner_id=owner, original_recorded_action_owner=owner,
             source_ids=row['source_ids'], source_group_id='v10_group_2083b27a9a21f702ab13',
             original_episode_id=row['episode_id'], original_message_index=row['message_index'],
             source_context={'path': row['packet_ref'], 'sha256': hashlib.sha256((OUT / row['packet_ref']).read_bytes()).hexdigest()},
             necessary_material_original_message_indices=[], necessary_material_original_entry_ids=[],
             target_tool_call_id=original_call['id'], target_original_code_sha256=hs(code), target_code_unicode_exclusions=[])
    for needle, why in [('para("本课选自人教版', 'SPECIFIC_TEXTBOOK_EXERCISE_ALIGNMENT_NOT_IN_SUPPLIED_MATERIAL'),
                        ('para("八年级学生已掌握', 'ACTUAL_LEARNER_PROFILE_NOT_OBSERVED'),
                        ('para("口语训练总体设计思路：', 'SEVENTY_PERCENT_SPEAKING_SHARE_NOT_ESTABLISHED_BY_TIMING')]:
        start = code.index(needle); end = code.index('\n', start)
        r['target_code_unicode_exclusions'].append({'start': start, 'end': end, 'text_sha256': hs(code[start:end]), 'reason': why})
    call = {'id': original_call['id'], 'type': 'function', 'function': {'name': 'write', 'arguments': deepcopy(original_call['arguments'])}}
    r['messages'] = [{'role': 'system', 'content': '按明确教学委托制作资源；未指定细节可以合理设计，实际学生情况和教材原页不能冒充已核验。'},
      {'role': 'user', 'content': '当前 /workspace/tmp 与 /workspace/outputs 存在且可写，Python与python-docx可用。以下为完整委托；未给出真实班级学情或教材原页：\n\n' + timeline[0]['text'].split('用户任务：')[-1].strip()},
      {'role': 'assistant', 'content': '', 'reasoning_content': '', 'tool_calls': [call]}]
    # Explicitly recheck the newly added source against the same frozen holdout.
    reservation = load(ROOT / r['holdout_reservation']['path'])
    assert not set(r['source_ids']).intersection(reservation['reserved_source_ids'])
    assert r['source_group_id'] not in reservation['reserved_source_scope_components']
    made.append(r)
    # The second original lesson writer is syntactically broken; retain it in
    # audit and provide a separately authored minimal technical repair instead.
    original_owner = '7c1737c14d72dd011faec8a6'; row = index[original_owner]
    before = (OUT / row['code_ref']).read_text(encoding='utf-8')
    changes = [
      ('bullet("4. 文化意识与情感目标：", “', 'bullet("4. 文化意识与情感目标：", "'),
      ('def para(text, size=11, bold=False, align=None, space_after=4, indent=None, color=None):', 'def para(text, size=11, bold=False, align=None, space_after=4, indent=None, color=None, en=EN_FONT):'),
      ('    r = p.add_run(text)\n    set_run(r, size=size, bold=bold, color=color)', '    r = p.add_run(text)\n    set_run(r, size=size, bold=bold, color=color, en=en)')]
    after = before
    for old, new in changes:
        assert after.count(old) == 1
        after = after.replace(old, new, 1)
    import ast
    ast.parse(after)
    r = deepcopy(r); owner = 'new-lesson-quote-and-font-parameter-repair'
    call = {'id': 'curation09_' + hs(owner)[:24], 'type': 'function', 'function': {'name': 'edit', 'arguments': {'path': row['native_path'], 'edits': [{'oldText': a, 'newText': b} for a, b in changes]}}}
    r.update(id='curation09-' + owner, owner_id=owner, original_recorded_action_owner=None,
        original_writer_owner=original_owner, original_episode_id=row['episode_id'], original_message_index=None,
        stage='B_new_authored_local_python_repair', target_tool_call_id=call['id'],
        annotation_provenance='NEW_AUTHOR_REPAIR_FROM_ORIGINAL_COMPLETE_BROKEN_PROGRAM_AND_REAL_SYNTAX_ERROR',
        output_content_provenance='NEW_AUTHORED_SCHEMA_EDIT; NOT_ORIGINAL_NATIVE_EXEC_CALL',
        target_code_unicode_exclusions=[], approved_components=['R', 'A'],
        rationale_provenance='NEW_AUTHORED_STATIC_DIAGNOSIS; NOT_ORIGINAL_R',
        necessary_before_code_sha256=hs(before), expected_after_code_sha256=hs(after),
        local_after_not_yet_resource_retested=True,
        source_context={'path': row['packet_ref'], 'sha256': hashlib.sha256((OUT / row['packet_ref']).read_bytes()).hexdigest()})
    r.pop('target_original_code_sha256', None)
    timeline = load(OUT / 'episodes' / f"{row['episode_id']}.timeline.json")
    r['messages'] = [{'role': 'system', 'content': '只处理当前Python程序的语法和调用接口问题；不把程序可运行等同教案事实和课堂成效已验证。'},
      {'role': 'user', 'content': '当前文件：' + row['native_path'] + '，已存在且可编辑。实际运行报错如下。请修复造成程序无法生成文档的语法／调用问题，保持内容与其它排版不变。\n\n实际反馈：\n' + timeline[8]['text'] + '\n\n当前完整文件：\n' + before},
      {'role': 'assistant', 'content': '', 'reasoning_content': '错误位置使用中文弯引号作为字符串起始符，需换成英文双引号。文件还用en关键字调用para，但para签名未接收该参数；同时补入参数并传给set_run，避免语法修复后又因字体参数接口不一致中断。这里仅修复运行阻断，不判断教案全部内容。', 'tool_calls': [call]}]
    p = dest / 'lesson_after.py'; p.write_bytes(after.encode('utf-8')); r['expected_after_resource_ref'] = p.relative_to(OUT).as_posix()
    made.append(r)
    assert len(made) == 15
    with gzip.open(dest / 'candidates.raw.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as f:
        for r in made:
            assert r['training_admitted'] is False
            f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    save(dest / 'PREPARATION.json', {'status': 'ACTUAL15_BODY_CANDIDATES_PENDING_INDEPENDENT_ROOT_ADMISSION',
         'original_writer_views': 11, 'new_authored_local_repairs': 4, 'original_R_targets': 0,
         'new_R_targets': 4, 'negative_code_ranges': sum(len(r['target_code_unicode_exclusions']) for r in made),
         'supersedes_for_current_compilation': 'candidates01; retained audit original unchanged',
         'new_business_Teacher_Actor_calls': 0, 'training_started': False, 'curation_cost': 'UNKNOWN_NOT_ZERO'})
    print(json.dumps({'actual_candidates': len(made), 'writer_views': 11, 'new_repairs': 4,
                      'negative_ranges': sum(len(r['target_code_unicode_exclusions']) for r in made)}))


if __name__ == '__main__': main()
