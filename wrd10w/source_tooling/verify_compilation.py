"""Independent, CPU-only checks of compiled v10 ids, loss spans and lineage.

No weights or trainer are imported.  Optional sampled re-tokenization uses the
two local tokenizer asset sets and the saved plain causal template directly,
without invoking compile_main or CausalCompiler.
"""
from __future__ import annotations
import argparse
from array import array
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
ROOT = Path(__file__).resolve().parents[3]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(data): return hashlib.sha256(data).hexdigest()
def digest(path): return sha(Path(path).read_bytes())
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def ids_digest(ids):
    data = array('I', ids)
    if sys.byteorder != 'little': data.byteswap()
    return sha(data.tobytes())


def each(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip(): yield json.loads(line)


def check(root, retokenize=True):
    root = Path(root)
    report = load(root/'COMPILATION_REPORT.json')
    errors, counts = [], Counter()
    observed, ids, group_splits, source_splits = Counter(), set(), defaultdict(set), defaultdict(set)
    banks, effective = defaultdict(Counter), defaultdict(float)
    tokenizer_proof, tokenizers, template = {}, None, None

    def fail(code, owner=None):
        counts['error_'+code] += 1
        if len(errors) < 120: errors.append({'code': code, 'record_id': owner})

    if retokenize:
        from transformers import AutoTokenizer
        from transformers.utils.chat_template_utils import _compile_jinja_template
        assets = ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
        tokenizers = {name: AutoTokenizer.from_pretrained(assets/name, local_files_only=True, trust_remote_code=False)
                      for name in ('primary_14b', 'control_8b')}
        template = _compile_jinja_template(load(root/'CAUSAL_TEMPLATE.json')['variant'])
        tokenizer_proof = {'local_tokenizers_only': True, 'weights_loaded': False, 'direct_template_render_not_compiler_reuse': True}
    listed = {row['path'] for row in report['files']}
    actual = {path.name for path in root.glob('*.jsonl.gz') if path.name != report['held_file']['path']}
    if actual != listed: fail('STALE_OR_UNLISTED_SHARD')
    for ref in [*report['files'], report['held_file']]:
        path = root/ref['path']
        if not path.is_file() or path.stat().st_size != ref['bytes'] or digest(path) != ref['sha256']:
            fail('FILE_PIN_MISMATCH', ref['path'])
    for ref in report.get('immutable_inputs', []):
        path = Path(ref['path'])
        if not path.is_file() or digest(path) != ref['sha256']: fail('INPUT_CHANGED', ref['path'])

    for ref in report['files']:
        for row in each(root/ref['path']):
            owner = row['id']; counts['records_checked'] += 1
            if owner in ids: fail('DUPLICATE_ID', owner)
            ids.add(owner)
            meta = row.get('original_record_metadata', {})
            messages = row['messages']; arr = row['input_ids']; spans = row['supervision_spans']
            split, bank = row['split'], row['bank']
            multiplier = float(meta.get('loss_multiplier', 1))
            expected_approved = meta.get('supervision_message_indices', meta.get('supervision_candidate_message_indices'))
            if expected_approved is None:
                expected_approved = [i for i, value in enumerate(meta.get('message_loss_mask', [])) if value]
            if not expected_approved or len(expected_approved) != len(set(expected_approved)) or any(type(i) is not int for i in expected_approved):
                fail('INVALID_APPROVED_INDICES', owner)
            if 'message_loss_mask' in meta:
                mask = meta['message_loss_mask']
                if len(mask) != len(messages) or any(type(v) not in (int, bool) or v not in (0, 1) for v in mask):
                    fail('INVALID_MESSAGE_LOSS_MASK', owner)
                if expected_approved != [i for i, value in enumerate(mask) if value]: fail('MASK_OWNER_DISAGREEMENT', owner)
            if meta.get('training_admitted') is not True or meta.get('source_admission') != 'ADMIT': fail('ADMISSION_FLAGS_MISSING', owner)
            if any(meta.get(k) for k in ('original226', 'holdout12', 'protected_sources_visible_prefix', 'protected_source_ids')):
                fail('PROTECTED_SOURCE', owner)
            group = row.get('source_group_id')
            if not group: fail('SOURCE_GROUP_MISSING', owner)
            else: group_splits[group].add(split)
            for source in row.get('source_ids', []): source_splits[source].add(split)
            if len(arr) != row['total_tokens'] or any(type(x) is not int or not 0 <= x < 2**32 for x in arr): fail('TOKEN_ARRAY_INVALID', owner)
            if ids_digest(arr) != row['input_ids_sha256_u32le']: fail('INPUT_IDS_HASH_MISMATCH', owner)
            if sha(canonical(spans)) != row['supervision_spans_sha256']: fail('SPAN_HASH_MISMATCH', owner)
            previous, supervised = 0, 0; components = Counter(); weighted = 0.0
            for low, high, component, weight in spans:
                if not 0 <= low < high <= len(arr) or low < previous: fail('SPAN_RANGE_OR_OVERLAP', owner)
                previous = high
                if not 0 < weight <= 1: fail('LOSS_WEIGHT_INVALID', owner)
                supervised += high-low; components[component] += high-low; weighted += (high-low)*weight
                expected_weight = multiplier*(0.2 if component == 'F' else 1.0)
                if abs(weight-expected_weight) > 1e-9: fail('COMPONENT_LOSS_WEIGHT_MISMATCH', owner)
            if supervised != row['supervised_tokens'] or dict(components) != row['supervised_tokens_by_component']: fail('SUPERVISED_TOKEN_COUNTS_MISMATCH', owner)
            owned = []
            actual_approved = []
            for target in row['targets']:
                index = target['message_index']; subspans = target['owned_supervision_spans']
                if subspans:
                    actual_approved.append(index); owned.extend(subspans)
                    if index not in expected_approved or messages[index]['role'] != 'assistant': fail('UNAPPROVED_TARGET_LOSS', owner)
                if target['supervised_tokens'] != sum(high-low for low,high,_,_ in subspans): fail('OWNER_TOKEN_COUNT_MISMATCH', owner)
            if owned != spans: fail('GLOBAL_VS_OWNER_SPANS_MISMATCH', owner)
            if set(actual_approved) != set(expected_approved): fail('APPROVED_TARGET_EMPTY_OR_MISSING', owner)
            registry = {tool.get('function', tool).get('name'): tool.get('function', tool) for tool in row.get('tools', [])}
            for index in expected_approved:
                if type(index) is not int or not 0 <= index < len(messages): continue
                for call in messages[index].get('tool_calls', []):
                    fn = call.get('function', {}); schema = registry.get(fn.get('name'))
                    if not schema or not isinstance(schema.get('parameters'), dict): fail('TARGET_TOOL_SCHEMA_MISSING', owner)
                    else:
                        try:
                            from jsonschema import Draft202012Validator
                            value = json.loads(fn['arguments']) if isinstance(fn.get('arguments'), str) else fn.get('arguments')
                            if next(Draft202012Validator(schema['parameters']).iter_errors(value), None): fail('TARGET_TOOL_ARGUMENT_SCHEMA_INVALID', owner)
                        except (ValueError, KeyError, TypeError): fail('TARGET_TOOL_ARGUMENT_PARSE_FAILED', owner)
            bucket = '16k' if len(arr) <= 16384 else '32k'
            if len(arr) > 32768: fail('GT32K_TRAINING_ROW', owner)
            if ref['path'] != f'{bank}.{split}.{bucket}.jsonl.gz': fail('SHARD_METADATA_MISMATCH', owner)
            if retokenize and (counts['records_checked'] <= 32 or counts['records_checked'] % 97 == 0 or meta.get('approved_field_ranges') or row.get('view')=='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION'):
                kwargs = dict(tokenizers['primary_14b'].special_tokens_map); kwargs['enable_thinking'] = False
                rendered = template.render(messages=messages, tools=row.get('tools') or None, documents=None, add_generation_prompt=False, **kwargs)
                primary = tokenizers['primary_14b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
                other = tokenizers['control_8b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
                if row.get('view')=='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION':
                    if primary['input_ids'][:len(arr)]!=arr or ids_digest(primary['input_ids'])!=row.get('complete_input_ids_sha256_u32le') or len(primary['input_ids'])!=row.get('complete_rendered_tokens') or sha(rendered.encode())!=row.get('complete_rendered_sha256'):
                        fail('EXACT_FUTURE_SUFFIX_PREFIX_INVALID', owner)
                    decoded=tokenizers['primary_14b'].decode(arr,skip_special_tokens=False,clean_up_tokenization_spaces=False)
                    if sha(decoded.encode())!=row['rendered_sha256'] or meta.get('allow_reviewed_completion_prefix') is not True or expected_approved!=[len(messages)-1]:fail('PREFIX_METADATA_OR_HASH_INVALID',owner)
                elif primary['input_ids'] != arr or sha(rendered.encode()) != row['rendered_sha256']:
                    fail('INDEPENDENT_RENDER_OR_TOKENS_MISMATCH', owner)
                if primary != other: fail('14B_8B_DIRECT_RETOKENIZATION_MISMATCH', owner)
                allowed = []
                reviewed=[]
                target_map={target['message_index']:target for target in row['targets']}
                for region in meta.get('approved_field_ranges',[]):
                    index,field=region['message_index'],region['field']; raw=messages[index].get(field,'') or ''
                    start,end=region['start'],region['end']
                    if not 0<=start<end<=len(raw) or sha(raw[start:end].encode())!=region['text_sha256']:fail('REVIEWED_FIELD_RANGE_IDENTITY_INVALID',owner)
                    base=target_map[index]['rendered_assistant_span'][0]+len('<|im_start|>assistant\n')+len('<think>\n')
                    if field=='content':base+=len(messages[index].get('reasoning_content',''))+len('\n</think>\n\n')
                    if rendered[base+start:base+end]!=raw[start:end]:fail('REVIEWED_FIELD_OFFSET_INVALID',owner)
                    reviewed.append((base+start,base+end))
                for target in row['targets']:
                    if target['message_index'] not in expected_approved: continue
                    a,b = target['rendered_assistant_span']; header = '<|im_start|>assistant\n'
                    if not rendered[a:b].startswith(header) or not rendered[a:b].endswith('<|im_end|>\n'): fail('ASSISTANT_RENDER_BOUNDARY_INVALID', owner)
                    allowed.append((a+len(header),b))
                for lo,hi,component,_ in spans:
                    for start,end in primary['offset_mapping'][lo:hi]:
                        if not any(a <= start < end <= b for a,b in allowed): fail('INPUT_OR_ROLE_HEADER_HAS_LOSS', owner)
                        if meta.get('approved_components') is not None or meta.get('approved_field_ranges'):
                            if component not in set(meta.get('approved_components') or []) and not any(a<=start<end<=b for a,b in reviewed):fail('UNREVIEWED_COMPONENT_OR_FIELD_TOKEN_HAS_LOSS',owner)
                counts['direct_dual_tokenizer_canaries'] += 1
            for c in (observed, banks[bank]):
                c['sequences'] += 1; c['targets'] += len(actual_approved)
                c['input_tokens'] += len(arr); c['supervised_tokens'] += supervised
                c[bucket+'_sequences'] += 1; c[split+'_sequences'] += 1; c[split+'_supervised_tokens'] += supervised
            effective[bank] += weighted
    for group,splits in group_splits.items():
        if len(splits) != 1: fail('SOURCE_GROUP_CROSSES_SPLIT', group)
    for source,splits in source_splits.items():
        if len(splits) != 1: fail('SOURCE_ID_CROSSES_SPLIT', source)
    for key,value in observed.items():
        if report['counts'].get(key) != value: fail('REPORT_COUNTER_MISMATCH_'+key)
    for bank,counter in banks.items():
        for key,value in counter.items():
            if report['banks'].get(bank, {}).get(key) != value: fail('BANK_COUNTER_MISMATCH_'+key, bank)
    result = {'schema_version':'wrd-v10-independent-compiled-data-qa',
              'status':'PASS' if not errors else 'FAIL', 'counts':dict(counts), 'first_errors':errors,
              'actual_recount':dict(observed), 'weighted_supervised_token_equivalents_by_bank':dict(effective),
              'distinct_source_groups':len(group_splits), 'distinct_business_sources':len(source_splits),
              'tokenizer_checks':tokenizer_proof, 'weights_loaded':False, 'training_started':False,
              'semantic_annotation_validity_not_inferred_from_token_checks':True,
              'script_sha256':digest(Path(__file__)), 'compiled_report_sha256':digest(root/'COMPILATION_REPORT.json')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled', type=Path, default=ROOT/'output/20261027_wrd_main_v10/compiled')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--skip-retokenization', action='store_true')
    args = parser.parse_args(); result = check(args.compiled, not args.skip_retokenization)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status':result['status'],'counts':result['counts']},ensure_ascii=False))
    if result['status'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__': main()
