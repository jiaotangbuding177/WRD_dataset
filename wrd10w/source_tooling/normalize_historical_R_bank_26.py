"""Normalize already dual-token-verified R records without changing a token.

This writes a standard explicit bank, preserving the old candidate and flags.
Root semantic admission is a separate receipt; no training or Agent is run.
"""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
SOURCE = OUT / 'historical_v6_reasoning_review_01/combined26_peer_refined_01'
DEST = OUT / 'compiled/historical_semantic_R_26_01'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    assert not DEST.exists()
    source = SOURCE / 'candidate_R_only.jsonl.gz'
    complete = load(SOURCE / 'COMPLETE.json')
    assert sha(source) == complete['candidate_sha256']
    assert load(SOURCE / 'INDEPENDENT_TOKEN_QA.json')['status'] == 'PASS'
    with gzip.open(source, 'rt', encoding='utf-8') as handle:
        records = [json.loads(line) for line in handle]
    assert len(records) == 26
    scopes = {r['source_id']: r for r in
              (json.loads(line) for line in gzip.open(OUT / 'clean_inputs/source_scope.metadata.jsonl.gz', 'rt', encoding='utf-8'))}
    DEST.mkdir(parents=True)
    shard_paths = {}
    shard_handles = {}
    counts = Counter()
    token_keys = {'input_ids', 'supervision_spans', 'targets', 'total_tokens', 'supervised_tokens',
                  'supervised_tokens_by_component', 'input_ids_sha256_u32le', 'supervision_spans_sha256',
                  'rendered_sha256', 'assistant_generation_spans', 'second_tokenizer_independently_called',
                  'tokenizer_pair_proof', 'label_definition', 'label_ignore_index'}
    with ExitStack() as stack:
        for original in records:
            assert original['root_main_admission'] is False
            assert original['split'] == 'train' and original['total_tokens'] <= 32768
            assert all(scopes[s]['status'] == 'TRAIN' for s in original['source_ids'])
            assert set(original['supervised_tokens_by_component']) == {'R'}
            assert original['old_ActionProposal_JSON_output_loss'] == 0
            record = deepcopy(original)
            metadata = {k: v for k, v in original.items() if k not in token_keys | {'messages', 'tools'}}
            metadata.update(owner_id='historical_R:' + original['canonical_original_response_owner'],
                            supervision_message_indices=[len(original['messages']) - 1],
                            message_loss_mask=[0] * (len(original['messages']) - 1) + [1],
                            source_admission='ADMIT', training_admitted=True,
                            source_candidate_sha256=sha(source),
                            source_candidate_record_sha256=hashlib.sha256(
                                json.dumps(original, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
                            root_main_admission=False,
                            canonical_original_response_owner=original['canonical_original_response_owner'],
                            requires_external_root_admission=True)
            record.update(schema_version='wrd-verified-main-v10', bank='historical_semantic_R_main',
                          original_record_metadata=metadata, training_started=False)
            assert all(record[k] == original[k] for k in token_keys)
            assert record['messages'] == original['messages'] and record['tools'] == original['tools']
            bucket = '16k' if record['total_tokens'] <= 16384 else '32k'
            name = 'historical_semantic_R_main.train.' + bucket + '.jsonl.gz'
            if name not in shard_handles:
                shard_paths[name] = DEST / name
                shard_handles[name] = stack.enter_context(gzip.open(shard_paths[name], 'wt', encoding='utf-8', newline='\n'))
            shard_handles[name].write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
            counts['sequences'] += 1
            counts['targets'] += 1
            counts['input_tokens'] += record['total_tokens']
            counts['supervised_tokens'] += record['supervised_tokens']
            counts['component_R'] += record['supervised_tokens']
            counts['le16k_sequences'] += record['total_tokens'] <= 16384
            counts['le32k_sequences'] += 1
            counts['16k_sequences' if record['total_tokens'] <= 16384 else '32k_sequences'] += 1
            counts['train_sequences'] += 1
            counts['train_supervised_tokens'] += record['supervised_tokens']
    assert counts['input_tokens'] == 582457 and counts['supervised_tokens'] == 33153
    held = DEST / 'held.jsonl.gz'
    with gzip.open(held, 'wt', encoding='utf-8'):
        pass
    report = {'schema_version': 'wrd-v10-actual-token-compilation', 'counts': dict(counts),
              'files': [{'path': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in sorted(shard_paths.values())],
              'held_file': {'path': held.name, 'bytes': held.stat().st_size, 'sha256': sha(held)},
              'banks': {'historical_semantic_R_main': dict(counts)},
              'source_candidate': {'path': str(source), 'bytes': source.stat().st_size, 'sha256': sha(source)},
              'source_complete_sha256': sha(SOURCE / 'COMPLETE.json'),
              'independent_original_SSE_dual_token_QA_sha256': sha(SOURCE / 'INDEPENDENT_TOKEN_QA.json'),
              'no_input_target_label_weight_or_R_text_changed': True,
              'bank_wrapper_only_current_semantic_admission_is_external': True,
              'historical_condition_not_current_native_equivalence': True,
              'original_v6_or_other_revision_same_owners_not_to_be_loaded_twice': True,
              'model_weights_loaded': False, 'training_started': False,
              'script_sha256': sha(Path(__file__))}
    (DEST / 'COMPILATION_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DEST / 'CAUSAL_TEMPLATE.json').write_bytes((SOURCE / 'CAUSAL_TEMPLATE.json').read_bytes())
    print(json.dumps({'bank': str(DEST), **dict(counts), 'training_started': False}))


if __name__ == '__main__':
    main()
