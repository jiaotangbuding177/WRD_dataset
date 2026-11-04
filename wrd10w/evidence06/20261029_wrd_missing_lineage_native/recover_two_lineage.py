"""Offline identity/metadata recovery only; no protected source-text inspection."""
from pathlib import Path
from collections import Counter, defaultdict
import gzip, hashlib, json, re, shutil

ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).resolve().parent
V9=ROOT/'output/20261026_wrd_dataset_v9'
ARCHIVE=ROOT/'output/20261025_wrd_training_dataset/bundle/archive'
SCOPE=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def safe_file(p):
    p=Path(p)
    assert not any(x.lower() in {'private','.git','.ssh','sdk_traces','sdk-traces'} for x in p.parts)
    assert p.suffix.lower() not in {'.key','.db','.sqlite','.sqlite3'}
    for q in [p,*p.parents]:
        assert not q.is_symlink() and not (hasattr(q,'is_junction') and q.is_junction())
    return p
def pin(p):
    p=safe_file(p)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(p,expected=None):
    p=safe_file(p)
    if not p.is_file():return {'path':str(p),'exists':False}
    r=dict(pin(p),exists=True)
    if expected:r['exact_expected_SHA']=r['sha256']==expected
    return r
def save(name,data):
    p=DEST/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return pin(p)

def main():
    selected=json.loads((DEST/'SELECTED_METADATA_01.json').read_text(encoding='utf-8'))
    scope={r['source_id']:r for r in rows(SCOPE)}
    eps={r['episode_id']:r for r in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    produced=list(rows(V9/'outcomes/recomputed_scope_overlay/produced_versions.jsonl.gz'))
    reverse=defaultdict(list)
    for v in produced:
        for f in v.get('files',[]):
            reverse[f['sha256']].append({'episode_id':v['episode_id'],'catalog_route_id':v.get('catalog_route_id'),
              'relative_path':f['relative_path'],'original_path':f.get('physical_original_path'),
              'native':eps.get(v['episode_id'],{}).get('source_native'),
              'original_episode_source_ids_metadata':eps.get(v['episode_id'],{}).get('old_episode_source_ids_metadata',[])})
    out={'schema':'wrd-selected-two-lineage-identity-recovery-v1','status':'IDENTITY_AND_METADATA_ONLY_NO_TRAINING_ADMISSION',
      'scope_pin':pin(SCOPE),'episodes':{},'protected_business_bodies_inspected':False,
      'source_or_bank_modified':False,'new_native_calls':0,'training_started':False}
    known_meta=[]
    for e,v in selected['episodes'].items():
        ep=v['episodes'][0]['row']; held=[x['row'] for x in v['targets'] if x['row']['source_admission']=='HOLD_MISSING_EVIDENCE']
        ids=sorted({s for r in held for s in r['source_ids']})
        result={'route_id':ep['route_id'],'held_targets':len(held),'held_target_ids':[r['id'] for r in held],
          'held_target_indices':[r['source_message_index'] for r in held],
          'business_source_classification':{s:scope.get(s,{}).get('status','UNKNOWN') for s in ids},
          'native_carriers':[check(ep['source_original_path'],ep['source_native']['sha256']),check(ep['source_native']['path'],ep['source_native']['sha256'])],
          'resource_identities':[],'actual_tool_call_metadata':[]}
        unique={}
        for entry in v['resources']:
            r=entry['row']; f=r.get('file_identity'); key=(r['native_path'],(f or {}).get('sha256'))
            unique.setdefault(key,{'native_path':r['native_path'],'expected_identity':f,
              'observation_message_indices':[],'unknown_reasons':set(),'scope_proof_ids':[],
              'source_ids':set(),'prior_original_write_producers':[]})
            q=unique[key];q['observation_message_indices'].append(r['observed_after_assistant_message_index'])
            q['unknown_reasons'].update(r['unknown_reasons']);q['source_ids'].update(r['source_ids'])
            q['scope_proof_ids'].append(r['scope_proof_id']);q['prior_original_write_producers']+=r['original_proven_producer_prefixes']
        for q in unique.values():
            q['unknown_reasons']=sorted(q['unknown_reasons']);q['source_ids']=sorted(q['source_ids'])
            f=q['expected_identity'];q['carriers']=[]
            if f:
                for p in dict.fromkeys([f.get('source_path'),str(ARCHIVE/f['object'])] if f.get('object') else [f.get('source_path')]):
                    if p:q['carriers'].append(check(p,f['sha256']))
                q['all_metadata_final_tree_same_SHA_candidates_not_prior_producer_proof']=reverse.get(f['sha256'],[])
            result['resource_identities'].append(q)
        with Path(ep['source_original_path']).open('rt',encoding='utf-8-sig') as f:
            mi=-1
            for line_no,line in enumerate(f,1):
                ev=json.loads(line);m=ev.get('message')
                if not isinstance(m,dict):continue
                mi+=1
                if m.get('role')!='assistant':continue
                for c in m.get('content',[]):
                    if not isinstance(c,dict) or c.get('type')!='toolCall':continue
                    a=c.get('arguments',{});a=json.loads(a) if isinstance(a,str) else a
                    command=a.get('command','')
                    q={'message_index':mi,'event_line':line_no,'tool_call_id':c.get('id'),'tool_name':c.get('name'),
                      'argument_keys':list(a),'message_sha256':hashlib.sha256(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
                    if c.get('name') in {'read','cat'}:q['read_path']=a.get('path',a.get('file_path'))
                    if command:
                        q['command_sha256']=hashlib.sha256(command.encode()).hexdigest()
                        q['static_native_path_references']=sorted(set(re.findall(r'/workspace/[A-Za-z0-9_./$*{}:-]+',command)))
                        if 'read_source.py' in command:q['actual_source_reader_command']=command
                    result['actual_tool_call_metadata'].append(q)
        result['identity_coverage']={'unique_resources':len(unique),'exact_identity':sum(q['expected_identity'] is not None for q in unique.values()),
          'missing_identity':sum(q['expected_identity'] is None for q in unique.values()),
          'at_least_one_matching_carrier':sum(any(c.get('exact_expected_SHA') for c in q['carriers']) for q in result['resource_identities'])}
        out['episodes'][e]=result
    # Explicit metadata files; no conversation bodies or user_only_inputs are opened.
    html=Path('E:/skillloop_runs/w10/native_episodes/teaching-html-demo__make1/workspace/inputs')
    docx=Path('E:/skillloop_runs/workflow_library/make__docx-standardize-export/attempt_2/workspace/inputs')
    for p in [html/n for n in ['making_lineage.json','route_card.json','making_input_index.json','making_contract.json','source_bindings.json','reusable_packages.json','resource_catalog.json']]+[docx/n for n in ['previous.json','route.json','sources.json','reusable.json']]:
        p=safe_file(p);r=json.loads(p.read_text(encoding='utf-8-sig'));b=p.read_bytes();s=hashlib.sha256(b).hexdigest()
        op=DEST/'metadata_objects'/s;op.parent.mkdir(exist_ok=True)
        if not op.exists():op.write_bytes(b)
        assert sha(op)==s
        known_meta.append({'source':pin(p),'copied_exact_metadata':pin(op),'json':r})
    out['explicit_metadata_files']=known_meta
    out['previous_attempt_native_metadata']=[r for r in eps.values() if 'make__docx-standardize-export' in r.get('source_original_path','') and 'attempt_1' in r.get('source_original_path','')]
    receipt=save('TWO_EPISODE_IDENTITY_RECOVERY_01.json',out)
    print(json.dumps({'receipt':receipt,'counts':{e:r['identity_coverage'] for e,r in out['episodes'].items()},'metadata_copies':len(known_meta)}))

if __name__=='__main__':main()
