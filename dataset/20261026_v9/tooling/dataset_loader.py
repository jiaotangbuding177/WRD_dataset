"""Read v9 arrays and reconstruct loss masks. Importing never starts training."""
from __future__ import annotations

import gzip
import json


def iter_features(path):
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        for line in handle:
            if not line.strip():continue
            row=json.loads(line)
            ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids)
            last=0
            for begin,end,component,weight in row['supervision_spans']:
                assert 0<=last<=begin<end<=len(ids) and 0<weight<=1
                labels[begin:end]=ids[begin:end];weights[begin:end]=[float(weight)]*(end-begin);last=end
            assert sum(label!=-100 for label in labels)==row['supervised_tokens']>0
            # Only these fields go to the model/loss. Outcome/provenance and
            # original_record metadata are never concatenated into its input.
            yield {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}


def collate(features, pad_token_id):
    if not features:raise ValueError('empty_batch')
    size=max(len(f['input_ids'])for f in features)
    batch={k:[] for k in ('input_ids','attention_mask','labels','loss_weights')}
    for f in features:
        n=size-len(f['input_ids'])
        for key,pad in [('input_ids',pad_token_id),('attention_mask',0),('labels',-100),('loss_weights',0.0)]:
            batch[key].append(f[key]+[pad]*n)
    return batch


def weighted_causal_loss(logits, labels, loss_weights):
    """For a future authorized trainer, with the causal shift applied once.

    Divide by the count of active labels, NOT the sum of weights: otherwise
    auxiliary .1/.05 weights cancel in a single-bank batch. This function does
    no model forward, optimizer step, device selection or trainer creation.
    """
    import torch.nn.functional as functional
    shift_logits=logits[:, :-1, :].contiguous()
    shift_labels=labels[:, 1:].contiguous()
    shift_weights=loss_weights[:, 1:].contiguous()
    valid=shift_labels.ne(-100)
    count=valid.sum()
    if not bool(count):raise ValueError('batch_has_no_supervised_next_token')
    losses=functional.cross_entropy(shift_logits.reshape(-1,shift_logits.size(-1)),shift_labels.reshape(-1),ignore_index=-100,reduction='none').view_as(shift_labels)
    return (losses*shift_weights*valid).sum()/count
