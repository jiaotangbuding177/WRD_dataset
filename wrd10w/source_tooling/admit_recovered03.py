"""Normalize three independently reviewed banks without changing target bytes.

An explicit root acceptance file is mandatory. This never launches training.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261027_wrd_main_v10'
REC=OUT/'historical_v6_action_recovery_01'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':digest(p)}

SPECS={
    'style':('style_repair_01/native_projection_02','historical_style_repair_02','native_style.core7.compiled.jsonl.gz'),
    'helpers':('helpers_construction_01/native_projection_01','historical_helpers_construction_01','native_helpers.core7.compiled.jsonl.gz'),
    'oracle':('test_oracle_repair_01/native_projection_02','historical_test_oracle_repair_02','native_oracle.core7.compiled.jsonl.gz'),
}

def main(acceptance):
    accepted=load(acceptance)
    assert accepted['status']=='ROOT_ACCEPT_THREE_SCOPED_RECOVERIES_AFTER_INDEPENDENT_REVIEW'
    for name,(relative,bank,filename) in SPECS.items():
        proof=accepted['banks'][name]
        assert proof['approved'] is True
        for r in proof['required_files']:
            p=Path(r['path']);assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256']
        base=REC/relative;source=base/filename
        with gzip.open(source,'rt',encoding='utf-8') as f: rows=[json.loads(l) for l in f if l.strip()]
        assert len(rows)==1
        dest=OUT/'compiled'/bank;dest.mkdir(exist_ok=False)
        original=rows[0];row=deepcopy(original)
        structural={'input_ids','supervision_spans','targets','total_tokens','supervised_tokens','supervised_tokens_by_component',
                    'input_ids_sha256_u32le','supervision_spans_sha256','rendered_sha256','assistant_generation_spans',
                    'second_tokenizer_independently_called','tokenizer_pair_proof','label_definition','label_ignore_index',
                    'messages','tools','binary_arrays'}
        meta={k:deepcopy(v) for k,v in original.items() if k not in structural}
        meta.update(training_admitted=True,source_admission='ADMIT',root_main_admission=False,
                    requires_external_root_admission=True,original226=False,holdout12=False,
                    protected_sources_visible_prefix=False,owner_id=original['target_owner']['canonical_original_action_owner_id'])
        meta['supervision_message_indices']=[i for i,x in enumerate(meta['message_loss_mask']) if x]
        row['bank']=bank;meta['bank']=bank
        row['original_record_metadata']=meta
        row['schema_version']='wrd-verified-main-v10'
        for key in structural:
            if key in original: assert row[key]==original[key]
        assert row['total_tokens']<=16384
        fn=bank+'.train.16k.jsonl.gz'
        with gzip.open(dest/fn,'wt',encoding='utf-8',newline='\n') as f:
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        held=dest/'held.jsonl.gz'
        with gzip.open(held,'wt',encoding='utf-8'):pass
        counts={'sequences':1,'targets':1,'input_tokens':row['total_tokens'],'supervised_tokens':row['supervised_tokens'],
                '16k_sequences':1,'train_sequences':1,'train_supervised_tokens':row['supervised_tokens']}
        counts.update({'component_'+k:v for k,v in row['supervised_tokens_by_component'].items()})
        report={'schema_version':'wrd-main-v10-compiled-bank-v05','counts':counts,'banks':{bank:counts},
                'files':[{'path':fn,'bytes':(dest/fn).stat().st_size,'sha256':digest(dest/fn)}],
                'held_file':{'path':'held.jsonl.gz','bytes':held.stat().st_size,'sha256':digest(held)},
                'immutable_inputs':[pin(source),pin(base/'PORTABLE_SELECTION.json'),pin(acceptance)],
                'normalization_only_messages_ids_targets_spans_weights_unchanged':True,
                'new_functional_state_and_native_action_not_original_native_dispatch':True,
                'historical_R_scope':'RECORDED_CUMULATIVE_CONTIGUOUS_EXCERPT' if name=='oracle' else 'NEW_AUTHORED_CONCISE_R',
                'training_started':False,'script_sha256':digest(__file__)}
        save(dest/'COMPILATION_REPORT.json',report)
        (dest/'CAUSAL_TEMPLATE.json').write_bytes((base/'CAUSAL_TEMPLATE.json').read_bytes())
        rootproof={'schema':'wrd-root-scoped-historical-recovery-admission-v1',
                   'status':'ADMIT_SCOPED_HISTORICAL_RESOURCE_RECOVERY_WITH_EXPLICIT_NEW_INPUT',
                   'record_ids':[row['id']],'compilation_report_sha256':digest(dest/'COMPILATION_REPORT.json'),
                   'root_acceptance_sha256':digest(acceptance),'root_acceptance_path':str(acceptance.resolve()),
                   'independent_semantic_peer':proof['independent_semantic_peer'],
                   'original_or_new_R_and_action_origins':proof['origins'],
                   'scope':proof['scope'],'full_skill_quality_or_utility_approved':False,
                   'actual_native_dispatch':False,'training_started':False}
        save(dest/'ROOT_SEMANTIC_ADMISSION.json',rootproof)
        print(json.dumps({'bank':bank,**counts},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--acceptance',type=Path,required=True)
    main(p.parse_args().acceptance)
