"""Normalize reviewed CV arrays; never change original messages or target ids.

The length-limited response receives the standard explicit prefix metadata,
not a fabricated EOS. Semantic admission remains a separate root receipt.
"""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from array import array
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
SOURCE = OUT / 'native_CV_B_training_01'
DEST = OUT / 'compiled/native_CV_B_partial_01'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    selected = load(SOURCE / 'PORTABLE_SELECTION.json')['default_core32_data']
    source = SOURCE / selected['path']
    assert sha(source) == selected['sha256']
    assert load(SOURCE / 'ACTUAL_BINARY_READBACK_QA.json')['status'].startswith('PASS')
    with gzip.open(source, 'rt', encoding='utf-8') as handle:
        originals = [json.loads(line) for line in handle]
    assert len(originals) == 21
    template_path = OUT / 'compiled/native_B_partial_01/CAUSAL_TEMPLATE.json'
    template_info = load(template_path)
    template = _compile_jinja_template(template_info['variant'])
    tokenizer = AutoTokenizer.from_pretrained(
        ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets/primary_14b',
        local_files_only=True, trust_remote_code=False)
    assert not DEST.exists()
    DEST.mkdir(parents=True)
    counter, components, handles, paths = Counter(), Counter(), {}, {}
    with ExitStack() as stack:
        for original in originals:
            row = deepcopy(original)
            meta = row['original_record_metadata']
            meta['owner_id'] = meta['canonical_response_owner']
            meta['requires_external_root_admission'] = True
            if row.get('view') == 'ORIGINAL_LENGTH_LIMITED_RESPONSE_EXACT_REVIEWED_TOKEN_PREFIX_NO_EOS':
                kwargs = dict(tokenizer.special_tokens_map)
                kwargs['enable_thinking'] = False
                rendered = template.render(messages=row['messages'], tools=row['tools'], documents=None,
                                           add_generation_prompt=False, **kwargs)
                complete_ids = tokenizer(rendered, add_special_tokens=False)['input_ids']
                assert complete_ids[:row['total_tokens']] == row['input_ids']
                assert len(complete_ids) == row['full_template_tokens_before_prefix']
                assert hashlib.sha256(rendered.encode()).hexdigest() == row['full_template_rendered_sha256_before_prefix']
                binary = array('I', complete_ids)
                if sys.byteorder != 'little':
                    binary.byteswap()
                row.update(view='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION',
                           complete_rendered_tokens=len(complete_ids),
                           complete_input_ids_sha256_u32le=hashlib.sha256(binary.tobytes()).hexdigest(),
                           complete_rendered_sha256=hashlib.sha256(rendered.encode()).hexdigest())
                meta['allow_reviewed_completion_prefix'] = True
            for key in ('messages', 'tools', 'input_ids', 'targets', 'supervision_spans', 'total_tokens',
                        'supervised_tokens', 'supervised_tokens_by_component', 'rendered_sha256'):
                assert row[key] == original[key]
            bucket = '16k' if row['total_tokens'] <= 16384 else '32k'
            name = row['bank'] + '.train.' + bucket + '.jsonl.gz'
            if name not in handles:
                paths[name] = DEST / name
                handles[name] = stack.enter_context(gzip.open(paths[name], 'wt', encoding='utf-8', newline='\n'))
            handles[name].write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            counter.update(sequences=1, targets=1, input_tokens=row['total_tokens'],
                           supervised_tokens=row['supervised_tokens'], train_sequences=1,
                           train_supervised_tokens=row['supervised_tokens'])
            counter[bucket + '_sequences'] += 1
            components.update(row['supervised_tokens_by_component'])
    counter.update({'component_' + k: v for k, v in components.items()})
    assert counter['input_tokens'] == 376848 and counter['supervised_tokens'] == 6469
    held = DEST / 'held.jsonl.gz'
    with gzip.open(held, 'wt', encoding='utf-8'):
        pass
    report = {'schema_version': 'wrd-v10-actual-token-compilation', 'counts': dict(counter),
              'banks': {'native_CV_B_training_01': dict(counter)},
              'files': [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(paths.values())],
              'held_file': {'path': held.name, 'bytes': held.stat().st_size, 'sha256': sha(held)},
              'source_compiled_candidate': {'path': str(source), **selected},
              'all_token_ids_labels_weights_messages_and_tools_unchanged': True,
              'prefix_standard_metadata_only_no_new_stop': True,
              'source_binary_QA_sha256': sha(SOURCE / 'ACTUAL_BINARY_READBACK_QA.json'),
              'model_weights_loaded': False, 'training_started': False, 'script_sha256': sha(Path(__file__))}
    (DEST / 'COMPILATION_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DEST / 'CAUSAL_TEMPLATE.json').write_bytes(template_path.read_bytes())
    print(json.dumps(dict(counter)))


if __name__ == '__main__':
    main()
