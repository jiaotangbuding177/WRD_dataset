"""Compile a declared new functional state with verbatim reviewed old R.

This is not an original-input replay and not an Agent/model/training run.
The exact full old response stays intact; only nine reviewed R ranges get loss.
"""
from array import array
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

os.environ['USE_TORCH'] = '0'
os.environ['USE_TF'] = '0'
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
REVIEW = OUT / 'brev_reasoning_review_01/semantic_revision_02/REVIEW.json'
FEAS = OUT / 'brev_reasoning_review_01/recontext_feasibility_01'
DEST = OUT / 'recontext_original_R_01'
CALL = '0017_31464f4b0ae54464bfe76c8e05a6e95b'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def binary(name, code, values):
    data = array(code, values)
    if sys.byteorder != 'little':
        data.byteswap()
    path = DEST / name
    path.write_bytes(data.tobytes())
    return {'path': name, 'bytes': path.stat().st_size, 'sha256': digest(path)}


def main():
    DEST.mkdir(exist_ok=False)
    review = load(REVIEW)
    raw_path = Path(review['raw_path'])
    assert digest(raw_path) == review['raw_sha256']
    with gzip.open(raw_path, 'rt', encoding='utf-8') as handle:
        row = next(json.loads(line) for line in handle if json.loads(line)['call_id'] == CALL)
    assert digest(row['request']) == row['request_sha256']
    assert digest(row['response']) == row['response_sha256']
    original_R = row['message']['reasoning_content']
    assert len(original_R) == 29708 and len(row['native_tools']) == 53
    selected = [r for r in review['ranges'] if r['call_id'] == CALL and r['mask'] == 1]
    assert len(selected) == 9 and sum(r['end'] - r['start'] for r in selected) == 3278
    for item in selected:
        text = original_R[item['start']:item['end']]
        assert text == item['text'] and hashlib.sha256(text.encode()).hexdigest() == item['text_sha256']

    original_state = load(FEAS / 'NEW_STATE_FUNCTIONAL_INPUT.json')
    state = deepcopy(original_state)
    removed = '新纠错不是旧正式评测gold。'
    assert state['goal'].count(removed) == 1
    state['goal'] = state['goal'].replace(removed, '')
    log_view = state['resource_views'][13]
    assert log_view['view'] == 'EXPLICIT_NEW_DETERMINISTIC_BASELINE_LOG_PROJECTION_NOT_ORIGINAL_TOOL_TEXT'
    log_view['view'] = 'summary_of_the_previously_delivered_original_baseline_log'
    user = json.dumps(state, ensure_ascii=False, separators=(',', ':'))
    assert CALL not in user and '86336921615cb2d15ae7c7c531fa81a457ea201e353223e79de4900445b59f58' not in user
    system = [deepcopy(m) for m in row['native_messages'] if m['role'] == 'system']
    assert len(system) == 1
    messages = system + [{'role': 'user', 'content': user}, deepcopy(row['message'])]
    for message in messages:
        if message['role'] == 'assistant':
            message.setdefault('reasoning_content', '')
    assert messages[-1]['reasoning_content'] == original_R
    save(DEST / 'FUNCTIONAL_INPUT.json', state)

    shared = module(ROOT / 'research/data_prep/wrd_reasoning_v4/compile_native.py', 'stateR_shared_compiler')
    masking = module(ROOT / 'research/data_prep/wrd_main_v10/compile_main.py', 'stateR_masking')
    compiler = shared.CausalCompiler(ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets')
    canonical = 'native_B_revision_report_01_' + CALL
    identity = 'new_real_state_original_R_' + CALL
    owned = {2: {'id': canonical + ':m2', 'mechanical_usable': True,
                 'supervision_tier': 'new_real_state_original_R_candidate'}}
    result = compiler.compile_messages(messages, row['native_tools'], owned, independent=True)
    field_ranges = [{'message_index': 2, 'field': 'reasoning_content',
                     'start': r['start'], 'end': r['end'], 'text_sha256': r['text_sha256']}
                    for r in selected]
    masking.select_reviewed_spans(compiler, messages, row['native_tools'], result, [], field_ranges)
    assert 32768 < result['total_tokens'] <= 65536
    assert set(result['supervised_tokens_by_component']) == {'R'} and result['supervised_tokens'] > 0
    result['supervision_spans'] = [[a, b, cl, w * 0.25] for a, b, cl, w in result['supervision_spans']]
    for target in result['targets']:
        target['owned_supervision_spans'] = [[a, b, cl, w * 0.25]
                                             for a, b, cl, w in target['owned_supervision_spans']]
    result['supervision_spans_sha256'] = hashlib.sha256(masking.js(result['supervision_spans']).encode()).hexdigest()
    labels = [-100] * result['total_tokens']
    weights = [0.0] * result['total_tokens']
    for start, end, component, weight in result['supervision_spans']:
        assert component == 'R' and weight == 0.25
        labels[start:end] = result['input_ids'][start:end]
        weights[start:end] = [weight] * (end - start)

    # Fresh independent tokenizer offsets; do not reuse the masking helper's set.
    kwargs = dict(compiler.tokenizers['primary_14b'].special_tokens_map)
    kwargs['enable_thinking'] = False
    rendered = compiler.plain_compiled.render(messages=messages, tools=row['native_tools'],
                                             documents=None, add_generation_prompt=False, **kwargs)
    encoded = compiler.tokenizers['control_8b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
    assert encoded['input_ids'] == result['input_ids']
    base = result['targets'][0]['rendered_assistant_span'][0] + len('<|im_start|>assistant\n<think>\n')
    assert rendered[base:base + len(original_R)] == original_R
    expected = {i for i, (lo, hi) in enumerate(encoded['offset_mapping'])
                if any(base + r['start'] <= lo < hi <= base + r['end'] for r in selected)}
    observed = {i for i, value in enumerate(labels) if value != -100}
    assert expected == observed and len(expected) == result['supervised_tokens']
    assert all(weights[i] == 0.0 for i in set(range(len(weights))) - expected)
    record = {**result, 'id': identity, 'schema_version': 'wrd-real-state-original-reasoning-v1',
              'messages': messages, 'tools': row['native_tools'], 'bank': 'recontextualized_original_R',
              'stage': 'B_revision_diagnostic_plan', 'split': 'train', 'source_ids': review['source_ids'],
              'source_group_id': 'v10_native_group_a6a1c69fa6400f282a9a',
              'canonical_original_response_owner': canonical,
              'original_request_sha256': row['request_sha256'], 'original_response_sha256': row['response_sha256'],
              'target_original_R_utf8_sha256': hashlib.sha256(original_R.encode()).hexdigest(),
              'input_author': 'NEW_AI_AUTHORED_FUNCTIONAL_STATE', 'target_R_author': 'ORIGINAL_NATIVE_TEACHER',
              'is_original_native_input_equivalent': False, 'Teacher_generated_under_this_input': False,
              'all_original_R_unchanged': True, 'no_approved_A_or_content': True,
              'same_original_owner_views_mutually_exclusive': True, 'full_response_preserved_no_truncation': True,
              'root_main_admission': False, 'training_started': False, 'new_native_model_calls': 0}
    data = DEST / 'candidate.jsonl.gz'
    with gzip.open(data, 'wt', encoding='utf-8', newline='\n') as handle:
        handle.write(masking.js(record) + '\n')
    arrays = [binary('input_ids.u32le.bin', 'I', result['input_ids']),
              binary('labels.i64le.bin', 'q', labels), binary('weights.f32le.bin', 'f', weights)]
    source_files = [REVIEW, raw_path, FEAS / 'NEW_STATE_FUNCTIONAL_INPUT.json',
                    FEAS / 'FACT_PREMISE_MAP_V2.json', FEAS / 'DELIVERY_AND_PROJECTION_MAP.json',
                    FEAS / 'FULL_OLD_RESOURCE_PINS.json', Path(row['request']), Path(row['response'])]
    report = {'schema': 'wrd-real-state-original-R-candidate-actual-compilation-v1',
              'status': 'ACTUAL_ARRAYS_DUAL_TOKEN_QA_PASS_PENDING_ROOT_ADMISSION',
              'design_revision': '5.0.41', 'change_id': 'ALG-20261027-05',
              'sequences': 1, 'input_tokens': result['total_tokens'],
              'original_R_supervised_tokens': result['supervised_tokens'], 'new_original_R_owners': 0,
              'reviewed_R_ranges': selected, 'all_original_R_characters_preserved': len(original_R),
              'input_projection_deltas_from_feasibility': [
                  'Removed one curation-gold clause from goal; functional permissions and requirements unchanged.',
                  'Replaced the audit-style old-log representation flag with a plain summary label; log data unchanged.'],
              'source_files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in source_files],
              'actual_data': {'path': data.name, 'bytes': data.stat().st_size, 'sha256': digest(data)},
              'arrays': arrays, 'direct_independent_control_tokenizer_all_tokens_and_weights': 'PASS',
              'original_response_and_full_R_verbatim': True, 'no_future_response_added_to_input': True,
              'conditional_64k_profile_not_in_ACTIVE': True,
              'requires_source_semantic_and_owner_root_admission': True,
              'model_weights_loaded': False, 'training_started': False, 'new_native_model_calls': 0,
              'curation_compute_cost': 'UNKNOWN_NOT_ZERO', 'script_sha256': digest(Path(__file__))}
    save(DEST / 'COMPILATION_REPORT.json', report)
    save(DEST / 'CAUSAL_TEMPLATE.json', {'template': compiler.template, **compiler.proof})
    print(json.dumps({k: report[k] for k in ('status', 'sequences', 'input_tokens', 'original_R_supervised_tokens')}))


if __name__ == '__main__':
    main()
