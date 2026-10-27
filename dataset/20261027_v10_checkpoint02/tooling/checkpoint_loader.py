"""Load only checkpoint active arrays. No model, optimizer or training runner."""
from array import array
from collections import Counter
import argparse,gzip,hashlib,json,sys
from pathlib import Path,PurePosixPath
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def js(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def active_paths(root):
 manifest=json.loads((root/'TRAINING_MANIFEST.json').read_text(encoding='utf-8'))
 if manifest['full_WRD_main_training_ready']is not False or manifest['training_started']is not False:raise ValueError('wrong_checkpoint_contract')
 for row in manifest['actual_train_files']:
  p=PurePosixPath(row['path'])
  if p.is_absolute()or'..'in p.parts or'\\'in row['path']:raise ValueError('unsafe_training_path')
  path=root.joinpath(*p.parts)
  if path.stat().st_size!=row['bytes']or digest(path)!=row['sha256']:raise ValueError('active_array_pin_mismatch')
  yield path
def iter_features(root):
 for path in active_paths(Path(root)):
  with gzip.open(path,'rt',encoding='utf-8')as f:
   for line in f:
    if not line.strip():continue
    row=json.loads(line);ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids);last=0
    for lo,hi,component,weight in row['supervision_spans']:
     if not 0<=last<=lo<hi<=len(ids)or not 0<weight<=1:raise ValueError('invalid_mask_span')
     labels[lo:hi]=ids[lo:hi];weights[lo:hi]=[float(weight)]*(hi-lo);last=hi
    if sum(x!=-100 for x in labels)!=row['supervised_tokens']or len(ids)>32768:raise ValueError('mask_or_length_mismatch')
    yield {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}
def verify(root):
 root=Path(root);manifest=json.loads((root/'TRAINING_MANIFEST.json').read_text(encoding='utf-8'));counts=Counter();seen=set();samples=[]
 for path in active_paths(root):
  with gzip.open(path,'rt',encoding='utf-8')as f:
   for line in f:
    if not line.strip():continue
    row=json.loads(line);ids=row['input_ids'];data=array('I',ids)
    if sys.byteorder!='little':data.byteswap()
    if row['id']in seen:raise ValueError('duplicate_active_owner')
    seen.add(row['id'])
    if hashlib.sha256(data.tobytes()).hexdigest()!=row['input_ids_sha256_u32le']:raise ValueError('ids_hash_mismatch')
    if hashlib.sha256(js(row['supervision_spans']).encode()).hexdigest()!=row['supervision_spans_sha256']:raise ValueError('mask_hash_mismatch')
    spans=[]
    for target in row['targets']:spans.extend(target['owned_supervision_spans'])
    if spans!=row['supervision_spans']:raise ValueError('owner_global_mask_mismatch')
    counts['sequences']+=1;counts['input_tokens']+=len(ids);counts['supervised_tokens']+=row['supervised_tokens']
    for component,value in row['supervised_tokens_by_component'].items():counts['component_'+component]+=value
    counts['le16k_sequences']+=len(ids)<=16384;counts['le32k_sequences']+=len(ids)<=32768
 for feature in iter_features(root):
  n=sum(value!=-100 for value in feature['labels']);counts['loader_supervised_tokens']+=n;counts['loader_sequences']+=1
  if any((label==-100)!=(weight==0)for label,weight in zip(feature['labels'],feature['loss_weights'])):raise ValueError('labels_weights_disagree')
  if len(samples)<2:samples.append(feature)
 for key in ('sequences','input_tokens','supervised_tokens','le16k_sequences','le32k_sequences','component_F','component_D','component_R'):
  if counts[key]!=manifest['actual_counts'][key]:raise ValueError('manifest_counter_mismatch_'+key)
 if counts['loader_supervised_tokens']!=counts['supervised_tokens']or counts['loader_sequences']!=counts['sequences']:raise ValueError('loader_counter_mismatch')
 if len(samples)==2:
  maximum=max(len(x['input_ids'])for x in samples)
  for sample in samples:
   n=maximum-len(sample['input_ids']);labels=sample['labels']+[-100]*n;weights=sample['loss_weights']+[0.0]*n
   if any(x!=-100 for x in labels[len(sample['input_ids']):])or any(weights[len(sample['input_ids']):]):raise ValueError('pad_has_loss')
 return {'status':'PASS','counts':dict(counts),'only_manifest_active_arrays_loaded':True,'old_431_645_and_v9_not_loaded':True,'weights_loaded':False,'training_started':False,'full_WRD_main_training_ready':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);args=p.parse_args();print(json.dumps(verify(args.root)))
if __name__=='__main__':main()
