"""Combine explicit reviewed compiled reports without changing a retained row."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main(a):
 spec=importlib.util.spec_from_file_location('combine10_recount',ROOT/'research/data_prep/wrd_curation10/admit10.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert not a.out.exists();a.out.mkdir(parents=True)
 seen=set();buckets={'16k':[],'32k':[]};records=[];pins=[];templates=[]
 for reportpath in a.report:
  report=load(reportpath);templates.append(load(reportpath.parent/'CAUSAL_TEMPLATE.json'))
  pins.append(m.pin(reportpath))
  for ref in report['files']:
   for raw,r in m.raw_rows(m.verify_ref(reportpath.parent,ref)):
    assert r['id']not in seen;seen.add(r['id']);records.append(r)
    assert not r['original_record_metadata'].get('requires_exact_serialized_body_pruning_before_admission')
    buckets['16k'if r['total_tokens']<=16384 else'32k'].append(raw)
 geometry=[{k:v for k,v in t.items()if k!='independent_second_tokenizer_calls'}for t in templates]
 assert all(t==geometry[0]for t in geometry)
 files=[]
 for bucket,lines in buckets.items():
  if not lines:continue
  p=a.out/f'curation10.train.{bucket}.jsonl.gz';m.write_lines(p,lines);files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 template=dict(templates[0]);template['independent_second_tokenizer_calls']=sum(t['independent_second_tokenizer_calls']for t in templates);template['concatenation_tokenizer_calls']=0
 m.save(a.out/'CAUSAL_TEMPLATE.json',template)
 report=m.report_for(records,load(a.report[0]),files)
 with gzip.open(a.out/'held.jsonl.gz','wb'):pass
 report.update(status='ACTUAL_REVIEWED_COMPILED_UNION_PENDING_ROOT_FREEZE',source_compilation_reports=pins,
   held_file={'path':'held.jsonl.gz','bytes':(a.out/'held.jsonl.gz').stat().st_size,'sha256':sha(a.out/'held.jsonl.gz')},
   byte_preserved_uncompressed_rows=True,script_sha256=sha(__file__),new_tokenizer_calls_this_combine=0)
 m.save(a.out/'COMPILATION_REPORT.json',report)
 m.save(a.out/'ROW_ORIGIN_PINS.json',{'reports':pins,'record_ids':sorted(seen),'training_started':False})
 print(json.dumps({'counts':report['counts'],'report_sha256':sha(a.out/'COMPILATION_REPORT.json')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
